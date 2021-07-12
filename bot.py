# bot.py
import datetime as dt
import logging
import os
import random
import time
from typing import List, Mapping, Optional, Union, cast
import locale
from utils import chunk

from flag import flag
import requests
from discord import Color, Embed, Emoji, Message
from discord.activity import Game
from discord.channel import TextChannel
from discord.enums import ChannelType
from discord.ext import commands, tasks
from discord.ext.commands.context import Context
from dotenv import load_dotenv
from humanize import naturaltime

import osu
import backend
from honk import get_honk

logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')


# envvars
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OSU_API_KEY = os.getenv('OSU_API_KEY')
DEFAULT_PREFIX = os.getenv('DEFAULT_PREFIX') or '$'

AMEO_API_ENDPOINT = 'https://osutrack-api.ameo.dev/'
OSU_API_ENDPOINT = 'https://osu.ppy.sh/api/'

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
OSU_HIT_EMOJI_MAP = {
    'miss': '<:osuMiss:849349136955867166>',
    '50':   '<:osu50:849353678774206465>',
    '100':  '<:osu100:849349027438002176>',
    '300':  '<:osu300:849349068383453194>',
}

AUTO_UPDATE_CHANNEL_ID: int = 0


def get_prefix(bot: commands.Bot, message: Message):
    prefix = DEFAULT_PREFIX
    guild = message.guild
    if guild:
        prefix = backend.read_guild_data(guild.id, 'prefix')
    return prefix if prefix else DEFAULT_PREFIX


bot = commands.Bot(
    command_prefix=get_prefix,
    case_insensitive=True,
    activity=Game('$help, feel free to @Honkers with any feedback'),
)


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')


@bot.command(help='Says Hello!')
async def hello(ctx: Context):
    await ctx.send('Hello!')


@bot.command(help='Gives some info about the Bonkers')
async def about(ctx: Context):
    await ctx.send(
        'Developed by Randy. Hopefully it\'s not too shitty :P. https://github.com/randyyan2000/BonkersBot'
    )


@bot.command(help='Bonk the bonkers')
async def bonk(ctx: Context):
    bonks = backend.read_user_data(ctx.author.id, 'bonks') or 0
    bonks += 1
    backend.write_user_data(ctx.author.id, data={'bonks': bonks})
    await ctx.send(f'Boop. {reply_mention(ctx)} has bonked the bonkers {bonks} time{"" if bonks == 1 else "s"}')


@bot.command(help='honk')
async def honk(ctx: Context):
    message = await ctx.send(get_honk())
    time.sleep(5)
    await message.edit(content=random.choice(['🎺', '📯', '🇭 🇴 🇳 🇰']))


@bot.command(
    aliases=('update', 'u'),
    help='Runs an osu!track update for your registered profile (see $register) or an explicitly specified uid $update `<uid>`'
)
async def osu_update(ctx: Context, *, u: Optional[str] = None, showhs: bool = True):
    if not u:
        u = get_osuid(ctx)
    if not u:
        return await ctx.send(f'No osu profile set for user {reply_mention(ctx)}. You can register your osu profile using the $register command or specify an osu user id to update directly with $update <uid>.')
    user = get_user(u)
    if not user:
        return await ctx.send(f'invalid user')
    osuid = user['user_id']
    response = requests.post(f'{AMEO_API_ENDPOINT}update', params={'user': osuid, 'mode': 0})
    if response.status_code != 200:
        if response.status_code == 400:
            return await ctx.send(f'Invalid update request, please make sure a valid user id was given/registered.')
        else:
            return await ctx.send('Something went wrong :( Try going to https://ameobea.me/osutrack/ to make sure you account stats are initialized.')
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
            f'{chr(10).join(map(format_score_inline, r["newhs"][:5])) if showhs else ""}'
            f'{f"{chr(10)}..." if len(r["newhs"]) > 5 else ""}'
        )
    )
    updateEmbed.set_thumbnail(url=osu.profile_thumb(osuid))
    await ctx.send(embed=updateEmbed)
    if showhs:
        hsEmbeds = [get_score_embed(hs, osuid, r["username"]) for hs in r["newhs"][:5]]
        for embed in hsEmbeds:
            await ctx.send(embed=embed)


