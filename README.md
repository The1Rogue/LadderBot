# A bot to manage Ladder games

### Available commands:
/register playtak_name\
Register a user with their playtak name

/deregister\
Deregisters a user, wiping score data, but games played stay logged

/report game_id\
Reports a game from playtak with game_id for the ladder

/manual player_white player_black result game_id\
Manually reports a game for the ladder, can be used if the bot fails on the game_id.
For over the board games, use this with game_id = 0.

/rank name\
If name is left empty, returns your current rank and score,\
otherwise returns the rank and score of the playtak user given by name

/standings\
Returns a list of all player standings

/recent n\
Lists n most recent games, n defaults to 5

### config
config.json allows for easy configuration of the ladder:
defaultScore:\
The score a user gets when they register

decayTime:\
This is how fast decay is applied to users, in seconds.

decayValue:\
For every 'decayTime' a user is inactive, this much is deducted from their score.

gameSettings:\
A dict of settings the games should have to be valid.\
LadderBot will only accept reports of games that have these settings.\
Naming should follow playtak api standards.\

### Ranks
Ranks are listed in their own json file,\
Every rank should have these attributes:
- minScore: the lower bound of this rank
- win: the amount of points a person gains for a win in this rank
- loss: the amount of points a person loses for a loss in this rank
- icon: the name of an emote to use as an icon for this rank