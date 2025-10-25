import discord
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
SYSTEM_PROMPT_STRING = os.getenv('SYSTEM_PROMPT')

ids_string = os.getenv('ID_CANAL_PERMITIDO')
ID_CANAL_PERMITIDO_LISTA = [int(id_str.strip()) for id_str in ids_string.split(',')]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)
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

def get_or_create_chat_session(user_id):
    """
    Verifica o dicionário global 'user_chats' e retorna uma sessão de chat.
    Cria uma nova sessão se o usuário for novo.
    """
    global user_chats
    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])
    
    return user_chats[user_id]

async def send_skaven_response(target, pergunta, response_text):
    """
    Processa e envia a resposta do Gemini de forma paginada.
    'target' pode ser 'interaction' (para /perguntar) ou 'message' (para @menção).
    """
    is_first_message = True
    try:
        texto_restante = response_text
        LIMITE_MSG = 1980 
        if isinstance(target, discord.Interaction):
            prefixo_pergunta = f"**Pergunta do Pele-Lisa:**\n> {pergunta}\n\n"
            prefixo_resposta = "**Resposta-Genial:**\n"
        else:
            prefixo_pergunta = ""
            prefixo_resposta = ""


        while len(texto_restante) > 0:
            if is_first_message:
                limite_real = LIMITE_MSG - len(prefixo_pergunta) - len(prefixo_resposta)
                prefixo_atual = prefixo_pergunta + prefixo_resposta
            else:
                limite_real = LIMITE_MSG
                prefixo_atual = ""

            if len(texto_restante) <= limite_real:
                parte_para_enviar = prefixo_atual + texto_restante
                texto_restante = ""
            else:
                ponto_de_quebra = texto_restante.rfind('\n', 0, limite_real)
                if ponto_de_quebra == -1: ponto_de_quebra = texto_restante.rfind(' ', 0, limite_real)
                if ponto_de_quebra == -1: ponto_de_quebra = limite_real
                
                parte_para_enviar = prefixo_atual + texto_restante[:ponto_de_quebra]
                texto_restante = texto_restante[ponto_de_quebra:].lstrip()

            if is_first_message:
                is_first_message = False
                if isinstance(target, discord.Interaction):
                    await target.followup.send(parte_para_enviar)
                elif isinstance(target, discord.Message):
                    await target.reply(parte_para_enviar)
            else:
                await target.channel.send(parte_para_enviar)

    except Exception as e:
        print(f"ERRO-FALHA! Ocorreu um erro: {e}")
        error_message = "Não-não! Meu cérebro-motor falhou-fritou! Tente-tente de novo, rápido-rápido... talvez-seja um plano-trama dos outros clãs!"
        
        if is_first_message:
            if isinstance(target, discord.Interaction):
                await target.followup.send(error_message)
            elif isinstance(target, discord.Message):
                await target.reply(error_message)
        else:
            await target.channel.send("Não-não! Meu cérebro-motor falhou-fritou no meio-meio da resposta! A trama-plano falhou!")

@client.event
async def on_ready():
    """
    Executa quando o bot se conecta com sucesso ao Discord.
    Define o status de "Jogando" e sincroniza os comandos de barra.
    """
    print(f'Logado como {client.user}!')
    status_jogo = discord.Game(name="O Rato Chifrudo mandou")
    await client.change_presence(activity=status_jogo)
    print('Sincronizando comandos... (aguarde um instante)')
    await tree.sync()
    print(f'Comandos sincronizados! Bot-gênio pronto-pronto, sim-sim!')

@client.event
async def on_message(message):
    """
    Ouve por menções (@bot) nos canais permitidos.
    E também detecta "Respostas" (Replies) para dar contexto ao Gemini.
    """

    if message.author == client.user:
        return

    if message.channel.id not in ID_CANAL_PERMITIDO_LISTA:
        return
    
    if client.user.mentioned_in(message):
        pergunta_limpa = message.content.replace(f'<@{client.user.id}>', '').strip()
        if not pergunta_limpa:
            return

        async with message.channel.typing():
            try:
                prompt_para_gemini = pergunta_limpa
                if message.reference:
                    try:
                        original_message = await message.channel.fetch_message(message.reference.message_id)
                        if original_message.content:
                            prompt_para_gemini = f"""
                            O pele-lisa-tolo está-apontando para esta-outra mensagem de alguém:
                            '{original_message.content}'
                            
                            E agora-agora ele me pergunta-diz:
                            '{pergunta_limpa}'
                            
                            Responda-diga a ele-tolo, levando-o-o contexto em conta!
                            """
                    except Exception as e:
                        print(f"ERRO-FALHA ao buscar mensagem de referência: {e}")

                chat_session = get_or_create_chat_session(message.author.id)
                response = chat_session.send_message(prompt_para_gemini)

                await send_skaven_response(message, pergunta_limpa, response.text)
            
            except Exception as e:
                print(f"ERRO-FALHA na resposta por menção: {e}")
                await message.channel.send("Não-não! Meu cérebro-motor falhou-fritou ao tentar-tentar responder sua menção! A trama-plano falhou!")  
        return
                

@tree.command(name="perguntar", description="Faça uma pergunta-trama ao Grande Bot-Sábio!")
async def perguntar(interaction: discord.Interaction, pergunta: str):
    """O comando de barra (para testes e insígnia)."""
    
    if interaction.channel.id not in ID_CANAL_PERMITIDO_LISTA:
        await interaction.response.send_message(
            "Não-não! Tolo-tolo! Use-me apenas-só nos meus canais-covis designados!",
            ephemeral=True
        )
        return 
    
    await interaction.response.defer()

    chat_session = get_or_create_chat_session(interaction.user.id)
    response = chat_session.send_message(pergunta)
    await send_skaven_response(interaction, pergunta, response.text)

print("Iniciando o bot-gênio...")
client.run(DISCORD_TOKEN)