@ bot.command(
    aliases=('t', 'top'),
    help='$top (<rank=1>) (<username/userid>) gets the top #rank score for a given osu user (defaults to your registered user)'
)
async def osu_top(ctx: Context, rank: int = 1, *, u: Optional[str] = None):
    if rank < 1 or rank > 100:
        return await ctx.send('invalid score rank (must be between 1-100)')
    if not u:
        u = get_osuid(ctx)
    if not u:
        return await ctx.send('invalid user')
    topScores = get_top_scores(u=u, limit=rank)
    if not topScores:
        return await ctx.send(f'No top scores found for user {u}. Make sure to provide a valid osu username/id.')
    score = topScores[rank - 1]
    user = get_user(u)
    await ctx.send(embed=get_score_embed(score, user['user_id'], user['username']))


@ bot.command(
    aliases=('tr', 'topr', 'toprange'),
    help='$toprange (<rankstart=1>) (<rankend=1>) (<username/userid>) gets a range of top scores for a given osu user (defaults to your registered user)'
)
async def osu_toprange(ctx: Context, rankstart: int = 1, rankend: int = 10, *, u: Optional[str] = None):
    if rankstart < 1 or rankend < 1 or rankend > 100 or rankstart > rankend or rankend - rankstart >= 30:
        return await ctx.send('invalid score rank range (max 30 scores, ranks must be between 1-100) ')
    if not u:
        u = get_osuid(ctx)
    if not u:
        return await ctx.send('invalid user')
    topScores = get_top_scores(u, rankend)
    if not topScores:
        return await ctx.send(f'No top scores found for user {u}. Make sure to provide a valid osu username/id.')
    scores = topScores[rankstart - 1: rankend]
    chunkedScores = chunk(scores, 10)
    user = get_user(u)
    first = True
    for scoreChunk in chunkedScores:
        toprangeEmbed = Embed(
            type='rich',
            color=EMBED_COLOR,
            description='\n'.join(map(format_score_inline, scoreChunk))
        )
        if first:
            toprangeEmbed.set_author(
                name=f'Top {rankstart} - {rankend} scores for {user["username"]}',
                url=osu.profile_link(user["user_id"]),
                icon_url=osu.profile_thumb(user["user_id"]),
            )
            first = False
        await ctx.send(embed=toprangeEmbed)


@ bot.command(
    aliases=('register', 'r'),
    help='Registers an osu account to your discord user and runs an intial osu!track update'
)
async def osu_register(ctx: Context, *, u: Optional[str] = None):
    if not u:
        return await ctx.send('Please specify an osu profile username/id!')
    else:
        user = get_user(u)
        if not user:
            return await ctx.send(f'User {u} not found, you can try using an osu id instead')

        registeredGuilds = set(backend.read_user_data(ctx.author.id, 'guilds') or [])
        registeredGuilds.add(ctx.guild.id)
        backend.write_user_data(
            ctx.author.id,
            data={
                'osuid': user['user_id'],
                'guilds': list(registeredGuilds),
            },
        )
        await ctx.message.add_reaction('✅')
        await ctx.send(f'User {user["username"]} is now registered to {reply_mention(ctx)}. Here\'s your inital osu!track update')
        await osu_update(ctx, u=user['user_id'], showhs=False)


@ bot.command(
    aliases=('profile', 'p'),
    help='Displays a profile card for an osu account (default yours)'
)
async def osu_profile(ctx: Context, *, u: Optional[str] = ''):
    if not u:
        u = get_osuid(ctx)
    if not u:
        return await ctx.send('No osu account registered!')
    user = get_user(u)
    if not user:
        return await ctx.send(f'User {u} not found, you can try using an osu id instead')
    await ctx.send(embed=get_user_embed(user))


