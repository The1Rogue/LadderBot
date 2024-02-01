# A bot to manage Ladder games

### available commands:
/register playtak_name\
register a user with their playtak name

/deregister\
deregisters a user, wiping score data, but games played stay logged

/report game_id\
reports a game from playtak with game_id for the ladder

/manual player_white player_black result game_id\
manually reports a game for the ladder, can be used if the bot fails on the game_id.
for over the board games, use this with game_id = 0.

/rank\
returns your current rank and score

/standings\
returns a list of all player standings


### config
config.json allows for easy configuration of the ladder:
defaultScore:\
the score a user gets when they register

decayTime:\
this is how fast decay is applied to users, in seconds.

decayValue:\
for every 'decayTime' a user is inactive, this much is deducted from their score.

gameSettings:\
a dict of settings the games should have to be valid\
LadderBot will only accept reports of games that have these settings.\
naming should follow playtak api standards\

Ranks:\
a dict listing the different ranks and how they behave, in this format:\
lowerbound: \[rankName, gainOnWin, deductOnLoss\]
