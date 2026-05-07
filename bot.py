import os
import json
import discord
import pyotp
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from dotenv import load_dotenv

# -----------------------------
# CONFIGURAÇÕES
# -----------------------------
load_dotenv()
TOKEN = os.getenv("TOKEN")

CANAL_2FA_ID = 1501956404750192723        # Canal do painel 2FA
VOICE_CHANNEL_ID = 1501974133268025585    # Canal de voz
TICKET_CHANNEL_ID = 1464253775295287326   # Canal principal de tickets/painel
TICKET_CATEGORY_ID = 1464253983924293765  # Categoria onde tickets são criados

PIX_CHAVE = "d2e273ed-dc6b-4dfd-8c6e-80794350699d"
QR_IMAGE_PATH = "qr.png"
PAINEL_FILE = "painel.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

user_secrets = {}

# -----------------------------
# FUNÇÕES DE PAINEL SAVE/LOAD
# -----------------------------
def load_painel():
    if os.path.exists(PAINEL_FILE):
        with open(PAINEL_FILE, "r") as f:
            return json.load(f)
    return {}

def save_painel(data):
    with open(PAINEL_FILE, "w") as f:
        json.dump(data, f)

# -----------------------------
# LIMPAR MENSAGENS DO BOT
# -----------------------------
async def limpar_mensagens_do_bot(canal_id):
    """Apaga todas as mensagens que o bot enviou no canal"""
    channel = bot.get_channel(canal_id)
    if channel:
        async for msg in channel.history(limit=None):
            if msg.author == bot.user:
                try:
                    await msg.delete()
                    print(f"Mensagem {msg.id} apagada.")
                except Exception as e:
                    print(f"Erro ao apagar mensagem {msg.id}: {e}")

# -----------------------------
# 2FA SYSTEM
# -----------------------------
class SecretModal(Modal, title="Adicionar chave 2FA"):

    secret = TextInput(
        label="Sua chave 2FA",
        placeholder="Cole sua chave aqui",
        required=True,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        secret_value = str(self.secret.value).strip().replace(" ", "").replace("\n", "")
        try:
            totp = pyotp.TOTP(secret_value)
            codigo = totp.now()
            user_secrets[interaction.user.id] = secret_value

            await interaction.response.send_message(
                f"✅ Chave salva!\n\n🔐 Código 2FA: `{codigo}`",
                ephemeral=True
            )
        except Exception:
            await interaction.response.send_message(
                "❌ Chave 2FA inválida.",
                ephemeral=True
            )

class PanelView2FA(View):

    @discord.ui.button(label="Adicionar chave 2FA", style=discord.ButtonStyle.green, emoji="🔑")
    async def add_secret(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(SecretModal())

# -----------------------------
# PIX SYSTEM
# -----------------------------
class PixView(View):

    @discord.ui.button(label="Copiar chave Pix", style=discord.ButtonStyle.primary, emoji="📋")
    async def copiar_chave(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            f"📋 **Chave Pix:**\n```{PIX_CHAVE}```",
            ephemeral=True
        )

# -----------------------------
# TICKET SYSTEM
# -----------------------------
class CloseTicketView(View):

    @discord.ui.button(label="Fechar Ticket", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("🔒 Fechando ticket...", ephemeral=True)
        await interaction.channel.delete()

class TicketView(View):

    @discord.ui.button(label="Abrir Ticket", style=discord.ButtonStyle.green, emoji="🎫")
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        user = interaction.user
        category = discord.utils.get(guild.categories, id=TICKET_CATEGORY_ID)

        existing_channel = None
        if category:
            for channel in category.text_channels:
                if channel.name.startswith(f"ticket-{user.name.lower()}"):
                    existing_channel = channel
                    break

        if existing_channel:
            channel = existing_channel
            # Apaga todas as mensagens antigas do ticket
            async for msg in channel.history(limit=None, oldest_first=True):
                try:
                    await msg.delete()
                except:
                    pass
        else:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                guild.owner: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
            }
            channel = await guild.create_text_channel(
                name=f"ticket-{user.name}".lower(),
                overwrites=overwrites,
                category=category
            )

        await channel.send(
            f"🎫 Ticket criado por {user.mention}\n👑 Dono do servidor: {guild.owner.mention}",
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"✅ Ticket aberto: {channel.mention}",
            ephemeral=True
        )

# -----------------------------
# BOT READY
# -----------------------------
@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")

    # --------- Limpar mensagens antigas do painel 2FA e canal de tickets ---------
    await limpar_mensagens_do_bot(CANAL_2FA_ID)
    await limpar_mensagens_do_bot(TICKET_CHANNEL_ID)

    # --------- Enviar painel 2FA ---------
    canal_2fa = bot.get_channel(CANAL_2FA_ID)
    if canal_2fa:
        embed = discord.Embed(
            title="🔐 Painel 2FA",
            description="Clique para adicionar sua chave 2FA.",
            color=0x5865F2
        )
        msg = await canal_2fa.send(embed=embed, view=PanelView2FA())
        save_painel({"message_id": msg.id})

    # --------- Painel de tickets ---------
    ticket_channel = bot.get_channel(TICKET_CHANNEL_ID)
    if ticket_channel:
        embed = discord.Embed(
            title="🎫 Sistema de Tickets",
            description="Clique no botão abaixo para abrir um ticket privado.",
            color=0x00ff00
        )
        await ticket_channel.send(embed=embed, view=TicketView())

    # --------- Entrar na call ----------
    try:
        voice_channel = await bot.fetch_channel(VOICE_CHANNEL_ID)
        vc = discord.utils.get(bot.voice_clients, guild=voice_channel.guild)
        if vc and vc.is_connected():
            await vc.move_to(voice_channel)
        else:
            await voice_channel.connect()
        print("Entrou na call.")
    except Exception as e:
        print(f"Erro na call: {e}")

# -----------------------------
# PIX COMMAND
# -----------------------------
@bot.command()
async def pix(ctx):
    file = discord.File(QR_IMAGE_PATH)
    await ctx.send(
        content="**Nome: Gabriel Cardoso Barboza**\n💰 Pagamento via Pix",
        file=file,
        view=PixView()
    )

# -----------------------------
# RUN BOT
# -----------------------------
bot.run("MTUwMTk1NDU0NDIxOTg0ODc5NA.G4-lr0.hSZxaQG3D2nnE1cRn9olmxAC-gtBOu0vX3lmQw")
