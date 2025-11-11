import discord
from discord.ext import commands
from discord import app_commands
import google.generativeai as genai

class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot, model: genai.GenerativeModel, config: dict):
        self.bot = bot
        self.model = model
        self.config = config
        self.user_chats = {} #remover com a adição do banco
    
    def _get_or_create_chat_session(self, user_id):
        """
        [FUNÇÃO HELPER] Verifica o dicionário global 'user_chats' e retorna uma sessão de chat.
        Cria uma nova sessão se o usuário for novo.
        """
        if user_id not in self.user_chats:
            self.user_chats[user_id] = self.model.start_chat(history=[])
        return self.user_chats[user_id]

    def _generate_message_parts(self, remaining_text, ask_prefix, response_prefix, message_limit=1980):
        """
        [FUNÇÃO HELPER] Fatia o texto em pedaços de mensagem.
        Esta é uma função "geradora" (generator), que entrega um pedaço de cada vez.
        """
        is_first_message = True 
        while len(remaining_text) > 0:
            if is_first_message:
                real_limit = message_limit - len(ask_prefix) - len(response_prefix)
                current_prefix = ask_prefix + response_prefix
            else:
                real_limit = message_limit
                current_prefix = ""

            if len(remaining_text) <= real_limit:
                part_to_send = current_prefix + remaining_text
                remaining_text = ""
            else:
                break_point = remaining_text.rfind('\n', 0, real_limit)
                if break_point == -1: break_point = remaining_text.rfind(' ', 0, real_limit)
                if break_point == -1: break_point = real_limit
                part_to_send = current_prefix + remaining_text[:break_point]
                remaining_text = remaining_text[break_point:].lstrip()  
            yield part_to_send
            is_first_message = False

    async def _send_message_part(self, target, text, is_first):
        """
        [FUNÇÃO HELPER] Envia a mensagem para o Discord,
        tratando 'interaction', 'message' (reply) ou 'channel.send'.
        """
        if is_first:
            if isinstance(target, discord.Interaction):
                await target.followup.send(text)
            elif isinstance(target, discord.Message):
                await target.reply(text)
        else:
            await target.channel.send(text)

    async def send_response(self, target, ask, response_text):
        """
        Processa e envia a resposta do Gemini de forma paginada. (Refatorada)
        'target' pode ser 'interaction' (para /perguntar) ou 'message' (para @menção).
        """
        is_first_message = True
        if isinstance(target, discord.Interaction):
            ask_prefix = f"**Pergunta do Coisa-Humana:**\n> {ask}\n\n"
            response_prefix = "**Minha resposta:**\n"
        else:
            ask_prefix = ""
            response_prefix = ""

        try:
            for part in self._generate_message_parts(response_text, ask_prefix, response_prefix):
                await self._send_message_part(target, part, is_first=is_first_message)
                is_first_message = False
        except Exception as e:
            print(f"ERROR: Failed to send message --> {e}")
            error_message = "Não-não! Meu cérebro-motor falhou-fritou! Tente-tente de novo, rápido-rápido... talvez-seja um plano-trama de outros ratos!"

            await self._send_message_part(target, error_message, is_first=is_first_message)

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Ouve por menções (@bot) nos canais permitidos.
        E também detecta "Respostas" (Replies) para dar contexto ao Gemini.
        """
        if message.author == self.bot.user:
            return

        if message.channel.id not in self.config['ALLOWED_CHANNELS_ID_LIST']:
            return

        if self.bot.user.mentioned_in(message):
            clean_ask = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            if not clean_ask:
                return

            async with message.channel.typing():
                try:
                    prompt_to_genai = clean_ask
                    if message.reference:
                        try:
                            original_message = await message.channel.fetch_message(message.reference.message_id)
                            if original_message.content:
                                prompt_to_genai = f"""
                                O coisa-homem está apontando para esta outra mensagem de alguém sim-sim:
                                '{original_message.content}'

                                E ele me pergunta-diz:
                                '{clean_ask}'

                                Responda-diga ao coisa-homem tolo-tolo, levando o contexto em conta! Sim-sim!
                                """
                        except Exception as e:
                            print(f"ERROR: Failed to search reference message --> {e}")
                    chat_session = self._get_or_create_chat_session(message.author.id)
                    response = chat_session.send_message(prompt_to_genai)
                    await self.send_response(message, clean_ask, response.text)
                except Exception as e:
                    print(f"ERROR: Failed to response by mention --> {e}")
                    await message.channel.send("Não-não! Meu cérebro-motor falhou-fritou ao tentar-tentar responder sua menção!")  

    @app_commands.command(name="perguntar", description="Faça uma pergunta-trama ao Grande Bot-Sábio!")
    async def ask(self, interaction: discord.Interaction, ask: str):
        """
        O comando de barra (para testes e insígnia).
        """
        if interaction.channel.id not in self.config['ALLOWED_CHANNELS_ID_LIST']:
            await interaction.response.send_message(
                "Não-não! Tolo-tolo! Use-me apenas-só nos meus canais-covis designados!",
                ephemeral=True
            )
            return

        await interaction.response.defer()
        chat_session = self._get_or_create_chat_session(interaction.user.id)
        response = chat_session.send_message(ask)
        await self.send_response(interaction, ask, response.text)


    @app_commands.command(name="limpar-memoria", description="Limpa-apaga minhas memórias-lembranças sobre nossos planos-tramas.")
    async def clean_memory(self, interaction: discord.Interaction):
        """
        Limpa o histórico de chat do usuário que executou o comando.
        """
        if interaction.user.id != self.config['BOT_MASTER_ID']:
            await interaction.response.send_message(
                "Tolo-tolo! Você-você não é o meu mestre! Não-não pode-tocar minha mente-memória!",
                ephemeral=True
            )
            return

        user_id = interaction.user.id
        if user_id in self.user_chats:
            del self.user_chats[user_id]
            await interaction.response.send_message(
                "Sim-sim, Mestre! Minhas memórias-lembranças de nossa última trama-conversa foram... *esquecidas*. Estou-pronto para um novo-plano!",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Mestre, nós-nós nem-nem começamos uma trama-conversa ainda! Minha mente-memória já está-limpa!",
                ephemeral=True
            )