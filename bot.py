# bot.py
import datetime as dt
import json
import logging
import os
import time
from typing import Dict, List, Mapping, Optional, Tuple, Union, cast
from discord.channel import TextChannel
from discord.enums import ChannelType

from flag import flag
import requests
from discord import Color, Embed, Emoji
from discord.ext import commands, tasks
from dotenv import load_dotenv
from humanize import naturaltime

import osu

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

KEKW_EMOTE = '<:KEKW:805177941814018068>'
SADGE_EMOTE = '<:Sadge:805178964652982282>'
OSU_SCORE_EMOJI_MAP: Mapping[osu.ScoreRank, str] = {
    'XH': '<:osuXH:835607165279797269>',
    'SSH': '<:osuXH:835607165279797269>',
    'X': '<:osuSS:835607691787239435>',
    'SS': '<:osuSS:835607691787239435>',
    'SH': '<:osuSH:835607165653745684>',
    'S': '<:osuS:835607691790647327>',
    'A': '<:osuA:835607165263020052>',
    'B': '<:osuB:835611278357299202>',
    'C': '<:osuC:835611278172487694>',
}

# typing setup
Context = commands.Context

AUTO_UPDATE_CHANNEL_ID: int = 0

bot = commands.Bot(command_prefix=PREFIX)


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')


@bot.command(help='Says Hello!')
async def hello(ctx: Context):
    await ctx.send('Hello!')


@bot.command(help='Bonk the bonkers')
async def bonk(ctx: Context):
    bonks = int(read_user_data(ctx.author.id, 'bonks') or 0)
    bonks += 1
    write_user_data(ctx.author.id, data={'bonks': bonks})
    await ctx.send(f'Boop. {reply_mention(ctx)} has bonked the bonkers {bonks} time{"" if bonks == 1 else "s"}')


@bot.command(aliases=('update', 'u'),
             help='runs an osu!track update for your registered profile (see $register) or an explicitly specified uid $update `<uid>`')
async def osu_update(ctx: Context, osuid: Optional[str] = None, showhs: bool = True):
    if not osuid:
        osuid = get_osuid(ctx)

    if not osuid:
        return await ctx.send(f'No osu profile set for user {reply_mention(ctx)}. You can register your osu profile using the $register command or specify an osu user id to update directly with $update <uid>.')

    response = requests.post(f'{AMEO_API_ENDPOINT}update', params={'user': osuid, 'mode': 0})
    if response.status_code != 200:
        if response.status_code == 400:
            return await ctx.send(f'Invalid update request, please make sure a valid user id was given/registered.')
        else:
            return await ctx.send('Something went wrong :(')
    r = response.json()
    updateEmbed = Embed(
        title=f'osu!track update for {r["username"]}', type='rich', color=EMBED_COLOR,
        description=(
            f'[osu! profile]({osu.profile_link(osuid)}) · [osu!track profile]({osu.track_profile_link(r["username"])})\n'
            f'**Rank**: {format_diff(r["pp_rank"])}\n'
            f'**PP**: {format_diff(round(r["pp_raw"], 4))}\n'
            f'**Playcount**: {r["playcount"]}\n'
            f'**Acc**: {format_diff(round(r["accuracy"], 2))}\n\n'
            f'**New Highscores**: {len(r["newhs"])}{f" {KEKW_EMOTE}" if len(r["newhs"]) == 0 else ""}\n'
            f'{chr(10).join(map(format_score_inline, r["newhs"])) if showhs else ""}'
        )
    )
    updateEmbed.set_thumbnail(url=osu.profile_thumb(osuid))
    await ctx.send(embed=updateEmbed)
    if showhs:
        hsEmbeds = [get_score_embed(hs, osuid, r["username"]) for hs in r["newhs"]]
        for embed in hsEmbeds:
            await ctx.send(embed=embed)


@ bot.command(aliases=('t', 'top'),
              help='$top (<rank=1>) (<username/userid>) gets the top #rank score for a given osu user (defaults to your registered user)')
async def osu_top(ctx: Context, rank: int = 1, u: Optional[str] = None):
    if rank < 1 or rank > 100:
        return ctx.send('invalid score rank (must be between 1-100)')
    if not u:
        u = get_osuid(ctx)
    if not u:
        return ctx.send('invalid user')
    topScores = get_top_scores(u=u, limit=rank)
    if not topScores:
        return ctx.send(f'No top scores found for user {u}. Make sure to provide a valid osu username/id.')
    score = topScores[rank - 1]
    user = get_user(u)
    await ctx.send(embed=get_score_embed(score, user['user_id'], user['username']))


@ bot.command(aliases=('tr', 'topr', 'toprange'),
              help='$toprange (<rankstart=1>) (<rankend=1>) (<username/userid>) gets a range of top scores for a given osu user (defaults to your registered user)')
