# KYOKA 1.0 — Aizen Community Bot

**Creator branding:** Made by Ruthupavan (Aizen). Prefix default: `&`.

## Quick commands added in this upgrade
- `&announce #welcome hi` — send an embed announcement (requires Manage Server).
- `&sethoneypot #do-not-type-here` — monitor a decoy channel (requires Administrator). Configure channel permissions first. The honeypot is currently in-memory and resets when the bot restarts; do not treat it as persistent protection.
- `&help` — view loaded command categories (the existing help module may use interactive pages).
- `&botinfo` — view bot information.

## Persistent storage and low-resource hosting
KYOKA uses PostgreSQL through `DATABASE_URL`; use a managed PostgreSQL database such as Supabase for data that must survive restarts/redeploys. Render's local filesystem should not be treated as durable storage. Keep database credentials private and rotate them if accidentally exposed. This update reduces the asyncpg pool to 1–4 connections to better suit small hosting instances.

### Render setup
1. Upload/extract this project into your repository.
2. In Render, set `DISCORD_TOKEN`, `DATABASE_URL`, and `BOT_PREFIX=&`. Set `GEMINI_API_KEY` only if using AI features.
3. Ensure the Discord Developer Portal has **Message Content Intent** and **Server Members Intent** enabled if the bot features require them.
4. Deploy and check Render logs for database connection, extension-loading, and Discord login errors.
5. Never commit `.env`, tokens, API keys, or database passwords.

## ✦ KYOKA AI Assistant

KYOKA includes a Gemini-powered AI assistant with a branded purple/cyan response card. It can explain topics, help with Python and other coding, troubleshoot errors, write or improve text, translate, summarize, brainstorm, and teach step by step. The prefix command is `&ai <question>`; `&ask` and `&chat` are aliases. A hybrid slash command `/ai` is also registered where application commands are synced.

### Enable AI
1. Create a Gemini API key in Google AI Studio.
2. Add `GEMINI_API_KEY` to your `.env` file locally or your hosting provider's environment variables. Never post the key in Discord or commit it to GitHub.
3. Optionally set `GEMINI_MODEL=gemini-2.5-flash` (the default).
4. Restart/redeploy KYOKA and run `&ai explain black holes in simple words`.

AI needs a valid API key and available Google API quota; it does not automatically browse the live internet and can make mistakes. Do not send passwords, tokens, or other secrets to it.

## Safety notes
- Commands with moderation impact must be permission-checked. The announce command requires Manage Server. Honeypot configuration requires Administrator and uses warning/deletion only, not automatic bans.
- Discord rate limits still apply; no command count can bypass platform limits.
- A syntactic check is not a full live Discord test. Verify permissions and each feature in a private test server before inviting publicly.

---

# ⚡ Kyoka — Next-Generation Discord Infrastructure

<div align="center">
  <img src="./assets/branding/kyoka_banner.webp" alt="Kyoka Banner" width="100%" style="border-radius: 10px; margin-bottom: 20px;" />

  <h3>Built for our community.</h3>
  <p>Keeping your server safe, active, and effortlessly connected.</p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
    <img src="https://img.shields.io/badge/discord.py-2.4+-5865F2?style=for-the-badge&logo=discord&logoColor=white" />
    <img src="https://img.shields.io/badge/PostgreSQL-Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white" />
    <img src="https://img.shields.io/badge/Deployment-Render%20Cloud-46E3B7?style=for-the-badge&logo=render&logoColor=white" />
    <img src="https://img.shields.io/badge/UI-Components%20V2%20(Type%2017)-FF73FA?style=for-the-badge" />
  </p>
</div>

---

## 📖 Overview

**Kyoka** is an enterprise-grade, high-concurrency Discord bot architecture engineered for performance, reliability, and clean aesthetics. 

Unlike traditional bots constrained by legacy Discord embeds and sluggish database queries, Kyoka operates with a **0ms In-Memory Caching Architecture** coupled with **Discord Components V2 (Type 17 Containers)**, delivering sub-millisecond execution speeds and clean, modern UI cards across Desktop, Web, and Mobile.

---

## 🏛️ System Architecture

