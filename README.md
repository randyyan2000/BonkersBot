My first attempt at making discord bot :D

To be used personally (and maybe by a few friends) to track new scores for osu

Using Ameo's [osu!track api](https://github.com/Ameobea/osutrack-api) for osu!track updates and also [osu!api v1](https://github.com/ppy/osu-api/wiki) for getting beatmap, score, and user data.

### TODO 
- [X]  support auto updates in multiple servers (also start auto update on_ready) (this also means users need to keep track of what guild they're in)
- [x]  support usernames with spaces
- [ ]  update score embed difficulties based on enabled mods (dt/ht, hr/ez)
- [ ]  support any tr range, chunk scores by 10 to stay below embed size limit
- [ ]  format numbers with commas
- [ ]  add a $honk command
- [ ]  better error handling for invalid arguments/usage documentation
- [X]  add command for displaying beatmap info 
- [ ]  add per beatmap score leaderboard for guild members
- [ ]  add rotating logging handler
