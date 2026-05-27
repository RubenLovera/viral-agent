#!/usr/bin/env python3
"""message_poller — Poll iMessage group chats for new creator messages, classify, notify Telegram.

Run from Terminal (needs Full Disk Access) — NOT via launchd.
  python3 ~/VIRAL/scripts/message_poller.py

Polls every 2 minutes. State saved to ~/VIRAL/data/poller_state.json.
Sends classified alerts to the VIRAL Telegram group.
Writes interactions to ~/VIRAL/data/creators/{ss_id}.interactions.jsonl (Capa 5).
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path

import httpx
from google import genai

# ── Config ────────────────────────────────────────────────────────────────────

VIRAL_DIR  = Path.home() / 'VIRAL'
DATA_DIR   = VIRAL_DIR / 'data'
ENV_FILE   = VIRAL_DIR / '.env'

DB_PATH            = Path.home() / 'Library/Messages/chat.db'
STATE_FILE         = DATA_DIR / 'poller_state.json'
CREATORS_FILE      = DATA_DIR / 'creators_map.json'
VOICE_PROFILE_FILE = DATA_DIR / 'voice_profile.json'
CREATORS_DIR       = DATA_DIR / 'creators'  # local interactions cache

VPS_HOST           = 'root@187.127.255.6'
VPS_CREATORS_DIR   = '/root/culver-os/viral-bot/data/creators/'
SSH_PASS           = 'Dios-Es-Amor123'

APPLE_EPOCH  = 978307200
POLL_INTERVAL = 120  # seconds

# Classification labels
LABELS = ('draft', 'question', 'complaint', 'update', 'other')

LABEL_ICON = {
    'draft':     '📹',
    'question':  '❓',
    'complaint': '🚨',
    'update':    '✅',
    'other':     '💬',
}

# ── Load env ──────────────────────────────────────────────────────────────────

def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

load_env()

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
VIRAL_TOKEN    = os.environ.get('VIRAL_TOKEN', '')
CHAT_ID        = int(os.environ.get('CHAT_ID', '0'))
THREAD_ID      = int(os.environ.get('VIRAL_THREAD_ID', '0')) or None

_gemini = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# ── State ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ── Creators map ──────────────────────────────────────────────────────────────

def load_creators() -> list[dict]:
    if not CREATORS_FILE.exists():
        return []
    raw = json.loads(CREATORS_FILE.read_text())
    if isinstance(raw, list):
        return raw
    result = []
    for name, entry in raw.items():
        row = dict(entry)
        row.setdefault('creator_name', name)
        result.append(row)
    return [c for c in result if c.get('chat_identifier') and c.get('contract_status') != 'cancelled']

# ── Interaction logger (Capa 5) ───────────────────────────────────────────────

def _ss_id_for_chat(chat_uuid: str) -> tuple[str, str] | None:
    """Return (ss_id, creator_name) for a chat_identifier, or None."""
    creators = load_creators()
    for c in creators:
        if c.get('chat_identifier') == chat_uuid:
            ss_id = c.get('sideshift_id', '')
            name  = c.get('creator_name', 'Unknown')
            if ss_id:
                return ss_id, name
    return None


def append_interaction(ss_id: str, label: str, text: str) -> None:
    """Append a classified incoming message to the creator's local .interactions.jsonl."""
    CREATORS_DIR.mkdir(parents=True, exist_ok=True)
    path = CREATORS_DIR / f'{ss_id}.interactions.jsonl'
    entry = {
        'ts':   datetime.now().strftime('%Y-%m-%d %H:%M'),
        'type': 'incoming_message',
        'label': label,
        'text': text[:200],
    }
    with path.open('a') as f:
        f.write(json.dumps(entry) + '\n')


