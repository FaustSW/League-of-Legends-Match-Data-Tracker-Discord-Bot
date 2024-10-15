import discord
from discord import app_commands
import datetime
import aiohttp
import asyncio
import time
from collections import deque

from Utils.getChampionNameByID import get_champion_name
from Utils.gamemodes import get_queue_type
from Utils.summonerSpells import get_summoner_spell_name
from Utils.rankValues import calculate_rank_value

# Fetch Riot API key and Discord bot token from environment variables
RIOT_API_KEY = '<personal API key>'
BASE_URL = 'https://americas.api.riotgames.com'
MATCH_URL = 'https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid'
SUMMONER_ID = '<your acc summoner ID>'
NUM_LATEST_MATCHES = 3

# Rate limit parameters
RATE_LIMIT = 10  # Max number of times the command can be used
TIME_WINDOW = 120  # Time window in seconds (2 minutes)
command_usage_times = deque(maxlen=RATE_LIMIT)  # Stores timestamps of command usage

# Get account information by in-game name and tagline
async def account():
    url = f'{BASE_URL}/riot/account/v1/accounts/by-riot-id/Sourcewalker/Faust'
    headers = {"X-Riot-Token": RIOT_API_KEY}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            return None

# Get the last 5 match IDs for the account
async def get_match_ids():
    account_info = await account()
    if account_info:
        puuid = account_info.get('puuid')
        url = f'{BASE_URL}/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=5'
        headers = {"X-Riot-Token": RIOT_API_KEY}
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                return []
    return []

# Get match details for a given match ID
async def get_match_details(match_id):
    url = f'{BASE_URL}/lol/match/v5/matches/{match_id}'
    headers = {"X-Riot-Token": RIOT_API_KEY}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            return None
        
# Get current live game data
async def get_live_game():
    url = f'https://na1.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{SUMMONER_ID}'
    headers = {"X-Riot-Token": RIOT_API_KEY}
    
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                print("No active game found.")
                return None
            else:
                print(f"Unexpected error: {response.status}")
                return None
            return None

# Calculate relative time from game creation timestamp to current time
def get_relative_time(game_creation_timestamp):
    current_time = datetime.datetime.now(datetime.timezone.utc)
    game_creation_time = datetime.datetime.fromtimestamp(game_creation_timestamp / 1000, tz=datetime.timezone.utc)
    time_difference = current_time - game_creation_time

    days = time_difference.days
    seconds = time_difference.seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    if days > 0:
        return f"{days} day(s) ago"
    elif hours > 0:
        return f"{hours} hour(s) ago"
    return f"{minutes} minute(s) ago"

# Function to add the correct suffix to the day
def get_day_with_suffix(day):
    if 11 <= day <= 13:
        return f"{day}th"
    else:
        suffixes = {1: 'st', 2: 'nd', 3: 'rd'}
        return f"{day}{suffixes.get(day % 10, 'th')}"