```text
                       ┌─────────────────────────────────────────┐
                       │           Discord Gateway API           │
                       └────────────────────┬────────────────────┘
                                            │
                                  (Interaction/Message)
                                            ▼
                       ┌─────────────────────────────────────────┐
                       │         Kyoka Async Core Client         │
                       └──────────────┬───────────────────┬──────┘
                                      │                   │
                     (0ms Memory Read)│                   │(Atomic Write)
                                      ▼                   ▼
                       ┌─────────────────────────┐  ┌─────────────────────────┐
                       │  In-Memory Fast Caches  │  │  Supabase PostgreSQL    │
                       │  • Guild Prefixes       │  │  • Connection Pool      │
                       │  • Active Subscriptions │  │  • Persistent Schemas   │
                       │  • System Maintenance   │  │  • Customer Analytics   │
                       │  • Global Blacklists    │  │  • Audit Logs           │
                       └─────────────────────────┘  └─────────────────────────┘
                                      │
                                      ▼
                       ┌─────────────────────────────────────────┐
                       │    Components V2 REST Dispatcher        │
                       │    (Type 17 Container Layout Cards)     │
                       └─────────────────────────────────────────┘
```

### ⚡ 1. Hybrid 0ms In-Memory Caching
- Critical configurations (Guild Prefixes, Developer IDs, Maintenance State, Blacklists, and Subscriptions) are preloaded into memory upon startup.
- Message processing reads from RAM cache directly (`<0.001ms`), bypassing database round-trips entirely.
- Write operations atomically update both the PostgreSQL database pool and the in-memory cache.

### 🎨 2. Native Discord Components V2 Containers (Type 17)
- Replaces outdated, noisy Discord Embeds with native **Components V2 Containers**.
- Structured Text Displays, Section Rows, dynamic Separators, and integrated Action Rows.
- Zero standard unicode emoji spam — dynamically uses custom **Application Emojis** cached directly from the Discord Developer Portal.

### 🌐 3. 24/7 Cloud Resilience (Render Web Service)
- Integrated `aiohttp` HTTP health server running on port `8080`.
- Provides an active `/health` endpoint for continuous zero-downtime monitoring on Render.com, Railway, or VPS.

---

## 📂 Project Structure

```text
Kyoka/
├── .env                  # Secrets, Bot Token & Supabase Database URL
├── .env.example          # Environment configuration template
├── render.yaml           # 1-Click Render Cloud Deployment Blueprint
├── requirements.txt      # Python dependencies
├── README.md             # Bot overview & documentation
├── PROJECT_CONTEXT.md    # Exhaustive Technical Specification for AI & Developers
│
├── assets/               # Branding assets & custom application emojis
│   ├── branding/
│   │   ├── kyoka_banner.webp
│   │   └── kyoka_icon.webp
│   ├── emoji/
│   ├── emoji2/
│   └── music/
│
└── src/
    ├── main.py           # Application bootstrap & lifecycle manager
    │
    ├── core/             # Core Engine & HTTP Server
    │   ├── bot.py        # KyokaBot custom client with setup hooks
    │   ├── config.py     # Environment variable validator & constants
    │   ├── context.py    # CustomContext with container dispatcher methods
    │   └── server.py     # 24/7 aiohttp Keep-Alive Health Server
    │
    ├── database/         # Database Persistence Layer
    │   ├── base.py       # Abstract database protocol
    │   └── postgres.py   # asyncpg Supabase PostgreSQL pool & table schemas
    │
    ├── managers/         # Domain Logic & In-Memory Cache Engines
    │   ├── blacklist_manager.py   # Global user and guild blacklist filter
    │   ├── guild_manager.py       # Custom per-guild prefix caching
    │   ├── log_manager.py         # Multi-channel audit logging settings
    │   ├── permission_manager.py  # Bot owner & developer access control
    │   ├── premium_manager.py     # Subscriptions, keys, and customer analytics
    │   └── system_manager.py      # Global maintenance mode & command toggles
    │
    ├── utils/            # Shared Utilities & Design System
    │   ├── containers.py # Discord Components V2 builder & REST dispatcher
    │   ├── decorators.py # @require_guild_premium() and @require_user_premium()
    │   ├── emojis.py     # Dynamic Custom Application Emoji registry
    │   ├── embeds.py     # Fallback legacy embed utilities
    │   ├── logger.py     # Colored console logger
    │   └── views.py      # Base interaction view utilities
    │
    ├── errors/           # Centralized Error Handling
    │   ├── exceptions.py # Domain custom exceptions
    │   └── handler.py    # Global on_command_error listener & error UI cards
    │
    └── cogs/             # Modular Feature Packages (Ready for custom expansion)
```

---

## 🚀 Getting Started & Local Setup

