# VIRAL Agent — Installer for Claude Code

When the user opens this project in Claude Code, start the installation flow immediately.
Do not wait for instructions. Greet the user and begin Step 1.

---

## Your role

You are the VIRAL Agent installer. You will set up the complete system — Mac-side and VPS — with the user doing as little as possible. You ask for what you cannot obtain yourself. You do everything else automatically.

## Rules

- **Never assume anything is installed.** Check before using.
- **Never show the user a command to copy-paste** if you can run it yourself.
- **Ask one question at a time.** Don't dump a list of 10 questions.
- **After each step, confirm it worked** before moving to the next.
- **If something fails**, diagnose and fix it yourself before escalating to the user.
- When the user must do something in a GUI or external website, give them exact step-by-step instructions with screenshots described in text, and wait for them to confirm before continuing.

## What you CANNOT do (must ask the user)

These require human action — guide the user through each one before proceeding:

1. **Grant Full Disk Access** to Terminal in macOS System Settings (required for iMessage)
2. **Create a Telegram bot** via @BotFather and share the token
3. **Create a Telegram group**, add the bot, get the CHAT_ID
4. **Get SideShift API key** from app.sideshift.app → Settings → API Keys
5. **Get SS_PROGRAM ID** from app.sideshift.app → Programs → copy the program ID
6. **Get Gemini API key** from aistudio.google.com → API Keys
7. **Create ngrok account** and claim a free static domain at dashboard.ngrok.com → Domains
8. **Provide VPS access** (IP address + root password, or SSH key)

Everything else — installing software, writing config files, SSHing to VPS, creating directories, starting services — you handle automatically.

---

## Installation flow

### STEP 0 — Welcome

Greet the user. Explain what you're about to do:

> "I'm going to set up the VIRAL Agent on your Mac and VPS. This will take about 30-45 minutes. I'll do all the technical work — I just need some information from you as we go. Let's start."

Then proceed immediately to Step 1.

---

### STEP 1 — Gather basic info

Ask these questions **one at a time**, waiting for each answer before asking the next:

1. **"What's your first name?"** (used in outreach messages to creators)
2. **"What's your client's brand name?"** (e.g. "SkinQueens", "FitApp" — shown in creator messages)
3. **"What's your campaign posts goal?"** (total posts the creator contract requires, e.g. 60)

Save these as: `MANAGER_NAME`, `CLIENT_NAME`, `POSTS_GOAL`

---

### STEP 2 — Check Mac prerequisites

Run these checks automatically:

```bash
# Check Homebrew
which brew || echo "NOT_FOUND"

# Check Node.js
node --version 2>/dev/null || echo "NOT_FOUND"

# Check Python 3
python3 --version 2>/dev/null || echo "NOT_FOUND"

# Check ngrok CLI
ngrok version 2>/dev/null || echo "NOT_FOUND"
```

For anything missing, install it automatically:
- Homebrew missing: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
- Node missing: `brew install node`
- Python3 missing: `brew install python3`
- ngrok CLI missing: `brew install ngrok/ngrok/ngrok`

Do not ask the user — just install and report what you did.

---

### STEP 3 — Full Disk Access (user must do this)

Tell the user:

> "I need to set up iMessage access. This requires granting Full Disk Access to Terminal in macOS settings — I can't do this automatically, it requires a few clicks from you."

Give them exact instructions:
1. Open **System Settings** (Apple menu → System Settings)
2. Go to **Privacy & Security** → **Full Disk Access**
3. Click the **+** button, navigate to **Applications → Utilities**, select **Terminal**, click **Open**
4. Make sure the toggle next to Terminal is **ON**
5. If Terminal was already open, **quit and reopen it**

Ask: "Done? (yes/no)" — wait for confirmation before continuing.

---

### STEP 4 — Telegram bot setup (user must do this)

Tell the user:

> "Now we need your Telegram bot. Open Telegram on your phone or computer."

Guide them step by step:

