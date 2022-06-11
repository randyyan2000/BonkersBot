# BonkersBot

My first attempt at making discord bot :D

To be used personally (and some friends) to track new scores for osu.

Using Ameo's [osu!track api](https://github.com/Ameobea/osutrack-api) for osu!track updates and also [osu!api v1](https://github.com/ppy/osu-api/wiki) for getting beatmap, score, and user data.

## Screenshots
Automatic score update:  
![Automatic score update](/screenshots/1.png)  
Profile card:  
![Profile card](/screenshots/2.png)  
... and more!

## Feature Checklist
### TODO 
- [ ]  update score embed difficulties based on enabled mods (dt/ht, hr/ez)
- [ ]  better error handling for invalid arguments/usage documentation
- [ ]  add per beatmap score leaderboard for guild members
- [ ]  add rotating logging handler
- [ ]  automatic type conversion for api response objects AND none/null handling
- [ ]  add support for other osu game modes
  - [X]  done for osu_leaderboard (needs to be made more user friendly i.e. recognizing gamemode name strings)
  

### Completed
- [X]  support usernames with spaces
- [X]  support auto updates in multiple servers (also start auto update on_ready) (this also means users need to keep track of what guild they're in)
- [X]  format numbers with commas
- [X]  add command for displaying beatmap info 
- [X]  support any tr range, chunk scores by 10 to stay below embed size limit
- [X]  add a $honk command, for better or for worse
- [X]  types for osu track api responses
- [X]  command for per server leaderboard (pp, rank)
- [X]  replay download links in score embeds
- [X]  300/100/50/X counts in score embeds
- [X]  add top score rank cutoff for automatic osu updates
- [X]  add osu recent play command 
- [X]  add top score pp cutoff (to reduce low score spam) for automatic osu updates
- [X]  paginate osu leaderboard (controlled with emoji reactions)
