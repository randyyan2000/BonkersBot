# bot.py
import os

from discord.ext import commands
from discord import Embed, Color
import requests
from dotenv import load_dotenv
import json
from humanize import naturaltime
import flag
import datetime as dt
import time
import osu
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OSU_API_KEY = os.getenv('OSU_API_KEY')
USER_DATA = os.getenv('USER_DATA_FILE') or 'data.json'

AMEO_API_ENDPOINT = 'https://osutrack-api.ameo.dev/'
OSU_API_ENDPOINT = 'https://osu.ppy.sh/api/'

PREFIX = '$'
EMBED_COLOR = Color.from_rgb(255, 165, 0)

bot = commands.Bot(command_prefix=PREFIX)

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')


@bot.command(help='Says Hello!')
async def hello(ctx):
    await ctx.send('Hello!')


@bot.command(help='Bonk the bonkers')
async def bonk(ctx):
    bonks = read_user_data(ctx.author.id, 'bonks') or 0
    bonks += 1
    write_user_data(ctx.author.id, data={'bonks': bonks})
    await ctx.send(f'Boop. {reply_mention(ctx)} has bonked the bonkers {bonks} times')


@bot.command(aliases=('update', 'u'), help='runs an osu!track update for your registered profile (see $register) or an explicitly specified uid $update `<uid>`')
async def osu_update(ctx, osuid=None):
    if not osuid:
        osuid = get_osuid(ctx)
    
    if not osuid:
        return await ctx.send(f'No osu profile set for user {reply_mention(ctx)}. You can register your osu profile using the $register command or specify an osu user id to update directly with $update <uid>.')

    response = requests.post(f'{AMEO_API_ENDPOINT}update', params = {'user': osuid, 'mode': 0})
    if response.status_code != 200:
        if response.status_code == 400:
            return await ctx.send(f'Invalid update request, please make sure a valid user id was given/registered.')
        return await ctx.send('Something went wrong :(')
    print(response.text)
    r = response.json()
    updateEmbed = Embed(
        title=f'osu!track update for {r["username"]}',
        type='rich',
        color=EMBED_COLOR,
        description=f'[osu! profile]({osu.profile_link(osuid)}) · [osu!track Profile](https://ameobea.me/osutrack/user/{r["username"]})\n\
        **Rank**: {format_diff(r["pp_rank"])}\n\
        **PP**: {format_diff(round(r["pp_raw"], 4))}\n\
        **Playcount**: {r["playcount"]}\n\
        **Acc**: {format_diff(round(r["accuracy"], 2))}\n\n\
        **New Highscores**: {len(r["newhs"])}{" <:KEKW:805177941814018068>" if len(r["newhs"]) == 0 else ""}\n\
        {chr(10).join(map(format_hs, r["newhs"]))}'
    )
    updateEmbed.set_thumbnail(url=osu.profile_thumb(osuid))
    await ctx.send(embed=updateEmbed)

    hsEmbeds = [get_score_embed(hs, osuid, r["username"]) for hs in r["newhs"]]
    for embed in hsEmbeds:
        await ctx.send(embed=embed)


@bot.command(aliases=('t', 'top'), help='$top (<rank=1>) (<username/userid>) gets the top #rank score for a given osu user (defaults to your registered user)')
async def osu_top(ctx, rank: int=1, u: str=''):
    if not u:
        u = get_osuid(ctx)
    response = requests.post(f'{OSU_API_ENDPOINT}get_user_best', params={'k': OSU_API_KEY, 'u': u, 'limit': rank})
    score = response.json()[rank - 1]
    score['ranking'] = rank - 1
    user = get_user(u)
    await ctx.send(embed=get_score_embed(score, user['user_id'], user['username']))


@bot.command(aliases=('register', 'r'), help='registers an osu account to your discord user so you don\'t have to specify a user when running updates')
async def osu_register(ctx, osuid=None):
    if not osuid:
        return await ctx.send('Please specify an osu profile id!')
    else:
        write_user_data(ctx.author.id, data={'osuid': osuid})
        await ctx.message.add_reaction('✅')
        await ctx.send(f'User 40870022 registered to {reply_mention(ctx)}')


@bot.command(aliases=('profile', 'p'), help='displays a profile card for an osu account (default yours)')
async def osu_profile(ctx, u=None):
    if not u:
        u = get_osuid(ctx)
    user = get_user(u)
    await ctx.send(embed=get_user_embed(user))    


