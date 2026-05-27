# VIRAL Agent — Setup Guide

Install time: ~2 hours following this guide step by step.

---

## Section A — Prerequisites

Before you start, make sure you have:

- [ ] **Mac with iMessage active** — logged into your Apple ID, iMessages accessible in Messages.app
- [ ] **Full Disk Access for Terminal** — System Settings → Privacy & Security → Full Disk Access → toggle Terminal on. Required for iMessage database access.
- [ ] **VPS running Ubuntu 24.04** — your own, or use the shared one (ask Rubén)
- [ ] **ngrok account** — sign up at ngrok.com (free tier is fine)
- [ ] **Telegram bot** — create via @BotFather. Get your `CHAT_ID` by messaging the bot and checking `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
- [ ] **SideShift API key** — from app.sideshift.app → Settings → API Keys
- [ ] **Gemini API key** — from aistudio.google.com → API Keys

---

## Section B — Mac-side setup

### B1. Clone the repo

```bash
git clone git@github.com:RubenLovera/viral-agent.git ~/VIRAL
```

If `~/VIRAL` already exists (Rubén's setup), clone elsewhere and copy only the scripts you need.

### B2. Install mac-relay dependencies

```bash
cd ~/VIRAL/mac-relay
npm install
```

### B3. Get your ngrok static domain

1. Log in at ngrok.com
2. Go to **Domains** → **New Domain** → **Claim a free static domain**
3. Copy your domain (e.g. `yourname-viral.ngrok-free.app`) — you'll need it in Section B6

### B4. Configure Mac-side .env

Create `~/VIRAL/.env`:

```bash
MAC_RELAY_KEY=your-secret-key-here   # make up a strong random string
GEMINI_API_KEY=your-gemini-api-key
SIDESHIFT_API_KEY=your-sideshift-api-key
VPS_HOST=your-vps-ip
VPS_USER=root
```

### B5. Test mac-relay manually

```bash
MAC_RELAY_KEY=your-secret-key-here node ~/VIRAL/mac-relay/server.js
```

In another terminal: `curl http://localhost:3737/health` — should return `{"status":"ok"}`.

### B6. Install launchd services (auto-start on login)

Copy and edit the templates:

```bash
cp ~/VIRAL/templates/launchd/com.viral.mac-relay.plist.example \
   ~/Library/LaunchAgents/com.viral.mac-relay.plist

cp ~/VIRAL/templates/launchd/com.viral.ngrok.plist.example \
   ~/Library/LaunchAgents/com.viral.ngrok.plist
```

Edit both files — replace `YOUR_USERNAME` with your Mac username and fill in your values.

Load them:

```bash
launchctl load ~/Library/LaunchAgents/com.viral.mac-relay.plist
launchctl load ~/Library/LaunchAgents/com.viral.ngrok.plist
```

Verify: `curl https://YOUR-DOMAIN.ngrok-free.app/health` — should return `{"status":"ok"}`.

### B7. Generate voice profile (optional but recommended)

⚠️ Requires 50+ iMessages sent from this Mac to creators. If you don't have message history yet, skip this step — the bot will use a generic tone initially. Regenerate once you have history.

```bash
python3 ~/VIRAL/scripts/generate_voice_profile.py
```

This creates `~/VIRAL/data/voice_profile.json`. Keep it — you'll copy it to the VPS in Section C.

---

## Section C — VPS setup

SSH into your VPS: `ssh root@YOUR_VPS_IP`

### C1. Clone the repo (if VPS is your own)

```bash
cd /root
git clone git@github.com:RubenLovera/viral-agent.git culver-os
cd culver-os
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

If using Rubén's shared VPS — the repo and `.venv` already exist at `/root/culver-os`. Skip the clone; verify dependencies with:
```bash
/root/culver-os/.venv/bin/python -c "import telegram, google.genai, slack_sdk; print('OK')"
```

### C2. Create your instance directory

```bash
mkdir -p /root/culver-os/viral-bot-yourname/{data/creators,knowledge}
```

### C3. Configure your .env

```bash
cp /root/culver-os/templates/.env.viral.example /root/culver-os/.env.viral-yourname
nano /root/culver-os/.env.viral-yourname
```

Fill in every field. Key ones:
- `DATA_DIR=/root/culver-os/viral-bot-yourname/data`
- `KNOWLEDGE_DIR=/root/culver-os/viral-bot-yourname/knowledge`
- `MAC_RELAY_URL=https://your-domain.ngrok-free.app`
- `MAC_RELAY_KEY=` same secret as in your Mac `~/VIRAL/.env`
- `CLIENT_NAME=` your client's brand name
- `MANAGER_NAME=` your first name

### C4. Create creators_map.json

```bash
cp /root/culver-os/templates/creators_map.json.example \
   /root/culver-os/viral-bot-yourname/data/creators_map.json
```

Edit it: add your creators. Get `sideshift_id` from app.sideshift.app → Creators → click a creator → copy their contractor ID from the URL.

To get `chat_identifier` for iMessage: run this on your Mac:
```bash
python3 ~/VIRAL/scripts/message_poller.py --list-chats
```

### C5. Create campaign_brief.md

```bash
cp /root/culver-os/templates/campaign_brief.md.example \
   /root/culver-os/viral-bot-yourname/knowledge/campaign_brief.md
```

Edit it: fill in your client's campaign brief.

### C6. Copy voice profile (if you generated one in B7)

From your Mac:
```bash
sshpass -e rsync -az ~/VIRAL/data/voice_profile.json \
  root@YOUR_VPS_IP:/root/culver-os/viral-bot-yourname/data/voice_profile.json
```

### C7. Create and start the systemd service

```bash
cp /root/culver-os/templates/systemd/viral-bot.service.example \
   /etc/systemd/system/viral-bot-yourname.service
nano /etc/systemd/system/viral-bot-yourname.service
```

Edit: replace `yourname` with your actual name. Then:

```bash
systemctl daemon-reload
systemctl enable viral-bot-yourname
systemctl start viral-bot-yourname
systemctl status viral-bot-yourname
```

---

## Section D — Verification

Run these checks after starting the service:

- [ ] `/status` in Telegram → should show mac-relay ✅ and your CLIENT_NAME
- [ ] `/report` → generates a morning report (shows creator stats from SideShift)
- [ ] `/slackbrief` → reads your TVA Slack channels and sends a brief
- [ ] Wait for 6:00 AM PT or run `/statuscheck` manually → Status Check messages sent to all active creators
- [ ] Check `journalctl -u viral-bot-yourname -f` on VPS for any errors

---

## Troubleshooting

**mac-relay offline** — Check ngrok is running: `curl https://your-domain.ngrok-free.app/health`

**SideShift auth error** — Verify `SIDESHIFT_API_KEY` in your .env and that `SS_PROGRAM` is correct

**No creators in report** — Check `creators_map.json` has the right format and `sideshift_id` matches

**Gemini errors** — Check `GEMINI_API_KEY` is valid at aistudio.google.com

**Service won't start** — Run `journalctl -u viral-bot-yourname -n 50` and look for the Python error

---

## Updating

When new features are pushed to the repo:

```bash
# On VPS
cd /root/culver-os
git pull
systemctl restart viral-bot-yourname
```
