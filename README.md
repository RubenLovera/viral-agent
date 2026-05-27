# VIRAL Agent

Autonomous UGC creator coordination system for The Viral App (TVA) managers.

Sends daily status updates to creators via iMessage, tracks post progress via SideShift, reads TVA Slack for campaign context, and reports everything to a manager's Telegram.

## Architecture

Two processes, two machines:

```
Your Mac                          VPS
─────────────────                 ─────────────────────────
message_poller.py  ──────────→   viral_bot.py
mac-relay/server.js ←─────────   (reads iMessages, sends iMessages)
ngrok tunnel                     APScheduler (10 crons)
                                 SideShift API
                                 Gemini (LLM)
                                 Slack SDK
                                 Telegram Bot API
```

**Why does it need a Mac?** iMessage requires Full Disk Access on a physical Mac with your Apple ID. No SaaS platform can proxy this. The mac-relay bridges your VPS to your Mac's iMessage database via an ngrok tunnel.

## Prerequisites

- Mac with iMessage (Apple ID logged in, Full Disk Access for Terminal)
- VPS running Ubuntu 24.04
- ngrok free account (1 static domain)
- Telegram bot (@BotFather)
- SideShift API key
- Gemini API key
- TVA Slack tokens (optional, for Slack briefs)

## Install

See [SETUP.md](SETUP.md) for the full installation guide (~2 hours).

## Daily schedule

| Time (PT) | What it does |
|-----------|-------------|
| 6:00 AM   | Status Check — personalized iMessage to each creator with their stats |
| 7:30 AM   | Slack Brief — reads TVA channels, sends summary to Telegram |
| 9:00 AM   | Morning Report — full campaign stats in Telegram |
| 10:00 AM  | Onboarding Check — nudges creators with 0 posts |
| 11:00 AM  | Buenos Días Check — mid-morning engagement |
| 2:00 PM   | Warm-up Check — monitors warm-up creators, nudges at-risk ones |
| 5:00 PM   | Overdue Check — flags creators who haven't posted today |
| 9:00 PM   | Nightly Digest — end of day summary |
| 1st of month | Voice profile regeneration reminder |
| Every 15 min | mac-relay health check |

## Telegram commands

| Command | What it does |
|---------|-------------|
| `/status` | Bot status + mac-relay health |
| `/report` | Run morning report now |
| `/statuscheck` | Send Status Check to all creators now |
| `/channelstate` | Show channel states for all creators |
| `/profile <name>` | Show creator's full profile |
| `/slackbrief` | Read Slack channels now |
| `/classify <text>` | Classify an iMessage (draft/question/complaint/update/other) |
| `/remap <name> <chat_id>` | Reassign creator's chat identifier |
| `/check` | Run Buenos Días Check now |
| `/warmup` | Run Warm-up Check now |
| `/digest` | Run Nightly Digest now |
| `/onboarding` | Run Onboarding Check now |

## Repo structure

```
viral-agent/
├── agents/
│   └── viral_bot.py              ← VPS bot (all config via .env)
├── scripts/
│   ├── message_poller.py         ← Mac-side: polls iMessages → VPS
│   └── generate_voice_profile.py ← Mac-side: generates your voice profile
├── mac-relay/
│   ├── server.js                 ← Mac-side: HTTP bridge for iMessage
│   └── package.json
├── templates/
│   ├── .env.viral.example        ← All env vars documented
│   ├── creators_map.json.example ← Creator roster format
│   ├── campaign_brief.md.example ← Campaign brief template
│   ├── launchd/                  ← Mac auto-start services
│   └── systemd/                  ← VPS auto-start service
├── requirements.txt
├── SETUP.md                      ← Full installation guide
└── .gitignore
```

## Per-manager isolation

Each TVA manager runs their own instance with their own:
- Directory: `/root/culver-os/viral-bot-{name}/`
- Env file: `/root/culver-os/.env.viral-{name}`
- Systemd service: `viral-bot-{name}.service`
- Telegram bot, SideShift key, ngrok domain, creators_map.json

Multiple instances can run on the same VPS without interference.
