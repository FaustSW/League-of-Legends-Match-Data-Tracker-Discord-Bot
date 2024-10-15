import aiohttp
import asyncio

RIOT_API_KEY = '<PERSONAL API KEY HERE>'
SUMMONER_ID = '<This is where your personal acc summoner ID would go if you want to keep that functionality>'
BASE_URL = 'https://NA1.api.riotgames.com/lol/spectator/v5/active-games/by-summoner'
MATCH_URL = 'https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid'
INTERVAL = 10  # Check every 10 seconds

# To keep track of Sourcewalker's game state
game_in_progress = False
current_game_id = None  # Track the current game ID to query results when it ends

async def check_spectator(channel):
    global game_in_progress, current_game_id

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                url = f'{BASE_URL}/{SUMMONER_ID}'
                headers = {"X-Riot-Token": RIOT_API_KEY}
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        game_data = await response.json()

                        if not game_in_progress:
                            game_in_progress = True
                            current_game_id = game_data['gameId']  # Track the game ID
                            await channel.send(":Meditate: Sourcewalker is in a game now! Monitoring... :YiStare:")

                    elif response.status == 404:
                        # No active game found, check if a game was in progress previously
                        if game_in_progress:
                            game_in_progress = False
                            await asyncio.sleep(30) # Wait 30 seconds for the API to update
                            result, deaths = await check_match_result(current_game_id, session)  # Check the result of the game
                            await channel.send(f":babyrageyi: Sourcewalker's game just ended! {result}")
                            await channel.send(f":YiLUL: Amount of times Sourcewalker died: {deaths} :copium:")
                            await track_rank_after_game(current_game_id)
        except Exception as e:
            await channel.send(f"An error occurred in the spectator check: {str(e)}")

        # Wait for 10 seconds before checking again
        await asyncio.sleep(INTERVAL)

async def check_match_result(game_id, session):
    try:
        # Get the most recent match details using the puuid
        match_url = f'{MATCH_URL}/{SUMMONER_ID}/ids?start=0&count=1'
        headers = {"X-Riot-Token": RIOT_API_KEY}
        async with session.get(match_url, headers=headers) as match_response:
            if match_response.status == 200:
                match_ids = await match_response.json()
                if match_ids:
                    match_id = match_ids[0]
                    match_detail_url = f'https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}'
                    async with session.get(match_detail_url, headers=headers) as match_detail_response:
                        if match_detail_response.status == 200:
                            match_data = await match_detail_response.json()
                            for participant in match_data['info']['participants']:
                                if participant['puuid'] == SUMMONER_ID:
                                    deaths = participant['deaths']  # Get number of deaths
                                    if participant['win']:
                                        return "Sourcewalker's team won!", deaths
                                    else:
                                        return "Sourcewalker's team lost!", deaths
            return "Unable to determine match result.", 0
    except Exception as e:
        return f"Error: {str(e)}", 0