async def osu_toprange(ctx: Context, rankstart: int = 1, rankend: int = 10, u: Optional[str] = None):
    if rankstart < 1 or rankend < 1 or rankend > 100 or rankstart > rankend or rankend - rankstart >= 15:
        return await ctx.send('invalid score rank range (max 15 scores, ranks must be between 1-100) ')
    if not u:
        u = get_osuid(ctx)
    if not u:
        return await ctx.send('invalid user')
    topScores = get_top_scores(u, rankend)
    if not topScores:
        return ctx.send(f'No top scores found for user {u}. Make sure to provide a valid osu username/id.')
    scores = topScores[rankstart - 1: rankend]
    user = get_user(u)

    toprangeEmbed = Embed(
        type='rich',
        color=EMBED_COLOR,
        description='\n'.join(map(format_score_inline, scores))
    )
    toprangeEmbed.set_author(
        name=f'Top {rankstart} - {rankend} scores for {user["username"]}',
        url=osu.profile_link(user["user_id"]),
        icon_url=osu.profile_thumb(user["user_id"]),
    )
    await ctx.send(embed=toprangeEmbed)


@ bot.command(aliases=('register', 'r'),
              help='registers an osu account to your discord user and runs an intial osu!track update')
async def osu_register(ctx: Context, u: Optional[str] = None):
    if not u:
        return await ctx.send('Please specify an osu profile username/id!')
    else:
        user = get_user(u)
        if not user:
            return await ctx.send(f'User {u} not found, you can try using an osu id instead')
        oldid = get_osuid(ctx)
        if oldid != user['user_id']:
            write_user_data(ctx.author.id, data={'osuid': user['user_id']})
            await ctx.message.add_reaction('✅')
            await ctx.send(f'User {user["username"]} is now registered to {reply_mention(ctx)}. Here\'s your inital osu!track update')
            await osu_update(ctx, osuid=user['user_id'], showhs=False)
        else:
            await ctx.send(f'osu user **{user["username"]}** is already registered')


@ bot.command(aliases=('profile', 'p'), help='displays a profile card for an osu account (default yours)')
async def osu_profile(ctx: Context, u: Optional[str] = ''):
    if not u:
        u = get_osuid(ctx)
    if not u:
        return await ctx.send('No osu account registered!')
    user = get_user(u)
    if not user:
        return await ctx.send(f'User {u} not found, you can try using an osu id instead')
    await ctx.send(embed=get_user_embed(user))


@ tasks.loop(minutes=10)
async def osu_auto_update():
    print(f'Running top score update for {dt.datetime.now()}')
    channel = bot.get_channel(AUTO_UPDATE_CHANNEL_ID)
    if not channel or channel.type != ChannelType.text:
        print(f'Top score update failed: invalid channel ID {AUTO_UPDATE_CHANNEL_ID}')
        logging.error(f'Top score update failed: invalid channel ID {AUTO_UPDATE_CHANNEL_ID}')
        return
    channel = cast(TextChannel, channel)

    allRecentTopScores = {}
    osuids = get_all_osuid()
    for uid, osuid in osuids:
        topScores = get_top_scores(u=osuid, limit=100)
        recentTopScores = list(filter(is_recent_score, topScores))
        if len(recentTopScores):
            allRecentTopScores[(uid, osuid)] = recentTopScores
    if len(allRecentTopScores):
        print(allRecentTopScores)
        # await channel.send('New top scores from the past hour 🎉')
        for (uid, osuid), scores in allRecentTopScores.items():
            if len(scores):
                await channel.send(f'New top scores for <@{uid}>')
                user = get_user(osuid)
                for score in scores:
                    await channel.send(embed=get_score_embed(score, osuid, user['username']))
    # else:
    #     await channel.send(f'No top scores in past hour {SADGE_EMOTE}')


def is_recent_score(score, timedelta=dt.timedelta(minutes=10, seconds=10)) -> bool:
    '''
        Returns True if `score` was submitted within `timedelta` (default 1 day) time before datetime.utcnow()
    '''
    return dt.datetime.utcnow() - dt.datetime.fromisoformat(score['date']) < timedelta


@ bot.command(help='enables automatic updates of highscores for registered users')
@ commands.has_permissions(administrator=True)
async def enable_osu_automatic_updates(ctx):
    global AUTO_UPDATE_CHANNEL_ID
    oldUpdateChannelID = AUTO_UPDATE_CHANNEL_ID
    AUTO_UPDATE_CHANNEL_ID = ctx.channel.id
    await ctx.message.add_reaction('✅')
    if oldUpdateChannelID:
        osu_auto_update.stop()
        ctx.send(
            f'Bonkers will now automatically send top scores in <#{ctx.channel.id}> instead of <#{oldUpdateChannelID}>'
        )
    else:
        await ctx.send(f'Bonkers will now automatically send top scores in <#{ctx.channel.id}>')
    osu_auto_update.start()


