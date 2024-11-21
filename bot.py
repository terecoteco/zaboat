import discord
from discord.ext import commands
from yt_dlp import YoutubeDL
import asyncio
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Configuração do bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=None, intents=intents)
tree = bot.tree  # Atalho para comandos slash

# Fila de músicas
queues = {}

# Evento quando o bot estiver online
@bot.event
async def on_ready():
    await tree.sync()
    print(f"Bot conectado como {bot.user} e comandos slash sincronizados.")
    while True:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="suas música 🎶"))
        await asyncio.sleep(3)
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="/help"))
        await asyncio.sleep(3)
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Músicas no Discord 🎶🎶"))
        await asyncio.sleep(3)

# Obter URL de streaming de áudio do YouTube
def get_audio_stream(query):
    ydl_opts = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        if "youtube.com" in query or "youtu.be" in query:
            info = ydl.extract_info(query, download=False)
        else:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)["entries"][0]
        return info["url"], info["title"]

# Conectar ao canal de voz
async def connect_to_voice(interaction):
    if interaction.user.voice:
        voice_channel = interaction.user.voice.channel
        if not interaction.guild.voice_client:
            return await voice_channel.connect()
        return interaction.guild.voice_client
    else:
        await interaction.response.send_message("Você precisa estar em um canal de voz!", ephemeral=True)
        return None

# Manipular a fila
def handle_queue(guild_id):
    if guild_id in queues and queues[guild_id]:
        url, title = queues[guild_id].pop(0)
        vc = discord.utils.get(bot.voice_clients, guild__id=guild_id)
        if vc:
            vc.play(
                discord.FFmpegPCMAudio(source=url, executable="ffmpeg"),
                after=lambda e: handle_queue(guild_id),
            )

# Comando /play
@tree.command(name="play", description="Toca uma música do YouTube.")
async def play(interaction: discord.Interaction, query: str):
    await interaction.response.defer()  # Evita responder imediatamente

    vc = await connect_to_voice(interaction)
    if vc is None:
        return

    try:
        url, title = get_audio_stream(query)
    except Exception as e:
        await interaction.followup.send(f"Erro ao buscar a música: {e}")
        return

    if not vc.is_playing():
        vc.play(
            discord.FFmpegPCMAudio(source=url, executable="ffmpeg"),
            after=lambda e: handle_queue(interaction.guild.id),
        )
        await interaction.followup.send(f"Tocando: *{title}*")
    else:
        queues.setdefault(interaction.guild.id, []).append((url, title))
        await interaction.followup.send(f"Música *{title}* adicionada à fila.")

# Comando /skip
@tree.command(name="skip", description="Pula para a próxima música.")
async def skip(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()  # Ativa o `after` do player para pular
        await interaction.response.send_message("Música pulada!")
    else:
        await interaction.response.send_message("Nenhuma música está tocando no momento.")

# Comando /stop
@tree.command(name="stop", description="Para a música e limpa a fila.")
async def stop(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        queues[interaction.guild.id] = []
        await interaction.response.send_message("Música parada e fila limpa!")
    else:
        await interaction.response.send_message("Nenhuma música está tocando no momento.")

# Comando /pause
@tree.command(name="pause", description="Pausa a musica.")
async def pause(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await interaction.response.send_message("Música pausada!")
    else:
        await interaction.response.send_message("Nenhuma música está tocando no momento.")

# Comando /resume
@tree.command(name="resume", description="Continua a musica pausada.")
async def resume(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await interaction.response.send_message("Música resumida!")
    else:
        await interaction.response.send_message("Nenhuma musica pausada!")

# Comando /queue
@tree.command(name="queue", description="Mostra a fila de músicas.")
async def queue(interaction: discord.Interaction):
    if interaction.guild.id in queues and queues[interaction.guild.id]:
        queue_text = "Fila de músicas:\n"
        for url, title in queues[interaction.guild.id]:
            queue_text += f"- {title}\n"
        await interaction.response.send_message(queue_text)
    else:
        await interaction.response.send_message('A fila está vazia!')

# Comando /leave
@tree.command(name="leave", description="Sai do canal de voz.")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
        await interaction.response.send_message('Saindo do canal de voz...')
    else:
        await interaction.response.send_message('Não estou conectado a nenhum canal de voz!')

# Comando /ping
@tree.command(name="ping", description="Responde com 'Pong!'.")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

# Comando /help
@tree.command(name="help", description="Mostra os comandos disponíveis.")
async def help(interaction: discord.Interaction):
    help_text = """
**Comandos disponíveis:**
/play [música ou URL] - Toca uma música ou adiciona à fila.
/skip - Pula para a próxima música.
/stop - Para a música e limpa a fila.
/pause - Pausa a musica.
/resume - Continua a musica pausada.
/queue - Mostra a fila de informações.
/leave - Sai do canal de voz.
/ping - Responde com 'Pong!'.
/help - Mostra esta mensagem de ajuda.
    """
    await interaction.response.send_message(help_text, ephemeral=True)

# Rodar o bot
bot.run(TOKEN)