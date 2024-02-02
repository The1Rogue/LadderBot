

import asyncio
import json
import datetime

import discord
import requests
import sqlite3

con = sqlite3.connect('ladder.db')
cur = con.cursor()

KNOWN_GUILDS = [1201101141115674694]#, 176389490762448897]
bot = discord.Bot()

CONFIG = {}
RANKS = {}
BOTTOM_RANK = None

with open("token.txt") as file:
    token = file.read()

def loadConfig():
    """Loads config and rank data"""
    global CONFIG, RANKS, BOTTOM_RANK
    with open("config.json") as f:
        CONFIG = json.load(f)

    with open("ranks.json") as f:
        RANKS = json.load(f)

    BOTTOM_RANK = ""
    s = 999
    for i in RANKS:
        if RANKS[i]["minScore"] < s:
            s = RANKS[i]["minScore"]
            BOTTOM_RANK = i

def saveConfig():
    """Saves config and rank data"""
    with open("config.json", "w") as f:
        json.dump(CONFIG, f)

    with open("ranks.json", "w") as f:
        json.dump(RANKS, f)

def gameValid(game: dict) -> bool:
    """Checks if a game's settings are correct"""
    for i in CONFIG["gameSettings"]:
        if game[i] != CONFIG["gameSettings"][i]:
            return False
    return True

def getTrueScore(score: float, lastplayed: int) -> float:
    """Get the score with decay deducted"""
    if lastplayed == 0:
        return score
    inactive = int(datetime.datetime.utcnow().timestamp()) - lastplayed
    days = inactive // CONFIG["decayTime"]
    return max(score - days * CONFIG["decayValue"], 0)

def getRank(score: float) -> str:
    """Get the rank a score belongs into"""
    global BOTTOM_RANK
    s = -1
    r = None
    for i in RANKS:
        if s < RANKS[i]["minScore"] < score:
            s = RANKS[i]["minScore"]
            r = i
    return r if r is not None else BOTTOM_RANK

def win(player: str):
    """Update player data with a win"""
    u = cur.execute("SELECT score, lastplayed FROM PLAYERS WHERE playtak = ?", (player,)).fetchone()
    s = getTrueScore(u[0], u[1])
    r = getRank(s)

    cur.execute("UPDATE PLAYERS SET score = ?, lastplayed = ? WHERE playtak = ?",
                (s + RANKS[r]["win"], int(datetime.datetime.utcnow().timestamp()), player))
    con.commit()

def lose(player: str):
    """Update player data with a loss"""
    u = cur.execute("SELECT score, lastplayed FROM PLAYERS WHERE playtak = ?", (player,)).fetchone()
    s = getTrueScore(u[0], u[1])
    r = getRank(s)

    cur.execute("UPDATE PLAYERS SET score = ?, lastplayed = ? WHERE playtak = ?",
                (max(s - RANKS[r]["loss"], 0), int(datetime.datetime.utcnow().timestamp()), player))
    con.commit()

def draw(player: str):
    """update player data with a draw"""
    pass

@bot.slash_command(guild_ids=KNOWN_GUILDS)
async def manual(ctx, player_white: str, player_black: str, result: str, game_id: int = 0):
    """Report a game manually for the ladder"""
    await ctx.defer()
    r = cur.execute("SELECT discordID FROM PLAYERS WHERE playtak = ?", (player_white,)).fetchone()
    if r is None:
        return await ctx.respond(f"Player {player_white} is not yet registered in the ladder")

    #verify player black exists
    r = cur.execute("SELECT discordID FROM PLAYERS WHERE playtak = ?", (player_black,)).fetchone()
    if r is None:
        return await ctx.respond(f"Player {player_black} is not yet registered in the ladder")

    match result:
        case "R-0" | "F-0" | "1-0":
            win(player_white)
            lose(player_black)

        case "0-R" | "0-F" | "0-1":
            lose(player_white)
            win(player_black)

        case "1/2-1/2":
            draw(player_white)
            draw(player_black)

        case result:
            return await ctx.respond(f"{result} is not a valid result")

    if game_id != 0:
        #verify a game with id does not already exist
        r = cur.execute("SELECT id FROM GAMES WHERE id = ?", (game_id,))
        if r.fetchone() is not None:
            return await ctx.respond(f"A game with id {game_id} has already been reported! (please use id 0 for over the board games)")

    cur.execute("INSERT INTO GAMES VALUES(?,?,?,?,?)",
                (game_id, int(datetime.datetime.utcnow().timestamp()), player_white, player_black, result))
    con.commit()
    return await ctx.respond(f"Successfully registered game \"{player_white} - {player_black}\" as {result}!")