@bot.command(aliases=('map', 'm'), help='displays info for a given beatmap id')
async def osu_map(ctx: Context, beatmapid: str):
    if not beatmapid:
        return await ctx.send('No beatmap id specified!')
    beatmap = get_beatmap(beatmapid)
    if not beatmap:
        return await ctx.send('Beatmap not found!')
    return await ctx.send(embed=get_beatmap_embed(beatmap))


@bot.command(
    aliases=('l', 'sl'),
    help='displays a leaderboard for registered osu profiles in this server'
)
async def osu_leaderboard(ctx: Context, mode: int = 0):
    gid = ctx.guild.id
    userData = backend.read_all_data(backend.USER_DATA)
    guildUsers: List[osu.User] = []
    for uid, userData in userData.items():
        if 'osuid' not in userData or 'guilds' not in userData:
            continue
        registeredGuilds = userData['guilds']
        if gid in registeredGuilds:
            user = get_user(userData['osuid'], mode)
            if user:
                guildUsers.append(user)
            else:
                await ctx.send(
                    f'Profile retrieval failed for user {osu.profile_link(userData["osuid"])}'
                )
    guildUsers.sort(key=lambda user: (int(user['pp_rank'] or 0) or float('inf'), -float(user['level'] or 0)))
    chunkedGuildUsers = chunk(guildUsers, 10)

    first = True
    for userChunk in chunkedGuildUsers:
        leaderboardRows = []
        for i, user in enumerate(userChunk):
            leaderboardRows.append(
                f'**#{i + 1}** '
                f'{flag(user["country"])} [{user["username"]}]({osu.profile_link(user["user_id"])}) - '
                f'#{int(user["pp_rank"] or 0):n} | '
                f'{float(user["pp_raw"] or 0):n}pp | '
                f'LVL {float(user["level"] or 0):.2f}'
            )

        leaderboardEmbed = Embed(
            type='rich',
            color=EMBED_COLOR,
            description='\n'.join(leaderboardRows)
        )
        if first:
            leaderboardEmbed.set_author(
                name=f'{osu.MODE_STRING_ENUM[mode]} leaderboard for {ctx.guild.name}',
                icon_url=str(ctx.guild.icon_url) or Embed.Empty,
            )
            first = False
        await ctx.send(embed=leaderboardEmbed)


@ tasks.loop(minutes=10)
async def osu_auto_update():
    print(f'Running top score update for {dt.datetime.now()}')
    logger.debug(f'Running top score update for {dt.datetime.now()}')

    # allRecentTopScores = {}
    allUserData = backend.read_all_data(backend.USER_DATA)
    allGuildData = backend.read_all_data(backend.GUILD_DATA)

    for uid, userData in allUserData.items():
        if 'osuid' not in userData or 'guilds' not in userData:
            continue
        registeredGuilds = userData['guilds']
        if not len(registeredGuilds):
            continue
        osuid = userData['osuid']
        topScores = get_top_scores(u=osuid, limit=100)
        recentTopScores = list(filter(is_recent_score, topScores))
        # if len(recentTopScores):
        #     allRecentTopScores[(uid, osuid)] = recentTopScores
        if len(recentTopScores):
            for gid in registeredGuilds:
                guildData = allGuildData.get(str(gid), {})
                cid = guildData.get('osu_update_channel')
                if not cid:
                    logger.warn(f'registered guild {gid} has no auto update channel set')
                    continue
                channel = bot.get_channel(cid)
                if not channel or channel.type != ChannelType.text:
                    print(f'Top score update failed: invalid channel ID {cid}')
                    logger.error(f'Top score update failed: invalid channel ID {cid}')
                    continue
                channel = cast(TextChannel, channel)

                # filter scores on osu_update_cutoff
                scoreCutoff = min(guildData.get('osu_update_score_cutoff', 100), 100)
                filteredRecentTopScores = list(filter(
                    lambda score : score['ranking'] < scoreCutoff, recentTopScores
                ))
                if len(filteredRecentTopScores):
                    await channel.send(f'New top scores for <@{uid}>')
                    user = get_user(osuid)
                    for score in filteredRecentTopScores:
                        await channel.send(embed=get_score_embed(score, osuid, user['username']))

    # if len(allRecentTopScores):
    #     print(allRecentTopScores)
    #     # await channel.send('New top scores from the past hour 🎉')
    #     for (uid, osuid), scores in allRecentTopScores.items():
    #         if len(scores):
    #             await channel.send(f'New top scores for <@{uid}>')
    #             user = get_user(osuid)
    #             for score in scores:
    #                 await channel.send(embed=get_score_embed(score, osuid, user['username']))
    # else:
    #     await channel.send(f'No top scores in past hour {SADGE_EMOTE}')


