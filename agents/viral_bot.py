#!/usr/bin/env python3
"""viral_bot — VIRAL Agent for The Viral App UGC coordination.

Bot #5 of CulverOS. Autonomous multi-creator campaign coordinator for UGC managers.
All client-specific values (campaign name, paths, credentials) are configured via .env.
"""
import asyncio
import html as html_module
import json
import logging
import os
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from google import genai
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters,
)

load_dotenv(os.environ.get('ENV_FILE', '/root/culver-os/.env.viral'))

# ── Config ────────────────────────────────────────────────────────────────────

TELEGRAM_TOKEN   = os.environ['VIRAL_TOKEN']
CHAT_ID          = int(os.environ['CHAT_ID'])
VIRAL_THREAD_ID  = int(os.environ.get('VIRAL_THREAD_ID', 0)) or None
MAC_RELAY_URL    = os.environ.get('MAC_RELAY_URL', '')  # http://MacBook-Air.local:3737
MAC_RELAY_KEY    = os.environ.get('MAC_RELAY_KEY', '')

DATA_DIR          = Path(os.environ.get('DATA_DIR', '/root/culver-os/viral-bot/data'))
STATE_FILE        = DATA_DIR / 'viral-bot-state.json'
CREATORS_MAP_FILE = DATA_DIR / 'creators_map.json'
VOICE_PROFILE_FILE   = DATA_DIR / 'voice_profile.json'
CHANNEL_STATE_FILE   = DATA_DIR / 'channel_state.json'
CADENCE_FILE         = DATA_DIR / 'cadence_state.json'
KNOWLEDGE_DIR     = Path(os.environ.get('KNOWLEDGE_DIR', '/root/culver-os/viral-bot/knowledge'))
BRIEF_FILE        = KNOWLEDGE_DIR / os.environ.get('BRIEF_FILENAME', 'campaign_brief.md')
CREATORS_DIR      = DATA_DIR / 'creators'
TEMPLATES         = Path(os.environ.get('TEMPLATES_DIR', '/root/culver-os/viral-bot/templates'))
POSTS_GOAL        = int(os.environ.get('POSTS_GOAL', '60'))

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
_gemini = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
GEMINI_MODEL   = 'gemini-2.5-flash'

SLACK_BOT_TOKEN   = os.environ.get('SLACK_BOT_TOKEN', '')
SLACK_USER_TOKEN  = os.environ.get('SLACK_USER_TOKEN', '')  # needed for DMs (D...)
SLACK_CHANNEL_IDS = [c.strip() for c in os.environ.get('SLACK_CHANNEL_IDS', '').split(',') if c.strip()]
TVA_CONTEXT_FILE  = KNOWLEDGE_DIR / 'tva_context.md'

LA_TZ = ZoneInfo('America/Los_Angeles')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
logger = logging.getLogger('viral_bot')

# ── SideShift API ─────────────────────────────────────────────────────────────

SS_BASE    = 'https://app.sideshift.app/api/v1'
SS_PROGRAM = os.environ.get('SS_PROGRAM', '')

CLIENT_NAME  = os.environ.get('CLIENT_NAME', 'SkinQueens')
MANAGER_NAME = os.environ.get('MANAGER_NAME', 'Ruben')
VPS_HOST     = os.environ.get('VPS_HOST', '')

def _ss_headers():
    return {'x-api-key': os.environ['SIDESHIFT_API_KEY']}


async def _ss(path: str, params: dict | None = None) -> dict:
    url = f'{SS_BASE}{path}'
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, params=params or {}, headers=_ss_headers())
        r.raise_for_status()
        return r.json()


async def _ss_post(path: str, payload: dict) -> dict:
    url = f'{SS_BASE}{path}'
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload, headers=_ss_headers())
        r.raise_for_status()
        return r.json()


async def _ss_paginate(path: str, params: dict,
                       page_limit: int = 200, max_pages: int = 25) -> list:
    """Fetch all pages from a SideShift endpoint using cursor-based pagination."""
    all_items: list = []
    cursor: str | None = None
    for page in range(max_pages):
        page_params = {**params, 'limit': page_limit}
        if cursor:
            page_params['cursor'] = cursor
        data   = await _ss(path, page_params)
        items  = data.get('items', data.get('data', []))
        all_items.extend(items)
        cursor = data.get('nextCursor') or data.get('next_cursor')
        if not cursor or len(items) < page_limit:
            break
        logger.debug('_ss_paginate %s page %d: %d items, cursor=%s', path, page + 1, len(items), cursor[:8])
    logger.info('_ss_paginate %s: %d total items', path, len(all_items))
    return all_items

# ── Creators DB ───────────────────────────────────────────────────────────────

def load_creators() -> list[dict]:
    path = DATA_DIR / 'creators.json'
    if not path.exists():
        logger.warning('creators.json not found at %s', path)
        return []
    data = json.loads(path.read_text())
    return data.get('creators', data) if isinstance(data, dict) else data


def skinqueens_creators(creators: list[dict]) -> list[dict]:
    return [c for c in creators if any(
        'skinqueen' in (camp or '').lower()
        for camp in c.get('campaigns', [])
    )]


def load_creators_map() -> list[dict]:
    if not CREATORS_MAP_FILE.exists():
        logger.warning('creators_map.json not found at %s', CREATORS_MAP_FILE)
        return []
    raw = json.loads(CREATORS_MAP_FILE.read_text())
    if isinstance(raw, list):
        return raw
    # Dict format: {"Creator Name": {fields...}}
    result = []
    for name, entry in raw.items():
        row = dict(entry)
        row.setdefault('creator_name', name)
        result.append(row)
    return result

# ── State ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ── Mac Relay (iMessage) ──────────────────────────────────────────────────────

async def send_imessage(to: str, message: str) -> bool:
    if not MAC_RELAY_URL:
        logger.info('MAC_RELAY_URL not set — skipping iMessage to %s', to)
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f'{MAC_RELAY_URL}/imessage',
                json={'to': to, 'message': message},
                headers={'X-Relay-Key': MAC_RELAY_KEY},
            )
            r.raise_for_status()
            return True
    except Exception as e:
        logger.error('mac-relay error: %s', e)
        return False


async def send_group_imessage(chat_identifier: str, message: str) -> bool:
    if not MAC_RELAY_URL:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                f'{MAC_RELAY_URL}/send-group',
                json={'chat_identifier': chat_identifier, 'message': message},
                headers={'X-Relay-Key': MAC_RELAY_KEY},
            )
            r.raise_for_status()
            return True
    except Exception as e:
        logger.error('mac-relay send-group error: %s', e)
        return False

# ── Telegram Helpers ──────────────────────────────────────────────────────────

async def send(bot: Bot, text: str):
    kwargs = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'HTML'}
    if VIRAL_THREAD_ID:
        kwargs['message_thread_id'] = VIRAL_THREAD_ID
    await bot.send_message(**kwargs)

# ── Report Formatters ─────────────────────────────────────────────────────────

def fmt_views(n: int | None) -> str:
    if n is None:
        return '—'
    if n >= 1_000_000:
        return f'{n / 1_000_000:.1f}M'
    if n >= 1_000:
        return f'{n / 1_000:.1f}k'
    return str(n)


def _yesterday_str() -> str:
    return (date.today() - timedelta(days=1)).isoformat()


def _today_str() -> str:
    return date.today().isoformat()

# ── Morning Report (9am cron) ─────────────────────────────────────────────────

async def morning_report(bot: Bot):
    logger.info('Running morning report')
    today = datetime.now(LA_TZ).strftime('%A, %B %d')
    lines = [f'🌅 <b>VIRAL Morning Report</b> — {today}\n']

    # ── SkinQueens overview ──
    try:
        overview = await _ss('/analytics/overview', {'programId': SS_PROGRAM})
        summary  = overview.get('data', {}).get('summary', {})
        total_views  = summary.get('totalViews', 0)
        total_posts  = summary.get('totalPosts', 0)
        active_cr    = summary.get('uniqueCreators', 0)
        total_earned = summary.get('totalEarnings', 0)

        lines.append('📊 <b>SkinQueens</b>')
        lines.append(f'  • Views totales: {fmt_views(total_views)}')
        lines.append(f'  • Posts totales: {total_posts}')
        lines.append(f'  • Creadores activos: {active_cr}')
        if total_earned:
            lines.append(f'  • Pagado a creadores: ${total_earned:.2f}')
        lines.append('')
    except Exception as e:
        lines.append(f'⚠️ Error fetching overview: {e}\n')

    # ── Top 5 videos ──
    try:
        videos_data = await _ss('/analytics/videos', {
            'program': SS_PROGRAM,
            'limit': 5,
            'sortBy': 'views',
            'sortOrder': 'desc',
        })
        videos = videos_data.get('items', videos_data.get('data', []))
        if videos:
            lines.append('🎬 <b>Top Videos</b>')
            for i, v in enumerate(videos[:5], 1):
                creator_name = v.get('contractorName', v.get('creator', 'Unknown'))
                views  = v.get('views', 0)
                likes  = v.get('likes', 0)
                er     = v.get('engagementRate', 0)
                platform = v.get('platform', '')
                platform_icon = {'tiktok': '🎵', 'instagram': '📷', 'youtube': '▶️'}.get(platform, '📱')
                lines.append(
                    f'  {i}. {platform_icon} {creator_name} — '
                    f'{fmt_views(views)} views | {fmt_views(likes)} likes | ER {er:.1f}%'
                )
            lines.append('')
    except Exception as e:
        lines.append(f'⚠️ Error fetching videos: {e}\n')

    # ── Posts yesterday ──
    try:
        posts_data  = await _ss('/posts', {
            'program': SS_PROGRAM,
            'fromDate': _yesterday_str(),
            'toDate': _today_str(),
            'limit': 100,
        })
        posts_yesterday = posts_data.get('items', posts_data.get('data', []))
        posted_yesterday = len(posts_yesterday)
        posted_names     = [
            p.get('contractorName', p.get('creator', 'Unknown'))
            for p in posts_yesterday
        ]

        lines.append(f'✅ <b>Postearon ayer:</b> {posted_yesterday}')
        if posted_names:
            lines.append('  ' + ', '.join(posted_names[:10]))
            if len(posted_names) > 10:
                lines.append(f'  ...y {len(posted_names) - 10} más')
        lines.append('')
    except Exception as e:
        lines.append(f'⚠️ Error fetching posts: {e}\n')

    # ── Contracts ──
    try:
        contracts_data = await _ss('/contracts', {'limit': 100})
        contracts = contracts_data.get('items', contracts_data.get('data', []))
        pending_contracts = [c for c in contracts if c.get('status') in ('pending', 'invited')]
        active_contracts  = [c for c in contracts if c.get('status') == 'active']

        if pending_contracts:
            lines.append(f'📋 <b>Contratos pendientes:</b> {len(pending_contracts)}')
            for c in pending_contracts[:5]:
                creator_name = c.get('contractorName', 'Unknown')
                lines.append(f'  • {creator_name} ({c.get("status", "")})')
            lines.append('')
        lines.append(f'📝 Contratos activos: {len(active_contracts)}')
        lines.append('')
    except Exception as e:
        lines.append(f'⚠️ Error fetching contracts: {e}\n')

    # ── Pending payouts ──
    try:
        payouts_data = await _ss('/payouts/pending', {'limit': 50})
        pending = payouts_data.get('items', payouts_data.get('data', []))
        if pending:
            total_pending = sum(p.get('amount', 0) for p in pending)
            lines.append(f'💸 <b>Pagos pendientes:</b> {len(pending)} (${total_pending:.2f})')
            lines.append('')
    except Exception as e:
        logger.warning('Error fetching payouts: %s', e)

    # ── Creators summary from creators_map ──
    creators_map = load_creators_map()
    if creators_map:
        active_n  = len([c for c in creators_map if c.get('contract_status') == 'active'])
        pending_n = len([c for c in creators_map if c.get('contract_status') == 'pending'])
        lines.append(f'👥 <b>Creadoras {CLIENT_NAME}:</b> {len(creators_map)} total — {active_n} activas, {pending_n} pendientes')

    # Save state
    new_state = {'last_run': datetime.now(LA_TZ).isoformat()}
    save_state(new_state)

    await send(bot, '\n'.join(lines))
    logger.info('Morning report sent')

