import os
import discord
from dotenv import load_dotenv
import database

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Adicionar intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = discord.Bot(intents=intents)

@bot.event
async def on_ready():
    print(f'Conectado como {bot.user}')
    print('------')
    print("Configurando o banco de dados...")
    database.setup_database()
    print("Banco de dados pronto.")

bot.load_extension('cogs.rpg_commands')

bot.run(TOKEN)