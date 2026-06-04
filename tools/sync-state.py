#!/usr/bin/env python3
"""sync-state.py — Daily state sync for SkinQueens creators.

Reads fresh data from SideShift API and updates creators_map.json:
  - If posts > 0 AND warmup_start_date set → clears warmup_start_date, sets posting_since
  - If warmup days elapsed (> WARMUP_DAYS) AND no posts → logs warning, clears warmup_start_date
  - Updates last_sync timestamp

Run daily before status_check (e.g. 5:50 AM PT via cron):
    python3 tools/sync-state.py

Or manually:
    python3 tools/sync-state.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path.home() / '.zshrc', override=False)
load_dotenv(Path.home() / 'VIRAL' / '.env', override=False)

VIRAL_DIR        = Path.home() / 'VIRAL'
DATA_DIR         = VIRAL_DIR / 'data'
CREATORS_MAP_VPS = Path('/root/culver-os/viral-bot/data/creators_map.json')

SS_BASE    = 'https://app.sideshift.app/api/v1'
SS_PROGRAM = os.environ.get('SS_PROGRAM', 'TB3foYXKIztJmVZmPkyJ')
SS_API_KEY = os.environ.get('SIDESHIFT_API_KEY', '')
WARMUP_DAYS = 3


def _ss_headers() -> dict:
    return {'x-api-key': SS_API_KEY}


def fetch_all_posts() -> list[dict]:
    """Fetch all posts for the program (all pages)."""
    all_posts: list[dict] = []
    cursor = None
    for _ in range(25):
        params: dict = {'programId': SS_PROGRAM, 'limit': 200}
        if cursor:
            params['cursor'] = cursor
        r = httpx.get(f'{SS_BASE}/posts', params=params, headers=_ss_headers(), timeout=20)
        r.raise_for_status()
        data   = r.json()
        items  = data.get('items', data.get('data', []))
        all_posts.extend(items)
        cursor = data.get('nextCursor') or data.get('next_cursor')
        if not cursor or len(items) < 200:
            break
    return all_posts


def load_creators_map(path: Path) -> tuple[list[dict], bool]:
    """Returns (list, is_dict_format)."""
    if not path.exists():
        return [], False
    raw = json.loads(path.read_text())
    if isinstance(raw, list):
        return raw, False
    result = []
    for name, entry in raw.items():
        row = dict(entry)
        row.setdefault('creator_name', name)
        result.append(row)
    return result, True


def save_creators_map(path: Path, creators: list[dict], is_dict: bool) -> None:
    if is_dict:
        out = {c['creator_name']: {k: v for k, v in c.items() if k != 'creator_name'}
               for c in creators}
    else:
        out = creators
    path.write_text(json.dumps(out, indent=2))


def find_creators_map() -> Path:
    candidates = [
        VIRAL_DIR / 'data' / 'creators_map.json',
        DATA_DIR / 'creators_map.json',
    ]
    for p in candidates:
        if p.exists():
            return p
    print('ERROR: creators_map.json not found. Tried:', [str(p) for p in candidates])
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Sync creator state from SideShift API')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without writing')
    args = parser.parse_args()

    if not SS_API_KEY:
        print('ERROR: SIDESHIFT_API_KEY not set')
        sys.exit(1)

    map_path = find_creators_map()
    creators, is_dict = load_creators_map(map_path)
    today = date.today()

    print(f'Loaded {len(creators)} creators from {map_path}')

    print('Fetching posts from SideShift API...')
    posts = fetch_all_posts()
    print(f'  → {len(posts)} posts fetched')

    posts_by_cid: dict[str, int] = {}
    for p in posts:
        cid = p.get('contractorId') or p.get('creatorId') or ''
        if cid:
            posts_by_cid[cid] = posts_by_cid.get(cid, 0) + 1

    changes = 0
    for c in creators:
        ss_id      = c.get('sideshift_id', '')
        name       = c.get('creator_name', 'Creator')
        status     = c.get('contract_status', '')
        start_date = c.get('warmup_start_date', '')
        post_count = posts_by_cid.get(ss_id, 0)

        if status not in ('active', 'pending'):
            continue

        if start_date:
            try:
                start = date.fromisoformat(start_date)
            except ValueError:
                continue

            days_in = (today - start).days + 1

            if post_count > 0:
                # Creator is posting — warm-up complete
                if not c.get('posting_since'):
                    posting_since = today.isoformat()
                    print(f'  ✅ {name}: warm-up done (day {days_in}), {post_count} posts → posting_since={posting_since}')
                    if not args.dry_run:
                        c['posting_since']    = posting_since
                        c['warmup_start_date'] = ''  # clear so status_check handles them normally
                    changes += 1
            elif days_in > WARMUP_DAYS:
                # Warm-up expired without posts
                print(f'  ⚠️  {name}: warm-up expired (day {days_in}, 0 posts) — clearing warmup_start_date')
                if not args.dry_run:
                    c['warmup_start_date'] = ''
                changes += 1
            else:
                print(f'  🌱 {name}: warm-up day {days_in}/{WARMUP_DAYS} | {post_count} posts')
        else:
            if post_count > 0 and not c.get('posting_since'):
                posting_since = today.isoformat()
                print(f'  📌 {name}: no warmup_start_date but {post_count} posts → posting_since={posting_since}')
                if not args.dry_run:
                    c['posting_since'] = posting_since
                changes += 1

    c['last_sync'] = today.isoformat() if creators else ''

    if args.dry_run:
        print(f'\n[DRY RUN] {changes} changes would be written to {map_path}')
    else:
        if changes:
            save_creators_map(map_path, creators, is_dict)
            print(f'\n✅ {changes} changes saved to {map_path}')
        else:
            print('\nNo changes needed.')


if __name__ == '__main__':
    main()
