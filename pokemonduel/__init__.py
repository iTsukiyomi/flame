from .commands import PokemonDuel

guildowner=1234

async def setup(bot):
    await bot.add_cog(PokemonDuel(bot))