# ── Buenos Días Check (11am cron) ─────────────────────────────────────────────

async def buenos_dias_check(bot: Bot):
    """11 AM — Alert about active creators who haven't posted today."""
    logger.info('Running buenos días check')
    creators_map = load_creators_map()
    cs_all       = load_channel_state()

    active = [c for c in creators_map if c.get('contract_status') == 'active']
    if not active:
        return

    silent = []
    for c in active:
        ss_id = c.get('sideshift_id', '')
        cs    = cs_all.get(ss_id, {})
        days  = cs.get('days_since_last')
        if days is None or days >= 1:
            silent.append(c)

    if not silent:
        logger.info('Buenos días check: all creators posted')
        return

    lines = [f'⏰ <b>Sin postear hoy:</b> {len(silent)} creadoras\n']
    for c in silent[:10]:
        name  = c.get('creator_name', 'Creator')
        ss_id = c.get('sideshift_id', '')
        cs    = cs_all.get(ss_id, {})
        days  = cs.get('days_since_last', '?')
        lines.append(f'  • {name} — {days}d sin postear')

    await send(bot, '\n'.join(lines))

# ── Overdue Check (5pm cron) ──────────────────────────────────────────────────

async def overdue_check(bot: Bot):
    """5 PM — Alert about active creators silent for 24h+ based on channel state."""
    logger.info('Running overdue check')
    creators_map = load_creators_map()
    cs_all       = load_channel_state()

    active = [c for c in creators_map if c.get('contract_status') == 'active']
    if not active:
        return

    overdue = []
    for c in active:
        ss_id = c.get('sideshift_id', '')
        cs    = cs_all.get(ss_id, {})
        days  = cs.get('days_since_last')
        if days is not None and days >= 1:
            overdue.append((c.get('creator_name', 'Creator'), days))

    if not overdue:
        logger.info('Overdue check: no overdue creators')
        return

    lines = [f'🚨 <b>OVERDUE — sin postear hoy:</b> {len(overdue)} creadoras\n']
    for name, days in sorted(overdue, key=lambda x: x[1], reverse=True)[:10]:
        lines.append(f'  • {name} — {days}d sin postear')
    lines.append('\n→ Considera escalar al team lead.')
    await send(bot, '\n'.join(lines))

# ── Nightly Digest (9pm cron) ─────────────────────────────────────────────────

async def nightly_digest(bot: Bot):
    logger.info('Running nightly digest')
    today     = datetime.now(LA_TZ).strftime('%A, %B %d')
    today_str = _today_str()
    lines     = [f'🌙 <b>VIRAL Nightly Digest</b> — {today}\n']

    posts_today, views_today, top_creator, top_views = [], 0, '—', 0

    # ── Posts today (filter client-side by uploadedAt Unix timestamp) ──
    try:
        import calendar
        today_midnight_utc = calendar.timegm(date.today().timetuple())
        posts_data  = await _ss('/posts', {
            'program': SS_PROGRAM,
            'limit':   500,
        })
        all_posts_raw = posts_data.get('items', posts_data.get('data', []))
        posts_today   = [p for p in all_posts_raw
                         if (p.get('uploadedAt') or 0) >= today_midnight_utc]
        views_today = sum(p.get('views', 0) for p in posts_today)

        posted_names = [p.get('contractorName', p.get('creator', '?')) for p in posts_today]

        if posts_today:
            top_post    = max(posts_today, key=lambda p: p.get('views', 0))
            top_creator = top_post.get('contractorName', top_post.get('creator', '—'))
            top_views   = top_post.get('views', 0)

        lines.append(f'📊 <b>Today\'s Activity</b>')
        lines.append(f'  • Posts: {len(posts_today)} | Views: {fmt_views(views_today)}')
        if top_creator != '—':
            lines.append(f'  • Top post: {top_creator} ({fmt_views(top_views)} views)')
        if posted_names:
            lines.append(f'  • Posted: {", ".join(posted_names[:8])}' +
                         (f' +{len(posted_names)-8} more' if len(posted_names) > 8 else ''))
        lines.append('')
    except Exception as e:
        lines.append(f'⚠️ Posts error: {e}\n')

    # ── Channel state pipeline ──
    cs_all = load_channel_state()
    if not cs_all:
        lines.append('👥 <b>Creator Pipeline:</b> <i>No data yet — populates at 6 AM</i>\n')
    if cs_all:
        counts   = {'onboarding': 0, 'warm_up': 0, 'active': 0, 'silent': 0}
        silent_names = []
        creators_map = load_creators_map()
        name_by_id   = {c.get('sideshift_id', ''): c.get('creator_name', '?') for c in creators_map}

        for ss_id, cs in cs_all.items():
            st = cs.get('state', 'active')
            counts[st] = counts.get(st, 0) + 1
            if st == 'silent':
                days = cs.get('days_since_last', '?')
                silent_names.append(f'{name_by_id.get(ss_id, "?")} ({days}d)')

        lines.append('👥 <b>Creator Pipeline</b>')
        lines.append(
            f'  ✅ Active: {counts["active"]}  '
            f'🌱 Warm-up: {counts["warm_up"]}  '
            f'🆕 Onboarding: {counts["onboarding"]}  '
            f'🔇 Silent: {counts["silent"]}'
        )
        if silent_names:
            lines.append(f'  → Silent: {", ".join(silent_names[:5])}' +
                         (f' +{len(silent_names)-5}' if len(silent_names) > 5 else ''))
        lines.append('')

    # ── Cadence — how many contacted today ──
    cadence   = load_cadence()
    contacted = sum(1 for v in cadence.values() if v.get('last_contacted') == today_str)
    if contacted:
        lines.append(f'📨 <b>Contacted today:</b> {contacted} creators')
        lines.append('')

    # ── Pending payouts ──
    try:
        payouts_data  = await _ss('/payouts/pending', {'limit': 200})
        pending_pays  = payouts_data.get('items', payouts_data.get('data', []))
        if pending_pays:
            total_pending = sum(p.get('amount', 0) for p in pending_pays)
            lines.append(f'💸 <b>Pending payouts:</b> {len(pending_pays)} creators (${total_pending:.2f})')
            lines.append('')
    except Exception as e:
        logger.warning('Nightly digest payouts error: %s', e)

    # ── AI insight ──
    if _gemini and posts_today:
        try:
            n_posted  = len(posts_today)
            n_silent  = counts.get('silent', 0) if cs_all else '?'
            n_active  = counts.get('active', 0) if cs_all else '?'
            loop      = asyncio.get_event_loop()
            prompt    = (
                f"You are a UGC campaign manager summarizing today's performance for {CLIENT_NAME}.\n"
                f"Data: {n_posted} posts today, {fmt_views(views_today)} total views, "
                f"top creator {top_creator} ({fmt_views(top_views)} views), "
                f"{n_active} active creators, {n_silent} silent.\n"
                f"Write 2 sentences max: one on today's performance, one actionable focus for tomorrow. "
                f"Be direct and data-driven. No emojis."
            )
            response = await loop.run_in_executor(
                None,
                lambda: _gemini.models.generate_content(model=GEMINI_MODEL, contents=prompt),
            )
            insight = response.text.strip()
            lines.append(f'🤖 <b>Insight:</b> <i>{insight}</i>')
        except Exception as e:
            logger.warning('Nightly digest Gemini error: %s', e)

    await send(bot, '\n'.join(lines))
    logger.info('Nightly digest sent')


# ── Voice Profile + LLM Message Builder ──────────────────────────────────────

_cached_voice_profile: dict | None = None


def load_voice_profile() -> dict | None:
    global _cached_voice_profile
    if _cached_voice_profile is not None:
        return _cached_voice_profile
    if VOICE_PROFILE_FILE.exists():
        _cached_voice_profile = json.loads(VOICE_PROFILE_FILE.read_text())
        return _cached_voice_profile
    logger.warning('voice_profile.json not found — LLM messages disabled')
    return None


def load_brief() -> str | None:
    if BRIEF_FILE.exists():
        return BRIEF_FILE.read_text().strip()
    return None


def load_tva_context() -> str | None:
    if TVA_CONTEXT_FILE.exists():
        return TVA_CONTEXT_FILE.read_text().strip()
    return None


def load_creator_profile(ss_id: str) -> dict | None:
    path = CREATORS_DIR / f'{ss_id}.json'
    if path.exists():
        return json.loads(path.read_text())
    return None


