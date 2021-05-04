from json.decoder import JSONDecodeError
import logging
from typing import Any, Dict, Final, Literal, Mapping, Optional, Type, TypedDict, Union, overload
import os
import json

from discord.guild import Guild

logger = logging.getLogger('discord')
USER_DATA: Final = 'users.json'
GUILD_DATA: Final = 'guilds.json'

UserDataFilenameType = Literal['users.json']
GuildDataFilenameType = Literal['guilds.json']
FilenameType = Union[UserDataFilenameType, GuildDataFilenameType]


UserID = Union[str, int]
GuildID = Union[str, int]


class UserData(TypedDict, total=False):
    osuid: str
    bonks: int
    guilds: list[int]


UserDataKey = Literal['osuid', 'bonks', 'guilds']


class GuildData(TypedDict, total=False):
    osu_update_channel: int
    prefix: str


GuildDataKey = Literal['osu_update_channel', 'prefix']


@overload
def read_all_data(filename: UserDataFilenameType) -> Dict[UserID, UserData]: ...


@overload
def read_all_data(filename: GuildDataFilenameType) -> Dict[GuildID, GuildData]: ...


def read_all_data(filename: str) -> Union[Dict[UserID, UserData], Dict[GuildID, GuildData]]:
    with open(filename, "a+") as fp:
        try:
            fp.seek(0)
            allData = json.load(fp)
        except JSONDecodeError as e:
            if os.path.getsize(filename):
                # issue with json file, dump contents and rewrite
                fp.seek(0)
                contents = fp.read()
                logger.critical(f'Corrupted data for file {filename}! File contents: {contents}')
            else:
                logger.warning(logging.WARNING, f'File empty: {filename}')
                pass
            allData = {}
    return allData


@overload
def read_data(filename: UserDataFilenameType, *, id: UserID, key: str) -> Any: ...


@overload
def read_data(filename: GuildDataFilenameType, *, id: GuildID, key: str) -> Any: ...


def read_data(filename: FilenameType, *, id: Union[int, str], key: str):
    allData = read_all_data(filename)
    userData = allData[f'{id}'] if f'{id}' in allData else {}
    return userData[key] if key in userData else None


@overload
def read_user_data(uid: UserID, key: Literal["osuid"]) -> Optional[str]: ...


@overload
def read_user_data(uid: UserID, key: Literal["bonks"]) -> Optional[int]: ...


@overload
def read_user_data(uid: UserID, key: Literal["guilds"]) -> Optional[list[int]]: ...


def read_user_data(uid: UserID, key: UserDataKey) -> Optional[Any]:
    return read_data(USER_DATA, id=uid, key=key)


def read_guild_data(gid: GuildID, key: GuildDataKey) -> Optional[str]:
    return read_data(GUILD_DATA, id=gid, key=key)


@overload
def write_data(filename: UserDataFilenameType, id: UserID, data: UserData, truncate: bool = False) -> None: ...


@overload
def write_data(filename: GuildDataFilenameType, id: GuildID, data: GuildData, truncate: bool = False) -> None: ...


def write_data(
    filename: FilenameType,
    id: Union[int, str],
    data,
    truncate: bool = False
) -> None:
    allData = read_all_data(filename)
    userData: Union[UserData, GuildData] = allData[f'{id}'] if f'{id}' in allData else {}
    if truncate:
        userData = data
    else:
        userData.update(data)
    # TODO: maybe fix this when PEP type support is expanded or maybe never
    allData[f'{id}'] = userData  # type: ignore
    with open(filename, "w+") as fp:
        json.dump(allData, fp, sort_keys=True, indent=4)


def write_user_data(uid: UserID, data: UserData = {}, truncate: bool = False) -> None:
    write_data(USER_DATA, uid, data, truncate)


def write_guild_data(gid: GuildID, data: GuildData = {}, truncate: bool = False) -> None:
    write_data(GUILD_DATA, gid, data, truncate)