@osu_auto_update.before_loop
async def before_osu_auto_update():
    print('waiting for bot to log on')
    await bot.wait_until_ready()  # wait until the bot logs on


def is_recent_score(score, timedelta=dt.timedelta(minutes=10, seconds=5)) -> bool:
    '''
        Returns True if `score` was submitted within `timedelta` (default 1 day) time before datetime.utcnow()
    '''
    return dt.datetime.utcnow() - dt.datetime.fromisoformat(score['date']) < timedelta


@bot.command(help='Changes the prefix for commands to be recognized by Bonkers')
@commands.has_permissions(administrator=True)
async def set_bonkers_prefix(ctx: Context, prefix: str):
    if not ctx.guild:
        return await ctx.send('Can\'t change prefix outside a server')
    if prefix:
        backend.write_guild_data(ctx.guild.id, {'prefix': prefix})
        await ctx.message.add_reaction('✅')
        await ctx.send(f'Bonkers will now respond to commands prefixed with {prefix}')
    else:
        await ctx.send('No prefix specified!')


@ set_bonkers_prefix.error
async def set_bonkers_prefix_error(ctx: Context, error):
    await ctx.send('You must be an admin to enable automatic top score updates')


@bot.command(help='Unregisters mentioned users')
@commands.has_permissions(administrator=True)
async def osu_unregister(ctx: Context):
    mentionedIDs = [mention.id for mention in ctx.message.mentions]
    if not len(mentionedIDs):
        mentionedIDs.append(ctx.author.id)

    for uid in mentionedIDs:
        registeredGuilds = backend.read_user_data(uid, 'guilds') or []
        try:
            registeredGuilds.remove(ctx.guild.id)
        except ValueError:
            pass
        backend.write_user_data(uid, data={'guilds': registeredGuilds})

    await ctx.message.add_reaction('✅')
    await ctx.send(
        f'User(s) {chr(32).join([f"<@{uid}>" for uid in mentionedIDs])} osu account(s) are now unregistered from this server.'
    )


@ bot.command(aliases=('enable_osu_auto_update', 'osu_auto_update', 'eoau'),
              help='Enables automatic updates of highscores for registered users')
@ commands.has_permissions(administrator=True)
async def enable_osu_automatic_updates(ctx: Context):
    backend.write_guild_data(ctx.guild.id, data={'osu_update_channel': ctx.channel.id})
    await ctx.message.add_reaction('✅')
    await ctx.send(f'Bonkers will now automatically send top scores in <#{ctx.channel.id}>')


@ enable_osu_automatic_updates.error
async def enable_osu_automatic_updates_error(ctx: Context, error):
    await ctx.send('You must be an admin to enable automatic top score updates')


@ bot.command(aliases=('set_osu_update_cutoff', 'cutoff'),
              help='Sets the top score cutoff for automatic updates')
@ commands.has_permissions(administrator=True)
async def set_osu_auto_update_cutoff(ctx: Context, cutoff: int):
    if cutoff < 1 or cutoff > 100:
        return await ctx.send('Invalid cutoff (must be between 1-100)')
    backend.write_guild_data(ctx.guild.id, data={'osu_update_score_cutoff': cutoff})
    await ctx.message.add_reaction('✅')
    await ctx.send(f'Bonkers will now only send update with scores in the top {cutoff}')


@ set_osu_auto_update_cutoff.error
async def enable_osu_automatic_updates_error(ctx: Context, error):
    await ctx.send('You must be an admin to set the top score update cutoff')