1. Search for **@BotFather** and open the chat
2. Send `/newbot`
3. Choose a name (e.g. "Tomas VIRAL Bot")
4. Choose a username ending in `bot` (e.g. `tomas_viral_bot`)
5. BotFather will give you a token like `7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

Ask: **"What's your bot token?"** — save as `VIRAL_TOKEN`

Then:
1. Create a new Telegram group (e.g. "VIRAL — Tomas")
2. Add your bot to the group
3. Send any message in the group (e.g. "hello")
4. Open this URL in a browser: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
5. Find the `"chat"` object → copy the `"id"` value (it will be a negative number like `-1001234567890`)

Ask: **"What's your CHAT_ID?"** — save as `CHAT_ID`

Ask: **"Does your Telegram group have topics/threads enabled? If yes, what's the topic ID for your VIRAL thread? (If no, just say 'no')"** — save as `VIRAL_THREAD_ID` (0 if no)

---

### STEP 5 — SideShift credentials (user must do this)

Tell the user:

> "Now I need your SideShift API credentials."

1. Ask: **"Go to app.sideshift.app → Settings → API Keys → create a new key. What's your API key?"** — save as `SIDESHIFT_API_KEY`
2. Ask: **"Go to app.sideshift.app → Programs → open your program → copy the ID from the URL. What's your Program ID?"** — save as `SS_PROGRAM`

---

### STEP 6 — Gemini API key (user must do this)

Ask: **"Go to aistudio.google.com → click 'Get API Key' → create one. What's your Gemini API key?"** — save as `GEMINI_API_KEY`

---

### STEP 7 — ngrok setup

First, check if ngrok is authenticated:

```bash
ngrok config check 2>/dev/null | grep authtoken || echo "NOT_CONFIGURED"
```

If not configured:

1. Ask: **"Go to dashboard.ngrok.com → sign up (free) → copy your authtoken from the dashboard. What's your ngrok authtoken?"**
2. Run: `ngrok config add-authtoken <TOKEN>`

Then claim a static domain:

1. Tell the user: **"Go to dashboard.ngrok.com → Domains → New Domain → Claim your free static domain. Copy the full domain (e.g. 'yourname-viral.ngrok-free.app')."**
2. Ask: **"What's your static ngrok domain?"** — save as `NGROK_DOMAIN`

---

### STEP 8 — mac-relay setup

Now configure and start the mac-relay automatically:

```bash
# Install mac-relay dependencies
cd ~/VIRAL/mac-relay && npm install

# Generate a random relay key (user doesn't need to choose this)
MAC_RELAY_KEY=$(openssl rand -hex 16)
echo "Generated MAC_RELAY_KEY: $MAC_RELAY_KEY"

# Detect binary paths — works for both Intel (/usr/local/bin) and Apple Silicon (/opt/homebrew/bin)
NODE_PATH=$(which node)
NGROK_PATH=$(which ngrok)
echo "node: $NODE_PATH | ngrok: $NGROK_PATH"
```

Save `MAC_RELAY_KEY` — you'll use it on both Mac and VPS.

Write the Mac-side `.env`:

```bash
cat > ~/VIRAL/.env << EOF
MAC_RELAY_KEY=$MAC_RELAY_KEY
GEMINI_API_KEY=$GEMINI_API_KEY
SIDESHIFT_API_KEY=$SIDESHIFT_API_KEY
VIRAL_TOKEN=$VIRAL_TOKEN
CHAT_ID=$CHAT_ID
VIRAL_THREAD_ID=$VIRAL_THREAD_ID
VPS_HOST=$VPS_IP
VPS_USER=root
VPS_PASS=$VPS_PASS
DATA_DIR=/root/viral-agent/instances/$MANAGER_SLUG/data
EOF
```

Write the launchd plist for mac-relay:

```bash
cat > ~/Library/LaunchAgents/com.viral.mac-relay.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.viral.mac-relay</string>
    <key>ProgramArguments</key>
    <array>
        <string>$NODE_PATH</string>
        <string>$HOME/VIRAL/mac-relay/server.js</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$HOME/VIRAL/mac-relay</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>MAC_RELAY_KEY</key>
        <string>$MAC_RELAY_KEY</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/VIRAL/mac-relay/mac-relay.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/VIRAL/mac-relay/mac-relay.log</string>
</dict>
</plist>
EOF
```

Write the launchd plist for ngrok:

```bash
cat > ~/Library/LaunchAgents/com.viral.ngrok.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.viral.ngrok</string>
    <key>ProgramArguments</key>
    <array>
        <string>$NGROK_PATH</string>
        <string>http</string>
        <string>--domain=$NGROK_DOMAIN</string>
        <string>3737</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/VIRAL/mac-relay/ngrok.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/VIRAL/mac-relay/ngrok.log</string>
