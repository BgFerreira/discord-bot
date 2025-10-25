import discord
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ID_CANAL_PERMITIDO = int(os.getenv('ID_CANAL_PERMITIDO'))
SYSTEM_PROMPT_STRING = os.getenv('SYSTEM_PROMPT')

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

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

@client.event
async def on_ready():
    print(f'Logado como {client.user}!')
    print('Sincronizando comandos... (aguarde um instante)')
    await tree.sync()
    print(f'Comandos sincronizados! Bot-gênio pronto-pronto, sim-sim!')

@tree.command(name="perguntar", description="Faça uma pergunta-trama ao Grande Bot-Sábio!")
async def perguntar(interaction: discord.Interaction, pergunta: str):
    if interaction.channel.id != ID_CANAL_PERMITIDO:
        await interaction.response.send_message(
            f"Não-Não! Tolo-tolo! Use-me no canal <#{ID_CANAL_PERMITIDO}>, sim-sim! Rápido-rápido!",
            ephemeral=True
        )
        return
    
    await interaction.response.defer()

    try:
        chat_session = model.start_chat()
        response = chat_session.send_message(pergunta)        
        texto_restante = response.text
        is_first_message = True
        LIMITE_MSG = 1980

        while len(texto_restante) > 0:
            if len(texto_restante) <= LIMITE_MSG:
                parte_para_enviar = texto_restante
                texto_restante = ""
            else:
                ponto_de_quebra = texto_restante.rfind('\n', 0, LIMITE_MSG)
                if ponto_de_quebra == -1:
                    ponto_de_quebra = texto_restante.rfind(' ', 0, LIMITE_MSG)
                if ponto_de_quebra == -1:
                    ponto_de_quebra = LIMITE_MSG
                
                parte_para_enviar = texto_restante[:ponto_de_quebra]
                texto_restante = texto_restante[ponto_de_quebra:].lstrip()

            if is_first_message:
                await interaction.followup.send(parte_para_enviar)
                is_first_message = False
            else:
                await interaction.channel.send(parte_para_enviar)

    except Exception as e:
        print(f"ERRO-FALHA! Ocorreu um erro: {e}")

        if is_first_message:
            await interaction.followup.send("Não-não! Meu cérebro-motor falhou-fritou! Tente-tente de novo, rápido-rápido... talvez-seja um plano-trama dos outros clãs!")
        else:
            await interaction.channel.send("Não-não! Meu cérebro-motor falhou-fritou no meio-meio da resposta! A trama-plano falhou!")

print("Iniciando o bot-gênio...")
client.run(DISCORD_TOKEN)