@bot.slash_command(guild_ids=KNOWN_GUILDS)
async def report(ctx, game_id: int):
    """Report a game with a given id for the ladder"""
    await ctx.defer()
    r = requests.get(f"https://api.playtak.com/v1/games-history?id={game_id}").json()
    #verify game exists (or if there are somehow duplicates)
    if r["total"] != 1:
        return await ctx.respond(f"Could not report, found {r['total']} games with id {game_id}")

    game = r["items"][0]
    pw = game["player_white"]
    pb = game["player_black"]

    #verify player white exists
    r = cur.execute("SELECT discordID FROM PLAYERS WHERE playtak = ?", (pw,)).fetchone()
    if r is None:
        return await ctx.respond(f"Player {pw} is not yet registered in the ladder")

    #verify player black exists
    r = cur.execute("SELECT discordID FROM PLAYERS WHERE playtak = ?", (pb,)).fetchone()
    if r is None:
        return await ctx.respond(f"Player {pb} is not yet registered in the ladder")

    #verify game settings
    if not gameValid(game):
        return await ctx.respond(f"The game settings were not correct, please check if you reported the correct game\nif you would still like to submit it, please report manually")

    match game["result"]:
        case "R-0" | "F-0" | "1-0":
            win(pw)
            lose(pb)

        case "0-R" | "0-F" | "0-1":
            lose(pb)
            win(pw)

        case "1/2-1/2":
            draw(pw)
            draw(pb)

        case result:
            return await ctx.respond(f"{result} is an invalid game result, something weird is going on here.....")

    #verify a game with id does not already exist
    r = cur.execute("SELECT id FROM GAMES WHERE id = ?", (game_id,))
    if r.fetchone() is not None:
        return await ctx.respond(f"A game with id {game_id} has already been reported!")

    cur.execute("INSERT INTO GAMES VALUES(?,?,?,?,?)", (game_id, game["date"], pw, pb, game["result"]))
    con.commit()
    return await ctx.respond(f"Successfully registered game \"{pw} - {pb}\" as {game['result']}!")

@bot.slash_command(guild_ids=KNOWN_GUILDS)
async def register(ctx, playtak_name: str):
    """Register with your playtak username"""

    # verify player does not overlap
    r = cur.execute("SELECT discordID, playtak FROM PLAYERS WHERE playtak = ? OR discordID = ?", (playtak_name, ctx.author.id))
    user = r.fetchone()
    if user is not None:
        return await ctx.respond(f"User <@{user[0]}> is already registered as {user[1]}")

    cur.execute("INSERT INTO PLAYERS VALUES(?,?,?,?)", (ctx.author.id, playtak_name, CONFIG["defaultScore"], 0))
    con.commit()
    await ctx.respond(f"Successfully registered you as {playtak_name}!")

@bot.slash_command(guild_ids=KNOWN_GUILDS)
async def deregister(ctx):
    """Deregisters you, resets your score!"""

    cur.execute("DELETE FROM PLAYERS WHERE discordID = ?", (ctx.author.id,))
    con.commit()
    await ctx.respond("Successfully deregistered you!")

@bot.slash_command(guild_ids=KNOWN_GUILDS)
async def rank(ctx, name=None):
    """Get your (or someone elses) rank"""
    if name is None:
        u = cur.execute("SELECT score, lastplayed FROM PLAYERS WHERE discordID = ?", (ctx.author.id,)).fetchone()
        if u is None:
            return await ctx.respond("You aren't registered yet!")
    else:
        u = cur.execute("SELECT score, lastplayed FROM PLAYERS WHERE playtak = ?", (name,)).fetchone()
        if u is None:
            return await ctx.respond(f"No player with the name {name} is registered!")

    s = getTrueScore(u[0], u[1])
    r = getRank(s)
    out = f"# {ctx.author.display_name}" if name is None else f"# {name}"
    out += f"\n**Rank**: {r}\n**Score**: {s}"
    now = int(datetime.datetime.utcnow().timestamp())
    if now - u[1] > CONFIG["decayTime"]:
        out += " (inactive)"
    await ctx.respond(out)

@bot.slash_command(guild_ids=KNOWN_GUILDS)
async def standings(ctx):
    """Get all the rankings"""
    await ctx.defer()

    players = cur.execute("SELECT playtak, score, lastplayed FROM PLAYERS").fetchall()
    ranking = {i: [] for i in RANKS}
    inactive = []
    now = int(datetime.datetime.utcnow().timestamp())
    for player in players:
        s = getTrueScore(player[1], player[2])
        r = getRank(s)
        ranking[r].append(player[0])
        if now - player[2] > CONFIG["decayTime"]:
            inactive.append(player[0])
    out = "# CURRENT STANDINGS\n"
    for i in ranking:
        if len(ranking[i]) > 0:
            out += f"- :{RANKS[i]['icon']}: **{i}**: {', '.join(ranking[i])}\n"

    if len(inactive) > 0:
        out += f"\n**Inactive**: {', '.join(inactive)}"

    await ctx.respond(out)

@bot.slash_command(guild_ids=KNOWN_GUILDS)
async def recent(ctx, n: int = 5):
    """Get recently played games"""
    await ctx.defer()
    r = cur.execute("SELECT * FROM GAMES ORDER BY date DESC LIMIT ?", (n,)).fetchall()
    out = "# Recent games:\n"
    for i in r:
        out += f" - {i[2]} vs. {i[3]} ({i[4]})"
        out += f"[ptn.ninja](https://playtak.com/games/{i[0]}/ninjaviewer)\n" if i[0] != 0 else "\n"
    await ctx.respond(out)

loadConfig()
asyncio.run(bot.start(token))
