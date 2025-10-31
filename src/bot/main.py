import sqlite3
import discord
import google.generativeai as genai
import os
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


def _get_or_create_chat_session(user_id):
    """
    [FUNÇÃO HELPER] Verifica o dicionário global 'user_chats' e retorna uma sessão de chat.
    Cria uma nova sessão se o usuário for novo.
    """
    global user_chats
    if user_id not in user_chats:
        user_chats[user_id] = model.start_chat(history=[])
    
    return user_chats[user_id]


def _gerar_pedacos_mensagem(texto_restante, prefixo_pergunta, prefixo_resposta, limite_mensagem=1980):
    """
    [FUNÇÃO HELPER] Fatia o texto em pedaços de mensagem.
    Esta é uma função "geradora" (generator), que entrega um pedaço de cada vez.
    Sua complexidade é baixa.
    """
    is_first_message = True
    
    while len(texto_restante) > 0:
        if is_first_message:
            limite_real = limite_mensagem - len(prefixo_pergunta) - len(prefixo_resposta)
            prefixo_atual = prefixo_pergunta + prefixo_resposta
        else:
            limite_real = limite_mensagem
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
        
        yield parte_para_enviar
        is_first_message = False


async def _enviar_pedaco_discord(target, texto, is_first):
    """
    [FUNÇÃO HELPER] Envia a mensagem para o Discord,
    tratando 'interaction', 'message' (reply) ou 'channel.send'.
    Sua complexidade é baixa.
    """
    if is_first:
        if isinstance(target, discord.Interaction):
            await target.followup.send(texto)
        elif isinstance(target, discord.Message):
            await target.reply(texto)
    else:
        await target.channel.send(texto)


async def send_skaven_response(target, pergunta, response_text):
    """
    Processa e envia a resposta do Gemini de forma paginada. (Refatorada)
    'target' pode ser 'interaction' (para /perguntar) ou 'message' (para @menção).
    Esta função agora só orquestra e sua complexidade é baixíssima.
    """
    is_first_message = True
    
    if isinstance(target, discord.Interaction):
        prefixo_pergunta = f"**Pergunta do Pele-Lisa:**\n> {pergunta}\n\n"
        prefixo_resposta = "**Resposta-Genial:**\n"
    else:
        prefixo_pergunta = ""
        prefixo_resposta = ""

    try:
        for pedaco in _gerar_pedacos_mensagem(response_text, prefixo_pergunta, prefixo_resposta):
            await _enviar_pedaco_discord(target, pedaco, is_first=is_first_message)
            is_first_message = False

    except Exception as e:
        print(f"ERRO-FALHA! Ocorreu um erro: {e}")
        error_message = "Não-não! Meu cérebro-motor falhou-fritou! Tente-tente de novo, rápido-rápido... talvez-seja um plano-trama dos outros clãs!"

        await _enviar_pedaco_discord(target, error_message, is_first=is_first_message)


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
    print('Comandos sincronizados! Bot-gênio pronto-pronto, sim-sim!')


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

                chat_session = _get_or_create_chat_session(message.author.id)
                response = chat_session.send_message(prompt_para_gemini)

                await send_skaven_response(message, pergunta_limpa, response.text)

            except Exception as e:
                print(f"ERRO-FALHA na resposta por menção: {e}")
                await message.channel.send("Não-não! Meu cérebro-motor falhou-fritou ao tentar-tentar responder sua menção! A trama-plano falhou!")  
                

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

    chat_session = _get_or_create_chat_session(interaction.user.id)
    response = chat_session.send_message(pergunta)
    await send_skaven_response(interaction, pergunta, response.text)


@tree.command(name="limpar-memoria", description="[MESTRE] Limpa-apaga meu histórico de chat com o bot.")
async def limpar_memoria(interaction: discord.Interaction):
    """
    [COMANDO DE MESTRE] Limpa o histórico de chat do usuário que executou o comando.
    Verifica se o usuário é o 'Mestre Supremo' definido no .env.
    """

    if interaction.user.id != MESTRE_SUPREMO_ID:
        await interaction.response.send_message(
            "Tolo-tolo! Você-você não é o Mestre-Supremo! Não-não pode-tocar minha mente-memória!",
            ephemeral=True
        )
        return

    user_id = interaction.user.id
    
    if user_id in user_chats:
        del user_chats[user_id]
        await interaction.response.send_message(
            "Sim-sim, Mestre! Minhas memórias-lembranças de nossa última trama-conversa foram... *esquecidas*. Estou-pronto para um novo-plano!",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "Mestre, nós-nós nem-nem começamos uma trama-conversa ainda! Minha mente-memória já está-limpa!",
            ephemeral=True
        )


print("Iniciando o bot-gênio...")
client.run(DISCORD_TOKEN)