import sqlite3
import discord
import google.generativeai as genai
import os
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

ids_string = os.getenv('ID_CANAL_PERMITIDO')
ID_CANAL_PERMITIDO_LISTA = [int(id_str.strip()) for id_str in ids_string.split(',')]
MESTRE_SUPREMO_ID = int(os.getenv('MESTRE_SUPREMO_ID'))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
PROMPT_FILE_PATH = os.path.join(CONFIG_DIR, 'prompt.md')
BOT_CONFIG_PATH = os.path.join(CONFIG_DIR, 'bot_config.json')

try:
    with open(PROMPT_FILE_PATH, 'r', encoding='utf-8') as f:
        SYSTEM_PROMPT_STRING = f.read()
except FileNotFoundError:
    print(f"ERRO CRÍTICO: Arquivo de prompt '{PROMPT_FILE_PATH}' não encontrado!")
    SYSTEM_PROMPT_STRING = "Erro: Prompt não carregado."
except Exception as e:
    print(f"ERRO CRÍTICO ao carregar prompt do arquivo: {e}")
    SYSTEM_PROMPT_STRING = "Erro: Prompt inválido."

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
user_chats = {}

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

@bot.event
async def on_ready():
    """
    Executa quando o bot se conecta com sucesso ao Discord.
    Define o status de "Jogando" e sincroniza os comandos de barra.
    """
    print(f'Logado como {bot.user}!')
    status_jogo = discord.Game(name="O Rato Chifrudo mandou")
    await bot.change_presence(activity=status_jogo)
    print('Sincronizando comandos... (aguarde um instante)')
    await bot.tree.sync()
    print('Comandos sincronizados! Bot-gênio pronto-pronto, sim-sim!')

print("Iniciando o bot-gênio...")
bot.run(DISCORD_TOKEN)