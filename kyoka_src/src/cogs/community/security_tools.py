from __future__ import annotations

import discord
from discord.ext import commands

from src.core.config import Config

class SecurityTools(commands.Cog):
    """Small, transparent security helpers. Server channel permissions remain authoritative."""
    category = "Security"
    def __init__(self, bot):
        self.bot = bot
        self.honeypots: dict[int, int] = {}

    @commands.command(name="sethoneypot", aliases=["honeypot"], help="Configure a decoy channel: &sethoneypot #do-not-type-here")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def set_honeypot(self, ctx: commands.Context, channel: discord.TextChannel):
        self.honeypots[ctx.guild.id] = channel.id
        await ctx.reply(embed=discord.Embed(
            title="Aizen Security • Honeypot configured",
            description=f"{channel.mention} is now monitored as a decoy channel for this bot session. Set channel permissions so normal members should not post there. Suspicious posts are logged and warned; this does not auto-ban users.",
            color=Config.COLORS.PRIMARY).set_footer(text=Config.FOOTER_TEXT), mention_author=False)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        if self.honeypots.get(message.guild.id) != message.channel.id:
            return
        if message.author.guild_permissions.administrator or message.author.guild_permissions.manage_guild:
            return
        try:
            await message.author.send(f"You posted in {message.channel.mention} in **{message.guild.name}**. This is a monitored decoy channel; if this was accidental, contact the server staff.")
        except (discord.Forbidden, discord.HTTPException):
            pass
        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass
        try:
            await message.channel.send(f"{message.author.mention}, this channel is monitored. Please contact staff if this was a mistake.", delete_after=10, allowed_mentions=discord.AllowedMentions(users=True))
        except (discord.Forbidden, discord.HTTPException):
            pass

async def setup(bot):
    await bot.add_cog(SecurityTools(bot))