@ bot.command(aliases=('dt', 'test'), help='Super secret command used for testing during development')
@ commands.has_permissions(administrator=True)
async def dev_test(ctx):
    await ctx.send(get_honk())

    # pass
    # # set up test data
    # osuid = '17626463'
    # r = json.load(open('test.json', 'r'))
    # updateEmbed = Embed(
    #     title=f'osu!track update for {r["username"]}', type='rich', color=EMBED_COLOR,
    #     description=(
    #         f'[osu! profile]({osu.profile_link(osuid)}) · [osu!track profile]({osu.track_profile_link(r["username"])})\n'
    #         f'**Rank**: {format_diff(r["pp_rank"])}\n'
    #         f'**PP**: {format_diff(round(r["pp_raw"], 4))}\n'
    #         f'**Playcount**: {r["playcount"]}\n'
    #         f'**Acc**: {format_diff(round(r["accuracy"], 2))}\n\n'
    #         f'**New Highscores**: {len(r["newhs"])}{f" {KEKW_EMOTE}" if len(r["newhs"]) == 0 else ""}\n'
    #         f'{chr(10).join(map(format_score_inline, r["newhs"]))}'
    #     )
    # )
    # updateEmbed.set_thumbnail(url=osu.profile_thumb(osuid))
    # await ctx.send(embed=updateEmbed)

    # hsEmbeds = [get_score_embed(hs, osuid, r["username"]) for hs in r["newhs"]]
    # for embed in hsEmbeds:
    #     await ctx.send(embed=embed)


def get_score_embed(score: osu.Score, osuid: str, username: str) -> Embed:
    if 'meta' not in score:
        score['meta'] = get_beatmap(score["beatmap_id"])
    bmp = score['meta']
    title = f'{bmp["title"]} [{bmp["version"]}] | {float(bmp["difficultyrating"]):.2f}★'

    description = (
        f'**[{title}]({osu.beatmap_link(score["beatmap_id"])})\n'
        f'{osu_score_emoji(score["rank"])} | '
        f'{osu.mod_string(int(score["enabled_mods"]))} | '
        f'{get_score_acc(score)}% ({score["maxcombo"]}/{bmp["max_combo"]}) | '
        f'{score["pp"]}pp | '
        f'{get_score_timedelta(score)}**\n'
        f'{OSU_HIT_EMOJI_MAP["300"]} {score["count300"]} '
        f'{OSU_HIT_EMOJI_MAP["100"]} {score["count100"]}'
        f'{OSU_HIT_EMOJI_MAP["50"]} {score["count50"]} '
        f'{OSU_HIT_EMOJI_MAP["miss"]} {score["countmiss"]}\n\n'
        f'**Beatmap Info** ({bmp["beatmap_id"]})'
    )
    if int(score['replay_available']) == 1:
        description += f' ([Replay]({osu.score_replay_link(score["score_id"])}))'
    description += (
        f'\nLength **{format_seconds(int(bmp["total_length"]))}** ~ '
        f'CS**{bmp["diff_size"]}** '
        f'AR**{bmp["diff_approach"]}** '
        f'OD**{bmp["diff_overall"]}** '
        f'HP**{bmp["diff_drain"]}** ~ '
        f'**{bmp["bpm"]}** BPM ~ '
        f'**{float(bmp["difficultyrating"]):.2f}**★'
    )

    scoreEmbed = Embed(
        type='rich',
        color=EMBED_COLOR,
        description=description,
    )
    authortitle = f'{username} - #{score["ranking"] + 1} Top Play' if 'ranking' in score else username
    scoreEmbed.set_author(name=authortitle, url=osu.profile_link(osuid), icon_url=osu.profile_thumb(osuid))
    scoreEmbed.set_thumbnail(url=osu.beatmap_thumb(bmp['beatmapset_id']))
    return scoreEmbed