def sync_interactions_to_vps() -> None:
    """Rsync local .interactions.jsonl files to VPS. Only pushes Mac-side files."""
    jsonl_files = list(CREATORS_DIR.glob('*.interactions.jsonl'))
    if not jsonl_files:
        return
    try:
        subprocess.run(
            [
                'sshpass', '-p', SSH_PASS, 'rsync', '-az',
                '--include=*.interactions.jsonl', '--exclude=*',
                '-e', 'ssh -o StrictHostKeyChecking=no',
                str(CREATORS_DIR) + '/',
                f'{VPS_HOST}:{VPS_CREATORS_DIR}',
            ],
            timeout=20, capture_output=True, check=False,
        )
        print(f'  [sync] pushed {len(jsonl_files)} interaction file(s) to VPS')
    except FileNotFoundError:
        print('  [sync] sshpass not found — skipping VPS sync')
    except Exception as e:
        print(f'  [sync] rsync error: {e}')


# ── iMessage reader ───────────────────────────────────────────────────────────

def parse_streamtyped(blob: bytes) -> str | None:
    marker = b'\x84\x01\x2b'
    pos    = blob.find(marker)
    if pos == -1:
        return None
    i = pos + len(marker)
    if i >= len(blob):
        return None
    len_byte = blob[i]
    if len_byte < 0x80:
        str_len, str_start = len_byte, i + 1
    elif len_byte == 0x81:
        if i + 2 >= len(blob):
            return None
        str_len   = blob[i + 1] | (blob[i + 2] << 8)
        str_start = i + 3
    else:
        return None
    if str_start + str_len > len(blob):
        return None
    try:
        return blob[str_start:str_start + str_len].decode('utf-8').strip()
    except UnicodeDecodeError:
        return None


def read_new_messages(con: sqlite3.Connection, chat_uuid: str, since_rowid: int) -> list[dict]:
    cur = con.cursor()
    cur.execute(
        "SELECT ROWID FROM chat WHERE chat_identifier LIKE ? LIMIT 1",
        (f'%{chat_uuid}%',),
    )
    row = cur.fetchone()
    if not row:
        return []
    chat_db_id = row[0]

    cur.execute("""
        SELECT m.ROWID, m.text, m.attributedBody, m.date, m.is_from_me
        FROM message m
        JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
        WHERE cmj.chat_id = ?
          AND m.ROWID > ?
          AND m.is_from_me = 0
        ORDER BY m.ROWID ASC
        LIMIT 50
    """, (chat_db_id, since_rowid))

    messages = []
    for rowid, text, attr_body, apple_ts, _ in cur.fetchall():
        content = text.strip() if text and text.strip() else (
            parse_streamtyped(bytes(attr_body)) if attr_body else None
        )
        if not content or len(content) < 3:
            continue
        ts = int(apple_ts / 1_000_000_000) + APPLE_EPOCH if apple_ts else 0
        messages.append({'rowid': rowid, 'text': content, 'ts': ts})
    return messages

# ── Voice Profile + Draft Generator ──────────────────────────────────────────

def load_voice_profile() -> dict | None:
    if VOICE_PROFILE_FILE.exists():
        return json.loads(VOICE_PROFILE_FILE.read_text())
    return None


def _voice_context_brief(vp: dict) -> str:
    """Compact voice descriptor for short prompts."""
    tones   = ', '.join(vp.get('tone_descriptors', [])[:3])
    samples = ' | '.join(vp.get('sample_phrases', [])[:3])
    emojis  = ' '.join(vp.get('emoji_patterns', {}).get('frequent', [])[:3])
    return f'Tone: {tones}. Emojis: {emojis}. Example phrases: {samples}'


def generate_draft_reply(creator_name: str, message_text: str) -> str | None:
    """Generate a draft iMessage reply using Gemini + voice profile (#19)."""
    if not _gemini:
        return None
    vp = load_voice_profile()
    if not vp:
        return None

    first = creator_name.split()[0]
    voice = _voice_context_brief(vp)

    prompt = (
        f'Reply to this iMessage from UGC creator {first}: "{message_text[:200]}"\n'
        f'Voice style: {voice}\n'
        f'Rules: 2-3 lines, casual iMessage style, helpful and direct. '
        f'Write ONLY the reply text, nothing else.'
    )

    try:
        resp = _gemini.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        return resp.text.strip()
    except Exception as e:
        print(f'  [draft] Gemini error: {e}')
        return None