@ enable_osu_automatic_updates.error
async def enable_osu_automatic_updates_error(ctx, error):
    await ctx.send('You must be an admin to enable automatic top score updates')


@ bot.command(aliases=('dt', 'test'), help='command used for testing during development')
async def dev_test(ctx):
    # set up test data
    osuid = '17626463'
    r = json.load(open('test.json', 'r'))
    updateEmbed = Embed(
        title=f'osu!track update for {r["username"]}', type='rich', color=EMBED_COLOR,
        description=(
            f'[osu! profile]({osu.profile_link(osuid)}) · [osu!track profile]({osu.track_profile_link(r["username"])})\n'
            f'**Rank**: {format_diff(r["pp_rank"])}\n'
            f'**PP**: {format_diff(round(r["pp_raw"], 4))}\n'
            f'**Playcount**: {r["playcount"]}\n'
            f'**Acc**: {format_diff(round(r["accuracy"], 2))}\n\n'
            f'**New Highscores**: {len(r["newhs"])}{f" {KEKW_EMOTE}" if len(r["newhs"]) == 0 else ""}\n'
            f'{chr(10).join(map(format_score_inline, r["newhs"]))}'
        )
    )
    updateEmbed.set_thumbnail(url=osu.profile_thumb(osuid))
    await ctx.send(embed=updateEmbed)

    hsEmbeds = [get_score_embed(hs, osuid, r["username"]) for hs in r["newhs"]]
    for embed in hsEmbeds:
        await ctx.send(embed=embed)


def get_score_embed(score: osu.Score, osuid: str, username: str) -> Embed:
    if 'meta' not in score:
        score['meta'] = get_beatmap(score["beatmap_id"])
    bmp = score['meta']
    title = f'{bmp["title"]}[{bmp["version"]}] | {round(float(bmp["difficultyrating"]), 2)}★'
    scoreEmbed = Embed(
        type='rich',
        color=EMBED_COLOR,
        description=(
            f'**#{score["ranking"] + 1}: [{title}]({osu.beatmap_link(score["beatmap_id"])})\n'
            f'{osu_score_emoji(score["rank"])} | '
            f'{osu.mod_string(int(score["enabled_mods"]))} | '
            f'{get_score_acc(score)}% ({score["maxcombo"]}/{bmp["max_combo"]}) | '
            f'{score["pp"]}pp | '
            f'{get_score_timedelta(score)}**'
        ),
    )
    scoreEmbed.add_field(
        name='Beatmap Info',
        value=(
            f'Length **{format_seconds(int(bmp["total_length"]))}** ~ '
            f'CS**{bmp["diff_size"]}** '
            f'AR**{bmp["diff_approach"]}** '
            f'OD**{bmp["diff_overall"]}** '
            f'HP**{bmp["diff_drain"]}** ~ '
            f'**{bmp["bpm"]}** BPM ~ '
            f'**{round(float(bmp["difficultyrating"]), 2)}**★'
        ),
        inline=False
    )
    authortitle = f'{username} - #{score["ranking"] + 1} Top Play' if 'ranking' in score else username
    scoreEmbed.set_author(name=authortitle, url=osu.profile_link(osuid), icon_url=osu.profile_thumb(osuid))
    scoreEmbed.set_thumbnail(url=osu.beatmap_thumb(bmp['beatmapset_id']))
    return scoreEmbed


def get_user_embed(user: osu.User) -> Embed:
    osuid = user['user_id']
    userEmbed = Embed(
        title=(
            f'{flag(user["country"])} {user["username"]} - {user["pp_raw"]}pp | '
            f'#{user["pp_rank"]} | '
            f'{user["country"]} #{user["pp_country_rank"]}'
        ),
        url=osu.profile_link(osuid),
        type='rich',
        color=EMBED_COLOR,
    )
    userEmbed.add_field(
        name='Ranked Score',
        value=f'{user["ranked_score"]}',
        inline=True
    )
    userEmbed.add_field(
        name='Total score',
        value=f'{user["total_score"]}',
        inline=True,
    )
    userEmbed.add_field(
        name='Hit Accuracy',
        value=f'{round(float(user["accuracy"]), 2)}%',
        inline=True,
    )
    userEmbed.add_field(
        name='Play Count',
        value=f'{user["playcount"]}',
        inline=True,
    )
    userEmbed.add_field(
        name='Play Time',
        value=format_seconds(int(user["total_seconds_played"])),
        inline=True,
    )
    userEmbed.add_field(
        name='Level',
        value=f'{user["level"]}',
        inline=True,
    )
    userEmbed.add_field(
        name='Grades',
        value=(
            f'{osu_score_emoji("XH")} \u200b {user["count_rank_ssh"]} \u200b '
            f'{osu_score_emoji("SS")} \u200b {user["count_rank_ss"]} \u200b '
            f'{osu_score_emoji("SH")} \u200b {user["count_rank_sh"]} \u200b '
            f'{osu_score_emoji("S")} \u200b {user["count_rank_s"]} \u200b '
            f'{osu_score_emoji("A")} \u200b {user["count_rank_a"]}'
        ),
        inline=False,
    )
    userEmbed.set_thumbnail(url=osu.profile_thumb(osuid))
    return userEmbed


