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

def mod_string(modnum):
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
        return 'NM'


def profile_thumb(osuid):
    return f'http://s.ppy.sh/a/{osuid}'

def profile_link(osuid):
    return f'https://osu.ppy.sh/users/{osuid}'

def beatmap_thumb(beatmapsetid):
    return f'https://b.ppy.sh/thumb/{beatmapsetid}l.jpg'

def beatmap_link(beatmapid):
    return f'https://osu.ppy.sh/b/{beatmapid}'