def append_creator_action(ss_id: str, name: str, action_type: str, text: str) -> None:
    """Log a proactive bot action to actions[] in the creator profile (Capa 6)."""
    CREATORS_DIR.mkdir(parents=True, exist_ok=True)
    path = CREATORS_DIR / f'{ss_id}.json'
    profile = load_creator_profile(ss_id) or {
        'ss_id': ss_id, 'name': name, 'notes': [],
        'events': [], 'interactions': [], 'actions': [],
    }
    profile.setdefault('actions', []).append({
        'ts':   datetime.now(tz=LA_TZ).strftime('%Y-%m-%d %H:%M'),
        'type': action_type,
        'text': text,
    })
    profile['last_updated'] = datetime.now(tz=LA_TZ).strftime('%Y-%m-%d')
    path.write_text(json.dumps(profile, indent=2))
    logger.debug('Creator action: %s [%s]', name, action_type)


def append_creator_note(ss_id: str, name: str, event: str, text: str) -> None:
    CREATORS_DIR.mkdir(parents=True, exist_ok=True)
    path = CREATORS_DIR / f'{ss_id}.json'
    profile = load_creator_profile(ss_id) or {'ss_id': ss_id, 'name': name, 'notes': []}
    profile['notes'].append({
        'ts': datetime.now(tz=LA_TZ).strftime('%Y-%m-%d %H:%M'),
        'event': event,
        'text': text,
    })
    profile['last_updated'] = datetime.now(tz=LA_TZ).strftime('%Y-%m-%d')
    path.write_text(json.dumps(profile, indent=2))
    logger.debug('Creator note: %s [%s]', name, event)


def update_creator_state(ss_id: str, name: str, cs: dict,
                         total_views: int = 0, total_likes: int = 0) -> None:
    """Overwrite the state dict in a creator profile. Called by status_check (6 AM)."""
    CREATORS_DIR.mkdir(parents=True, exist_ok=True)
    path = CREATORS_DIR / f'{ss_id}.json'
    profile = load_creator_profile(ss_id) or {
        'ss_id': ss_id, 'name': name, 'notes': [],
        'events': [], 'interactions': [], 'actions': [],
    }
    today = datetime.now(tz=LA_TZ).strftime('%Y-%m-%d')

    old_state = profile.get('state', {})
    old_cs    = old_state.get('channel_state', '')
    new_cs    = cs.get('state', 'onboarding')

    profile['state'] = {
        'channel_state':         new_cs,
        'posts_count':           cs.get('posts_count', 0),
        'posts_goal':            POSTS_GOAL,
        'progress_pct':          round((cs.get('posts_count', 0) / POSTS_GOAL) * 100),
        'days_since_last_post':  cs.get('days_since_last'),
        'last_post_date':        cs.get('last_post_date'),
        'first_post_date':       cs.get('first_post_date'),
        'total_views':           total_views,
        'total_likes':           total_likes,
        'updated_at':            today,
    }

    # Record state transitions as episodic events
    if 'events' not in profile:
        profile['events'] = []
    ts_now = datetime.now(tz=LA_TZ).strftime('%Y-%m-%d %H:%M')
    if old_cs and old_cs != new_cs:
        profile['events'].append({
            'ts': ts_now, 'type': 'state_change',
            'text': f'{old_cs} → {new_cs}.',
        })
    if cs.get('first_post_date'):
        existing = {e.get('type') for e in profile['events']}
        if 'first_post' not in existing:
            profile['events'].append({
                'ts': cs['first_post_date'], 'type': 'first_post',
                'text': f'First post on {cs["first_post_date"]}.',
            })

    for key in ('interactions', 'actions'):
        if key not in profile:
            profile[key] = []

    # Merge interactions written by message_poller (Capa 5 — Mac side)
    interactions_file = CREATORS_DIR / f'{ss_id}.interactions.jsonl'
    if interactions_file.exists():
        existing_ts = {ix.get('ts') for ix in profile['interactions']}
        for line in interactions_file.read_text().splitlines():
            try:
                entry = json.loads(line)
                if entry.get('ts') not in existing_ts:
                    profile['interactions'].append(entry)
                    existing_ts.add(entry['ts'])
            except Exception:
                pass

    profile['last_updated'] = today
    path.write_text(json.dumps(profile, indent=2))
    logger.debug('Creator state updated: %s [%s, %d posts]', name, new_cs, cs.get('posts_count', 0))


def _profile_context(ss_id: str) -> str:
    """Build a compact context string from a creator profile for LLM injection."""
    profile = load_creator_profile(ss_id)
    if not profile:
        return ''
    parts = []

    state = profile.get('state', {})
    if state:
        cs    = state.get('channel_state', '?')
        posts = state.get('posts_count', 0)
        goal  = state.get('posts_goal', POSTS_GOAL)
        views = state.get('total_views', 0)
        days  = state.get('days_since_last_post')
        handles = ', '.join(state.get('social_handles', []))
        line = f'Status: {cs} — {posts}/{goal} posts'
        if views:
            line += f' — {views:,} views'
        if days is not None:
            line += f' — last post {days}d ago'
        if handles:
            line += f' — {handles}'
        parts.append(line)

    events = [e for e in profile.get('events', []) if e.get('type') != 'state_snapshot'][-3:]
    if events:
        parts.append('Key events: ' + '; '.join(e['text'] for e in events))

    recent_notes = profile.get('notes', [])[-3:]
    if recent_notes:
        parts.append('Notes: ' + '; '.join(f"[{n['event']}] {n['text']}" for n in recent_notes))

    recent_ix = profile.get('interactions', [])[-3:]
    if recent_ix:
        parts.append('Recent topics: ' + '; '.join(ix.get('text', '') for ix in recent_ix))

    return '\n'.join(parts) if parts else ''


# ── Channel State ─────────────────────────────────────────────────────────────

# ── Cadence (daily contact frequency control) ─────────────────────────────────

def load_cadence() -> dict:
    if CADENCE_FILE.exists():
        return json.loads(CADENCE_FILE.read_text())
    return {}


def save_cadence(cadence: dict):
    CADENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CADENCE_FILE.write_text(json.dumps(cadence, indent=2))


def should_contact(
    status: str,
    channel_state: dict | None,
    cadence: dict,
    chat_ident: str,
) -> tuple[bool, str]:
    """Return (send, reason). reason: ok | already_today | pending_cooldown |
    outreach_cooldown | silent_escalate | at_risk."""
    entry = cadence.get(chat_ident, {})

    # At-risk creators: stop all proactive contact (#24 escalation policy)
    if entry.get('at_risk'):
        return False, 'at_risk'

    last  = entry.get('last_contacted')
    today = date.today().isoformat()

    if last == today:
        return False, 'already_today'

    cs_state    = (channel_state or {}).get('state', 'active')
    days_silent = (channel_state or {}).get('days_since_last') or 0

    if status == 'active':
        # Silent ≥2 days AND was already nudged yesterday → escalate, don't spam
        if cs_state == 'silent' and days_silent >= 2 and last:
            return False, 'silent_escalate'
        return True, 'ok'

    if status == 'pending':
        if not last:
            return True, 'ok'
        if (date.today() - date.fromisoformat(last)).days >= 2:
            return True, 'ok'
        return False, 'pending_cooldown'

    if status == 'outreach':
        if not last:
            return True, 'ok'
        if (date.today() - date.fromisoformat(last)).days >= 3:
            return True, 'ok'
        return False, 'outreach_cooldown'

    return True, 'ok'


def record_contact(cadence: dict, chat_ident: str, status: str, cs_state: str):
    """Update cadence entry after a successful send."""
    entry = cadence.get(chat_ident, {})
    entry['last_contacted']  = date.today().isoformat()
    entry['last_status']     = status
    entry['last_cs_state']   = cs_state
    entry['contact_count']   = entry.get('contact_count', 0) + 1
    # Track consecutive silent follow-ups for #24 escalation policy
    if cs_state == 'silent':
        entry['silent_follow_ups'] = entry.get('silent_follow_ups', 0) + 1
    else:
        entry['silent_follow_ups'] = 0  # Reset when creator is active again
    cadence[chat_ident]      = entry


def load_channel_state() -> dict:
    if CHANNEL_STATE_FILE.exists():
        return json.loads(CHANNEL_STATE_FILE.read_text())
    return {}


def save_channel_state(state: dict):
    CHANNEL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHANNEL_STATE_FILE.write_text(json.dumps(state, indent=2))


def _post_date_str(p: dict) -> str | None:
    """Return YYYY-MM-DD for a post, preferring uploadedAt (Unix ts) over createdAt (string)."""
    ts = p.get('uploadedAt')
    if ts:
        return datetime.fromtimestamp(ts, tz=LA_TZ).strftime('%Y-%m-%d')
    created = p.get('createdAt', '')
    return created[:10] if created else None


def compute_channel_state(ss_id: str, posts_by_cid: dict) -> dict:
    """Derive channel state from posts data for one creator."""
    posts = posts_by_cid.get(ss_id, [])
    now   = datetime.now(LA_TZ).date()

    if not posts:
        return {'state': 'onboarding', 'posts_count': 0,
                'days_since_last': None, 'last_post_date': None, 'first_post_date': None}

    post_dates = sorted(d for p in posts if (d := _post_date_str(p)))
    if not post_dates:
        return {'state': 'onboarding', 'posts_count': 0,
                'days_since_last': None, 'last_post_date': None, 'first_post_date': None}

    first_date_str = post_dates[0]
    last_date_str  = post_dates[-1]

    try:
        days_since = (now - date.fromisoformat(last_date_str)).days
        days_in    = (now - date.fromisoformat(first_date_str)).days
    except ValueError:
        days_since = 999
        days_in    = 999

    count = len(posts)

    if days_in <= 7 and count <= 5:
        state = 'warm_up'
    elif days_since >= 2:
        state = 'silent'
    else:
        state = 'active'

    return {
        'state': state,
        'posts_count': count,
        'days_since_last': days_since,
        'last_post_date': last_date_str,
        'first_post_date': first_date_str,
    }


def _channel_state_hint(cs: dict | None) -> str:
    """One-line hint for the LLM based on channel state."""
    if not cs:
        return ''
    s      = cs.get('state', 'active')
    count  = cs.get('posts_count', 0)
    days   = cs.get('days_since_last')
    hints  = {
        'onboarding': 'They have 0 posts — encourage them to make their first post today.',
        'warm_up':    f'They are in warm-up ({count} posts so far, {cs.get("days_in_campaign", "new")} days in) — keep it encouraging and momentum-building.',
        'active':     'They are posting consistently — keep the energy positive.',
        'silent':     f'They have not posted in {days} day(s) — use a gentle check-in tone, not pushy.',
    }
    return hints.get(s, '')


