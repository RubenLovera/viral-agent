#!/usr/bin/env python3
"""Extract Ruben's iMessage text for voice profile generation.

Reads ~/Library/Messages/chat.db (streamtyped NSAttributedString format).
Exports up to 200 authentic messages to /tmp/ruben_messages.txt.

Sources (in order):
  1. SkinQueens groups — campaign-specific tone (skips today's bot messages)
  2. All other conversations — general authentic voice, last 6 months
"""
import re
import sqlite3
import time
from pathlib import Path

DB_PATH  = Path.home() / 'Library/Messages/chat.db'
OUT_FILE = Path('/tmp/ruben_messages.txt')
MIN_LEN  = 20
MAX_MSGS = 200

APPLE_EPOCH    = 978307200
_now           = time.time()
SIX_MONTHS_NS  = int((_now - APPLE_EPOCH - 15_552_000) * 1e9)
TODAY_START_NS = int((_now - _now % 86400 - APPLE_EPOCH) * 1e9)

SKIP_PHRASES = [
    'NSString', 'NSObject', 'NSAttributed', 'NSMutable', '__kIM',
    'Good morning', 'Your update for today', 'Total views:', 'Pending payment:',
    'Any questions? Reply here', 'log into SideShift',
    "We'd love to have you join", 'great opportunity to get paid',
    '¡Buenos días', 'Buenos días',
]


def parse_streamtyped(blob: bytes) -> str | None:
    """Extract text from a streamtyped NSAttributedString blob.

    Format: \x84\x01\x2b + length_encoding + utf8_text
      - length_byte < 0x80 → 1-byte length, text starts at next byte
      - length_byte == 0x81 → next 2 bytes are little-endian uint16 length
    """
    marker = b'\x84\x01\x2b'
    pos = blob.find(marker)
    if pos == -1:
        return None

    i = pos + len(marker)
    if i >= len(blob):
        return None

    len_byte = blob[i]
    if len_byte < 0x80:
        str_len   = len_byte
        str_start = i + 1
    elif len_byte == 0x81:
        if i + 2 >= len(blob):
            return None
        str_len   = blob[i + 1] | (blob[i + 2] << 8)  # little-endian
        str_start = i + 3
    else:
        return None

    if str_start + str_len > len(blob):
        return None

    try:
        return blob[str_start:str_start + str_len].decode('utf-8').strip()
    except UnicodeDecodeError:
        return None


def get_text(attr_body, raw_text: str | None) -> str | None:
    if raw_text and len(raw_text.strip()) >= MIN_LEN:
        t = raw_text.strip()
        return None if any(p in t for p in SKIP_PHRASES) else t

    if attr_body is None:
        return None

    result = parse_streamtyped(bytes(attr_body))
    if not result or len(result) < MIN_LEN:
        return None
    if any(p in result for p in SKIP_PHRASES):
        return None
    return result


def fetch(cur, chat_ids: list[int], before_ns: int,
          after_ns: int = 0, limit: int = 2000) -> list[tuple]:
    if not chat_ids:
        return []
    ph     = ','.join('?' * len(chat_ids))
    params = list(chat_ids) + [before_ns]
    extra  = ''
    if after_ns:
        extra = 'AND m.date > ?'
        params.append(after_ns)
    params.append(limit)
    cur.execute(f"""
        SELECT m.attributedBody, m.text
        FROM message m
        JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
        WHERE cmj.chat_id IN ({ph})
          AND m.is_from_me = 1
          AND m.date < ?
          {extra}
          AND (m.attributedBody IS NOT NULL
               OR (m.text IS NOT NULL AND length(trim(m.text)) > 0))
        ORDER BY m.date DESC
        LIMIT ?
    """, params)
    return cur.fetchall()


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # SkinQueens chat IDs
    cur.execute("""
        SELECT ROWID FROM chat
        WHERE display_name LIKE '%SkinQueen%'
           OR display_name LIKE '%Skin Queen%'
    """)
    sq_ids = [r[0] for r in cur.fetchall()]

    # All other recent chat IDs
    ph_excl = f"NOT IN ({','.join('?' * len(sq_ids))})" if sq_ids else "IS NOT NULL"
    cur.execute(f"""
        SELECT DISTINCT cmj.chat_id
        FROM message m
        JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
        WHERE m.is_from_me = 1
          AND m.date > ?
          AND cmj.chat_id {ph_excl}
        LIMIT 500
    """, [SIX_MONTHS_NS] + sq_ids)
    other_ids = [r[0] for r in cur.fetchall()]

    messages: list[str] = []

    # ── Source 1: SkinQueens (before today's bot messages) ───────────────────
    for attr_body, text in fetch(cur, sq_ids, before_ns=TODAY_START_NS):
        if len(messages) >= MAX_MSGS:
            break
        msg = get_text(attr_body, text)
        if msg:
            messages.append(msg)

    # ── Source 2: All other conversations (last 6 months) ────────────────────
    for attr_body, text in fetch(
        cur, other_ids,
        before_ns=TODAY_START_NS, after_ns=SIX_MONTHS_NS,
        limit=(MAX_MSGS - len(messages)) * 6,
    ):
        if len(messages) >= MAX_MSGS:
            break
        msg = get_text(attr_body, text)
        if msg:
            messages.append(msg)

    con.close()

    messages = messages[:MAX_MSGS]
    OUT_FILE.write_text('\n---\n'.join(messages), encoding='utf-8')

    print(f'✅ Extracted {len(messages)} messages → {OUT_FILE}')
    print(f'\nSample (first 5):')
    for m in messages[:5]:
        print(f'  • {m[:100]}')


if __name__ == '__main__':
    main()