def write_user_data(uid: Union[int, str], data: Dict = {}, truncate: bool = False) -> None:
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


def read_user_data(uid: Union[int, str], key: str) -> Optional[str]:
    with open(USER_DATA, "r") as fp:
        allData = json.load(fp)
    userData = allData[f'{uid}'] if f'{uid}' in allData else {}
    return userData[key] if key in userData else None


def get_osuid(ctx: Context) -> Optional[str]:
    return read_user_data(ctx.author.id, 'osuid')


def get_all_osuid() -> List[Tuple[str, str]]:
    with open(USER_DATA, "r") as fp:
        allData = json.load(fp)
        return [(uid, allData[uid]['osuid']) for uid in allData if 'osuid' in allData[uid]]


def format_seconds(seconds: int) -> str:
    if seconds >= 86400:
        # format play time
        days = seconds // 86400
        seconds %= 86400
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        return f'{days}d {hours}h {minutes}m'
    else:
        # format bmp length
        fmt = '%H:%M:%S' if seconds >= 3600 else '%M:%S'
        return time.strftime(fmt, time.gmtime(seconds))


def format_score_inline(score: osu.Score) -> str:
    if 'meta' not in score:
        score['meta'] = get_beatmap(score["beatmap_id"])
    meta = score['meta']
    title = format_title(meta['title'], meta['version'])
    modString = f'**{osu.mod_string(int(score["enabled_mods"]))}**' if int(score["enabled_mods"]) > 0 else ''
    return f'**#{score["ranking"] + 1}**: [{title}](https://osu.ppy.sh/b/{score["beatmap_id"]}){modString} \t| \
        {osu_score_emoji(score["rank"])} {get_score_acc(score)}% \t| \
        {score["pp"]}pp'


def format_title(title: str, diff: str):
    if len(title) + len(diff) > 25:
        return f'{title[:23 - len(diff)]}...[{diff}]'
    else:
        return f'{title}[{diff}]'


def format_diff(d: int):
    if d > 0:
        return f'+{str(d)}'
    else:
        return str(d)


def reply_mention(ctx: Context) -> str:
    return f'<@{ctx.author.id}>'


def get_user(u: str) -> Optional[osu.User]:
    response = requests.post(f'{OSU_API_ENDPOINT}get_user', params={'k': OSU_API_KEY, 'u': u}).json()
    return response[0] if len(response) else None


def get_beatmap(beatmapid: str):
    return requests.post(f'{OSU_API_ENDPOINT}get_beatmaps', params={'k': OSU_API_KEY, 'b': beatmapid}).json()[0]


def get_top_scores(u: str, limit: int) -> List[osu.Score]:
    topScores = requests.post(
        f'{OSU_API_ENDPOINT}get_user_best',
        params={'k': OSU_API_KEY, 'u': u, 'limit': limit}
    ).json()
    for i, score in enumerate(topScores):
        score["ranking"] = i
    return topScores


def get_score_acc(score: osu.Score):
    countmiss = int(score["countmiss"])
    count50 = int(score["count50"])
    count100 = int(score["count100"])
    count300 = int(score["count300"])
    # see https://osu.ppy.sh/wiki/en/Accuracy
    acc = (count50 + 2 * count100 + 6 * count300) / (countmiss + count50 + count100 + count300) / 6 * 100
    return round(acc, 2)


def get_score_timedelta(score: osu.Score) -> str:
    return cast(str, naturaltime(dt.datetime.utcnow() - dt.datetime.fromisoformat(score['date'])))


def osu_score_emoji(rank: osu.ScoreRank) -> Union[Emoji, str]:
    return OSU_SCORE_EMOJI_MAP[rank] if rank in OSU_SCORE_EMOJI_MAP else f'**{rank}**'


if not TOKEN:
    raise Exception('no discord bot token DISCORD_TOKEN provided in .env file')
bot.run(TOKEN)