async def _llm_msg(prompt: str) -> str | None:
    """Call Gemini Flash; return text or None on failure."""
    if not _gemini:
        return None
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: _gemini.models.generate_content(model=GEMINI_MODEL, contents=prompt),
        )
        return response.text.strip()
    except Exception as e:
        logger.warning('Gemini error: %s', e)
        return None


def _voice_context(vp: dict) -> str:
    """Compact voice profile summary for the LLM prompt."""
    tones   = ', '.join(vp.get('tone_descriptors', []))
    samples = '\n'.join(f'  • {p}' for p in vp.get('sample_phrases', [])[:5])
    emojis  = ' '.join(vp.get('emoji_patterns', {}).get('frequent', [])[:4])
    return (
        f'Tone: {tones}\n'
        f'Sentence style: {vp.get("sentence_length", "short")}, '
        f'{vp.get("punctuation_style", "")}\n'
        f'Typical emojis: {emojis}\n'
        f'Sample phrases from this person:\n{samples}'
    )


async def llm_status_msg(name: str, posts_done: int, posts_goal: int,
                         total_views: int, last_views: int | None,
                         pending_pay: float,
                         channel_state: dict | None = None,
                         ss_id: str = '') -> str:
    vp = load_voice_profile()
    if not vp:
        return build_status_msg(name, posts_done, posts_goal, total_views, last_views, pending_pay)

    brief    = load_brief()
    tva_ctx  = load_tva_context()
    first    = name.split()[0]
    pct      = posts_done / posts_goal * 100 if posts_goal else 0
    bar      = _progress_bar(posts_done, posts_goal)
    last_str = fmt_views(last_views) if last_views else '—'
    cs_hint  = _channel_state_hint(channel_state)
    brief_section   = f'\nCampaign context:\n{brief}\n' if brief else ''
    tva_section     = f'\nTVA internal context (use to align messaging with current priorities):\n{tva_ctx}\n' if tva_ctx else ''
    profile_section = f'\n{_profile_context(ss_id)}\n' if ss_id else ''

    prompt = f"""You are a UGC campaign manager writing a short iMessage status update to a creator.
Write exactly in this person's voice:

{_voice_context(vp)}
{brief_section}{tva_section}{profile_section}
Creator first name: {first}
Creator channel state: {cs_hint}

Stats to include (keep all of these, exactly as given):
  Posts: {posts_done}/{posts_goal} [{bar}] {pct:.0f}%
  Total views: {fmt_views(total_views)}
  Last post views: {last_str}
  Pending payment: ${pending_pay:.2f}

Rules:
- Sound exactly like the sample phrases above — same warmth, length, emoji style
- Adapt tone to the channel state hint above
- Keep the stats block intact (posts, views, payment) — do NOT invent numbers
- 4-6 lines max, no bullet points, conversational iMessage style
- End with a brief motivational line appropriate for their state
- Do NOT use "Good morning" as greeting if it sounds repetitive; vary it naturally
- Write ONLY the message text, nothing else"""

    result = await _llm_msg(prompt)
    if not result:
        return build_status_msg(name, posts_done, posts_goal, total_views, last_views, pending_pay)
    return result


async def llm_pending_msg(name: str, ss_id: str = '') -> str:
    vp = load_voice_profile()
    if not vp:
        return build_pending_msg(name)

    brief = load_brief()
    first = name.split()[0]
    brief_section   = f'\nCampaign context:\n{brief}\n' if brief else ''
    profile_section = f'\n{_profile_context(ss_id)}\n' if ss_id else ''

    prompt = f"""You are a UGC campaign manager writing a short iMessage to a creator who signed up \
but hasn't activated their SideShift contract yet.
Write exactly in this person's voice:

{_voice_context(vp)}
{brief_section}{profile_section}
Creator first name: {first}

Rules:
- Friendly check-in, no pressure
- Mention they need to log into SideShift to activate and start posting
- Offer to help if they have questions
- 3-4 lines, iMessage style, sounds like the sample phrases above
- Write ONLY the message text, nothing else"""

    result = await _llm_msg(prompt)
    return result if result else build_pending_msg(name)


async def llm_outreach_msg(name: str, ss_id: str = '') -> str:
    vp = load_voice_profile()
    if not vp:
        return build_outreach_msg(name)

    brief = load_brief()
    first = name.split()[0]
    brief_section   = f'\nCampaign context:\n{brief}\n' if brief else ''
    profile_section = f'\n{_profile_context(ss_id)}\n' if ss_id else ''

    prompt = f"""You are a UGC campaign manager writing a short iMessage to a creator you want to recruit \
for the {CLIENT_NAME} campaign.
Write exactly in this person's voice:

{_voice_context(vp)}
{brief_section}{profile_section}
Creator first name: {first}

Rules:
- Introduce yourself as {MANAGER_NAME} from The Viral App / {CLIENT_NAME}
- Keep it brief and inviting, not salesy
- Mention it's a paid UGC opportunity for content they're already making
- Ask if they're interested and offer to send details
- 3-4 lines max, iMessage style, sounds like the sample phrases above
- Write ONLY the message text, nothing else"""

    result = await _llm_msg(prompt)
    return result if result else build_outreach_msg(name)


async def llm_onboarding_msg(name: str, ss_id: str = '') -> str:
    """First-post encouragement for creators in onboarding state (0 posts)."""
    vp = load_voice_profile()
    brief = load_brief()
    first = name.split()[0]
    if vp:
        brief_section = f'\nCampaign context:\n{brief}\n' if brief else ''
        profile_section = f'\n{_profile_context(ss_id)}\n' if ss_id else ''
        prompt = f"""You are a UGC campaign manager writing a short iMessage to a creator who just joined {CLIENT_NAME} but hasn't posted yet.
Write exactly in this person's voice:

{_voice_context(vp)}
{brief_section}{profile_section}
Creator first name: {first}

Context: They set up their SideShift account but have 0 posts. Help them make their first one today.

Rules:
- Welcome them and encourage them to make their first post
- Mention: download the {CLIENT_NAME} app, try it, and film a quick TikTok about their first experience
- Casual and encouraging, not pushy
- 3-4 lines, iMessage style
- Write ONLY the message text, nothing else"""
        result = await _llm_msg(prompt)
        if result:
            return result
    return (
        f'Hey {first}! 👋 Welcome to {CLIENT_NAME} — so excited to have you!\n'
        f'Whenever you\'re ready: download the app, try it out, '
        f'and film a quick TikTok showing your experience. That\'s your first post! 🎬\n'
        f'Any questions? I\'m here 😊'
    )


async def llm_warmup_complete_msg(name: str, ss_id: str = '') -> str:
    """Congratulatory message when creator transitions warm_up → active."""
    vp = load_voice_profile()
    brief = load_brief()
    first = name.split()[0]
    if vp:
        brief_section = f'\nCampaign context:\n{brief}\n' if brief else ''
        profile_section = f'\n{_profile_context(ss_id)}\n' if ss_id else ''
        prompt = f"""You are a UGC campaign manager celebrating a creator completing their warm-up phase.
Write exactly in this person's voice:

{_voice_context(vp)}
{brief_section}{profile_section}
Creator first name: {first}

Context: They posted consistently for 7 days through warm-up. They're now in the main {CLIENT_NAME} campaign and earning full rates. Goal is {POSTS_GOAL} total posts.

Rules:
- Celebrate their warm-up completion warmly
- Let them know they're now in the main campaign earning full rates
- Remind them the goal is {POSTS_GOAL} posts total — they're on their way!
- Energetic and motivating, 4-5 lines
- Write ONLY the message text, nothing else"""
        result = await _llm_msg(prompt)
        if result:
            return result
    return (
        f'🎉 {first}, you completed your warm-up — amazing work!\n\n'
        f'You\'re now officially in the main {CLIENT_NAME} campaign and earning at full rate. '
        f'Your goal: {POSTS_GOAL} total posts.\n\n'
        f'Keep that momentum going — you\'re crushing it! 🚀'
    )


async def send_warmup_complete(bot: Bot, name: str, chat_ident: str, ss_id: str):
    """Send warm-up completion iMessage to creator + alert Rubén in Telegram."""
    msg = await llm_warmup_complete_msg(name, ss_id)
    ok  = await send_group_imessage(chat_ident, msg)
    status_txt = '✅ sent' if ok else '⚠️ relay failed'
    append_creator_note(ss_id, name, 'warmup_complete',
                        f'Warm-up complete. Now active. iMessage {status_txt}.')
    if ok:
        append_creator_action(ss_id, name, 'warmup_complete_msg', msg[:120])
    await send(bot, (
        f'🎉 <b>{name} completed warm-up!</b> → now <b>Active</b>\n'
        f'Warm-up complete message {status_txt}.'
    ))
    logger.info('Warm-up complete triggered for %s', name)


# ── Status Check (6am cron) ───────────────────────────────────────────────────

def _progress_bar(done: int, goal: int, width: int = 10) -> str:
    pct = min(done / goal, 1.0) if goal > 0 else 0
    filled = round(pct * width)
    return '█' * filled + '░' * (width - filled)


def _motivational_phrase(pct: float) -> str:
    if pct >= 0.81:
        return "You're almost there — finish strong! 🏆"
    elif pct >= 0.61:
        return "Final stretch! Keep that momentum going 🎯"
    elif pct >= 0.41:
        return "Halfway there! Don't stop now 🚀"
    elif pct >= 0.21:
        return "Great pace! Keep it up 🔥"
    else:
        return "Let's go! Every post gets you closer to your goal 💪"


def build_status_msg(name: str, posts_done: int, posts_goal: int,
                     total_views: int, last_views: int | None,
                     pending_pay: float) -> str:
    pct   = posts_done / posts_goal if posts_goal > 0 else 0
    bar   = _progress_bar(posts_done, posts_goal)
    first = name.split()[0]
    return (
        f'Good morning {first}! Your update for today 📊\n'
        f'📹 Posts: {posts_done}/{posts_goal} [{bar}] {pct * 100:.0f}%\n'
        f'📈 Total views: {fmt_views(total_views)} | Last post: {fmt_views(last_views)} views\n'
        f'💰 Pending payment: ${pending_pay:.2f}\n'
        f'Today: {_motivational_phrase(pct)}'
    )