def get_user_embed(user: osu.User) -> Embed:
    osuid = user['user_id']
    userEmbed = Embed(
        title=(
            f'{flag(user["country"])} {user["username"]} - {float(user["pp_raw"]):n}pp | '
            f'#{int(user["pp_rank"]):n} | '
            f'{user["country"]} #{int(user["pp_country_rank"]):n}'
        ),
        url=osu.profile_link(osuid),
        type='rich',
        color=EMBED_COLOR,
    )
    userEmbed.add_field(
        name='Ranked Score',
        value=f'{int(user["ranked_score"]):n}',
        inline=True
    )
    userEmbed.add_field(
        name='Total score',
        value=f'{int(user["total_score"]):n}',
        inline=True,
    )
    userEmbed.add_field(
        name='Hit Accuracy',
        value=f'{float(user["accuracy"]):.2f}%',
        inline=True,
    )
    userEmbed.add_field(
        name='Play Count',
        value=f'{int(user["playcount"]):n}',
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
            f'{osu_score_emoji("XH")} \u200b {int(user["count_rank_ssh"]):n} \u200b '
            f'{osu_score_emoji("SS")} \u200b {int(user["count_rank_ss"]):n} \u200b '
            f'{osu_score_emoji("SH")} \u200b {int(user["count_rank_sh"]):n} \u200b '
            f'{osu_score_emoji("S")} \u200b {int(user["count_rank_s"]):n} \u200b '
            f'{osu_score_emoji("A")} \u200b {int(user["count_rank_a"]):n}'
        ),
        inline=False,
    )
    userEmbed.set_thumbnail(url=osu.profile_thumb(osuid))
    return userEmbed


def get_beatmap_embed(bmp: osu.Beatmap):
    beatmapEmbed = Embed(
        title=f'{bmp["title"]} [{bmp["version"]}] | {float(bmp["difficultyrating"]):.2f}★',
        url=osu.beatmap_link(bmp['beatmap_id']),
        color=EMBED_COLOR,
    )
    beatmapEmbed.add_field(
        name=f'Beatmap Info ({bmp["beatmap_id"]}) ({osu.BEATMAP_STATUS_ENUM[int(bmp["approved"])]})',
        value=(
            f'Length **{format_seconds(int(bmp["total_length"]))}** ~ '
            f'Max Combo **{bmp["max_combo"]}**\n'
            f'CS**{bmp["diff_size"]}** '
            f'AR**{bmp["diff_approach"]}** '
            f'OD**{bmp["diff_overall"]}** '
            f'HP**{bmp["diff_drain"]}** ~ '
            f'**{bmp["bpm"]}** BPM ~ '
            f'**{float(bmp["difficultyrating"]):.2f}**★'
        ),
        inline=False
    )
    beatmapEmbed.set_thumbnail(url=osu.beatmap_thumb(bmp['beatmapset_id']))
    beatmapEmbed.set_footer(
        text=f'Mapped by {bmp["creator"]}',
        icon_url=osu.profile_thumb(bmp['creator_id'])
    )
    return beatmapEmbed


def get_osuid(ctx: Context) -> Optional[str]:
    return backend.read_user_data(ctx.author.id, 'osuid')


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


def get_user(u: str, mode: int = 0) -> Optional[osu.User]:
    try:
        return requests.post(
            f'{OSU_API_ENDPOINT}get_user',
            params={'k': OSU_API_KEY, 'u': u, 'm': mode}
        ).json()[0]
    except:
        return None


def get_beatmap(beatmapid: str) -> Optional[osu.Beatmap]:
    try:
        return requests.post(f'{OSU_API_ENDPOINT}get_beatmaps', params={'k': OSU_API_KEY, 'b': beatmapid}).json()[0]
    except:
        return None


def get_top_scores(u: str, limit: int) -> List[osu.Score]:
    response = requests.post(
        f'{OSU_API_ENDPOINT}get_user_best',
        params={'k': OSU_API_KEY, 'u': u, 'limit': limit}
    )
    try:
        topScores = response.json()
        for i, score in enumerate(topScores):
            score["ranking"] = i
        return topScores
    except:
        logger.critical(f'get_user_best api call failed! Reponse: {response.text}')
        return []


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
osu_auto_update.start()
bot.run(TOKEN)