# Slash command to fetch and display latest match history with rate limiting
@app_commands.command(name="stalkmatches", description="Stalk Sourcewalker's latest match history and see what he's up to")
async def stalkmatches_command(interaction: discord.Interaction):
    current_time = time.time()

    # Remove timestamps older than TIME_WINDOW
    while command_usage_times and current_time - command_usage_times[0] > TIME_WINDOW:
        command_usage_times.popleft()

    # Check if the command is within the rate limit
    if len(command_usage_times) < RATE_LIMIT:
        # Add the current timestamp to the deque
        command_usage_times.append(current_time)

        try:
            match_ids = await get_match_ids()
            if match_ids:
                # Retrieve match details concurrently for each match ID
                tasks = [get_match_details(match_id) for match_id in match_ids]
                match_details_list = await asyncio.gather(*tasks)
                match_details_list = [details for details in match_details_list if details]

                # Sort matches by game creation time (newest first)
                match_details_list.sort(key=lambda match: match['info']['gameCreation'], reverse=True)
                latest_match_details = match_details_list[:NUM_LATEST_MATCHES]

                if latest_match_details:
                    message = f"Latest 3 matches for Sourcewalker:\n"
                    embeds = []
                    for match in latest_match_details:
                        # Get relative time
                        relative_time = get_relative_time(match['info']['gameCreation'])

                        # Get queue type
                        queue_type = get_queue_type(match['info']['queueId'])
                        participant_id = next((p['participantId'] for p in match['info']['participants'] if p['summonerName'] == 'Sourcewalker'), None)
                        if not participant_id:
                            await interaction.response.send_message("Sourcewalker not found in the match.")
                            return
                        
                       # Get Sourcewalker's champion ID and name with emoji
                        champion_id = next(p['championId'] for p in match['info']['participants'] if p['participantId'] == participant_id)
                        champion_name_with_emoji = get_champion_name(champion_id)

                        # Split the champion emoji and name
                        split_result = champion_name_with_emoji.split(' ', 1)
                        if len(split_result) == 2:
                            emoji, actual_champion_name = split_result
                        else:
                            actual_champion_name = split_result[0]

                        # Get Win/Loss
                        win = next(p['win'] for p in match['info']['participants'] if p['participantId'] == participant_id)
                        result = "Win" if win else "Loss"

                        # Get enemy and ally champions
                        source_team_id = next((p['teamId'] for p in match['info']['participants'] if p['summonerName'] == 'Sourcewalker'), None)
                        if source_team_id is None:
                            await interaction.response.send_message("Sourcewalker not found in the match.")
                            return

                        ally_champions = []
                        enemy_champions = []

                        # Loop through participants to gather ally and enemy champions
                        for participant in match['info']['participants']:
                            champ_name_with_emoji = get_champion_name(participant['championId'])
                            if participant['teamId'] == source_team_id:
                                if participant['summonerName'] == 'Sourcewalker':
                                    # Bold and underline only Sourcewalker's champion name (excluding emoji)
                                    emoji, champ_name = champ_name_with_emoji.split(' ', 1)
                                    formatted_champion = f"{emoji} __**{champ_name}**__"
                                    ally_champions.append(formatted_champion)
                                else:
                                    ally_champions.append(champ_name_with_emoji)
                            else:
                                enemy_champions.append(champ_name_with_emoji)

                        # Join ally and enemy champions as strings
                        ally_champions_str = ', '.join(ally_champions)
                        enemy_champions_str = ', '.join(enemy_champions)

                        # Get CS total and CS per minute
                        total_minions_killed = next((p['totalMinionsKilled'] for p in match['info']['participants'] if p['participantId'] == participant_id), 0)
                        neutral_minions_killed = next((p['neutralMinionsKilled'] for p in match['info']['participants'] if p['participantId'] == participant_id), 0)
                        cs_total = total_minions_killed + neutral_minions_killed

                        game_duration_seconds = match['info']['gameDuration']
                        game_duration_minutes, game_duration_seconds = divmod(game_duration_seconds, 60)

                        cs_per_minute = cs_total / (game_duration_minutes if game_duration_minutes > 0 else 1)

                        # Get KDA
                        participant = next(p for p in match['info']['participants'] if p['participantId'] == participant_id)
                        kills = participant['kills']
                        deaths = participant['deaths']
                        assists = participant['assists']
                        kda = f"{kills}/{deaths}/{assists}"

                        # Change embed color based on win or loss
                        embed_color = discord.Color.blue() if win else discord.Color.red()

                        # Get the user who sent the command
                        requested_by = interaction.user.name
                        avatar_url = interaction.user.avatar.url

                        # Get current date and time for footer
                        now = datetime.datetime.now()
                        month = now.strftime("%B")
                        day_with_suffix = get_day_with_suffix(now.day)
                        nowtime = now.strftime("at %I:%M %p")
                        formatted_time = f"{month} {day_with_suffix}, {nowtime}"

                        # Assemble message
                        embed = discord.Embed(
                            title=f"Match Details",
                            color=embed_color
                        )
                        embed.description = f"View full match details on [OP.GG](https://op.gg/summoners/na/Sourcewalker-Faust)"

                        # Set the champion icon thumbnail in the embed
                        embed.set_thumbnail(url=f"https://cdn.communitydragon.org/latest/champion/{champion_id}/square")

                        embed.add_field(name="Queue Type", value=queue_type, inline=True)
                        embed.add_field(name="Win/Loss", value=result, inline=True)
                        embed.add_field(name="Champion Picked", value=actual_champion_name, inline=True)
                        embed.add_field(name="Duration", value=f"{game_duration_minutes}m {game_duration_seconds}s", inline=False)
                        embed.add_field(name="KDA", value=kda, inline=True)
                        embed.add_field(name="CS Total", value=cs_total, inline=True)
                        embed.add_field(name="CS/min", value=f"{cs_per_minute:.2f}", inline=True)
                        embed.add_field(name="Ally Champions", value=ally_champions_str, inline=False)
                        embed.add_field(name="Enemy Champions", value=enemy_champions_str, inline=True)
                        embed.add_field(name="Time Ago", value=relative_time, inline=False)

                        embed.set_footer(text=f"Requested by {requested_by} • {formatted_time} ", icon_url=avatar_url)

                        embeds.append(embed)

                    await interaction.response.send_message(embeds=embeds)
                else:
                    await interaction.response.send_message("No match details found.")
            else:
                await interaction.response.send_message("Sourcewalker was not found. Stuck in plat probably")
        except Exception as e:
            print(f"Error: {e}")
            await interaction.followup.send("An error occurred while processing the command.", ephemeral=True)
    else:
        # Deny the command if rate limit is reached
        await interaction.response.send_message(f"Rate limit reached: You can only run this command {RATE_LIMIT} times every {TIME_WINDOW // 60} minutes.")


