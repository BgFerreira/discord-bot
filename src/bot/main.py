import discord
import google.generativeai as genai
import os
import json
import asyncio
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
PROMPT_FILE_PATH = os.path.join(CONFIG_DIR, 'prompt.md')
BOT_CONFIG_PATH = os.path.join(CONFIG_DIR, 'bot_config.json')

try:
    with open(PROMPT_FILE_PATH, 'r', encoding='utf-8') as f:
        SYSTEM_PROMPT_STRING = f.read()
    print("SYSTEM: Prompt loaded!")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to load prompt --> {e}")
    SYSTEM_PROMPT_STRING = "Prompt not loaded"

try:
    with open(BOT_CONFIG_PATH, 'r', encoding='utf-8') as f:
        CONFIG = json.load(f)
    print("SYSTEM: Config loaded!")
except Exception as e:
    print(f"CRITICAL ERROR: Failed to load config --> {e}")
    CONFIG = {}

genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
  "temperature": 1,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
]
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash-lite",
    safety_settings=safety_settings,
    generation_config=generation_config,
    system_instruction=SYSTEM_PROMPT_STRING
)
print("SYSTEM: GenAI loaded!")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def load_cogs():
    """
    Encontra e carrega todos os Cogs, injetando o model e o config.
    """
    cogs_path = os.path.join(BASE_DIR, 'cogs')
    for filename in os.listdir(cogs_path):
        if filename.endswith('.py') and not filename.startswith('__'):
            cog_name = filename[:-3]
            try:
                cog_module_path = f'src.bot.cogs.{cog_name}'
                await bot.load_extension(cog_module_path)

                extension = bot.extensions[cog_module_path]
                if hasattr(extension, 'setup'):
                    await extension.setup(bot, model=model, config=CONFIG)
            except Exception as e:
                print(f"ERROR: Failed to load cog {cog_name} --> {e}")

@bot.event
async def on_ready():
    """
    Executa quando o bot se conecta com sucesso ao Discord.
    Define o status de "Jogando" e sincroniza os comandos de barra.
    """
    print(f'Logged as {bot.user}!')
    status_jogo = discord.Game(name="VERMINTIDE 2")
    await bot.change_presence(activity=status_jogo)
    await bot.tree.sync()
    print('SYSTEM: Bot ready!')

async def main():
    async with bot:
        await load_cogs()
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    print("SYSTEM: Starting bot . . .")
    asyncio.run(main())