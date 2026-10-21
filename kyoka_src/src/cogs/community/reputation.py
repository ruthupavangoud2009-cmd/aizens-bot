from __future__ import annotations

import os
import discord
from discord.ext import commands

OWNER_ID = 1505515188991033409
SUPPORT_URL = "https://discord.gg/p6GvJtsMb"


def owner_only():
    async def predicate(ctx: commands.Context) -> bool:
        if ctx.author.id != OWNER_ID:
            raise commands.CheckFailure("This command is restricted to the bot owner.")
        return True
    return commands.check(predicate)


class CommunityReputation(commands.Cog):
    """Prefix-first service bills, community vouches, and Gemini chat for Kyoka."""
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await self.bot.db.execute("""
            CREATE TABLE IF NOT EXISTS kyoka_vouches (
                id BIGSERIAL PRIMARY KEY, guild_id BIGINT NOT NULL,
                voucher_id BIGINT NOT NULL, vouchee_id BIGINT NOT NULL,
                reason TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(guild_id, voucher_id, vouchee_id)
            );
        """)
        await self.bot.db.execute("""
            CREATE TABLE IF NOT EXISTS kyoka_bills (
                id BIGSERIAL PRIMARY KEY, guild_id BIGINT NOT NULL,
                biller_id BIGINT NOT NULL, customer_id BIGINT,
                server_name TEXT NOT NULL, service TEXT NOT NULL,
                apa_tax INTEGER NOT NULL DEFAULT 0, conglomerate_tax INTEGER NOT NULL DEFAULT 0,
                priority_tax INTEGER NOT NULL DEFAULT 0, total_value BIGINT NOT NULL,
                payment TEXT NOT NULL DEFAULT 'Pending', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        await self.bot.db.execute("""
            CREATE TABLE IF NOT EXISTS kyoka_bill_settings (
                guild_id BIGINT PRIMARY KEY, server_name TEXT NOT NULL
            );
        """)

    def owner_check(self, ctx):
        return ctx.author.id == OWNER_ID

    @commands.command(name="vouch", aliases=["rep"])
    @commands.guild_only()
    async def vouch(self, ctx, member: discord.Member, *, reason: str):
        """Vouch for a member: ?vouch @member completed service was fast"""
        if member.bot or member.id == ctx.author.id:
            return await ctx.send("❌ You can't vouch for yourself or a bot.")
        reason = reason.strip()[:500]
        try:
            await self.bot.db.execute(
                "INSERT INTO kyoka_vouches (guild_id, voucher_id, vouchee_id, reason) VALUES ($1,$2,$3,$4) ON CONFLICT (guild_id, voucher_id, vouchee_id) DO UPDATE SET reason = EXCLUDED.reason, created_at = NOW();",
                ctx.guild.id, ctx.author.id, member.id, reason)
        except Exception:
            return await ctx.send("❌ Couldn't save the vouch. Check that the database is connected and updated.")
        embed = discord.Embed(title="✦ Community Vouch Saved", color=0x9B5DE5)
        embed.description = f"**{member.display_name}** received a vouch from {ctx.author.mention}.\n\n**Reason**\n{discord.utils.escape_markdown(reason)}"
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Vouches are community claims, not independent transaction verification.")
        await ctx.send(embed=embed)

    @commands.command(name="vouchlb", aliases=["vouchleaderboard", "replb"])
    @commands.guild_only()
    async def vouch_leaderboard(self, ctx):
        rows = await self.bot.db.fetch_all(
            "SELECT vouchee_id, COUNT(*) AS total FROM kyoka_vouches WHERE guild_id=$1 GROUP BY vouchee_id ORDER BY total DESC, vouchee_id ASC LIMIT 10;", ctx.guild.id)
        embed = discord.Embed(title="🏆 Vouch Leaderboard", color=0x9B5DE5)
        if not rows:
            embed.description = "No vouches yet. Use `?vouch @member reason` to get started."
        else:
            embed.description = "\n".join(f"**{i}.** <@{int(row['vouchee_id'])}> — **{int(row['total'])}** vouch(es)" for i, row in enumerate(rows, 1))
        embed.set_footer(text="Community reputation • Claims are not transaction verification")
        await ctx.send(embed=embed)

    @commands.command(name="vouches", aliases=["repcheck"])
    @commands.guild_only()
    async def vouches(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        rows = await self.bot.db.fetch_all("SELECT voucher_id, reason, created_at FROM kyoka_vouches WHERE guild_id=$1 AND vouchee_id=$2 ORDER BY created_at DESC LIMIT 8;", ctx.guild.id, member.id)
        count = await self.bot.db.fetch_one("SELECT COUNT(*) AS total FROM kyoka_vouches WHERE guild_id=$1 AND vouchee_id=$2;", ctx.guild.id, member.id)
        embed = discord.Embed(title=f"Community Vouches • {member.display_name}", description=f"**Total vouches:** {int(count['total']) if count else 0}", color=0x9B5DE5)
        embed.set_thumbnail(url=member.display_avatar.url)
        for r in rows:
            embed.add_field(name=f"From user ID {int(r['voucher_id'])}", value=str(r['reason'])[:400], inline=False)
        if not rows: embed.add_field(name="No records", value="This member has no vouches yet.")
        embed.set_footer(text="Vouches are community claims, not proof of a transaction.")
        await ctx.send(embed=embed)

    @commands.command(name="billname", aliases=["setbillname"])
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def bill_name(self, ctx, *, name: str):
        """Set the custom heading printed on bills for this server."""
        name = name.strip()[:80]
        await self.bot.db.execute("INSERT INTO kyoka_bill_settings (guild_id, server_name) VALUES ($1,$2) ON CONFLICT (guild_id) DO UPDATE SET server_name=EXCLUDED.server_name;", ctx.guild.id, name)
        await ctx.send(f"✅ Bill branding set to **{discord.utils.escape_markdown(name)}**.")

    @commands.command(name="bill", aliases=["servicebill", "invoice"])
    @commands.guild_only()
    async def bill(self, ctx, *, details: str = ""):
        """Create a service bill with optional customer mention and pipe-separated fields."""
        # Parse the optional leading mention ourselves so bills also work without a customer.
        import re
        customer = None
        mention = re.match(r"^<@!?(\d+)>\s*", details)
        if mention:
            customer = ctx.guild.get_member(int(mention.group(1)))
            if customer is None:
                return await ctx.send("❌ I couldn't find that customer in this server.")
            details = details[mention.end():]
        details = details.strip().lstrip("|").strip()
        parts = [p.strip() for p in details.split("|")]
        if len(parts) < 6:
            return await ctx.send("**Bill format**\n`?bill @customer | Farming frags | 5 | 5 | 0 | 40 | Pending` or `?bill Farming frags | 5 | 5 | 0 | 40 | Pending`\nCustomer is optional. Taxes and total are numeric; payment can be Pending/Paid/etc.")
        service = parts[0][:120]
        try:
            apa, conglomerate, priority, total = (int(parts[i].replace(",", "").replace("m", "000000")) for i in range(1,5))
        except ValueError:
            return await ctx.send("❌ APA, conglomerate, priority tax, and total must be whole numbers (e.g. `5 | 5 | 0 | 40`).")
        if min(apa, conglomerate, priority, total) < 0 or total > 10**15:
            return await ctx.send("❌ Values must be non-negative and within a reasonable range.")
        payment = (parts[5] if len(parts) > 5 else "Pending")[:50]
        settings = await self.bot.db.fetch_one("SELECT server_name FROM kyoka_bill_settings WHERE guild_id=$1;", ctx.guild.id)
        server_name = settings['server_name'] if settings else ctx.guild.name
        row = await self.bot.db.fetch_one("INSERT INTO kyoka_bills (guild_id,biller_id,customer_id,server_name,service,apa_tax,conglomerate_tax,priority_tax,total_value,payment) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING id;", ctx.guild.id, ctx.author.id, customer.id if customer else None, server_name, service, apa, conglomerate, priority, total, payment)
        bill_id = int(row['id']) if row else 0
        embed = discord.Embed(title=server_name.upper(), color=0xE74C3C)
        embed.description = (f"## SERVICE BILL\n━━━━━━━━━━━━━━━━━━━━\n"
            f"• **Service**\n`{service}`\n\n• **APA Tax**\n`{apa}`\n\n"
            f"• **Conglomerate Tax**\n`{conglomerate}`\n\n• **Priority Tax**\n`{priority}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n• **Total Value**\n`{total:,}`\n\n• **Payment**\n`{discord.utils.escape_markdown(payment)}`\n"
            f"━━━━━━━━━━━━━━━━━━━━\n**END OF BILL**")
        embed.set_footer(text=f"Bill ID: TOP-{bill_id:08d} • Created by {ctx.author.display_name}")
        await ctx.send(content=customer.mention if customer else None, embed=embed)

    @commands.command(name="billinfo", aliases=["billhelp"])
    async def bill_help(self, ctx):
        embed = discord.Embed(title="Service Bill Commands", color=0xE74C3C)
        embed.description = (f"`?bill @member | service | APA | conglomerate | priority | total | payment`\n"
                            f"`?billname Your Server Name` — server managers only\n"
                            f"`?billhistory` — recent bills\n\n**Support:** {SUPPORT_URL}\n**Owner:** <@{OWNER_ID}>")
        await ctx.send(embed=embed)

    @commands.command(name="billhistory")
    @commands.guild_only()
    async def bill_history(self, ctx):
        rows = await self.bot.db.fetch_all("SELECT id, service, total_value, payment, created_at FROM kyoka_bills WHERE guild_id=$1 ORDER BY id DESC LIMIT 10;", ctx.guild.id)
        embed = discord.Embed(title="Recent Service Bills", color=0xE74C3C)
        embed.description = "\n".join(f"`TOP-{int(r['id']):08d}` • **{discord.utils.escape_markdown(r['service'])}** • `{int(r['total_value']):,}` • {discord.utils.escape_markdown(r['payment'])}" for r in rows) or "No bills created yet."
        await ctx.send(embed=embed)

    @commands.command(name="ask", aliases=["ai", "chat"])
    async def ask_ai(self, ctx, *, question: str):
        """Ask the Gemini assistant about services, Discord, or general questions."""
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return await ctx.send("⚠️ AI chat isn't configured yet. Add `GEMINI_API_KEY` to your environment variables.")
        if not getattr(self.bot, 'session', None):
            return await ctx.send("⚠️ AI service is temporarily unavailable.")
        async with ctx.typing():
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
                payload = {"system_instruction":{"parts":[{"text":"You are Kyoka, a friendly Discord community and gaming services assistant. Explain service options clearly, never claim a service was purchased or completed unless verified, and direct support questions to https://discord.gg/p6GvJtsMb. Keep answers helpful and concise."}]},"contents":[{"parts":[{"text":question[:4000]}]}],"generationConfig":{"temperature":0.6,"maxOutputTokens":700}}
                async with self.bot.session.post(url, json=payload, timeout=25) as response:
                    data = await response.json(content_type=None)
                    if response.status != 200:
                        msg = data.get('error', {}).get('message', 'Gemini request failed')
                        return await ctx.send(f"⚠️ Gemini error: {str(msg)[:250]}")
                answer = "".join(p.get('text','') for c in data.get('candidates',[]) for p in c.get('content',{}).get('parts',[])).strip()
                if not answer: answer = "I couldn't generate a response just now. Please try again."
                for start in range(0, min(len(answer), 6000), 1900):
                    await ctx.send(answer[start:start+1900])
            except Exception:
                await ctx.send("⚠️ I couldn't reach Gemini just now. Please try again later.")

    @commands.command(name="support", aliases=["helpdesk"])
    async def support(self, ctx):
        embed = discord.Embed(title="Kyoka Support", description=f"Need help with bills, vouches, or bot setup?\n\n[Join the support server]({SUPPORT_URL})\n**Bot owner:** <@{OWNER_ID}>", color=0x9B5DE5)
        await ctx.send(embed=embed)

    @commands.command(name="ownerinfo")
    async def owner_info(self, ctx):
        await ctx.send(f"**Kyoka Bot Owner:** <@{OWNER_ID}>\n**Support:** {SUPPORT_URL}")

    @commands.command(name="ownerannounce")
    @owner_only()
    @commands.guild_only()
    async def owner_announce(self, ctx, channel: discord.TextChannel, *, message: str):
        """Owner-only: send a bot-owner announcement to a chosen channel."""
        embed = discord.Embed(title="📢 Announcement", description=message[:4000], color=0x9B5DE5)
        embed.set_footer(text="Kyoka • Official announcement")
        await channel.send(embed=embed)
        await ctx.send(f"✅ Announcement sent to {channel.mention}.", delete_after=8)

    @commands.command(name="ownerstats")
    @owner_only()
    async def owner_stats(self, ctx):
        embed = discord.Embed(title="Owner Control • Kyoka", color=0x9B5DE5)
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)))
        embed.add_field(name="Users cached", value=str(len(self.bot.users)))
        embed.add_field(name="Latency", value=f"{self.bot.latency*1000:.0f} ms")
        embed.add_field(name="Owner", value=f"<@{OWNER_ID}>  `{OWNER_ID}`", inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CommunityReputation(bot))