def build_pending_msg(name: str) -> str:
    first = name.split()[0]
    return (
        f'Hey {first}! 👋 Just checking in on your {CLIENT_NAME} contract.\n'
        f"Your account is almost ready — log into SideShift to activate it "
        f"and start posting!\n"
        f'Any questions? Reply here and we\'ll help you get set up 🙌'
    )


def build_outreach_msg(name: str) -> str:
    first = name.split()[0]
    return (
        f'Hey {first}! This is {MANAGER_NAME} from The Viral App 👋\n'
        f"We'd love to have you join the {CLIENT_NAME} campaign — "
        f"it's a great opportunity to get paid for content you're already making!\n"
        f'Interested? Reply here and I\'ll send you all the details 🎬'
    )


async def status_check(bot: Bot):
    """6 AM PT — Send personalized Status Check to all creators by contract status.
    active   → stats message (posts, views, payment)
    pending  → onboarding nudge (activate SideShift contract)
    outreach → recruitment message (join the campaign)
    cancelled → skip
    """
    logger.info('Running Status Check')
    creators_map = load_creators_map()
    to_contact   = [c for c in creators_map if c.get('contract_status') != 'cancelled']

    if not to_contact:
        logger.warning('No creators to contact in creators_map.json')
        return

    active_entries = [c for c in to_contact if c.get('contract_status') == 'active']

    # Fetch SideShift data only for active creators (paginated)
    try:
        all_posts = await _ss_paginate('/posts', {'program': SS_PROGRAM})
    except Exception as e:
        logger.error('Status Check: posts fetch failed: %s', e)
        all_posts = []

    try:
        all_payouts = await _ss_paginate('/payouts/pending', {})
    except Exception as e:
        logger.error('Status Check: payouts fetch failed: %s', e)
        all_payouts = []

    try:
        all_contracts = await _ss_paginate('/contracts', {'programId': SS_PROGRAM})
    except Exception as e:
        logger.error('Status Check: contracts fetch failed: %s', e)
        all_contracts = []

    # Index by contractorId
    posts_by_cid: dict[str, list] = {}
    for p in all_posts:
        cid = p.get('contractorId') or p.get('creatorId') or ''
        if cid:
            posts_by_cid.setdefault(cid, []).append(p)

    payouts_by_cid: dict[str, list] = {}
    for p in all_payouts:
        cid = p.get('contractorId') or p.get('creatorId') or ''
        if cid:
            payouts_by_cid.setdefault(cid, []).append(p)

    contracts_by_cid: dict[str, dict] = {}
    for c in all_contracts:
        cid = c.get('contractorId') or c.get('creatorId') or ''
        if cid:
            contracts_by_cid[cid] = c

    # Compute and persist channel state for all active creators
    channel_states: dict[str, dict] = {}
    saved_cs          = load_channel_state()
    warmup_transitions: list[tuple[str, str, str]] = []  # (name, chat_ident, ss_id)

    for entry in active_entries:
        ss_id = entry.get('sideshift_id') or ''
        if not ss_id:
            continue
        old_cs = saved_cs.get(ss_id, {})
        cs     = compute_channel_state(ss_id, posts_by_cid)
        cs['updated_at'] = datetime.now(LA_TZ).isoformat()

        # Preserve warmup_completed_at marker to prevent re-triggering (#17)
        if old_cs.get('warmup_completed_at'):
            cs['warmup_completed_at'] = old_cs['warmup_completed_at']
        elif old_cs.get('state') == 'warm_up' and cs.get('state') == 'active':
            # Warm-up → active transition detected
            cs['warmup_completed_at'] = datetime.now(LA_TZ).isoformat()
            wu_chat = entry.get('chat_identifier', '')
            wu_name = entry.get('creator_name', 'Creator')
            if wu_chat:
                warmup_transitions.append((wu_name, wu_chat, ss_id))
            logger.info('Warm-up complete detected: %s', wu_name)

        channel_states[ss_id] = cs
        saved_cs[ss_id]       = cs

        # ── Update creator profile (daily snapshot) ───────────────────────────
        creator_name = entry.get('creator_name', 'Creator')
        creator_posts = posts_by_cid.get(ss_id, [])
        total_views = sum(p.get('views', 0) for p in creator_posts)
        total_likes = sum(p.get('likes', 0) for p in creator_posts)
        update_creator_state(ss_id, creator_name, cs, total_views, total_likes)

    save_channel_state(saved_cs)
    logger.info('Channel state updated for %d creators', len(channel_states))

    # Trigger warm-up complete flows (#17)
    for wu_name, wu_chat, wu_ss_id in warmup_transitions:
        await send_warmup_complete(bot, wu_name, wu_chat, wu_ss_id)

    relay_ok   = bool(MAC_RELAY_URL and MAC_RELAY_KEY)
    cadence    = load_cadence()
    sent_ok    = 0
    sent_fail  = 0
    skipped    = 0
    cooldown   = 0
    escalations: list[str] = []   # silent creators to report to Ruben
    tg_blocks:   list[str] = []

    for entry in to_contact:
        name       = entry.get('creator_name', 'Creator')
        chat_ident = entry.get('chat_identifier', '')
        status     = entry.get('contract_status', '')
        ss_id      = entry.get('sideshift_id') or ''

        if not chat_ident:
            logger.warning('No chat_identifier for %s — skipping', name)
            skipped += 1
            continue

        cs       = channel_states.get(ss_id)
        cs_state = (cs or {}).get('state', 'active')

        # ── Cadence gate ──────────────────────────────────────────────────────
        send_ok, reason = should_contact(status, cs, cadence, chat_ident)
        if not send_ok:
            if reason == 'at_risk':
                # Already marked at_risk — skip silently, don't spam
                logger.info('Skipping at-risk creator: %s', name)
                skipped += 1
            elif reason == 'silent_escalate':
                days       = (cs or {}).get('days_since_last', '?')
                follow_ups = cadence.get(chat_ident, {}).get('silent_follow_ups', 0)

                if follow_ups >= 3:
                    # ── Escalation Policy (#24): 3+ unanswered follow-ups → at_risk ──
                    cadence_entry = cadence.get(chat_ident, {})
                    if not cadence_entry.get('at_risk'):
                        cadence_entry['at_risk']       = True
                        cadence_entry['at_risk_since'] = date.today().isoformat()
                        cadence[chat_ident]            = cadence_entry
                        if ss_id:
                            append_creator_note(ss_id, name, 'at_risk',
                                                f'{follow_ups} unanswered follow-ups, {days}d silent — cadence stopped.')
                        escalations.append(
                            f'  🚨 <b>{name}</b> → <b>AT RISK</b> '
                            f'({follow_ups} unanswered follow-ups, {days}d silent) '
                            f'— cadence stopped'
                        )
                        logger.info('AT RISK: %s (%s follow-ups, %sd silent)', name, follow_ups, days)
                else:
                    escalations.append(f'  🔇 {name} — {days}d without posting (follow-up #{follow_ups + 1})')
                    logger.info('Escalating silent creator: %s (%sd)', name, days)
            else:
                logger.info('Cadence skip [%s] %s: %s', reason, status, name)
                cooldown += 1
            continue

        # ── Build message ─────────────────────────────────────────────────────
        if status == 'active':
            contract   = contracts_by_cid.get(ss_id, {})
            posts_done = contract.get('postsCompleted', contract.get('posts_done',
                         len(posts_by_cid.get(ss_id, []))))
            posts_goal = contract.get('postsGoal', contract.get('posts_goal', POSTS_GOAL))
            creator_posts = posts_by_cid.get(ss_id, [])
            total_views   = sum(p.get('views', 0) for p in creator_posts)
            last_views    = None
            if creator_posts:
                last_post  = max(creator_posts, key=lambda p: p.get('uploadedAt') or 0)
                last_views = last_post.get('views')
            pending_pay = sum(p.get('amount', 0) for p in payouts_by_cid.get(ss_id, []))
            msg = await llm_status_msg(name, posts_done, posts_goal, total_views, last_views, pending_pay, cs, ss_id)

        elif status == 'pending':
            msg = await llm_pending_msg(name, ss_id)

        elif status == 'outreach':
            msg = await llm_outreach_msg(name, ss_id)

        else:
            skipped += 1
            continue

        # ── Send ──────────────────────────────────────────────────────────────
        if relay_ok:
            ok = await send_group_imessage(chat_ident, msg)
            if ok:
                sent_ok += 1
                record_contact(cadence, chat_ident, status, cs_state)
                if ss_id:
                    append_creator_action(ss_id, name, f'status_check_{status}',
                                          f'[{cs_state}] {msg[:120]}')
                logger.info('Status Check [%s/%s] sent: %s', status, cs_state, name)
            else:
                sent_fail += 1
                logger.warning('Status Check [%s] failed: %s', status, name)
            await asyncio.sleep(random.uniform(20, 60))
        else:
            tg_blocks.append(f'<b>{name}</b> ({status}/{cs_state})\n{msg}')
            record_contact(cadence, chat_ident, status, cs_state)

    save_cadence(cadence)

    # ── Summary to Ruben ──────────────────────────────────────────────────────
    if relay_ok:
        summary = (
            f'✅ Status Check done: {sent_ok} sent, {sent_fail} failed, '
            f'{skipped} skipped, {cooldown} on cooldown\n'
            f'({len(active_entries)} active · '
            f'{len([c for c in to_contact if c.get("contract_status") == "pending"])} pending · '
            f'{len([c for c in to_contact if c.get("contract_status") == "outreach"])} outreach)'
        )
        await send(bot, summary)
    else:
        header = f'⚠️ mac-relay offline — Status Check ({len(to_contact)} creators):\n\n'
        chunk  = header
        for block in tg_blocks:
            if len(chunk) + len(block) > 3800:
                await send(bot, chunk)
                chunk = ''
            chunk += block + '\n\n'
        if chunk:
            await send(bot, chunk)

    if escalations:
        esc_msg = (
            f'🚨 <b>Silent creators — needs attention ({len(escalations)}):</b>\n'
            + '\n'.join(escalations)
            + '\n\n→ Consider reaching out manually or adjusting their campaign status.'
        )
        await send(bot, esc_msg)

