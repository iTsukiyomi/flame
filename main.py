import asyncio
import os
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

intents = discord.Intents.default()
intents.members = True
intents.message_content  = True

class Flame(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or(';'),
            intents=intents,
            description='test',
            case_insensitive=True
        )

    async def setup_hook(self):
        print('starting...')
        try:
            await self.load_extension('pokemonduel')
            print('loaded pokeduel')
        except Exception as e:
            print(e)

    async def on_ready(self):
        print(f'{self.user} logged in ')

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"missing arguments `{error.param}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"bro what")
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("no perms bro")
        else:
            logging.error(f"unexpected error in {ctx.command}: {error}")
            await ctx.send("bruh")

async def main():
    bot = Flame()
    token = os.getenv("DISCORD_TOKEN")
    await bot.start(token)

if __name__ == '__main__':
    asyncio.run(main())