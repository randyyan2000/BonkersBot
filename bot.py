# bot.py
import os

from discord.ext import commands
from discord import Embed, Color
import requests
from dotenv import load_dotenv
import json

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OSU_API_KEY = os.getenv('OSU_API_KEY')

AMEO_API_ENDPOINT = 'https://osutrack-api.ameo.dev/'
OSU_API_ENDPOINT = 'https://osu.ppy.sh/api/'

PREFIX = '$'
EMBED_COLOR = Color.from_rgb(255, 165, 0)

bot = commands.Bot(command_prefix=PREFIX)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')


@bot.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise


@bot.command(help='Says Hello!')
async def hello(ctx):
    await ctx.send('Hello!')


@bot.command(aliases=('update', 'u'), help='runs an osu!track update for your registered profile (see $register) or a')
async def osu_update(ctx, uid=None):
    if not uid:
        uid = get_uid(ctx)
    
    if not uid:
        return await ctx.send(f'No osu profile set for user {reply_mention(ctx)}. You can register your osu profile using the $register command or specify an osu user id to update directly with $update <uid>.')

    response = requests.post(f'{AMEO_API_ENDPOINT}update', params = {'user': uid, 'mode': 0})
    if response.status_code != 200:
        if response.status_code == 400:
            return await ctx.send(f'Invalid update request, please make sure a valid user id was given/registered.')
        return await ctx.send('Something went wrong :(')
    print(response.text)
    r = response.json()
    print(r)
    updateEmbed = Embed(
        title=f'osu!track update for {r["username"]}',
        type='rich',
        color=Color.from_rgb(255, 165, 0),
        description=f'[osu! profile](https://osu.ppy.sh/users/{uid}) · [osu!track Profile](https://ameobea.me/osutrack/user/{r["username"]})\n\
        **Rank**: {format_diff(r["pp_rank"])}\n\
        **PP**: {format_diff(round(r["pp_raw"], 4))}\n\
        **Playcount**: {r["playcount"]}\n\
        **Acc**: {format_diff(r["accuracy"])}\n\n\
        **New Highscores**: {len(r["newhs"])}{" <:KEKW:805177941814018068>" if len(r["newhs"]) == 0 else ""}\n\
        {chr(10).join(map(format_hs, r["newhs"]))}'
    )
    updateEmbed.set_thumbnail(url=f'http://s.ppy.sh/a/{uid}')
    await ctx.send(embed=updateEmbed)


@bot.command(aliases=('register', 'r'), help='registers an osu account to your discord user so you don\'t have to specify a user when running updates')
async def osu_register(ctx, uid=None):
    if not uid:
        return await ctx.send('Please specify an osu profile id!')
    else:
        with open("uids.json", "r") as fp:
            uidMap = json.load(fp)
            uidMap[f'{ctx.author.id}'] = uid
        with open("uids.json", "w+") as fp:
            json.dump(uidMap, fp, sort_keys=True, indent=4)
            await ctx.send(f'User 40870022 registered to {reply_mention(ctx)}')


@bot.command(aliases=('t', 'test'), help='command used for testing during development')
async def dev_test(ctx):
    uid = 17626463
    r = json.load(open('test.json', 'r'))
    updateEmbed = Embed(
        title=f'osu!track update for {r["username"]}',
        type='rich',
        color=EMBED_COLOR,
        description=f'[osu! profile](https://osu.ppy.sh/users/{uid}) · [osu!track Profile](https://ameobea.me/osutrack/user/{r["username"]})\n\
        **Rank**: {format_diff(r["pp_rank"])}\n\
        **PP**: {format_diff(round(r["pp_raw"], 4))}\n\
        **Playcount**: {r["playcount"]}\n\
        **Acc**: {format_diff(round(r["accuracy"], 2))}\n\n\
        **New Highscores**: {len(r["newhs"])}{" <:KEKW:805177941814018068>" if len(r["newhs"]) == 0 else ""}\n\
        {chr(10).join(map(format_hs, r["newhs"]))}'
    )
    updateEmbed.set_thumbnail(url=f'http://s.ppy.sh/a/{uid}')
    await ctx.send(embed=updateEmbed)

    hsEmbeds = [await get_hs_embed(hs) for hs in r["newhs"]]
    for embed in hsEmbeds:
        await ctx.send(embed=embed)


async def get_hs_embed(hs):
    bmp = hs['meta']
    title = f'{bmp["title"]}[{bmp["version"]}]'
    hsEmbed = Embed(
        type='rich',
        color=EMBED_COLOR,
        description=f'**#{hs["ranking"] + 1}**: [{title}](https://osu.ppy.sh/b/{hs["beatmap_id"]}) \t| **{hs["rank"]}** {round(hs["acc"], 2)}% \t| {hs["pp"]}pp',
    )
    hsEmbed.set_thumbnail(url=f'https://b.ppy.sh/thumb/{bmp["beatmapset_id"]}l.jpg')
    return hsEmbed
    
def get_uid(ctx):
    with open("uids.json", "r") as fp:
        uidMap = json.load(fp)
        if f'{ctx.author.id}' in uidMap:
            return uidMap[f'{ctx.author.id}']
    return None


def format_hs(hs):
    response = requests.post(f'{OSU_API_ENDPOINT}get_beatmaps', params={'k': OSU_API_KEY, 'b': hs["beatmap_id"]})
    meta = response.json()[0]
    hs['meta'] = meta
    trimmed_title = meta["title"][:22] + '...' if len(meta["title"]) > 25 else meta["title"]
    title = f'{trimmed_title}[{meta["version"]}]'
    countmiss, count50, count100, count300 = int(hs["countmiss"]), int(hs["count50"]), int(hs["count100"]), int(hs["count300"])
    acc = (count50 + 2 * count100 + 6 * count300) / (countmiss + count50 + count100 + count300) / 6 * 100 # see https://osu.ppy.sh/wiki/en/Accuracy
    hs['acc'] = acc
    return f'**#{hs["ranking"] + 1}**: [{title}](https://osu.ppy.sh/b/{hs["beatmap_id"]}) \t| **{hs["rank"]}** {round(acc, 2)}% \t| {hs["pp"]}pp'


def format_diff(d):
    if d > 0:
        return f'+{str(d)}'
    else:
        return str(d)


def reply_mention(ctx):
    return f'<@{ctx.author.id}>'

bot.run(TOKEN)