@bot.command(aliases=('dt', 'test'), help='command used for testing during development')
async def dev_test(ctx):
    osuid = 17626463
    r = json.load(open('test.json', 'r'))
    updateEmbed = Embed(
        title=f'osu!track update for {r["username"]}',
        type='rich',
        color=EMBED_COLOR,
        description=f'[osu! profile]({osu.profile_link(osuid)}) · [osu!track Profile](https://ameobea.me/osutrack/user/{r["username"]})\n\
        **Rank**: {format_diff(r["pp_rank"])}\n\
        **PP**: {format_diff(round(r["pp_raw"], 4))}\n\
        **Playcount**: {r["playcount"]}\n\
        **Acc**: {format_diff(round(r["accuracy"], 2))}\n\n\
        **New Highscores**: {len(r["newhs"])}{" <:KEKW:805177941814018068>" if len(r["newhs"]) == 0 else ""}\n\
        {chr(10).join(map(format_hs, r["newhs"]))}'
    )
    updateEmbed.set_thumbnail(url=osu.profile_thumb(osuid))
    await ctx.send(embed=updateEmbed)

    hsEmbeds = [get_score_embed(hs, osuid, r["username"]) for hs in r["newhs"]]
    for embed in hsEmbeds:
        await ctx.send(embed=embed)


def get_score_embed(score, osuid, username):
    if 'meta' not in score:
        response = requests.post(f'{OSU_API_ENDPOINT}get_beatmaps', params={'k': OSU_API_KEY, 'b': score["beatmap_id"]})
        score['meta'] = response.json()[0]
    bmp = score['meta']
    title = f'{bmp["title"]}[{bmp["version"]}] | {round(float(bmp["difficultyrating"]), 2)}★'
    scoreEmbed = Embed(
        type='rich',
        color=EMBED_COLOR,
        description=f'**#{score["ranking"] + 1}: [{title}]({osu.beatmap_link(score["beatmap_id"])})\n\
        {osu_score_emoji(score["rank"])} | \
        {osu.mod_string(int(score["enabled_mods"]))} | \
        {get_score_acc(score)}% ({score["maxcombo"]}/{bmp["max_combo"]}) | \
        {score["pp"]}pp | \
        {get_score_timedelta(score)}**',
    )
    # scoreEmbed.add_field(
    #     name=f'#{score["ranking"] + 1}: [{title}]({osu.beatmap_link(score["beatmap_id"])})',
    #     value=f'**{osu_score_emoji(score["rank"])} | \
    #         {osu.mod_string(int(score["enabled_mods"]))} | \
    #         {get_score_acc(score)}% ({score["maxcombo"]}/{bmp["max_combo"]} max) | \
    #         {score["pp"]}pp | \
    #         {get_score_timedelta(score)}**',
    #     inline=False
    # )
    scoreEmbed.add_field(
        name='Beatmap Info',
        value=f'Length **{format_seconds(int(bmp["total_length"]))}** ~ \
            CS**{bmp["diff_size"]}** \
            AR**{bmp["diff_approach"]}** \
            OD**{bmp["diff_overall"]}** \
            HP**{bmp["diff_drain"]}** ~ \
            **{bmp["bpm"]}** BPM ~ \
            **{round(float(bmp["difficultyrating"]), 2)}**★',
        inline=False
    )
    authortitle = f'{username} - #{score["ranking"] + 1} Top Play' if 'ranking' in score else username
    scoreEmbed.set_author(name=authortitle, url=osu.profile_link(osuid), icon_url=osu.profile_thumb(osuid))
    scoreEmbed.set_thumbnail(url=osu.beatmap_thumb(bmp['beatmapset_id']))
    return scoreEmbed


