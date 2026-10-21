from __future__ import annotations

import asyncio
import random
import re
import discord
from discord.ext import commands


class CommunityExtra(commands.Cog):
    """Persistent community games, shared vouches, per-server named bills and safe fun commands."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games: dict[int, dict] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    async def cog_load(self):
        await self.bot.db.execute("""
            CREATE TABLE IF NOT EXISTS kyoka_vouches (
                id BIGSERIAL PRIMARY KEY, guild_id BIGINT NOT NULL, voucher_id BIGINT NOT NULL,
                vouchee_id BIGINT NOT NULL, details TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )""")
        await self.bot.db.execute("""
            CREATE TABLE IF NOT EXISTS kyoka_bills (
                guild_id BIGINT NOT NULL, bill_name TEXT NOT NULL, bill_text TEXT NOT NULL,
                owner_id BIGINT NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (guild_id, bill_name)
            )""")

    @commands.command(name="guessstart", aliases=["guessgame", "numbergame"])
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def guess_start(self, ctx: commands.Context, answer: int):
        """Start a number guessing game in this channel; the host chooses the secret number."""
        if not 1 <= answer <= 100:
            return await ctx.reply("Choose a secret number from **1 to 100**.", mention_author=False)
        if ctx.channel.id in self.active_games:
            return await ctx.reply("A guessing game is already running in this channel.", mention_author=False)
        self.active_games[ctx.channel.id] = {"answer": answer, "host": ctx.author.id, "guild": ctx.guild.id}
        embed = discord.Embed(title="🎯 Guess the Number", description=(
            f"{ctx.author.mention} is hosting a **1–100** guessing game!\n\n"
            "Send your guess as a number in this channel.\n"
            "➕ = too low · ➖ = too high\n\n"
            "First correct guess wins. The channel will be locked when the game ends."
        ), color=0x00E5FF)
        embed.set_footer(text="Host: secret number chosen • Use the configured prefix + guessstop to cancel")
        await ctx.send(embed=embed)

    @commands.command(name="guessstop")
    @commands.guild_only()
    async def guess_stop(self, ctx: commands.Context):
        game = self.active_games.get(ctx.channel.id)
        if not game:
            return await ctx.reply("There isn't a game running here.", mention_author=False)
        if ctx.author.id != game["host"] and not ctx.author.guild_permissions.manage_channels:
            return await ctx.reply("Only the host or a channel manager can stop this game.", mention_author=False)
        self.active_games.pop(ctx.channel.id, None)
        await ctx.send("🛑 Guessing game cancelled. The channel has not been locked.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.content.strip().isdigit():
            return
        game = self.active_games.get(message.channel.id)
        if not game:
            return
        # Do not treat command invocations or out-of-range numbers as guesses.
        try:
            guess = int(message.content.strip())
        except ValueError:
            return
        if not 1 <= guess <= 100:
            return
        answer = game["answer"]
        try:
            if guess < answer:
                await message.add_reaction("➕")
            elif guess > answer:
                await message.add_reaction("➖")
            else:
                self.active_games.pop(message.channel.id, None)
                await message.add_reaction("🏆")
                await message.channel.send(
                    f"🎉 {message.author.mention} guessed it! The answer was **{answer}**.\n"
                    f"Please DM <@{game['host']}> or open a support ticket to claim your prize.",
                    allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
                )
                try:
                    await message.author.send(
                        f"🏆 You won the number game in **{message.guild.name}**! The answer was **{answer}**.\n"
                        f"To claim your prize, DM the host <@{game['host']}> or create a support ticket in the server."
                    )
                except (discord.Forbidden, discord.HTTPException):
                    await message.channel.send(f"{message.author.mention}, I couldn't DM you—please check your DM privacy settings.")
                try:
                    host = self.bot.get_user(game["host"]) or await self.bot.fetch_user(game["host"])
                    await host.send(f"🎯 Your guessing game in **{message.guild.name}** was won by {message.author} ({message.author.id}). Answer: **{answer}**.")
                except (discord.Forbidden, discord.HTTPException):
                    pass
                # Lock only the current channel's default role; retain other overwrites.
                if isinstance(message.channel, discord.TextChannel):
                    try:
                        await message.channel.set_permissions(message.guild.default_role, send_messages=False, reason="Guessing game finished")
                    except (discord.Forbidden, discord.HTTPException):
                        await message.channel.send("⚠️ I couldn't lock this channel. Please check my Manage Channels permission.")
        except discord.HTTPException:
            pass

    @commands.command(name="billset")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def bill_set(self, ctx: commands.Context, name: str, *, bill_text: str):
        """Save a bill scoped to this server. Example: ?billset yonko_bill Customer: ..."""
        name = name.strip().lower().replace(" ", "_")[:80]
        if not re.fullmatch(r"[a-z0-9_-]+", name):
            return await ctx.reply("Bill names can use letters, numbers, underscores and hyphens.", mention_author=False)
        if len(bill_text) > 3500:
            return await ctx.reply("Bill details must be 3500 characters or fewer.", mention_author=False)
        await self.bot.db.execute("""
            INSERT INTO kyoka_bills (guild_id, bill_name, bill_text, owner_id, updated_at)
            VALUES (?, ?, ?, ?, NOW())
            ON CONFLICT (guild_id, bill_name) DO UPDATE SET bill_text=EXCLUDED.bill_text,
            owner_id=EXCLUDED.owner_id, updated_at=NOW()
        """, ctx.guild.id, name, bill_text, ctx.author.id)
        await ctx.reply(f"✅ Saved bill **{name.replace('_', ' ')}** for this server.", mention_author=False)

    @commands.command(name="bill", aliases=["showbill"])
    @commands.guild_only()
    async def bill_show(self, ctx: commands.Context, *, name: str):
        name = name.strip().lower().replace(" ", "_")[:80]
        row = await self.bot.db.fetch_one("SELECT bill_text, updated_at FROM kyoka_bills WHERE guild_id=? AND bill_name=?", ctx.guild.id, name)
        if not row:
            return await ctx.reply(f"No bill named **{name.replace('_', ' ')}** is saved in this server. Use `{ctx.prefix}billset {name} <details>` to create it.", mention_author=False)
        embed = discord.Embed(title=f"🧾 {name.replace('_', ' ').title()}", description=row["bill_text"], color=0x00E676)
        embed.set_footer(text=f"Server: {ctx.guild.name} • Bills are saved separately per server")
        await ctx.send(embed=embed)

    @commands.command(name="bills")
    @commands.guild_only()
    async def bill_list(self, ctx: commands.Context):
        rows = await self.bot.db.fetch_all("SELECT bill_name FROM kyoka_bills WHERE guild_id=? ORDER BY bill_name", ctx.guild.id)
        if not rows:
            return await ctx.reply("No saved bills in this server yet. Use `billset` to create one.", mention_author=False)
        await ctx.reply("🧾 **Saved bills in this server**\n" + "\n".join(f"• `{r['bill_name']}`" for r in rows[:50]), mention_author=False)

    @commands.command(name="billdelete")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def bill_delete(self, ctx: commands.Context, *, name: str):
        name = name.strip().lower().replace(" ", "_")[:80]
        await self.bot.db.execute("DELETE FROM kyoka_bills WHERE guild_id=? AND bill_name=?", ctx.guild.id, name)
        await ctx.reply(f"🗑️ Deleted bill **{name.replace('_', ' ')}** if it existed.", mention_author=False)

    @commands.command(name="vouch")
    @commands.guild_only()
    async def vouch(self, ctx: commands.Context, member: discord.Member, *, details: str):
        if member.bot or member.id == ctx.author.id:
            return await ctx.reply("You can't vouch for yourself or a bot.", mention_author=False)
        if not details.strip() or len(details) > 800:
            return await ctx.reply("Give a short vouch description (up to 800 characters).", mention_author=False)
        await self.bot.db.execute("INSERT INTO kyoka_vouches (guild_id, voucher_id, vouchee_id, details) VALUES (?,?,?,?)", ctx.guild.id, ctx.author.id, member.id, details.strip())
        await ctx.reply(f"✅ Vouch saved for {member.mention}. Records use the shared database and remain available across servers where KYOKA is installed.", mention_author=False)

    @commands.command(name="vouches", aliases=["vouchcount"])
    @commands.guild_only()
    async def vouches(self, ctx: commands.Context, member: discord.Member | None = None):
        target = member or ctx.author
        row = await self.bot.db.fetch_one("SELECT COUNT(*) AS total FROM kyoka_vouches WHERE vouchee_id=?", target.id)
        rows = await self.bot.db.fetch_all("SELECT details, guild_id FROM kyoka_vouches WHERE vouchee_id=? ORDER BY created_at DESC LIMIT 5", target.id)
        embed = discord.Embed(title=f"🌟 Vouches for {target.display_name}", description=f"**Total vouches across KYOKA servers:** {int(row['total']) if row else 0}", color=0x00E676)
        for i, v in enumerate(rows, 1):
            guild = self.bot.get_guild(int(v['guild_id']))
            embed.add_field(name=f"Recent vouch {i} • {guild.name if guild else 'Other server'}", value=v['details'][:800], inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="coinflip", aliases=["coin"])
    async def coinflip(self, ctx: commands.Context):
        await ctx.reply(f"🪙 **{random.choice(['Heads', 'Tails'])}!**", mention_author=False)

    @commands.command(name="dice", aliases=["roll"])
    async def dice(self, ctx: commands.Context, sides: int = 6):
        if not 2 <= sides <= 100:
            return await ctx.reply("Choose between 2 and 100 sides.", mention_author=False)
        await ctx.reply(f"🎲 You rolled **{random.randint(1, sides)}** (d{sides}).", mention_author=False)

    @commands.command(name="choose")
    async def choose(self, ctx: commands.Context, *, options: str):
        choices = [x.strip() for x in re.split(r",|\bor\b|\|", options, flags=re.I) if x.strip()]
        if len(choices) < 2 or len(choices) > 20:
            return await ctx.reply("Give 2–20 choices separated by commas. Example: `?choose fruit, raids, trading`", mention_author=False)
        await ctx.reply(f"🤔 I choose: **{random.choice(choices)[:200]}**", mention_author=False)

    @commands.command(name="poll")
    @commands.guild_only()
    async def poll(self, ctx: commands.Context, *, question: str):
        if len(question) > 900:
            return await ctx.reply("Poll question must be 900 characters or fewer.", mention_author=False)
        embed = discord.Embed(title="📊 Community Poll", description=question, color=0x00E5FF)
        embed.set_footer(text=f"Poll by {ctx.author.display_name}")
        msg = await ctx.send(embed=embed)
        for emoji in ("👍", "👎"):
            try:
                await msg.add_reaction(emoji)
            except discord.HTTPException:
                break

    @commands.command(name="ping")
    async def fun_ping(self, ctx: commands.Context, count: int = 1, member: discord.Member | None = None):
        """Playful, deliberately rate-limited ping; capped to prevent mention spam."""
        count = max(1, min(count, 5))
        target = member or ctx.author
        if target.bot:
            return await ctx.reply("Let's not ping bots for fun 😅", mention_author=False)
        for i in range(count):
            await ctx.send(f"🔔 {target.mention}", allowed_mentions=discord.AllowedMentions(users=[target], roles=False, everyone=False, replied_user=False))
            if i < count - 1:
                await asyncio.sleep(1.2)

    @commands.command(name="trivia")
    async def trivia(self, ctx: commands.Context):
        question, answer, choices = random.choice([
            ("How many sides does a hexagon have?", "6", "4 • 5 • 6 • 8"),
            ("Which planet is known as the Red Planet?", "mars", "Venus • Mars • Jupiter • Mercury"),
            ("What is 9 × 7?", "63", "56 • 63 • 72 • 81"),
            ("Which ocean is the largest?", "pacific", "Atlantic • Indian • Arctic • Pacific"),
        ])
        await ctx.reply(f"🧠 **Trivia:** {question}\nOptions: {choices}\nAnswer: `{ctx.prefix}answer <your answer>`", mention_author=False)
        self._trivia = getattr(self, "_trivia", {})
        self._trivia[ctx.channel.id] = (answer, ctx.author.id)

    @commands.command(name="answer")
    async def trivia_answer(self, ctx: commands.Context, *, answer: str):
        item = getattr(self, "_trivia", {}).get(ctx.channel.id)
        if not item:
            return await ctx.reply("Start a round with `trivia` first.", mention_author=False)
        if answer.strip().lower() == item[0]:
            self._trivia.pop(ctx.channel.id, None)
            await ctx.reply(f"🏆 Correct, {ctx.author.mention}!", mention_author=False)
        else:
            await ctx.reply("Not quite—try again!", mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(CommunityExtra(bot))
