#!/usr/bin/env python3
"""Read iMessages from a specific group chat since a given ROWID.

Usage: python3 read_messages.py <chat_uuid> <since_rowid>
Output: JSON array of {rowid, text, ts_unix, is_from_me}
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH    = Path.home() / 'Library/Messages/chat.db'
APPLE_EPOCH = 978307200  # seconds between Unix epoch and Apple epoch (2001-01-01)


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


def get_text(attr_body, raw_text) -> str | None:
    if raw_text and raw_text.strip():
        return raw_text.strip()
    if attr_body:
        return parse_streamtyped(bytes(attr_body))
    return None


def main():
    if len(sys.argv) < 3:
        print(json.dumps({'error': 'Usage: read_messages.py <chat_uuid> <since_rowid>'}))
        sys.exit(1)

    chat_uuid  = sys.argv[1]
    since_rowid = int(sys.argv[2])

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Find chat by UUID (stored as "chat{uuid}" or just the uuid in chat_identifier)
    cur.execute("""
        SELECT ROWID FROM chat
        WHERE chat_identifier LIKE ?
        LIMIT 1
    """, (f'%{chat_uuid}%',))
    row = cur.fetchone()
    if not row:
        print(json.dumps({'messages': [], 'error': f'Chat not found: {chat_uuid}'}))
        con.close()
        return

    chat_db_id = row[0]

    cur.execute("""
        SELECT m.ROWID, m.text, m.attributedBody, m.date, m.is_from_me
        FROM message m
        JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
        WHERE cmj.chat_id = ?
          AND m.ROWID > ?
        ORDER BY m.ROWID ASC
        LIMIT 100
    """, (chat_db_id, since_rowid))

    messages = []
    for rowid, text, attr_body, apple_ts, is_from_me in cur.fetchall():
        content = get_text(attr_body, text)
        if not content or len(content.strip()) < 2:
            continue
        ts_unix = int(apple_ts / 1_000_000_000) + APPLE_EPOCH if apple_ts else 0
        messages.append({
            'rowid':       rowid,
            'text':        content,
            'ts_unix':     ts_unix,
            'is_from_me':  bool(is_from_me),
        })

    con.close()
    print(json.dumps({'messages': messages}))


if __name__ == '__main__':
    main()
