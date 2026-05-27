# VIRAL Agent

Autonomous UGC creator coordination system for The Viral App (TVA) managers.

Sends daily status updates to creators via iMessage, tracks post progress via SideShift, reads TVA Slack for campaign context, and reports everything to your Telegram.

---

## Install

**This system is installed entirely through Claude Code.** You don't run commands — Claude does everything for you.

### Step 1 — Open Claude Code

```bash
claude
```

### Step 2 — Paste this prompt

```
Install the VIRAL Agent on this Mac and VPS.
Repo: https://github.com/RubenLovera/viral-agent.git
Clone it to ~/VIRAL, read the CLAUDE.md inside, and follow the installation instructions step by step.
```

That's it. Claude will clone the repo, ask you for your credentials one by one, and set up everything — Mac-side and VPS — automatically.

**Installation takes ~30-45 minutes.**

---

## What you'll need before starting

Have these accounts/keys ready — Claude will ask for them one by one:

- [ ] VPS running Ubuntu 24.04 (IP + root password)
- [ ] Telegram bot token (create via @BotFather)
- [ ] SideShift API key (app.sideshift.app → Settings → API Keys)
- [ ] SideShift Program ID (your client's program)
- [ ] Gemini API key (aistudio.google.com)
- [ ] ngrok account (ngrok.com — free tier)

---

## How it works

### System architecture

```mermaid
graph TB
    subgraph MAC["💻 Your Mac  (Full Disk Access required)"]
        RELAY["mac-relay\nNode.js · port 3737\nlaunchd service"]
        POLLER["message_poller.py\npolls iMessage DB\nevery 2 min"]
        DB[("iMessage\nchat.db")]
        NGROK["ngrok tunnel\nstatic domain"]
    end

    subgraph VPS["🖥️ VPS  (Ubuntu 24.04 · always-on)"]
        BOT["viral_bot.py\n10 daily crons\nTelegram handlers"]
    end

    TG(["📱 Telegram\n(your phone)"])
    SS(["📊 SideShift API\nposts · analytics · payouts"])
    SLACK(["💬 Slack TVA\ncampaign channels"])
    AI(["🤖 Gemini AI\nmessage generation"])

    BOT -->|"POST /send-group\nvia HTTPS"| NGROK
    NGROK -->|"→ localhost:3737"| RELAY
    RELAY -->|"AppleScript\nosascript"| DB

    POLLER -->|"sqlite3 SELECT"| DB
    POLLER -->|"classify + draft reply"| AI
    POLLER -->|"alert + inline buttons"| TG

    BOT -->|"reports · alerts · briefs"| TG
    TG -->|"manager taps button"| BOT
    BOT -->|"posts · analytics · payouts"| SS
    BOT -->|"read channels (24h)"| SLACK
    BOT -->|"generate iMessages"| AI
```

### Creator pipeline

Creators move through 5 states. The bot adjusts its cadence automatically.

```mermaid
stateDiagram-v2
    direction LR
    [*] --> onboarding : creator added
    onboarding --> warm_up : first post
    warm_up --> active : >5 posts or >7 days
    active --> silent : 48h no post
    silent --> active : new post
    silent --> at_risk : 3 ignored follow-ups
    at_risk --> [*] : contact paused · manager alerted
```

### Incoming message flow

Every iMessage a creator sends becomes a classified Telegram alert within 2 minutes.

```mermaid
graph LR
    A(["💬 Creator\nsends iMessage"])
    B["message_poller.py\nreads chat.db\nevery 2 min"]
    C{{"Gemini\nclassifier"}}
    D1["📹 Draft video\nApprove · Changes · Reject"]
    D2["❓ Question\nAI draft reply ready"]
    D3["🚨 Complaint\nurgent alert"]
    D4["✅ Update\nnotification"]
    E(["📱 Telegram\ninline buttons"])
    F(["👤 Manager\ntaps button"])
    G["viral_bot.py\n→ mac-relay → ngrok"]
    H(["💬 Reply\ndelivered via iMessage"])

    A --> B --> C
    C --> D1 & D2 & D3 & D4
    D1 & D2 & D3 & D4 --> E --> F --> G --> H
```

### Creator memory

Each creator has a profile that builds up over time from multiple sources. When the bot generates a message, it reads all four layers and combines them with shared campaign context before calling Gemini.

```mermaid
flowchart LR
    subgraph WRITERS[" "]
        SS["📊 SideShift API\nposts · views · payouts"]
        MP["message_poller.py\niMessages from creator"]
        VB["viral_bot.py\ncrons + state transitions"]
    end

    subgraph PROFILE["📁 creators/{id}.json  —  one file per creator"]
        ST["① state\nposts · views · progress %\nchannel · days since post\n─────────────────\nupdated: 6 AM daily"]
        EV["② events\nfirst_post · warmup_complete\nstate_change · at_risk\n─────────────────\nupdated: on each milestone"]
        IX["③ interactions\nincoming messages classified\nDRAFT · QUESTION · COMPLAINT\n─────────────────\nupdated: every 2 min (Mac → VPS)"]
        AC["④ actions\noutgoing messages sent by bot\nstatus_check · onboarding · nudges\n─────────────────\nupdated: on every iMessage sent"]
    end

    subgraph SHARED["Shared context  (injected at send time)"]
        BR["campaign_brief.md\nclient brand context"]
        TC["tva_context.md\ndaily Slack brief"]
        VP["voice_profile.json\nmanager tone + phrases"]
    end

    SS -->|"6 AM\nstatus_check"| ST
    VB -->|"milestone reached\nor state transition"| EV
    MP -->|"classify → rsync\nmerge at 6 AM"| IX
    VB -->|"logged after\nevery send"| AC

    ST & EV & IX & AC --> GM
    BR & TC & VP --> GM
    GM["🤖 Gemini\ngenerates personalized\niMessage for this creator"]
    GM --> OUT["💬 iMessage\ndelivered via mac-relay"]
```

---

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

## Multiple managers

Each TVA manager runs their own isolated instance — their own Telegram bot, SideShift key, ngrok domain, and creator roster. Multiple instances can run on the same VPS without interference.

To install for a new manager, they clone the repo and run `claude` from the directory.