def get_user_embed(user):
    osuid = user['user_id']
    userEmbed = Embed(
        title=f'{flag.flag(user["country"])} {user["username"]} - {user["pp_raw"]}pp (#{user["pp_rank"]}) ({user["country"]} #{user["pp_country_rank"]})', 
        url=osu.profile_link(osuid),
        type='rich',
        color=EMBED_COLOR,
    )
    userEmbed.add_field(
        name='Ranked Score',
        value=user["ranked_score"],
        inline=True
    )
    userEmbed.add_field(
        name='Total score',
        value=user["total_score"],
        inline=True,
    )
    userEmbed.add_field(
        name='Hit Accuracy',
        value=round(float(user["accuracy"]), 2),
        inline=True,
    )
    userEmbed.add_field(
        name='Play Count',
        value=user["playcount"],
        inline=True,
    )
    userEmbed.add_field(
        name='Play Time',
        value=format_seconds(int(user["total_seconds_played"])),
        inline=True,
    )
    userEmbed.add_field(
        name='Level',
        value=user["level"],
        inline=True,
    )
    userEmbed.add_field(
        name='Grades',
        value=f'{osu_score_emoji("XH")} {user["count_rank_ssh"]}  \t\
            {osu_score_emoji("SS")} {user["count_rank_ss"]}  \t\
            {osu_score_emoji("SH")} {user["count_rank_sh"]}  \t\
            {osu_score_emoji("S")} {user["count_rank_s"]}  \t\
            {osu_score_emoji("A")} {user["count_rank_a"]}',
        inline=False,
    )
    userEmbed.set_thumbnail(url=osu.profile_thumb(osuid))
    return userEmbed


def write_user_data(uid, data={}, truncate=False):
    with open(USER_DATA, "r") as fp:
        allData = json.load(fp)
    userData = allData[f'{uid}'] if f'{uid}' in allData else {}
    if truncate:
        userData = data
    else:
        userData.update(data)
    allData[f'{uid}'] = userData
    with open(USER_DATA, "w+") as fp:
        json.dump(allData, fp, sort_keys=True, indent=4)


def read_user_data(uid, key=None):
    with open(USER_DATA, "r") as fp:
        allData = json.load(fp)
    userData = allData[f'{uid}'] if f'{uid}' in allData else {}
    if key:
        return userData[key] if key in userData else None
    else:
        return userData


def get_osuid(ctx):
    return read_user_data(ctx.author.id, 'osuid')


def format_seconds(seconds):
    if seconds >= 86400:
        # formatting play time
        fmt = '%'
    fmt = '%H:%M:%S' if seconds >= 3600 else '%M:%S'
    return time.strftime(fmt, time.gmtime(seconds))


def format_hs(hs):
    response = requests.post(f'{OSU_API_ENDPOINT}get_beatmaps', params={'k': OSU_API_KEY, 'b': hs["beatmap_id"]})
    meta = response.json()[0]
    hs['meta'] = meta
    title = format_title(meta['title'], meta['version'])
    return f'**#{hs["ranking"] + 1}**: [{title}](https://osu.ppy.sh/b/{hs["beatmap_id"]}) \t| {osu_score_emoji(hs["rank"])} {get_score_acc(hs)}% \t| {hs["pp"]}pp'


def format_title(title, diff):
    if len(title) + len(diff) > 35:
        return f'{title[:32 - len(diff)]}...[{diff}]'
    else:
        return f'{title}[{diff}]'


def format_diff(d):
    if d > 0:
        return f'+{str(d)}'
    else:
        return str(d)


def reply_mention(ctx):
    return f'<@{ctx.author.id}>'


def get_user(u: str):
    return requests.post(f'{OSU_API_ENDPOINT}get_user', params={'k': OSU_API_KEY, 'u': u}).json()[0]

OSU_SCORE_EMOJI_MAP = {
    'XH': '<:osuXH:835607165279797269>',
    'SS': '<:osuSS:835607691787239435>',
    'SH': '<:osuSH:835607165653745684>',
    'S' : '<:osuS:835607691790647327>',
    'A' : '<:osuA:835607165263020052>',
    'B' : '<:osuB:835611278357299202>',
    'C' : '<:osuC:835611278172487694>',
}

def get_score_acc(score):
    countmiss, count50, count100, count300 = int(score["countmiss"]), int(score["count50"]), int(score["count100"]), int(score["count300"])
    acc = (count50 + 2 * count100 + 6 * count300) / (countmiss + count50 + count100 + count300) / 6 * 100 # see https://osu.ppy.sh/wiki/en/Accuracy
    return round(acc, 2)

def get_score_timedelta(score):
    return naturaltime(dt.datetime.utcnow() - dt.datetime.fromisoformat(score['date']))

def osu_score_emoji(rank):
    return OSU_SCORE_EMOJI_MAP[rank] if rank in OSU_SCORE_EMOJI_MAP else f'**{rank}**'


bot.run(TOKEN)