# Slash command to fetch and display live game stats
@app_commands.command(name="livegame", description="Get live stats of Sourcewalker's current game")
async def livegame_command(interaction: discord.Interaction):
    try:
        game_data = await get_live_game()
        
        if game_data:
            participants = game_data['participants']

            # Find Sourcewalker in the participants list
            sourcewalker_data = next((p for p in participants if p.get('riotId', '').lower() == 'sourcewalker#faust'), None)
            
            if not sourcewalker_data:
                await interaction.response.send_message("Sourcewalker is not in the current game.")
                return

            # Get queue type and game duration
            queue_type = get_queue_type(game_data['gameQueueConfigId'])
            game_duration = game_data['gameLength'] // 60  # Convert seconds to minutes

            # Get champion played
            champion_id = sourcewalker_data['championId']
            champion_name = get_champion_name(champion_id)

            # Get summoner spells
            spell1_id = sourcewalker_data['spell1Id']
            spell2_id = sourcewalker_data['spell2Id']
            spell_1_emoji, spell_1_name = get_summoner_spell_name(spell1_id)
            spell_2_emoji, spell_2_name = get_summoner_spell_name(spell2_id)

            # Get enemy and ally champions
            source_team_id = sourcewalker_data['teamId']
            ally_champions = []
            enemy_champions = []

            for participant in participants:
                champ_name_with_emoji = get_champion_name(participant['championId'])
                if participant['teamId'] == source_team_id:
                    if participant['riotId'] == 'Sourcewalker#Faust':
                        # Bold and underline only Sourcewalker's champion name (excluding emoji)
                        emoji, champ_name = champ_name_with_emoji.split(' ', 1)
                        formatted_champion = f"{emoji} __**{champ_name}**__"
                        ally_champions.append(formatted_champion)
                    else:
                        ally_champions.append(champ_name_with_emoji)
                else:
                    enemy_champions.append(champ_name_with_emoji)

            # Join ally and enemy champions as strings
            ally_champions_str = ', '.join(ally_champions)
            enemy_champions_str = ', '.join(enemy_champions)

            # Get banned champions
            banned_champions = game_data.get('bannedChampions', [])
            if banned_champions:
                banned_champions_emojis = []
                for ban in banned_champions:
                    champion_emoji = get_champion_name(ban['championId']).split(' ')[0]
                    banned_champions_emojis.append(champion_emoji)
                
                banned_champs_str = ' | '.join(banned_champions_emojis)
            else:
                banned_champs_str = "None"

            # Get requestor name and pfp
            requested_by = interaction.user.name
            avatar_url = interaction.user.avatar.url

            # Get current date and time for footer
            now = datetime.datetime.now()
            month = now.strftime("%B")
            day_with_suffix = get_day_with_suffix(now.day)
            nowtime = now.strftime("at %I:%M %p")
            formatted_time = f"{month} {day_with_suffix}, {nowtime}"

            # Embed message
            embed = discord.Embed(
                title="Live Game Stats for Sourcewalker",
                description=f"Queue Type: {queue_type}",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=f"https://cdn.communitydragon.org/latest/champion/{champion_id}/square")

            embed.add_field(name="Champion Picked", value=champion_name, inline=True)
            embed.add_field(name="Summoner Spells", value=f"{spell_1_emoji} {spell_1_name} **|** {spell_2_emoji} {spell_2_name}", inline=True)
            embed.add_field(name="Game Duration", value=f"{game_duration} minutes", inline=True)
            embed.add_field(name="Ally Champions", value=ally_champions_str, inline=False)
            embed.add_field(name="Enemy Champions", value=enemy_champions_str, inline=False)
            embed.add_field(name="Banned Champions", value=banned_champs_str, inline=False)

            embed.set_footer(text=f"Requested by {requested_by} • {formatted_time} ", icon_url=avatar_url)
            
            await interaction.response.send_message(embed=embed)

        else:
            await interaction.response.send_message("Sourcewalker is not currently in a live game.", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"An error occurred while processing the command: {str(e)}", ephemeral=True)