# ── Classifier ────────────────────────────────────────────────────────────────

def _keyword_classify(text: str) -> str | None:
    """Fast keyword pre-classifier — returns label or None if ambiguous."""
    t = text.lower()
    draft_signals = ['tiktok.com', 'instagram.com', 'youtube.com', 'youtu.be',
                     'draft', 'review this', 'check this out', 'what do you think']
    update_signals = ['just posted', 'i posted', 'already posted', 'done!', 'done ✅',
                      'uploaded', 'it\'s live', 'it is live', 'posted it']
    complaint_signals = ['not working', 'problem', 'issue', 'error', 'can\'t', 'cannot',
                         'not received', 'didn\'t receive', "haven't received", 'frustrated']
    question_signals = ['how do i', 'how do you', 'when will', 'can you', 'do i need',
                        'what should', 'is it ok', '?']
    if any(s in t for s in draft_signals):
        return 'draft'
    if any(s in t for s in update_signals):
        return 'update'
    if any(s in t for s in complaint_signals):
        return 'complaint'
    if any(s in t for s in question_signals):
        return 'question'
    return None


def classify_message(text: str) -> str:
    """Classify a creator message. Returns one of: draft question complaint update other.
    Uses keyword pre-classifier first; falls back to Gemini only if ambiguous."""
    # Try keyword first to save API quota
    label = _keyword_classify(text)
    if label:
        return label

    if not _gemini:
        return 'other'

    prompt = f"""Classify this iMessage from a UGC content creator into EXACTLY one of:
draft, question, complaint, update, other.

draft     — sharing a TikTok/Reel/video link or asking for draft approval
question  — asking something about the campaign, payment, or process
complaint — reporting a problem, expressing frustration
update    — reporting they posted, completed a task, or sharing good news
other     — social chit-chat or unclear

Message: "{text}"
Reply with ONLY the label (one lowercase word)."""

    try:
        resp = _gemini.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        label = resp.text.strip().lower().split()[0]
        return label if label in LABELS else 'other'
    except Exception as e:
        print(f'  [classifier] Gemini error: {e}')
        return 'other'

# ── Telegram sender ───────────────────────────────────────────────────────────

def tg_send(text: str, reply_markup: dict | None = None):
    if not VIRAL_TOKEN or not CHAT_ID:
        print(f'  [tg] Would send: {text[:80]}')
        return
    payload: dict = {
        'chat_id':    CHAT_ID,
        'text':       text,
        'parse_mode': 'HTML',
    }
    if THREAD_ID:
        payload['message_thread_id'] = THREAD_ID
    if reply_markup:
        payload['reply_markup'] = reply_markup
    try:
        r = httpx.post(
            f'https://api.telegram.org/bot{VIRAL_TOKEN}/sendMessage',
            json=payload,
            timeout=10,
        )
        r.raise_for_status()
    except Exception as e:
        print(f'  [tg] Error: {e}')

# ── Main loop ─────────────────────────────────────────────────────────────────

