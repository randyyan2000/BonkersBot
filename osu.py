from typing import TypedDict

from typing_extensions import Literal

# osu types (mostly mirrors osu api/ameo api documentation) with exceptions commented
# https://github.com/ppy/osu-api/wiki https://github.com/Ameobea/osutrack-api
ScoreRank = Literal['D', 'C', 'B', 'A', 'S', 'SH', 'X', 'SS', 'XH', 'SSH']


class Beatmap(TypedDict):
    submit_date          : str      # date submitted, in UTC
    approved_date        : str      # date ranked, in UTC
    artist               : str
    beatmap_id           : int      # beatmap_id is per difficulty
    beatmapset_id        : int      # beatmapset_id groups difficulties into a set
    bpm                  : int
    creator              : str
    creator_id           : int
    difficultyrating     : float    # The amount of stars the map would have ingame and on the website
    diff_aim             : float
    diff_speed           : float
    diff_size            : int      # Circle size value (CS)
    diff_overall         : float    # Overall difficulty (OD)
    diff_approach        : int      # Approach Rate (AR)
    diff_drain           : int      # Health drain (HP)
    hit_length           : int      # seconds from first note to last note not including breaks
    source               : str
    genre_id             : int      # 0 = any, 1 = unspecified, 2 = video game, 3 = anime, 4 = rock, 5 = pop, 6 = other, 7 = novelty, 9 = hip hop, 10 = electronic, 11 = metal, 12 = classical, 13 = folk, 14 = jazz (note that there's no 8)
    language_id          : int      # 0 = any, 1 = unspecified, 2 = english, 3 = japanese, 4 = chinese, 5 = instrumental, 6 = korean, 7 = french, 8 = german, 9 = swedish, 10 = spanish, 11 = italian, 12 = russian, 13 = polish, 14 = other
    title                : str      # song name
    total_length         : int      # seconds from first note to last note including breaks
    version              : str      # difficulty name
    mode                 : int      # game mode, TODO: make separate type for mode?
    tags                 : str      # Beatmap tags separated by spaces.
    rating               : float
    playcount            : int      # Number of times the beatmap was played
    passcount            : int      # Number of times the beatmap was passed, completed (the user didn't fail or retry)
    count_normal         : int
    count_slider         : int
    count_spinner        : int
    max_combo            : int      # The maximum combo a user can reach playing this beatmap


class Score(TypedDict, total=False):
    beatmap_id          : str
    score_id            : str
    score               : int
    maxcombo            : int
    count50             : int
    count100            : int
    count300            : int
    countmiss           : int
    countkatu           : int
    countgeki           : int
    perfect             : Literal[0, 1]     # 1 = maximum combo of map reached, 0 otherwise
    enabled_mods        : int               # bitwise flag representation of mods used. see reference
    user_id             : int
    date                : str               # UTC
    rank                : ScoreRank
    pp                  : float             # float value, 4 decimals
    replay_available    : Literal[0, 1]
    meta                : Beatmap           # beatmap metadata attached to score for use in embeds
    ranking             : int               # -1 to 99 represents the score's ranking within a users top scores (-1 if not a top score)
                                            # present in ameo osu!track update responses
                                            # manually filled in from osu api responses (based on index in get_user_best)


class User(TypedDict):
    user_id              : int
    username             : str
    join_date            : str      # In UTC
    count300             : int      # Total amount for all ranked, approved, and loved beatmaps played
    count100             : int      # Total amount for all ranked, approved, and loved beatmaps played
    count50              : int      # Total amount for all ranked, approved, and loved beatmaps played
    playcount            : int      # Only counts ranked, approved, and loved beatmaps
    ranked_score         : int      # Counts the best individual score on each ranked, approved, and loved beatmaps
    total_score          : int      # Counts every score on ranked, approved, and loved beatmaps
    pp_rank              : int
    level                : float
    pp_raw               : float    # For inactive players this will be 0 to purge them from leaderboards
    accuracy             : float
    count_rank_ss        : int
    count_rank_ssh       : int
    count_rank_s         : int      # Counts for SS/SSH/S/SH/A ranks on maps
    count_rank_sh        : int
    count_rank_a         : int    
    country              : int      # Uses the ISO3166-1 alpha-2 country code naming. See this for more information: https:#en.wikipedia.org/wiki/ISO_3166-1_alpha-2)
    total_seconds_played : int
    pp_country_rank      : int      # The user's rank in the country.


MODS_ENUM = {
    ''    : 0,
    'NF'  : 1,
    'EZ'  : 2,
    'TD'  : 4,
    'HD'  : 8,
    'HR'  : 16,
    'SD'  : 32,
    'DT'  : 64,
    'RX'  : 128,
    'HT'  : 256,
    'NC'  : 512,
    'FL'  : 1024,
    'AT'  : 2048,
    'SO'  : 4096,
    'AP'  : 8192,
    'PF'  : 16384,
    '4K'  : 32768,
    '5K'  : 65536,
    '6K'  : 131072,
    '7K'  : 262144,
    '8K'  : 524288,
    'FI'  : 1048576,
    'RD'  : 2097152,
    'LM'  : 4194304,
    '9K'  : 16777216,
    '10K' : 33554432,
    '1K'  : 67108864,
    '3K'  : 134217728,
    '2K'  : 268435456,
    'V2'  : 536870912,
}

def mod_string(modnum, nm='NM'):
    # e.g. '+HDDT'
    modStrs = []
    for mod in MODS_ENUM:
        if MODS_ENUM[mod] & modnum != 0:
            modStrs.append(mod)
    if len(modStrs):
        if 'NC' in modStrs and 'DT' in modStrs:
            modStrs.remove('DT')
        if 'PF' in modStrs and 'SD' in modStrs:
            modStrs.remove('SD')
        return f'+{"".join(modStrs)}'
    else:
        return nm


def update_score_difficulty(score: Score):

    pass

def profile_thumb(osuid: str) -> str:
    return f'http://s.ppy.sh/a/{osuid}'

def profile_link(osuid: str) -> str:
    return f'https://osu.ppy.sh/users/{osuid}'

def beatmap_thumb(beatmapsetid: str) -> str:
    return f'https://b.ppy.sh/thumb/{beatmapsetid}l.jpg'

def beatmap_link(beatmapid: str) -> str:
    return f'https://osu.ppy.sh/b/{beatmapid}'
