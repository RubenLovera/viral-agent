#!/usr/bin/env python3
"""sync_state.py — Daily state sync for UGC campaign creators.

Reads fresh post data from SideShift API and updates creators_map.json:
  - If posts > 0 AND warmup_start_date set → clears warmup_start_date, sets posting_since
  - If warmup days elapsed (> WARMUP_DAYS) AND no posts → logs warning, clears warmup_start_date
  - For active creators with posts but no posting_since → backfills posting_since
  - Updates last_sync timestamp

Run daily before status_check (cron: 50 12 * * * = 5:50 AM PT = 12:50 UTC):
    /root/viral-agent/.venv/bin/python3 /root/viral-agent/scripts/sync_state.py

Or manually with dry-run:
    /root/viral-agent/.venv/bin/python3 /root/viral-agent/scripts/sync_state.py --dry-run

Environment:
    Loaded from ENV_FILE env var, or /root/viral-agent/instances/<slug>/.env
    Required: SIDESHIFT_API_KEY, SS_PROGRAM
    Optional: DATA_DIR (default: /root/viral-agent/instances/<slug>/data)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load env — same as viral_bot.py
load_dotenv(os.environ.get('ENV_FILE', ''))

SS_BASE     = 'https://app.sideshift.app/api/v1'
SS_PROGRAM  = os.environ.get('SS_PROGRAM', '')
SS_API_KEY  = os.environ.get('SIDESHIFT_API_KEY', '')
DATA_DIR    = Path(os.environ.get('DATA_DIR', '/root/viral-agent/data'))
MAP_PATH    = DATA_DIR / 'creators_map.json'
WARMUP_DAYS = 3


def _ss_headers() -> dict:
    return {'x-api-key': SS_API_KEY}


def fetch_all_posts() -> list[dict]:
    """Fetch all posts for the program (paginates cursor-style, up to 25 pages)."""
    all_posts: list[dict] = []
    cursor = None
    for _ in range(25):
        params: dict = {'programId': SS_PROGRAM, 'limit': 200}
        if cursor:
            params['cursor'] = cursor
        r = httpx.get(f'{SS_BASE}/posts', params=params, headers=_ss_headers(), timeout=20)
        r.raise_for_status()
        data  = r.json()
        items = data.get('items', data.get('data', []))
        all_posts.extend(items)
        cursor = data.get('nextCursor') or data.get('next_cursor')
        if not cursor or len(items) < 200:
            break
    return all_posts


def load_map() -> tuple[list[dict], bool]:
    """Returns (list_of_creators, is_dict_format).

    creators_map.json can be either a list or a dict keyed by creator name.
    load_map() normalizes both to a list with a synthetic 'creator_name' field.
    """
    raw = json.loads(MAP_PATH.read_text())
    if isinstance(raw, list):
        return raw, False
    result = []
    for name, entry in raw.items():
        row = dict(entry)
        row.setdefault('creator_name', name)
        result.append(row)
    return result, True


def save_map(creators: list[dict], is_dict: bool) -> None:
    if is_dict:
        out = {c['creator_name']: {k: v for k, v in c.items() if k != 'creator_name'}
               for c in creators}
    else:
        out = creators
    MAP_PATH.write_text(json.dumps(out, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Show changes without writing')
    args = parser.parse_args()

    if not SS_API_KEY:
        print('ERROR: SIDESHIFT_API_KEY not set')
        sys.exit(1)
    if not SS_PROGRAM:
        print('ERROR: SS_PROGRAM not set')
        sys.exit(1)
    if not MAP_PATH.exists():
        print(f'ERROR: creators_map.json not found at {MAP_PATH}')
        sys.exit(1)

    creators, is_dict = load_map()
    today = date.today()
    print(f'Loaded {len(creators)} creators from {MAP_PATH}')

    print('Fetching posts from SideShift...')
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
                # Warm-up complete — creator started posting
                if not c.get('posting_since'):
                    posting_since = today.isoformat()
                    print(f'  ✅ {name}: warm-up done (day {days_in}), {post_count} posts → posting_since={posting_since}')
                    if not args.dry_run:
                        c['posting_since']     = posting_since
                        c['warmup_start_date'] = ''
                    changes += 1
            elif days_in > WARMUP_DAYS:
                # Warm-up window expired with no posts
                print(f'  ⚠️  {name}: warm-up expired (day {days_in}, 0 posts) — clearing warmup_start_date')
                if not args.dry_run:
                    c['warmup_start_date'] = ''
                changes += 1
            else:
                print(f'  🌱 {name}: warm-up day {days_in}/{WARMUP_DAYS} | {post_count} posts')
        else:
            # No warmup_start_date — backfill posting_since if creator has posts
            if post_count > 0 and not c.get('posting_since'):
                posting_since = today.isoformat()
                print(f'  📌 {name}: {post_count} posts, no posting_since → backfilling {posting_since}')
                if not args.dry_run:
                    c['posting_since'] = posting_since
                changes += 1

    # Update last_sync on the last entry (just a marker)
    if creators:
        creators[-1]['last_sync'] = today.isoformat()

    if args.dry_run:
        print(f'\n[DRY RUN] {changes} changes would be written to {MAP_PATH}')
    else:
        save_map(creators, is_dict)
        if changes:
            print(f'\n✅ {changes} changes saved to {MAP_PATH}')
        else:
            print('\nNo creator changes — last_sync updated.')


if __name__ == '__main__':
    main()
