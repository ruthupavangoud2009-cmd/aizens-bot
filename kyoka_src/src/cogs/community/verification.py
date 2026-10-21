from __future__ import annotations

import discord
from discord.ext import commands
from src.core.config import Config

OWNER_ID = 1505515188991033409

class VerifyButton(discord.ui.View):
    """Persistent verification button; role ID is stored in the button's custom_id."""
    def __init__(self, role_id: int):
        super().__init__(timeout=None)
        button = discord.ui.Button(label="Verify", style=discord.ButtonStyle.primary,
                                   emoji="✅", custom_id=f"kyoka:verify:{role_id}")
        button.callback = self._callback
        self.add_item(button)

    async def _callback(self, interaction: discord.Interaction):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Use this button inside the server.", ephemeral=True)
        try:
            role_id = int(interaction.data.get("custom_id", "").rsplit(":", 1)[1])
        except (ValueError, AttributeError, IndexError):
            return await interaction.response.send_message("This verification panel is invalid. Ask staff to repost it.", ephemeral=True)
        role = interaction.guild.get_role(role_id)
        if role is None:
            return await interaction.response.send_message("The verification role no longer exists. Ask staff to configure it again.", ephemeral=True)
        if role in interaction.user.roles:
            return await interaction.response.send_message("You're already verified. ✅", ephemeral=True)
        me = interaction.guild.me
        if not me or not me.guild_permissions.manage_roles or role >= me.top_role:
            return await interaction.response.send_message("The bot needs Manage Roles, and its role must be above the verification role.", ephemeral=True)
        try:
            await interaction.user.add_roles(role, reason="KYOKA verification button")
        except discord.Forbidden:
            return await interaction.response.send_message("I couldn't assign that role. Ask an administrator to check role permissions.", ephemeral=True)
        await interaction.response.send_message("Verification complete. Welcome! ✅", ephemeral=True)

class Verification(commands.Cog):
    """Aizen-themed button verification panel. Server role permissions gate protected channels."""
    category = "Security"

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="verifypanel", help="Post a verification panel: &verifypanel @Verified")
    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    async def verifypanel(self, ctx: commands.Context, role: discord.Role):
        if role.is_default() or role.managed:
            return await ctx.reply("Choose a normal member role, not @everyone or an integration role.", mention_author=False)
        if role >= ctx.guild.me.top_role:
            return await ctx.reply("Move my bot role above the verification role first.", mention_author=False)
        embed = discord.Embed(
            title="🛡️ AIZEN SECURITY • VERIFICATION",
            description=("This server uses verification to help protect its community.\n\n"
                         "Press **Verify** below to receive access. No website or password is required."),
            color=Config.COLORS.PRIMARY)
        embed.add_field(name="Secure access", value="Only the configured server role grants access to protected channels.", inline=False)
        embed.set_footer(text=Config.FOOTER_TEXT)
        view = VerifyButton(role.id)
        await ctx.send(embed=embed, view=view)
        # Register this view in-process so its button also works after message edits/restarts
        self.bot.add_view(VerifyButton(role.id))

    @verifypanel.error
    async def verifypanel_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("Administrator permission is required to configure verification.", mention_author=False)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("Usage: `&verifypanel @VerifiedRole`", mention_author=False)
        elif isinstance(error, commands.BadArgument):
            await ctx.reply("Mention a valid role. Example: `&verifypanel @Verified`", mention_author=False)
        else:
            raise error

async def setup(bot):
    await bot.add_cog(Verification(bot))
