# bot.py
import os

from discord.ext import commands
from discord import Embed, Color
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
PREFIX = '$'

bot = commands.Bot(command_prefix=PREFIX)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

@bot.command(help='Says Hello!')
async def hello(ctx):
    await ctx.send('Hello!')

@bot.command(aliases=('update', 'u'), help='runs an osu!track update')
async def ameo_update(ctx, uid):
    AMEO_API_ENDPOINT = 'https://osutrack-api.ameo.dev/'
    METHOD = 'update'
    r = requests.post(f'{AMEO_API_ENDPOINT}{METHOD}', params = {'user': uid, 'mode': 0}).json()
    updateEmbed = Embed(
        title=f'osu!track update for {r["username"]}',
        type='rich',
        color=Color.from_rgb(255, 165, 0),
        description=f'[osu! profile](https://osu.ppy.sh/users/{uid}) · [osu!track Profile](https://ameobea.me/osutrack/user/{r["username"]})\n\
        **Rank**: {format_diff(r["pp_rank"])}\n\
        **PP**: {format_diff(round(r["pp_raw"], 4))}\n\
        **Playcount**: {r["playcount"]}\n\
        **Acc**: {format_diff(r["accuracy"])}\n\n\
        **New Highscores**\n\
        {chr(10).join(map(format_hs, r["newhs"]))}'
    )
    await ctx.send(embed=updateEmbed)

def format_hs(hs):
    acc = (hs["count50"] + 2 * hs["count100"] + 6 * hs["count300"]) / (hs["countmiss"] + hs["count50"] + hs["count100"] + hs["count300"])
    return f'**#{hs["ranking"]}**: [beatmap](https://osu.ppy.sh/b/{hs["beatmap_id"]}) | {hs["rank"]} {acc} | {hs["pp"]}pp'

def format_diff(d):
    if d > 0:
        return f'+{str(d)}'
    else:
        return str(d)

bot.run(TOKEN)