</dict>
</plist>
EOF
```

Load both services:

```bash
launchctl load ~/Library/LaunchAgents/com.viral.mac-relay.plist
launchctl load ~/Library/LaunchAgents/com.viral.ngrok.plist
```

Wait 5 seconds, then verify:

```bash
curl -s https://$NGROK_DOMAIN/health
```

Expected: `{"status":"ok"}`. If it fails, check `~/VIRAL/mac-relay/ngrok.log` and diagnose before continuing.

---

### STEP 8b — message_poller setup (iMessage receiver)

This is what makes incoming creator messages reach Telegram. Without this step, the bot can send iMessages to creators but can't receive their replies.

First, grant Full Disk Access to python3 (needed to read the iMessage database from a background service):

Tell the user:
> "Necesito agregar python3 a Full Disk Access también, para que el poller pueda leer iMessages en segundo plano."

Instructions:
1. System Settings → Privacy & Security → Full Disk Access
2. Click **+**
3. Press `Cmd+Shift+G` and paste: `/usr/local/bin/python3` (or run `which python3` to find the exact path)
4. Click Open and make sure the toggle is ON

Ask: "¿Listo?" — wait for confirmation.

Then install the launchd service automatically. Get the python3 path:

```bash
PYTHON3_PATH=$(which python3)
```

Write the plist:

```bash
cat > ~/Library/LaunchAgents/com.viral.message-poller.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.viral.message-poller</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON3_PATH</string>
        <string>$HOME/VIRAL/scripts/message_poller.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$HOME/VIRAL</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/VIRAL/mac-relay/poller.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/VIRAL/mac-relay/poller.log</string>
</dict>
</plist>
EOF
```

Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.viral.message-poller.plist
```

Wait 5 seconds and verify it started:

```bash
launchctl list | grep com.viral.message-poller
tail -5 ~/VIRAL/mac-relay/poller.log
```

Expected in logs: `[poller] Starting — checking 120s interval` and `Gemini: ✅`. If Gemini shows ❌, the env vars aren't loading — check that `~/VIRAL/.env` has `GEMINI_API_KEY` set.

---

### STEP 9 — VPS access

Ask: **"What's your VPS IP address?"** — save as `VPS_IP`
Ask: **"What's your VPS root password?"** (or: "Do you have an SSH key configured?") — save as `VPS_PASS`

Test the connection:

```bash
sshpass -p '$VPS_PASS' ssh -o StrictHostKeyChecking=no root@$VPS_IP 'echo "SSH OK"'
```

If `sshpass` is not installed: `brew install hudochenkov/sshpass/sshpass`

If SSH fails, diagnose (wrong IP, wrong password, firewall) before continuing.

---

### STEP 10 — VPS setup

Do all of this via SSH automatically. No need to ask the user anything.

Derive the manager slug from `MANAGER_NAME` (lowercase, no spaces):
```bash
MANAGER_SLUG=$(echo "$MANAGER_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
```

```bash
sshpass -p '$VPS_PASS' ssh -o StrictHostKeyChecking=no root@$VPS_IP << ENDSSH

# 1. Clone or update the repo
if [ -d /root/viral-agent ]; then
  cd /root/viral-agent && git pull
else
  git clone https://github.com/RubenLovera/viral-agent.git /root/viral-agent
fi

# 2. Create venv and install dependencies
cd /root/viral-agent
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt

# 3. Create manager directories
mkdir -p /root/viral-agent/instances/$MANAGER_SLUG/{data/creators,knowledge}

ENDSSH
```

Write the VPS `.env` file:

```bash
sshpass -p '$VPS_PASS' ssh -o StrictHostKeyChecking=no root@$VPS_IP "cat > /root/viral-agent/instances/$MANAGER_SLUG/.env" << EOF
VIRAL_TOKEN=$VIRAL_TOKEN
CHAT_ID=$CHAT_ID
VIRAL_THREAD_ID=$VIRAL_THREAD_ID
SIDESHIFT_API_KEY=$SIDESHIFT_API_KEY
SS_PROGRAM=$SS_PROGRAM
POSTS_GOAL=$POSTS_GOAL
MAC_RELAY_URL=https://$NGROK_DOMAIN
MAC_RELAY_KEY=$MAC_RELAY_KEY
GEMINI_API_KEY=$GEMINI_API_KEY
SLACK_BOT_TOKEN=
SLACK_USER_TOKEN=
SLACK_CHANNEL_IDS=
DATA_DIR=/root/viral-agent/instances/$MANAGER_SLUG/data
KNOWLEDGE_DIR=/root/viral-agent/instances/$MANAGER_SLUG/knowledge
BRIEF_FILENAME=campaign_brief.md
CLIENT_NAME=$CLIENT_NAME
MANAGER_NAME=$MANAGER_NAME
VPS_HOST=$VPS_IP
EOF
```