def poll_once(state: dict) -> dict:
    # ── Check expired pending drafts (#23) ────────────────────────────────────
    pending_qdrafts = state.get('pending_qdrafts', {})
    now_ts = int(time.time())
    expired_keys = [k for k, v in pending_qdrafts.items()
                    if now_ts - v.get('created_at', 0) > 86400]
    for key in expired_keys:
        info = pending_qdrafts.pop(key)
        creator = info.get('creator_name', '?')
        print(f'  [draft-expired] {creator}')
        tg_send(f'⏰ <b>Draft expired</b> — no action taken for <b>{creator}</b>\'s message within 24h.')
    if expired_keys:
        state['pending_qdrafts'] = pending_qdrafts

    # ── Poll creator iMessage chats ───────────────────────────────────────────
    creators = load_creators()
    if not creators:
        print('[poller] No creators found in creators_map.json')
        return state

    try:
        con = sqlite3.connect(DB_PATH)
    except Exception as e:
        print(f'[poller] Cannot open chat.db: {e}')
        return state

    found_total = 0

    for creator in creators:
        name       = creator.get('creator_name', 'Unknown')
        chat_uuid  = creator.get('chat_identifier', '')
        if not chat_uuid:
            continue

        entry       = state.get(chat_uuid, {})
        since_rowid = entry.get('last_rowid', 0)
        first_run   = since_rowid == 0  # Don't send Telegram alerts on first run
        messages    = read_new_messages(con, chat_uuid, since_rowid)

        if first_run and messages:
            # Bootstrap: record current max rowid, don't notify
            max_rowid = max(m['rowid'] for m in messages)
            state[chat_uuid] = {'last_rowid': max_rowid, 'name': name}
            print(f'  [init] {name}: bootstrapped at rowid={max_rowid} ({len(messages)} msgs skipped)')
            continue

        for msg in messages:
            found_total += 1
            text  = msg['text']
            label = classify_message(text)
            icon  = LABEL_ICON.get(label, '💬')
            ts    = datetime.fromtimestamp(msg['ts']).strftime('%H:%M') if msg['ts'] else '?'

            print(f'  [{label}] {name}: {text[:60]}')

            # Capa 5 — write interaction to local JSONL (synced to VPS after cycle)
            creator_info = _ss_id_for_chat(chat_uuid)
            if creator_info:
                append_interaction(creator_info[0], label, text)

            # Alert Ruben in Telegram
            alert = (
                f'{icon} <b>[{label.upper()}]</b> from <b>{name}</b> at {ts}\n'
                f'<i>{text[:300]}</i>'
            )

            markup = None
            if label == 'draft':
                markup = {'inline_keyboard': [[
                    {'text': '✅ Approve',         'callback_data': f'draft_approve|{chat_uuid}'},
                    {'text': '🔄 Request Changes', 'callback_data': f'draft_changes|{chat_uuid}'},
                    {'text': '❌ Reject',           'callback_data': f'draft_reject|{chat_uuid}'},
                ]]}
            elif label == 'complaint':
                alert += '\n\n🚨 <b>Needs immediate attention</b>'
            elif label == 'question':
                # Generate draft reply with Gemini (#19-20)
                draft = generate_draft_reply(name, text)
                if draft:
                    alert = (
                        f'{icon} <b>[QUESTION]</b> from <b>{name}</b> at {ts}\n'
                        f'<i>{text[:300]}</i>\n\n'
                        f'✍️ Draft reply:\n{draft}'
                    )
                    markup = {'inline_keyboard': [[
                        {'text': '📤 Send', 'callback_data': f'qdraft_send|{chat_uuid}'},
                        {'text': '✏️ Edit', 'callback_data': f'qdraft_edit|{chat_uuid}'},
                        {'text': '⏭️ Skip', 'callback_data': f'qdraft_skip|{chat_uuid}'},
                    ]]}
                    # Track for expiry (#23)
                    draft_key = f'{chat_uuid}|{msg["rowid"]}'
                    state.setdefault('pending_qdrafts', {})[draft_key] = {
                        'creator_name': name,
                        'chat_uuid':    chat_uuid,
                        'created_at':   int(time.time()),
                    }
                else:
                    alert += '\n\n→ Reply manually or use a template'

            tg_send(alert, reply_markup=markup)

            # Update last seen rowid
            entry = state.get(chat_uuid, {})
            entry['last_rowid'] = max(entry.get('last_rowid', 0), msg['rowid'])
            entry['name']       = name
            state[chat_uuid]    = entry

    con.close()

    if found_total:
        print(f'[poller] {found_total} new message(s) classified and sent to Telegram')
        sync_interactions_to_vps()
    else:
        print(f'[poller] No new messages ({len(creators)} chats checked)')

    return state


def main():
    print(f'[poller] Starting — checking {POLL_INTERVAL}s interval')
    print(f'[poller] Gemini: {"✅" if _gemini else "❌ (no key)"}')
    print(f'[poller] Telegram: {"✅" if VIRAL_TOKEN else "❌ (no token)"}')

    state = load_state()

    while True:
        try:
            state = poll_once(state)
            save_state(state)
        except Exception as e:
            print(f'[poller] Error: {e}')
        time.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    main()