async def llm_warmup_nudge_msg(name: str, ss_id: str, days_in: int, days_remaining: int) -> str:
    """Mid-day nudge for at-risk warm-up creators."""
    vp    = load_voice_profile()
    brief = load_brief()
    first = name.split()[0]
    if vp:
        brief_section   = f'\nCampaign context:\n{brief}\n' if brief else ''
        profile_section = f'\n{_profile_context(ss_id)}\n' if ss_id else ''
        prompt = f"""You are a UGC campaign manager sending a mid-day check-in to a creator in their warm-up week.
Write exactly in this person's voice:

{_voice_context(vp)}
{brief_section}{profile_section}
Creator first name: {first}
Context: Day {days_in} of 7 in warm-up, {days_remaining} days remaining. They need to post today to stay on track.

Rules:
- Friendly and encouraging, not pressuring
- Mention they're in their warm-up week and today's post matters
- Keep it to 2-3 lines, iMessage style
- Write ONLY the message text, nothing else"""
        result = await _llm_msg(prompt)
        if result:
            return result
    return (
        f'Hey {first}! Mid-day check-in 🌱 '
        f'You\'re on day {days_in} of your warm-up — {days_remaining} days left. '
        f'A post today keeps the momentum going! 🎬'
    )


# ── Warm-up Check (2pm cron) ──────────────────────────────────────────────────

async def warmup_check(bot: Bot):
    """2 PM PT — dashboard of warm-up creators + nudge iMessage to at-risk ones."""
    logger.info('Running warmup check')
    cs_all       = load_channel_state()
    creators_map = load_creators_map()
    relay_ok     = bool(MAC_RELAY_URL and MAC_RELAY_KEY)
    today_str    = _today_str()

    warmup_entries = []
    for c in creators_map:
        ss_id  = c.get('sideshift_id', '')
        status = c.get('contract_status', '')
        if status != 'active' or not ss_id:
            continue
        cs = cs_all.get(ss_id, {})
        if cs.get('state') == 'warm_up':
            warmup_entries.append((c, cs))

    if not warmup_entries:
        logger.info('Warmup check: no creators in warm_up state')
        return

    lines   = [f'🌱 <b>Warm-up Check</b> — {len(warmup_entries)} creadoras\n']
    at_risk = []
    cadence = load_cadence()

    for c, cs in warmup_entries:
        name       = c.get('creator_name', 'Creator')
        ss_id      = c.get('sideshift_id', '')
        posts      = cs.get('posts_count', 0)
        days_since = cs.get('days_since_last')
        first_date = cs.get('first_post_date', '')

        days_in = 0
        if first_date:
            try:
                days_in = (date.today() - date.fromisoformat(first_date)).days
            except ValueError:
                pass

        days_remaining = max(0, 7 - days_in)
        bar = _progress_bar(posts, 5)

        # At risk: behind pace (expected ~1 post/day) and ≥2 days in
        expected = min(days_in, 5)
        is_at_risk = days_in >= 2 and posts < expected

        icon = '🚨' if is_at_risk else '✅'
        last_str = f' | últ: {days_since}d' if days_since is not None else ''
        lines.append(
            f'{icon} <b>{name}</b> — {posts}/5 [{bar}]'
            f' | día {days_in}/7 | {days_remaining}d restantes{last_str}'
        )

        if is_at_risk:
            at_risk.append((c, cs, days_in, days_remaining))

    await send(bot, '\n'.join(lines))

    if not at_risk:
        return

    # Send mid-day nudge to at-risk creators
    sent_ok = 0
    for c, cs, days_in, days_remaining in at_risk:
        name       = c.get('creator_name', 'Creator')
        ss_id      = c.get('sideshift_id', '')
        chat_ident = c.get('chat_identifier', '')
        if not chat_ident:
            continue

        # Separate cadence key so it doesn't conflict with 6 AM status_check
        wk = f'{chat_ident}_warmup'
        if cadence.get(wk, {}).get('last_contacted') == today_str:
            continue

        msg = await llm_warmup_nudge_msg(name, ss_id, days_in, days_remaining)
        if relay_ok:
            ok = await send_group_imessage(chat_ident, msg)
            if ok:
                sent_ok += 1
                cadence[wk] = {'last_contacted': today_str}
                if ss_id:
                    append_creator_action(ss_id, name, 'warmup_nudge', msg[:120])
                await asyncio.sleep(random.uniform(10, 30))

    save_cadence(cadence)
    risk_names = [c.get('creator_name', '?') for c, _, _, _ in at_risk]
    await send(bot, (
        f'⚠️ <b>At risk ({len(at_risk)}):</b> {", ".join(risk_names)}\n'
        + (f'→ {sent_ok} nudges enviados' if relay_ok else '→ mac-relay offline')
    ))


# ── Onboarding Check (10am cron) — #18 ───────────────────────────────────────

async def onboarding_check(bot: Bot):
    """10 AM PT — Send first-post encouragement to creators with 0 posts (onboarding state)."""
    logger.info('Running onboarding check')
    cs_all       = load_channel_state()
    creators_map = load_creators_map()
    cadence      = load_cadence()
    relay_ok     = bool(MAC_RELAY_URL and MAC_RELAY_KEY)

    to_onboard = []
    for c in creators_map:
        ss_id      = c.get('sideshift_id', '')
        status     = c.get('contract_status', '')
        chat_ident = c.get('chat_identifier', '')

        if status != 'active' or not chat_ident or not ss_id:
            continue

        cs = cs_all.get(ss_id, {})
        if cs.get('state') != 'onboarding':
            continue

        ok, reason = should_contact(status, cs, cadence, chat_ident)
        if not ok:
            logger.info('Onboarding skip [%s] %s', reason, c.get('creator_name'))
            continue

        to_onboard.append(c)

    if not to_onboard:
        logger.info('Onboarding check: no onboarding creators to contact')
        return

    sent_ok, sent_fail = 0, 0
    for c in to_onboard:
        name       = c.get('creator_name', 'Creator')
        chat_ident = c.get('chat_identifier', '')
        ss_id      = c.get('sideshift_id', '')

        msg = await llm_onboarding_msg(name, ss_id)

        if relay_ok:
            ok = await send_group_imessage(chat_ident, msg)
            if ok:
                sent_ok += 1
                record_contact(cadence, chat_ident, 'active', 'onboarding')
                if ss_id:
                    append_creator_note(ss_id, name, 'onboarding_msg', 'First-post encouragement sent.')
                    append_creator_action(ss_id, name, 'onboarding_msg', msg[:120])
                logger.info('Onboarding msg sent: %s', name)
            else:
                sent_fail += 1
                logger.warning('Onboarding relay failed: %s', name)
            await asyncio.sleep(random.uniform(15, 45))
        else:
            logger.info('Onboarding [relay_offline] would send to %s', name)
            sent_ok += 1
            record_contact(cadence, chat_ident, 'active', 'onboarding')

    save_cadence(cadence)

    if sent_ok or sent_fail:
        await send(bot, (
            f'🆕 <b>Onboarding check:</b> {sent_ok} first-post messages sent'
            + (f', {sent_fail} failed' if sent_fail else '')
        ))


# ── Template Loader ───────────────────────────────────────────────────────────

def _load_template(filename: str, default: str) -> str:
    path = TEMPLATES / filename
    if path.exists():
        return path.read_text().strip()
    return default

# ── Draft Approve/Reject ──────────────────────────────────────────────────────

# Tracks Telegram user_id → chat_uuid when Rubén taps "Request Changes"
_awaiting_feedback: dict[int, dict] = {}

# Tracks Telegram user_id → {chat_uuid, name} when Rubén taps "✏️ Edit" on a question draft
_awaiting_qdraft: dict[int, dict] = {}


def _creator_name_by_chat(chat_uuid: str) -> str:
    """Look up creator name from creators_map.json by chat_identifier."""
    creators = load_creators_map()
    for c in creators:
        if c.get('chat_identifier') == chat_uuid:
            return c.get('creator_name', 'Creator')
    return 'Creator'


async def handle_draft_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not query.data or '|' not in query.data:
        return

    action, chat_uuid = query.data.split('|', 1)
    name  = _creator_name_by_chat(chat_uuid)
    first = name.split()[0]

    if action == 'draft_approve':
        msg = f'Draft approved! ✅ Please post it now 😃'
        ok  = await send_group_imessage(chat_uuid, msg)
        status_text = f'✅ Approved and sent to {name}' if ok else f'✅ Approved but relay failed for {name}'
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(status_text)

    elif action == 'draft_reject':
        msg = f"Thanks for sharing {first}! We'll pass on this one, but keep them coming 😊"
        ok  = await send_group_imessage(chat_uuid, msg)
        status_text = f'❌ Rejection sent to {name}' if ok else f'❌ Rejected but relay failed for {name}'
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(status_text)

    elif action == 'draft_changes':
        _awaiting_feedback[query.from_user.id] = {
            'chat_uuid': chat_uuid,
            'name':      name,
            'message_id': query.message.message_id,
        }
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f'Type your feedback for <b>{name}</b> and I\'ll send it to them:',
            parse_mode='HTML',
        )


