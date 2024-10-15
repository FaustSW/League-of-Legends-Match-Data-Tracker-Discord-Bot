import discord
from discord import app_commands
from check_spectator import check_spectator
from commands import stalkmatches_command, livegame_command#, stalkrank_command only needed w/sql db rank tracking
import asyncio

# Define bot intents and initialize the client and command tree
intents = discord.Intents.default()
client = discord.Client(intents=intents, reconnect=True)
tree = app_commands.CommandTree(client)

# Register the commands from other files
tree.add_command(stalkmatches_command)
tree.add_command(livegame_command)
#tree.add_command(stalkrank_command) only needed w/sql db rank tracking

@client.event
async def on_ready():
    print(f'\033[32mLogged in as {client.user}\033[0m')
    if not hasattr(client, 'synced'):
        await tree.sync()  # Sync commands with Discord
        client.synced = True  # Ensure we don't sync commands again on reconnect
        print("\033[32mCommands synced.\033[0m")

    # Get the channel to send updates to
    channel = client.get_channel("""<PUT CHANNEL ID HERE>""")
    
    # Start the spectator check task
    client.loop.create_task(check_spectator(channel))

@client.event
async def on_disconnect():
    print("\033[91mBot disconnected, attempting to reconnect...\033[0m")

# Start the bot & handle any exceptions while trying to reconnect
async def run_bot():
    while True:
        try:
            await client.start('<PUT DISCORD BOT TOKEN HERE>')
        except discord.errors.ConnectionClosed:
            print ("\033[91mConnection lost, trying to reconnect in 5 seconds...\033[0m")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\033[93mKeyboardInterrupt detected: Bot shutting down gracefully.\033[0m")
