import random
from typing import List

honks: List[str] = [
    'https://tenor.com/view/pepe-clown-honk-honk-honk-red-nose-gif-13876101',
    'https://tenor.com/view/anime-crying-sad-honoka-afraid-gif-5959824',
    'https://tenor.com/view/love-live-honoka-kosaka-clapping-clap-good-job-gif-11917791',
    'https://tenor.com/view/honoka-gif-5514846',
    'https://tenor.com/view/honoka-k%c5%8dsaka-love-live-anime-cute-kawaii-gif-13451449',
    'https://tenor.com/view/honoka-love-live-anime-frown-gif-5514849',
    'https://tenor.com/view/honoka-anime-gif-5514844',
    'https://tenor.com/view/untitled-goose-game-honk-goose-video-game-gif-16337290',
    'https://tenor.com/view/goose-honk-inhale-inhales-untitled-gif-16237480',
    'https://tenor.com/view/truck-horns-driver-gif-8941664',
    'https://tenor.com/view/pepe-peepo-clown-gif-20274815',
    '📯',
    'https://tenor.com/view/untitled-goose-game-ouch-rude-honk-geese-gif-16427770',
    'https://tenor.com/view/pepe-peepo-clown-gif-20274804',
    'https://tenor.com/view/honk-goose-game-untitled-goose-game-flapping-wings-gif-16627067',
    'https://tenor.com/view/statewide-rp-mess-with-the-honk-you-get-the-bonk-baseballbat-untitled-goose-game-gif-17204101',
    'https://tenor.com/view/honoka-pillow-fight-anime-scared-gif-5514851',
    'https://tenor.com/view/chicken-chicken-dance-counter-strike-gif-18590425',
]


def get_honk() -> str:
    return honks[random.randrange(0, len(honks))]
