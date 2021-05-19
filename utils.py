from typing import List, TypeVar

T = TypeVar('T')


def chunk(list: List[T], chunkSize: int) -> List[List[T]]:
    if chunkSize < 1:
        raise Exception(f'Invalid chunk size {chunkSize}')
    return [list[i * chunkSize:(i + 1) * chunkSize]
            for i in range((len(list) + chunkSize - 1) // chunkSize)]