async def handle_qdraft_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle qdraft_send / qdraft_edit / qdraft_skip inline button taps (#21-22).
    The draft text is embedded in the Telegram message body after '✍️ Draft reply:'.
    """
    query = update.callback_query
    await query.answer()

    if not query.data or '|' not in query.data:
        return

    action, chat_uuid = query.data.split('|', 1)
    name              = _creator_name_by_chat(chat_uuid)

    # Parse draft from message plain text (Telegram strips HTML tags in .text)
    msg_text   = query.message.text or ''
    draft_text = None
    marker     = '✍️ Draft reply:\n'
    if marker in msg_text:
        draft_text = msg_text.split(marker, 1)[1].strip()

    if action == 'qdraft_send':
        if not draft_text:
            await query.message.reply_text('❌ Could not parse draft text from message.')
            return
        ok = await send_group_imessage(chat_uuid, draft_text)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f'✅ Draft sent to {name}.' if ok else f'❌ Relay failed — could not send to {name}.'
        )

    elif action == 'qdraft_edit':
        _awaiting_qdraft[query.from_user.id] = {'chat_uuid': chat_uuid, 'name': name}
        await query.edit_message_reply_markup(reply_markup=None)
        draft_preview = f'\n\nCurrent draft:\n<i>{draft_text[:300]}</i>' if draft_text else ''
        await query.message.reply_text(
            f'Type your edited reply for <b>{name}</b> and I\'ll send it:{draft_preview}',
            parse_mode='HTML',
        )

    elif action == 'qdraft_skip':
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f'⏭️ Skipped — no reply sent to {name}.')


async def handle_feedback_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Intercept Rubén's next message when awaiting draft feedback (qdraft edit or video feedback)."""
    user_id = update.effective_user.id

    # ── qdraft edit flow (#22) ──
    if user_id in _awaiting_qdraft:
        pending   = _awaiting_qdraft.pop(user_id)
        chat_uuid = pending['chat_uuid']
        name      = pending['name']
        text      = update.message.text or ''

        if not text.strip():
            await update.message.reply_text('Empty message — not sent.')
            return

        ok = await send_group_imessage(chat_uuid, text)
        if ok:
            await update.message.reply_text(f'✅ Edited reply sent to {name}.')
        else:
            await update.message.reply_text(f'❌ Relay failed — could not send to {name}.')
        return

    # ── original draft feedback flow (video approve/changes) ──
    if user_id not in _awaiting_feedback:
        return

    pending   = _awaiting_feedback.pop(user_id)
    chat_uuid = pending['chat_uuid']
    name      = pending['name']
    feedback  = update.message.text or ''

    if not feedback.strip():
        await update.message.reply_text('Empty message — feedback not sent.')
        return

    ok = await send_group_imessage(chat_uuid, feedback)
    if ok:
        await update.message.reply_text(f'✅ Feedback sent to {name}.')
    else:
        await update.message.reply_text(f'❌ Relay failed — could not send to {name}.')


# ── Telegram Commands ─────────────────────────────────────────────────────────

async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    await update.message.reply_text('Generando reporte...')
    await morning_report(context.bot)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    creators    = load_creators()
    sq_creators = skinqueens_creators(creators)
    state       = load_state()
    last_run    = state.get('last_run', 'nunca')

    text = (
        f'<b>VIRAL Bot — Status</b>\n'
        f'• DB local: {len(creators)} creadores\n'
        f'• {CLIENT_NAME} (local): {len(sq_creators)}\n'
        f'• Último reporte: {last_run}\n'
        f'• mac-relay: {"✅ configurado" if MAC_RELAY_URL else "❌ no configurado"}'
    )
    await update.message.reply_html(text)


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    await update.message.reply_text('Corriendo buenos días check...')
    await buenos_dias_check(context.bot)


async def cmd_statuscheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    await update.message.reply_text('Enviando Status Check a creadoras activas...')
    await status_check(context.bot)


async def cmd_classify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually classify a creator message. Usage: /classify <message text>"""
    if update.effective_chat.id != CHAT_ID:
        return
    text = ' '.join(context.args) if context.args else ''
    if not text:
        await update.message.reply_text('Usage: /classify <message text>')
        return
    if not _gemini:
        await update.message.reply_text('❌ Gemini not configured')
        return

    label_map = {
        'draft':     '📹 DRAFT — creator submitted a video for review',
        'question':  '❓ QUESTION — creator has a campaign question',
        'complaint': '🚨 COMPLAINT — creator reporting a problem',
        'update':    '✅ UPDATE — creator reporting they posted',
        'other':     '💬 OTHER — social or unclear message',
    }
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
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: _gemini.models.generate_content(model=GEMINI_MODEL, contents=prompt),
        )
        label = response.text.strip().lower().split()[0]
        if label not in ('draft', 'question', 'complaint', 'update', 'other'):
            label = 'other'
        result = label_map.get(label, f'❓ {label}')
        await update.message.reply_html(f'<b>Classification:</b> {result}\n\n<i>"{text[:200]}"</i>')
    except Exception as e:
        await update.message.reply_text(f'❌ Error: {e}')


async def cmd_remap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reassign a creator's chat_identifier without losing state.
    Usage: /remap <creator_name> <new_chat_identifier>
    Example: /remap "Sofia Morales" chat12345678901
    """
    if update.effective_chat.id != CHAT_ID:
        return
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            'Usage: /remap <creator_name> <new_chat_identifier>\n'
            'Example: /remap "Sofia Morales" chat12345678901'
        )
        return

    new_chat = args[-1]
    name_query = ' '.join(args[:-1]).strip('"\'')

    # Load and find creator
    creators_map = load_creators_map()
    raw = json.loads(CREATORS_MAP_FILE.read_text()) if CREATORS_MAP_FILE.exists() else []

    match_idx = None
    for i, c in enumerate(creators_map):
        if name_query.lower() in c.get('creator_name', '').lower():
            match_idx = i
            break

    if match_idx is None:
        await update.message.reply_text(f'❌ Creator not found: "{name_query}"')
        return

    creator = creators_map[match_idx]
    old_chat = creator.get('chat_identifier', '')
    name     = creator.get('creator_name', 'Creator')
    ss_id    = creator.get('sideshift_id', '')

    if old_chat == new_chat:
        await update.message.reply_text(f'⚠️ {name} already has that chat_identifier.')
        return

    # Update creators_map.json
    if isinstance(raw, list):
        raw[match_idx]['chat_identifier'] = new_chat
    else:
        raw[name]['chat_identifier'] = new_chat
    CREATORS_MAP_FILE.write_text(json.dumps(raw, indent=2))

    # Migrate cadence entry: old_chat → new_chat
    cadence = load_cadence()
    if old_chat in cadence:
        cadence[new_chat] = cadence.pop(old_chat)
        save_cadence(cadence)

    # Log to creator profile
    if ss_id:
        append_creator_note(ss_id, name, 'remap',
                            f'chat_identifier remapped: {old_chat} → {new_chat}')

    await update.message.reply_html(
        f'✅ <b>{name}</b> remapped\n'
        f'Old: <code>{old_chat}</code>\n'
        f'New: <code>{new_chat}</code>\n'
        f'Cadence history preserved ✓'
    )
    logger.info('Remap: %s %s → %s', name, old_chat, new_chat)


async def cmd_slackbrief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    await update.message.reply_text('Leyendo Slack... 💬')
    await slack_daily_brief(context.bot)


async def cmd_channelstate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    cs_all = load_channel_state()
    if not cs_all:
        await update.message.reply_text('No channel state data yet. Run /statuscheck first.')
        return

    creators_map = load_creators_map()
    name_by_id   = {c.get('sideshift_id', ''): c.get('creator_name', '?') for c in creators_map}

    state_icon = {'onboarding': '🆕', 'warm_up': '🌱', 'active': '✅', 'silent': '🔇'}
    counts     = {'onboarding': 0, 'warm_up': 0, 'active': 0, 'silent': 0}
    lines      = ['<b>📊 Channel State</b>\n']

    silent_list = []
    for ss_id, cs in cs_all.items():
        st   = cs.get('state', '?')
        name = name_by_id.get(ss_id, ss_id[:8])
        icon = state_icon.get(st, '❓')
        counts[st] = counts.get(st, 0) + 1
        if st == 'silent':
            days = cs.get('days_since_last', '?')
            silent_list.append(f'  {icon} {name} — {days}d silent')

    lines.append(
        f'✅ Active: {counts["active"]}  '
        f'🌱 Warm-up: {counts["warm_up"]}  '
        f'🆕 Onboarding: {counts["onboarding"]}  '
        f'🔇 Silent: {counts["silent"]}'
    )
    if silent_list:
        lines.append('\n<b>Silent creators:</b>')
        lines.extend(silent_list[:15])

    await update.message.reply_html('\n'.join(lines))

