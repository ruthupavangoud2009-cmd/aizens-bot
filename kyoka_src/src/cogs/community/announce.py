from __future__ import annotations

import discord
from discord.ext import commands

from src.core.config import Config


class Announce(commands.Cog):
    """Simple, permission-checked channel announcements."""
    category = "Community"

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="announce", aliases=["sayto", "announcement"],
                      help="Send a message to a channel: &announce #welcome hi")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def announce(self, ctx: commands.Context, channel: discord.TextChannel, *, message: str):
        if channel.guild.id != ctx.guild.id:
            return await ctx.reply("Choose a channel from this server.", mention_author=False)
        embed = discord.Embed(description=message[:4000], color=Config.COLORS.PRIMARY)
        embed.set_author(name=f"{ctx.author.display_name} • Announcement", icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=Config.FOOTER_TEXT)
        try:
            await channel.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        except discord.Forbidden:
            return await ctx.reply(f"I can't send messages or embeds in {channel.mention}. Check my channel permissions.", mention_author=False)
        await ctx.reply(f"Announcement sent to {channel.mention}.", mention_author=False, delete_after=8)

    @announce.error
    async def announce_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("You need **Manage Server** permission to announce.", mention_author=False)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("Usage: `&announce #welcome hi`", mention_author=False)
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("I couldn't find that channel. Usage: `&announce #welcome hi`", mention_author=False)
        else:
            raise error


async def setup(bot):
    await bot.add_cog(Announce(bot))