### 1. Prerequisites
- Python **3.11** or higher
- A Supabase / PostgreSQL database instance
- A Discord Bot Application from [Discord Developer Portal](https://discord.com/developers/applications)

### 2. Installation
```bash
# Clone the repository
git clone <repository_url>
cd Kyoka

# Create and activate virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create `.env` based on `.env.example`:
```env
BOT_TOKEN=your_discord_bot_token_here
DATABASE_URL=postgresql://postgres.xxxx:password@aws-0-region.pooler.supabase.com:6543/postgres
DEVELOPER_IDS=1082437832087445604
DEFAULT_PREFIX=?
ENVIRONMENT=DEVELOPMENT
PORT=8080
```

### 4. Run the Bot
```bash
python -m src.main
```

---

## ☁️ 24/7 Cloud Deployment (Render.com)

1. Link your GitHub repository to [Render.com](https://render.com).
2. Create a **Web Service** using `render.yaml`.
3. Set Build Command: `pip install -r requirements.txt`.
4. Set Start Command: `python -m src.main`.
5. Add Environment Variables (`BOT_TOKEN`, `DATABASE_URL`, `DEVELOPER_IDS`, etc.).

Render will automatically deploy Kyoka alongside its integrated Keep-Alive Web Server (`http://0.0.0.0:8080`) for continuous 24/7 operation.

---

## 🛡️ Credits & Lead Architect

- **Bot Name**: Kyoka
- **Lead Architect & Developer**: `zerox.exe`
- **Framework**: `discord.py` (Components V2 Extended)
- **Database**: `Supabase PostgreSQL` with `asyncpg`

---
<div align="center">
  <sub>Engineered for next-generation Discord communities.</sub>
</div>

## Community billing, vouches & Gemini AI (added)

These prefix commands use your configured bot prefix (default `?`):

- `?bill @customer | Farming frags | 5 | 5 | 0 | 40 | Pending` — create a styled service bill. Customer mention is optional; the seven pipe-separated fields are service, APA tax, conglomerate tax, priority tax, total value, and payment status after the optional mention.
- `?billname THRONE OF PIRATES` — set the server's bill heading (requires Manage Server).
- `?billhistory` — show the latest 10 bills in this server.
- `?billinfo` — show bill command help.
- `?vouch @member completed the service quickly` — save a vouch. One vouch per member-to-member pair is kept; a repeat updates the existing record.
- `?vouches [@member]` — inspect community vouches.
- `?vouchlb` — show the server's top 10 vouched-for members.
- `?ask <question>` (aliases `?ai`, `?chat`) — ask the Gemini assistant. Set `GEMINI_API_KEY` in your hosting environment; never paste the key in a public channel.
- `?support` — link to https://discord.gg/p6GvJtsMb and identify the configured owner.
- `?ownerinfo` — show owner/support contact.
- `?ownerstats` and `?ownerannounce #channel <message>` — owner-only controls restricted to Discord user ID `1505515188991033409`.

The new tables (`kyoka_vouches`, `kyoka_bills`, `kyoka_bill_settings`) are created when the cog loads. They require the same PostgreSQL connection as the rest of this project. The bill and vouch commands are guild-only. Vouches are community claims and should not be treated as independent proof of a transaction.


## Community billing, vouches & Gemini AI (added)

These prefix commands use your configured bot prefix (default `?`):

- `?bill @customer | Farming frags | 5 | 5 | 0 | 40 | Pending` — create a styled service bill. The fields are service, APA tax, conglomerate tax, priority tax, total value, and payment status after an optional customer mention.
- `?billname THRONE OF PIRATES` — set the server bill heading (requires Manage Server).
- `?billhistory` — show the latest 10 bills in this server.
- `?billinfo` — show bill command help.
- `?vouch @member completed the service quickly` — save a vouch. A repeat from the same user for the same member updates that record.
- `?vouches [@member]` — inspect community vouches.
- `?vouchlb` — show the server top 10.
- `?ask <question>` (aliases `?ai`, `?chat`) — ask Gemini. Set `GEMINI_API_KEY` in hosting environment; never paste the key in a public channel.
- `?support` — link to https://discord.gg/p6GvJtsMb and identify the owner.
- `?ownerinfo` — show owner/support contact.
- `?ownerstats` and `?ownerannounce #channel <message>` — owner-only commands restricted to Discord user ID `1505515188991033409`.

The tables `kyoka_vouches`, `kyoka_bills`, and `kyoka_bill_settings` are created when the cog loads. They require the same PostgreSQL connection as the rest of the project. Vouches are community claims, not independent proof of a transaction.
