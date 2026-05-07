import os
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import pyotp

TOKEN = os.getenv("TOKEN")

CANAL_ID = 1501956404750192723

intents = discord.Intents.all()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

user_secrets = {}

class SecretModal(Modal, title="Adicionar chave 2FA"):

    secret = TextInput(
        label="Sua chave 2FA",
        placeholder="Cole sua chave aqui",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):

        secret_value = str(self.secret)

        user_secrets[interaction.user.id] = secret_value

        totp = pyotp.TOTP(secret_value)
        codigo = totp.now()

        await interaction.response.send_message(
            f"✅ Chave salva com sucesso.\n\n🔐 Código 2FA: `{codigo}`",
            ephemeral=True,
            delete_after=30
        )

class PanelView(View):

    @discord.ui.button(
        label="Adicionar chave",
        style=discord.ButtonStyle.green,
        emoji="🔑"
    )
    async def add_secret(
        self,
        interaction: discord.Interaction,
        button: Button
    ):
        await interaction.response.send_modal(
            SecretModal()
        )

@bot.event
async def on_ready():

    print(f"Logado como {bot.user}")

    canal = bot.get_channel(CANAL_ID)

    if canal:

        embed = discord.Embed(
            title="🔐 Painel 2FA",
            description=(
                "Clique no botão abaixo para adicionar "
                "sua chave 2FA e gerar o código automaticamente."
            ),
            color=0x5865F2
        )

        await canal.send(
            embed=embed,
            view=PanelView()
        )

bot.run(TOKEN)