async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show creator profile. Usage: /profile <name>"""
    if update.effective_chat.id != CHAT_ID:
        return

    query = ' '.join(context.args).strip() if context.args else ''
    if not query:
        await update.message.reply_text('Usage: /profile <creator name>\nExample: /profile Sofia')
        return

    creators_map = load_creators_map()
    match = next(
        (c for c in creators_map if query.lower() in c.get('creator_name', '').lower()),
        None,
    )
    if not match:
        await update.message.reply_text(f'❌ Creator not found: "{query}"')
        return

    name   = match.get('creator_name', 'Creator')
    ss_id  = match.get('sideshift_id', '')
    status = match.get('contract_status', '—')

    def _e(s: str) -> str:
        return html_module.escape(str(s))

    lines = [f'<b>👤 {_e(name)}</b>', f'Contract: <b>{_e(status)}</b>']

    if ss_id:
        profile = load_creator_profile(ss_id)
        if profile:
            state = profile.get('state', {})
            if state:
                cs      = state.get('channel_state', '?')
                posts   = state.get('posts_count', 0)
                goal    = state.get('posts_goal', POSTS_GOAL)
                pct     = state.get('progress_pct', 0)
                views   = state.get('total_views', 0)
                days    = state.get('days_since_last_post')
                updated = state.get('updated_at', '—')
                bar     = _progress_bar(posts, goal)
                state_icon = {'onboarding': '🆕', 'warm_up': '🌱', 'active': '✅', 'silent': '🔇'}
                icon = state_icon.get(cs, '❓')
                lines.append(f'State: {icon} {_e(cs)}')
                lines.append(f'Posts: {posts}/{goal} [{_e(bar)}] {pct}%')
                lines.append(
                    f'Views: {fmt_views(views)}'
                    + (f' | Last: {days}d ago' if days is not None else '')
                )
                lines.append(f'<i>Updated: {_e(updated)}</i>')

            events = profile.get('events', [])[-5:]
            if events:
                lines.append('\n<b>Events:</b>')
                for ev in events:
                    lines.append(f'  • [{_e(ev.get("ts","")[:10])}] {_e(ev.get("text",""))}')

            notes = profile.get('notes', [])[-5:]
            if notes:
                lines.append('\n<b>Notes:</b>')
                for n in notes:
                    lines.append(
                        f'  • [{_e(n.get("ts","")[:10])}] '
                        f'[{_e(n.get("event",""))}] {_e(n.get("text",""))}'
                    )

            interactions = profile.get('interactions', [])[-3:]
            if interactions:
                lines.append('\n<b>Interactions:</b>')
                for ix in interactions:
                    lines.append(f'  • [{_e(ix.get("ts","")[:10])}] {_e(ix.get("text","")[:100])}')

            actions = profile.get('actions', [])[-3:]
            if actions:
                lines.append('\n<b>Bot actions:</b>')
                for a in actions:
                    lines.append(
                        f'  • [{_e(a.get("ts","")[:10])}] '
                        f'[{_e(a.get("type",""))}] {_e(a.get("text","")[:100])}'
                    )
        else:
            lines.append(f'\n⚠️ No profile file yet (ss_id: <code>{_e(ss_id)}</code>)')
    else:
        lines.append('\n⚠️ No SideShift ID — no profile available')

    lines.append(f'\n<code>ss_id: {_e(ss_id) or "—"}</code>')
    await update.message.reply_html('\n'.join(lines))


# ── Slack TVA Daily Brief ─────────────────────────────────────────────────────

async def _slack_resolve_users(slack, messages: list[dict]) -> dict[str, str]:
    """Resolve Slack user IDs to display names."""
    user_ids = {m.get('user') for m in messages if m.get('user')}
    names: dict[str, str] = {}
    for uid in user_ids:
        try:
            info = await slack.users_info(user=uid)
            profile = info['user']['profile']
            names[uid] = profile.get('display_name') or profile.get('real_name') or uid
        except Exception:
            names[uid] = uid
    return names


async def slack_daily_brief(bot: Bot):
    """7:30 AM PT daily — read TVA Slack channels, analyze, report to Telegram + update tva_context.md."""
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_IDS:
        logger.info('Slack daily brief: SLACK_BOT_TOKEN or SLACK_CHANNEL_IDS not set — skipping')
        return

    logger.info('Running Slack daily brief for %d channels', len(SLACK_CHANNEL_IDS))

    from slack_sdk.web.async_client import AsyncWebClient
    bot_client  = AsyncWebClient(token=SLACK_BOT_TOKEN)
    user_client = AsyncWebClient(token=SLACK_USER_TOKEN) if SLACK_USER_TOKEN else None
    oldest = str((datetime.now(LA_TZ) - timedelta(hours=24)).timestamp())

    # Channel labels — use Slack API name for channels, ID for DMs
    channel_labels: dict[str, str] = {}

    all_parts: list[str]         = []
    channel_summaries: list[str] = []

    for channel_id in SLACK_CHANNEL_IDS:
        # DMs (D...) use user token; channels (C...) use bot token
        is_dm  = channel_id.startswith('D')
        client = user_client if is_dm and user_client else bot_client
        ch_name = channel_labels.get(channel_id, channel_id)

        if is_dm and not user_client:
            channel_summaries.append(f'{ch_name}: sin user token')
            continue

        # Get channel name for public channels
        if not is_dm:
            try:
                info    = await client.conversations_info(channel=channel_id)
                ch_name = info['channel'].get('name', ch_name)
            except Exception:
                pass

        # Fetch message history
        try:
            result   = await client.conversations_history(channel=channel_id, oldest=oldest, limit=200)
            messages = result.get('messages', [])
        except Exception as e:
            logger.warning('Slack fetch [%s]: %s', channel_id, e)
            channel_summaries.append(f'{ch_name}: fetch error')
            continue

        if not messages:
            channel_summaries.append(f'{ch_name}: sin mensajes')
            continue

        # Resolve user IDs → names
        user_names = await _slack_resolve_users(client, messages)

        # Format oldest-first, skip bot messages and join/leave events
        lines: list[str] = []
        for m in reversed(messages):
            if m.get('subtype') in ('channel_join', 'channel_leave', 'bot_message'):
                continue
            ts   = datetime.fromtimestamp(float(m.get('ts', 0)), tz=LA_TZ).strftime('%H:%M')
            uid  = m.get('user', '')
            name = user_names.get(uid, uid)
            text = m.get('text', '').strip()
            if text:
                lines.append(f'[{ts}] {name}: {text}')

        if lines:
            all_parts.append(f'### {ch_name}\n' + '\n'.join(lines))
            channel_summaries.append(f'{ch_name}: {len(lines)} msgs')
        else:
            channel_summaries.append(f'{ch_name}: sin actividad')

    if not all_parts:
        logger.info('Slack daily brief: nothing to analyze')
        return

    full_transcript = '\n\n'.join(all_parts)

    # Gemini analysis
    analysis: str | None = None
    if _gemini:
        prompt = f"""You are analyzing internal Slack conversations at The Viral App (TVA), a UGC marketing agency.
Rubén is the UGC Manager / Campaign Manager there.

Slack transcript — last 24 hours:
{full_transcript[:7000]}

Write a concise daily brief (max 300 words) in Spanish covering:
1. **Prioridades y foco** — qué están priorizando los líderes de TVA hoy
2. **Decisiones o cambios** — algo que haya cambiado en la estrategia o proceso
3. **Expectativas del cliente** — feedback o requests del cliente si los hay
4. **Action items para Rubén** — qué debe saber o hacer hoy
5. **Tono y urgencia** — presión, calma, problemas

Sé directo y específico. Cita mensajes reales brevemente si es relevante. Sin relleno."""

        analysis = await _llm_msg(prompt)

    # Send to Telegram
    today = datetime.now(LA_TZ).strftime('%A, %B %d')
    tg_lines = [f'💬 <b>TVA Slack Brief</b> — {today}\n']
    tg_lines.append(f'<i>{" · ".join(channel_summaries)}</i>\n')
    tg_lines.append(analysis if analysis else '⚠️ Analysis unavailable — Gemini error')
    await send(bot, '\n'.join(tg_lines))

    # Update tva_context.md — injected into LLM prompts
    if analysis:
        TVA_CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
        TVA_CONTEXT_FILE.write_text(
            f'# TVA Slack Context — {datetime.now(LA_TZ).strftime("%Y-%m-%d")}\n\n{analysis}\n'
        )
        logger.info('tva_context.md updated')


# ── Relay Health Monitor ─────────────────────────────────────────────────────

_relay_up: bool | None = None  # None = unknown until first check


async def check_relay_health(bot: Bot):
    """Check MAC_RELAY_URL every 15 min; Telegram alert on state change only."""
    global _relay_up

    if not MAC_RELAY_URL:
        return

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.get(MAC_RELAY_URL, headers={'X-Relay-Key': MAC_RELAY_KEY})
        now_up = True
    except Exception:
        now_up = False

    if _relay_up is None:
        # First check after bot start — only alert if already down
        _relay_up = now_up
        if not now_up:
            await send(bot, (
                '⚠️ <b>Mac relay OFFLINE</b> — iMessages won\'t be sent.\n'
                'Start ngrok on your Mac to restore.'
            ))
        logger.info('Relay health: initial state = %s', 'UP' if now_up else 'DOWN')
        return

    if now_up == _relay_up:
        return  # No change — stay silent

    _relay_up = now_up
    if now_up:
        await send(bot, '✅ <b>Mac relay back ONLINE</b> — iMessages restored.')
        logger.info('Relay health: DOWN → UP')
    else:
        await send(bot, (
            '🚨 <b>Mac relay OFFLINE</b>\n'
            'iMessages won\'t be sent until the tunnel is back.\n'
            'Start ngrok on your Mac.'
        ))
        logger.info('Relay health: UP → DOWN')


# ── Monthly Voice Profile Reminder ───────────────────────────────────────────

async def _voice_profile_reminder(bot: Bot):
    """1st of each month — remind Rubén to regenerate the voice profile."""
    _vps = VPS_HOST or 'YOUR_VPS_IP'
    await send(bot, (
        '🎙️ <b>Monthly reminder: regenerate the voice profile!</b>\n\n'
        'Run on your Mac:\n'
        '<code>python3 ~/VIRAL/scripts/generate_voice_profile.py</code>\n\n'
        'Then sync to VPS:\n'
        f'<code>sshpass -e rsync -az ~/VIRAL/data/voice_profile.json '
        f'root@{_vps}:{DATA_DIR}/voice_profile.json</code>'
    ))
    logger.info('Voice profile monthly reminder sent')

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES.mkdir(parents=True, exist_ok=True)

    _app = Application.builder().token(TELEGRAM_TOKEN).build()
    _app.add_handler(CommandHandler('report', cmd_report))
    _app.add_handler(CommandHandler('status', cmd_status))
    _app.add_handler(CommandHandler('check', cmd_check))
    _app.add_handler(CommandHandler('statuscheck', cmd_statuscheck))
    _app.add_handler(CommandHandler('channelstate', cmd_channelstate))
    _app.add_handler(CommandHandler('classify', cmd_classify))
    _app.add_handler(CommandHandler('remap', cmd_remap))
    _app.add_handler(CommandHandler('profile', cmd_profile))
    _app.add_handler(CommandHandler('slackbrief', cmd_slackbrief))
    _app.add_handler(CommandHandler('warmup', lambda u, c: asyncio.create_task(warmup_check(c.bot)) or u.message.reply_text('Checking warm-up...') if u.effective_chat.id == CHAT_ID else None))
    _app.add_handler(CommandHandler('digest', lambda u, c: asyncio.create_task(nightly_digest(c.bot)) or u.message.reply_text('Generando digest...') if u.effective_chat.id == CHAT_ID else None))
    _app.add_handler(CommandHandler('onboarding', lambda u, c: asyncio.create_task(onboarding_check(c.bot)) or u.message.reply_text('Corriendo onboarding check...') if u.effective_chat.id == CHAT_ID else None))
    _app.add_handler(CallbackQueryHandler(handle_draft_callback, pattern=r'^draft_(approve|reject|changes)\|'))
    _app.add_handler(CallbackQueryHandler(handle_qdraft_callback, pattern=r'^qdraft_(send|edit|skip)\|'))
    _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback_text))

    scheduler = AsyncIOScheduler(timezone=LA_TZ)
    scheduler.add_job(
        status_check, 'cron', hour=6, minute=0, args=[_app.bot],
    )
    scheduler.add_job(
        morning_report, 'cron', hour=9, minute=0, args=[_app.bot],
    )
    scheduler.add_job(
        onboarding_check, 'cron', hour=10, minute=0, args=[_app.bot],
    )
    scheduler.add_job(
        buenos_dias_check, 'cron', hour=11, minute=0, args=[_app.bot],
    )
    scheduler.add_job(
        overdue_check, 'cron', hour=17, minute=0, args=[_app.bot],
    )
    scheduler.add_job(
        nightly_digest, 'cron', hour=21, minute=0, args=[_app.bot],
    )
    scheduler.add_job(
        _voice_profile_reminder, 'cron', day=1, hour=9, minute=0, args=[_app.bot],
    )
    scheduler.add_job(
        check_relay_health, 'interval', minutes=15, args=[_app.bot],
    )
    scheduler.add_job(
        slack_daily_brief, 'cron', hour=7, minute=30, args=[_app.bot],
    )
    scheduler.add_job(
        warmup_check, 'cron', hour=14, minute=0, args=[_app.bot],
    )

    async def post_init(app):
        scheduler.start()
        logger.info('VIRAL Bot started. Scheduler running.')

    _app.post_init = post_init
    _app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