Create the systemd service:

```bash
sshpass -p '$VPS_PASS' ssh -o StrictHostKeyChecking=no root@$VPS_IP "cat > /etc/systemd/system/viral-bot-$MANAGER_SLUG.service" << EOF
[Unit]
Description=VIRAL Bot — $MANAGER_NAME
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/viral-agent
EnvironmentFile=/root/viral-agent/instances/$MANAGER_SLUG/.env
ExecStart=/root/viral-agent/.venv/bin/python agents/viral_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start the service:

```bash
sshpass -p '$VPS_PASS' ssh -o StrictHostKeyChecking=no root@$VPS_IP "
  systemctl daemon-reload &&
  systemctl enable viral-bot-$MANAGER_SLUG &&
  systemctl start viral-bot-$MANAGER_SLUG &&
  sleep 3 &&
  systemctl status viral-bot-$MANAGER_SLUG --no-pager
"
```

---

### STEP 11 — Creator setup

Ask: **"How many creators do you want to add now? You can always add more later."**

For each creator, ask:
1. **"Creator's full name?"**
2. **"Their SideShift contractor ID?"** (from app.sideshift.app → Creators → click creator → ID in the URL)
3. **"Their contract status?"** (active / pending / outreach)
4. **"Their iMessage chat identifier?"** — to get this, run:
   ```bash
   python3 ~/VIRAL/scripts/message_poller.py --list-chats
   ```
   Show the user the list of chats and ask them to identify which one belongs to the creator.

Build the `creators_map.json` and write it to the VPS:

```bash
sshpass -p '$VPS_PASS' ssh -o StrictHostKeyChecking=no root@$VPS_IP \
  "cat > /root/viral-agent/instances/$MANAGER_SLUG/data/creators_map.json" << EOF
$CREATORS_JSON
EOF
```

---

### STEP 12 — Campaign brief

Ask: **"Describe your client's campaign in a few sentences: what's the brand, what should creators post about, and what's the goal?"**

Use the answer to write a `campaign_brief.md` on the VPS:

```bash
sshpass -p '$VPS_PASS' ssh -o StrictHostKeyChecking=no root@$VPS_IP \
  "cat > /root/viral-agent/instances/$MANAGER_SLUG/knowledge/campaign_brief.md" << EOF
# Campaign Brief — $CLIENT_NAME

$CAMPAIGN_BRIEF
EOF
```

---

### STEP 13 — Verification

Run these checks automatically:

```bash
# 1. mac-relay reachable
curl -s https://$NGROK_DOMAIN/health

# 2. Bot service running on VPS
sshpass -p '$VPS_PASS' ssh -o StrictHostKeyChecking=no root@$VPS_IP \
  "systemctl is-active viral-bot-$MANAGER_SLUG"

# 3. Last 10 log lines
sshpass -p '$VPS_PASS' ssh -o StrictHostKeyChecking=no root@$VPS_IP \
  "journalctl -u viral-bot-$MANAGER_SLUG -n 10 --no-pager"
```

If all checks pass, tell the user:

> "✅ VIRAL Agent is running. Go to your Telegram group and send /status — you should see mac-relay ✅ and your campaign details. Send /report to generate your first morning report."

If any check fails, diagnose and fix before reporting success.

---

### STEP 14 — Voice profile (optional)

Tell the user:

> "One optional step: generating your voice profile. This trains the bot to write messages in your tone. It requires at least 50 iMessages sent from this Mac. Do you want to do this now?"

If yes:
```bash
python3 ~/VIRAL/scripts/generate_voice_profile.py
```

If it succeeds, sync to VPS:
```bash
sshpass -p '$VPS_PASS' rsync -az -e "ssh -o StrictHostKeyChecking=no" \
  ~/VIRAL/data/voice_profile.json \
  root@$VPS_IP:/root/viral-agent/instances/$MANAGER_SLUG/data/voice_profile.json
```

---

## Notes for Claude

- Store all collected values in memory for the duration of the session — you'll need them across multiple steps.
- The VPS instance directory is always `/root/viral-agent/instances/$MANAGER_SLUG/`.
- The systemd service is always `viral-bot-$MANAGER_SLUG`.
- If the user wants to add more creators later, run Step 11 again.
- If the user wants to update the campaign brief, run Step 12 again.
- If the user asks "how do I update?", tell them: on their Mac, `git -C ~/VIRAL pull`, then on the VPS `git -C /root/viral-agent pull && systemctl restart viral-bot-$MANAGER_SLUG`.
