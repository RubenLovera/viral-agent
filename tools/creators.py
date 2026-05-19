#!/usr/bin/env python3
"""
Creator Database CLI — VIRAL / The Viral App
Usage: python3 tools/creators.py <command> [options]

Commands:
  list        List creators with filters
  search      Search by name, email, or any text field
  show        Show full profile of a creator
  add         Add a new creator manually
  update      Update one or more fields of a creator
  archive     Archive a creator (sets status=archived)
  blacklist   Mark creator as Do Not Contact
  restore     Restore archived creator to active
  tag         Add or remove tags from a creator
  note        Add a timestamped note to a creator
  shortlist   Generate a shortlist for a campaign (with criteria)
  export      Export filtered list to CSV or markdown table
  stats       Show database statistics
  dedup       Find potential duplicate entries
  enrich      Show creators missing key fields (niche, handles, tier)
  outreach    Add an outreach event to a creator's history
  sync        Pull fresh data from Done With You web app
"""

import json
import csv
import sys
import argparse
import hashlib
import urllib.request
import base64
from datetime import date, datetime
from pathlib import Path
from collections import Counter, defaultdict

DB_PATH   = Path(__file__).parent.parent / "creators" / "creators.json"
MD_PATH   = Path(__file__).parent.parent / "creators" / "creator-directory.md"
BASE_URL  = "https://done-with-you-production.up.railway.app"
DWY_USER  = "admin"
DWY_PASS  = "TVA@dmin2026!"

TIER_ORDER = {'S': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4, '': 5}


# ─── DB helpers ───────────────────────────────────────────────────────────────

def load_db():
    with open(DB_PATH) as f:
        return json.load(f)

def save_db(db):
    db['last_updated'] = date.today().isoformat()
    with open(DB_PATH, 'w') as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    regenerate_md(db)

def find_creator(db, query):
    """Find creator by id, name (partial), or email."""
    q = query.lower().strip()
    for c in db['creators']:
        if c['id'] == q:
            return c
        if q in c['name'].lower() or q in c['email'].lower():
            return c
    return None

def find_all(db, query):
    """Find all matching creators."""
    q = query.lower().strip()
    return [c for c in db['creators']
            if q in c['name'].lower() or q in c['email'].lower()]


# ─── Markdown regeneration ────────────────────────────────────────────────────

def regenerate_md(db):
    today = date.today().isoformat()
    creators = db['creators']
    by_tier = defaultdict(list)
    for c in creators:
        by_tier[c.get('tier','')].append(c)

    tier_labels = {
        'S': 'Tier S — Top Performers',
        'A': 'Tier A — High Performers',
        'B': 'Tier B — Sólidos',
        'C': 'Tier C — En Desarrollo',
        'D': 'Tier D — Nuevos / Por Evaluar',
        '':  'Sin Tier Asignado',
    }

    lines = [
        f"---",
        f"created: {db.get('created_at', today)}",
        f"updated: {today}",
        f"tags: [creators, database, ugc, tva]",
        f"status: active",
        f"source: {BASE_URL}/done-with-you/creators",
        f"---",
        f"",
        f"# Creator Directory — TVA",
        f"",
        f"Base de datos completa de creadores veteados de The Viral App.",
        f"**Total: {len([c for c in creators if c.get('status') != 'archived'])} activos** "
        f"| {len(creators)} totales | Última sync: {db.get('last_sync', today)}",
        f"",
        f"> Actualizar: `python3 tools/creators.py sync`",
        f"",
        f"---",
        f"",
        f"## Distribución",
        f"",
        f"| Tier | Descripción | Total | Activos |",
        f"|------|-------------|-------|---------|",
    ]

    for tier in ['S','A','B','C','D','']:
        group = by_tier[tier]
        if not group:
            continue
        active = sum(1 for c in group if c.get('status') != 'archived')
        desc = tier_labels[tier].split(" — ")[1] if " — " in tier_labels[tier] else tier_labels[tier]
        lines.append(f"| {tier or '—'} | {desc} | {len(group)} | {active} |")

    lines += ["", "---", ""]

    for tier in ['S','A','B','C','D','']:
        group = [c for c in by_tier[tier] if c.get('status') != 'archived']
        if not group:
            continue
        lines.append(f"## {tier_labels[tier]}")
        lines.append("")
        lines.append("| Nombre | Email | Género | País | Ciudad | Plataformas | Niche | Tags | SideShift | Handles |")
        lines.append("|--------|-------|--------|------|--------|-------------|-------|------|-----------|---------|")
        for c in sorted(group, key=lambda x: x['name']):
            gender_icon = '♀' if c.get('gender')=='f' else ('♂' if c.get('gender')=='m' else '?')
            platforms   = ', '.join(c.get('platforms', [])) or '—'
            niche       = ', '.join(c.get('niche', [])) or '—'
            tags        = ', '.join(c.get('tags', [])) or '—'
            sideshift   = '✓' if c.get('sideshift') else '—'
            tt  = f"@{c['tiktok_handle']}" if c.get('tiktok_handle') else '—'
            ig  = f"@{c['instagram_handle']}" if c.get('instagram_handle') else '—'
            handles = f"TT:{tt} IG:{ig}"
            lines.append(
                f"| {c['name']} | {c['email']} | {gender_icon} "
                f"| {c.get('country') or '—'} | {c.get('city') or '—'} "
                f"| {platforms} | {niche} | {tags} | {sideshift} | {handles} |"
            )
        lines.append("")

    MD_PATH.write_text("\n".join(lines))


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_list(args):
    db = load_db()
    creators = db['creators']

    if not args.include_archived:
        creators = [c for c in creators if c.get('status') != 'archived']
    if not args.include_blacklisted:
        creators = [c for c in creators if not c.get('blacklisted')]

    if args.tier:
        creators = [c for c in creators if c.get('tier','').upper() in [t.upper() for t in args.tier]]
    if args.country:
        creators = [c for c in creators if (c.get('country','') or '').upper() == args.country.upper()]
    if args.gender:
        creators = [c for c in creators if c.get('gender') == args.gender]
    if args.sideshift:
        creators = [c for c in creators if c.get('sideshift')]
    if args.platform:
        creators = [c for c in creators if args.platform.lower() in (c.get('platforms') or [])]
    if args.niche:
        creators = [c for c in creators if args.niche.lower() in [n.lower() for n in (c.get('niche') or [])]]
    if args.tag:
        creators = [c for c in creators if args.tag.lower() in [t.lower() for t in (c.get('tags') or [])]]
    if args.no_tier:
        creators = [c for c in creators if not c.get('tier')]
    if args.missing_handles:
        creators = [c for c in creators if not c.get('tiktok_handle') and not c.get('instagram_handle')]
    if args.missing_niche:
        creators = [c for c in creators if not c.get('niche')]

    creators = sorted(creators, key=lambda c: (TIER_ORDER.get(c.get('tier',''), 5), c['name']))

    print(f"{'NOMBRE':<28} {'EMAIL':<35} {'TIER':<5} {'GÉNERO':<7} {'PAÍS':<8} {'SIDESHIFT':<10} {'NICHE'}")
    print("─" * 110)
    for c in creators:
        gender = '♀' if c.get('gender')=='f' else ('♂' if c.get('gender')=='m' else '?')
        ss = '✓' if c.get('sideshift') else '—'
        niche = ', '.join(c.get('niche',[])[:2]) or '—'
        print(f"{c['name']:<28} {c['email']:<35} {c.get('tier','—'):<5} {gender:<7} {(c.get('country') or '—'):<8} {ss:<10} {niche}")
    print(f"\n{len(creators)} creadores")


def cmd_search(args):
    db = load_db()
    q = ' '.join(args.query).lower()
    matches = [
        c for c in db['creators']
        if q in c['name'].lower()
        or q in c['email'].lower()
        or q in (c.get('city') or '').lower()
        or q in (c.get('highlights') or '').lower()
        or any(q in t.lower() for t in (c.get('tags') or []))
        or any(q in n.lower() for n in (c.get('niche') or []))
        or any(q in a.lower() for a in (c.get('apps') or []))
    ]
    for c in matches:
        gender = '♀' if c.get('gender')=='f' else ('♂' if c.get('gender')=='m' else '?')
        ss = '✓' if c.get('sideshift') else '—'
        print(f"[{c.get('tier','—')}] {c['name']} {gender} | {c['email']} | {c.get('country','—')} | SideShift:{ss}")
        if c.get('highlights'):
            print(f"    → {c['highlights']}")
    print(f"\n{len(matches)} resultados para '{q}'")


def cmd_show(args):
    db = load_db()
    c = find_creator(db, args.query)
    if not c:
        print(f"No encontrado: {args.query}")
        return
    gender = {'f': 'Mujer', 'm': 'Hombre', 'unknown': 'Desconocido'}.get(c.get('gender',''), '?')
    print(f"\n{'═'*50}")
    print(f"  {c['name']}  [{c.get('tier','Sin tier')}]  |  ID: {c['id']}")
    print(f"{'═'*50}")
    print(f"  Email:        {c['email']}")
    print(f"  Teléfono:     {c.get('phone') or '—'}")
    print(f"  Género:       {gender}")
    print(f"  País:         {c.get('country') or '—'}")
    print(f"  Ciudad:       {c.get('city') or '—'}")
    print(f"  Estado:       {c.get('status','active')}" + (" 🚫 BLACKLISTED" if c.get('blacklisted') else ""))
    print(f"  Plataformas:  {', '.join(c.get('platforms',[])) or '—'}")
    print(f"  TikTok:       {'@'+c['tiktok_handle'] if c.get('tiktok_handle') else '—'}")
    print(f"  Instagram:    {'@'+c['instagram_handle'] if c.get('instagram_handle') else '—'}")
    print(f"  SideShift:    {'✓ Registrado' if c.get('sideshift') else '—'}")
    print(f"  Niche:        {', '.join(c.get('niche',[])) or '—'}")
    print(f"  Tags:         {', '.join(c.get('tags',[])) or '—'}")
    print(f"  Apps (hist):  {', '.join(c.get('apps',[])) or '—'}")
    print(f"  Campañas:     {', '.join(c.get('campaigns',[])) or '—'}")
    if c.get('highlights'):
        print(f"  Highlights:   {c['highlights']}")
    if c.get('notes'):
        print(f"\n  NOTAS:")
        for n in c['notes']:
            print(f"    [{n['date']}] {n['text']}")
    if c.get('outreach_history'):
        print(f"\n  OUTREACH:")
        for o in c['outreach_history']:
            print(f"    [{o['date']}] {o['channel']} → {o['result']}")
    print()


def cmd_add(args):
    db = load_db()
    uid = hashlib.md5(args.email.encode()).hexdigest()[:8]
    if any(c['email'] == args.email for c in db['creators']):
        print(f"Ya existe un creador con email {args.email}")
        return
    today = date.today().isoformat()
    creator = {
        'id': uid,
        'name': args.name,
        'email': args.email,
        'phone': args.phone or '',
        'country': args.country or '',
        'city': args.city or '',
        'tier': args.tier or '',
        'source': 'Manual',
        'gender': args.gender or 'unknown',
        'niche': args.niche.split(',') if args.niche else [],
        'tags': [],
        'notes': [],
        'status': 'active',
        'platforms': args.platforms.split(',') if args.platforms else [],
        'apps': [],
        'campaigns': [],
        'sideshift': False,
        'highlights': '',
        'tiktok_handle': args.tiktok or '',
        'instagram_handle': args.instagram or '',
        'outreach_history': [],
        'blacklisted': False,
        'created_at': today,
        'updated_at': today,
    }
    db['creators'].append(creator)
    db['total'] = len(db['creators'])
    save_db(db)
    print(f"Creador añadido: {args.name} (id: {uid})")


def cmd_update(args):
    db = load_db()
    c = find_creator(db, args.query)
    if not c:
        print(f"No encontrado: {args.query}")
        return
    fields = {
        'tier': args.tier, 'country': args.country, 'city': args.city,
        'phone': args.phone, 'gender': args.gender, 'highlights': args.highlights,
        'tiktok_handle': args.tiktok, 'instagram_handle': args.instagram,
        'sideshift': args.sideshift,
    }
    updated = []
    for k, v in fields.items():
        if v is not None:
            c[k] = v
            updated.append(k)
    if args.niche:
        c['niche'] = [n.strip() for n in args.niche.split(',')]
        updated.append('niche')
    if args.platforms:
        c['platforms'] = [p.strip() for p in args.platforms.split(',')]
        updated.append('platforms')
    c['updated_at'] = date.today().isoformat()
    save_db(db)
    print(f"Actualizado: {c['name']} — campos: {', '.join(updated)}")


def cmd_archive(args):
    db = load_db()
    c = find_creator(db, args.query)
    if not c:
        print(f"No encontrado: {args.query}")
        return
    c['status'] = 'archived'
    c['updated_at'] = date.today().isoformat()
    save_db(db)
    print(f"Archivado: {c['name']}")


def cmd_restore(args):
    db = load_db()
    c = find_creator(db, args.query)
    if not c:
        print(f"No encontrado: {args.query}")
        return
    c['status'] = 'active'
    c['updated_at'] = date.today().isoformat()
    save_db(db)
    print(f"Restaurado: {c['name']}")


def cmd_blacklist(args):
    db = load_db()
    c = find_creator(db, args.query)
    if not c:
        print(f"No encontrado: {args.query}")
        return
    c['blacklisted'] = True
    c['status'] = 'archived'
    if args.reason:
        c['notes'].append({'date': date.today().isoformat(), 'text': f'[BLACKLIST] {args.reason}'})
    c['updated_at'] = date.today().isoformat()
    save_db(db)
    print(f"Blacklisteado: {c['name']}")


def cmd_tag(args):
    db = load_db()
    c = find_creator(db, args.query)
    if not c:
        print(f"No encontrado: {args.query}")
        return
    tags = [t.strip().lower() for t in args.tags.split(',')]
    if args.remove:
        c['tags'] = [t for t in c.get('tags',[]) if t not in tags]
        print(f"Tags removidos de {c['name']}: {tags}")
    else:
        existing = set(c.get('tags',[]))
        existing.update(tags)
        c['tags'] = sorted(existing)
        print(f"Tags de {c['name']}: {c['tags']}")
    c['updated_at'] = date.today().isoformat()
    save_db(db)


def cmd_note(args):
    db = load_db()
    c = find_creator(db, args.query)
    if not c:
        print(f"No encontrado: {args.query}")
        return
    note = {'date': date.today().isoformat(), 'text': ' '.join(args.text)}
    c.setdefault('notes', []).append(note)
    c['updated_at'] = date.today().isoformat()
    save_db(db)
    print(f"Nota añadida a {c['name']}: {note['text']}")


def cmd_outreach(args):
    db = load_db()
    c = find_creator(db, args.query)
    if not c:
        print(f"No encontrado: {args.query}")
        return
    event = {
        'date': date.today().isoformat(),
        'channel': args.channel,
        'result': args.result,
        'notes': args.notes or '',
    }
    c.setdefault('outreach_history', []).append(event)
    c['updated_at'] = date.today().isoformat()
    save_db(db)
    print(f"Outreach registrado para {c['name']}: {args.channel} → {args.result}")


def cmd_shortlist(args):
    db = load_db()
    creators = [c for c in db['creators'] if c.get('status') != 'archived' and not c.get('blacklisted')]

    if args.tier:
        creators = [c for c in creators if c.get('tier','') in [t.upper() for t in args.tier]]
    if args.gender:
        creators = [c for c in creators if c.get('gender') == args.gender]
    if args.country:
        creators = [c for c in creators if (c.get('country','') or '').upper() == args.country.upper()]
    if args.sideshift:
        creators = [c for c in creators if c.get('sideshift')]
    if args.niche:
        creators = [c for c in creators if args.niche.lower() in [n.lower() for n in (c.get('niche') or [])]]
    if args.tag:
        creators = [c for c in creators if args.tag.lower() in [t.lower() for t in (c.get('tags') or [])]]
    if args.not_in_campaign:
        creators = [c for c in creators if args.not_in_campaign not in (c.get('campaigns') or [])]
    if args.limit:
        creators = creators[:args.limit]

    creators = sorted(creators, key=lambda c: (TIER_ORDER.get(c.get('tier',''), 5), c['name']))

    print(f"# Shortlist — {args.label or 'Campaña'}")
    print(f"Generado: {date.today().isoformat()} | Total: {len(creators)}\n")
    print(f"| # | Nombre | Email | Teléfono | Tier | País | SideShift | Niche |")
    print(f"|---|--------|-------|----------|------|------|-----------|-------|")
    for i, c in enumerate(creators, 1):
        ss = '✓' if c.get('sideshift') else '—'
        niche = ', '.join(c.get('niche', [])) or '—'
        print(f"| {i} | {c['name']} | {c['email']} | {c.get('phone') or '—'} | {c.get('tier','—')} | {c.get('country','—')} | {ss} | {niche} |")

    if args.output:
        Path(args.output).write_text('\n'.join([
            f"# Shortlist — {args.label or 'Campaña'}",
            f"Generado: {date.today().isoformat()} | Total: {len(creators)}", "",
            "| # | Nombre | Email | Teléfono | Tier | País | SideShift | Niche |",
            "|---|--------|-------|----------|------|------|-----------|-------|",
        ] + [
            f"| {i} | {c['name']} | {c['email']} | {c.get('phone') or '—'} | {c.get('tier','—')} | {c.get('country','—')} | {'✓' if c.get('sideshift') else '—'} | {', '.join(c.get('niche',[])) or '—'} |"
            for i, c in enumerate(creators, 1)
        ]))
        print(f"\nGuardado en: {args.output}")


def cmd_export(args):
    db = load_db()
    creators = [c for c in db['creators'] if c.get('status') != 'archived' or args.include_archived]

    if args.tier:
        creators = [c for c in creators if c.get('tier','') in [t.upper() for t in args.tier]]
    if args.gender:
        creators = [c for c in creators if c.get('gender') == args.gender]
    if args.country:
        creators = [c for c in creators if (c.get('country','') or '').upper() == args.country.upper()]
    if args.sideshift:
        creators = [c for c in creators if c.get('sideshift')]

    output = args.output or f"creators/exports/export-{date.today().isoformat()}.csv"
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    with open(output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'name','email','phone','country','city','tier','gender',
            'sideshift','platforms','niche','tags','tiktok_handle','instagram_handle',
            'status','highlights'
        ])
        writer.writeheader()
        for c in creators:
            writer.writerow({
                'name': c['name'], 'email': c['email'], 'phone': c.get('phone',''),
                'country': c.get('country',''), 'city': c.get('city',''),
                'tier': c.get('tier',''), 'gender': c.get('gender',''),
                'sideshift': 'yes' if c.get('sideshift') else 'no',
                'platforms': '|'.join(c.get('platforms',[])),
                'niche': '|'.join(c.get('niche',[])),
                'tags': '|'.join(c.get('tags',[])),
                'tiktok_handle': c.get('tiktok_handle',''),
                'instagram_handle': c.get('instagram_handle',''),
                'status': c.get('status','active'),
                'highlights': c.get('highlights',''),
            })
    print(f"Exportado: {len(creators)} creadores → {output}")


def cmd_stats(args):
    db = load_db()
    creators = db['creators']
    active = [c for c in creators if c.get('status') != 'archived' and not c.get('blacklisted')]

    print(f"\n{'═'*45}")
    print(f"  CREATOR DIRECTORY — STATS")
    print(f"{'═'*45}")
    print(f"  Total:          {len(creators)}")
    print(f"  Activos:        {len(active)}")
    print(f"  Archivados:     {sum(1 for c in creators if c.get('status')=='archived')}")
    print(f"  Blacklisted:    {sum(1 for c in creators if c.get('blacklisted'))}")
    print(f"  En SideShift:   {sum(1 for c in active if c.get('sideshift'))}")
    print(f"  Última sync:    {db.get('last_sync','—')}")

    print(f"\n  POR TIER:")
    tier_counts = Counter(c.get('tier','') or '—' for c in active)
    for tier in ['S','A','B','C','D','—']:
        n = tier_counts.get(tier, 0)
        if n: print(f"    Tier {tier}: {n:>3} {'█'*(n//2)}")

    print(f"\n  POR GÉNERO:")
    gender_counts = Counter(c.get('gender','unknown') for c in active)
    print(f"    Mujeres:  {gender_counts.get('f',0)}")
    print(f"    Hombres:  {gender_counts.get('m',0)}")
    print(f"    Unknown:  {gender_counts.get('unknown',0)}")

    print(f"\n  POR PAÍS:")
    country_counts = Counter((c.get('country') or 'Sin datos') for c in active)
    for country, n in country_counts.most_common():
        print(f"    {country:<20} {n}")

    print(f"\n  POR PLATAFORMA:")
    plat_counts = Counter(p for c in active for p in (c.get('platforms') or []))
    for plat, n in plat_counts.most_common():
        print(f"    {plat:<15} {n}")

    niches = [n for c in active for n in (c.get('niche') or [])]
    if niches:
        print(f"\n  TOP NICHES:")
        for niche, n in Counter(niches).most_common(10):
            print(f"    {niche:<20} {n}")

    print()


def cmd_dedup(args):
    db = load_db()
    seen_emails = defaultdict(list)
    seen_names  = defaultdict(list)
    for c in db['creators']:
        seen_emails[c['email'].lower()].append(c)
        seen_names[c['name'].lower()].append(c)
    found = False
    for email, group in seen_emails.items():
        if len(group) > 1:
            print(f"DUPLICADO EMAIL: {email}")
            for c in group:
                print(f"  [{c['id']}] {c['name']}")
            found = True
    for name, group in seen_names.items():
        if len(group) > 1:
            print(f"DUPLICADO NOMBRE: {name}")
            for c in group:
                print(f"  [{c['id']}] {c['email']}")
            found = True
    if not found:
        print("No se encontraron duplicados.")


def cmd_enrich(args):
    db = load_db()
    creators = [c for c in db['creators'] if c.get('status') != 'archived']

    missing_tier    = [c for c in creators if not c.get('tier')]
    missing_niche   = [c for c in creators if not c.get('niche')]
    missing_handles = [c for c in creators if not c.get('tiktok_handle') and not c.get('instagram_handle')]
    missing_gender  = [c for c in creators if c.get('gender') == 'unknown']

    print(f"{'═'*45}")
    print(f"  ENRIQUECIMIENTO PENDIENTE")
    print(f"{'═'*45}")
    print(f"  Sin tier:     {len(missing_tier)}")
    print(f"  Sin niche:    {len(missing_niche)}")
    print(f"  Sin handles:  {len(missing_handles)}")
    print(f"  Sin género:   {len(missing_gender)}")

    if args.field == 'tier':
        print(f"\nCreadores sin tier:")
        for c in sorted(missing_tier, key=lambda x: x['name']):
            ss = '✓' if c.get('sideshift') else '—'
            print(f"  {c['name']:<28} {c['email']:<35} SideShift:{ss}")
    elif args.field == 'niche':
        print(f"\nCreadores sin niche:")
        for c in sorted(missing_niche, key=lambda x: x['name']):
            print(f"  {c['name']:<28} {c['email']}")
    elif args.field == 'handles':
        print(f"\nCreadores sin handles:")
        for c in sorted(missing_handles, key=lambda x: x['name']):
            print(f"  {c['name']:<28} {c['email']}")


def cmd_sync(args):
    print("Conectando a Done With You...")
    token = base64.b64encode(f"{DWY_USER}:{DWY_PASS}".encode()).decode()
    def fetch(path):
        req = urllib.request.Request(f"{BASE_URL}{path}", headers={"Authorization": f"Basic {token}"})
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())

    new_creators  = fetch("/api/creators")["creators"]
    new_profiles  = fetch("/api/creator-profiles")["profiles"]
    print(f"  {len(new_creators)} creadores | {len(new_profiles)} perfiles")

    # Load existing DB to preserve local enrichments
    if DB_PATH.exists():
        db = load_db()
        existing = {c['email']: c for c in db['creators']}
    else:
        db = {'creators': []}
        existing = {}

    profile_by_email = {p['email']: p for p in new_profiles}
    profile_by_name  = {p['name'].lower().strip(): p for p in new_profiles}

    today = date.today().isoformat()
    merged = []
    added = updated = 0

    for nc in new_creators:
        uid = hashlib.md5(nc['email'].encode()).hexdigest()[:8]
        p = profile_by_email.get(nc['email']) or profile_by_name.get(nc['name'].lower().strip())

        if nc['email'] in existing:
            c = existing[nc['email']]
            # Update source-of-truth fields, preserve local enrichments
            c.update({
                'name': nc['name'], 'phone': nc.get('phone','') or c.get('phone',''),
                'country': nc.get('country','') or c.get('country',''),
                'city': nc.get('city','') or c.get('city',''),
                'tier': nc.get('tier','') or c.get('tier',''),
                'sideshift': (p.get('sideshift', False) if p else False) or c.get('sideshift', False),
                'platforms': p.get('platforms', c.get('platforms',[])) if p else c.get('platforms',[]),
                'apps': list(set((p.get('apps',[]) if p else []) + c.get('apps',[]))),
                'campaigns': list(set((p.get('campaigns',[]) if p else []) + c.get('campaigns',[]))),
                'highlights': p.get('highlights','') if p else c.get('highlights',''),
                'updated_at': today,
            })
            merged.append(c)
            updated += 1
        else:
            first = nc['name'].split()[0].lower()
            female = {'aaniyah','abby','adele','aleaya','alexa','alexis','alina','amanda','ashley','audrey','ava','barbara','briana','brianna','bryana','carrie','cassandra','chandni','christina','danielle','dulce','emmanuela','gia','grace','gracie','gigi','hailey','haily','isabella','jada','janiya','javeria','jazmyne','jennifer','karissa','kathryn','katie','kavya','kayla','keytonya','kimora','lauren','lea','lexi','lily','lolo','mackenzi','madison','malaika','margarida','marta','mckenzie','megan','mia','my','nasia','natalie','naysa','nicole','nina','niya','noha','olamide','paloma','peinda','praise','rachel','rebaone','rujala','sara','susan','tabbie','tina','tofunmi','vera','taylor'}
            male = {'aaron','aaryan','adam','akshansh','alexander','alfie','alvaro','anderson','andrew','anthony','ashton','aydin','aymar','ayub','azaan','bobby','carson','charlie','chase','chris','cj','daniel','david','dee','derick','dilan','domagoj','eddie','elias','epue','eric','frank','gabriel','gavin','geo','george','hayden','isaac','jd','jacob','jaden','jake','javien','jibril','joe','joel','john','johnny','jordan','jose','joshua','julian','justin','karam','kelton','kendrick','keonn','kevin','khoi','khyan','legasse','leonard','lukas','mark','mason','mateus','max','michael','mikita','milan','nash','nebiy','ngo','nick','omar','ramez','rayhaan','rijan','russell','sameer','shao','smith','spencer','sreesh','suraj','tae','taha','thomas','tobias','tommy','travis','william','yug','zach','zahne'}
            gender = 'f' if first in female else ('m' if first in male else 'unknown')
            merged.append({
                'id': uid, 'name': nc['name'], 'email': nc['email'],
                'phone': nc.get('phone','') or '', 'country': nc.get('country','') or '',
                'city': nc.get('city','') or '', 'tier': nc.get('tier','') or '',
                'source': nc.get('source','') or '', 'gender': gender,
                'niche': [], 'tags': [], 'notes': [], 'status': 'active',
                'platforms': p.get('platforms',[]) if p else [],
                'apps': p.get('apps',[]) if p else [],
                'campaigns': p.get('campaigns',[]) if p else [],
                'sideshift': p.get('sideshift', False) if p else False,
                'highlights': p.get('highlights','') if p else '',
                'tiktok_handle': '', 'instagram_handle': '',
                'outreach_history': [], 'blacklisted': False,
                'created_at': today, 'updated_at': today,
            })
            added += 1

    db['creators'] = merged
    db['total'] = len(merged)
    db['last_sync'] = today
    db.setdefault('created_at', today)
    save_db(db)
    print(f"Sync completado: {added} nuevos, {updated} actualizados | Total: {len(merged)}")


# ─── CLI setup ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Creator Database CLI')
    sub = parser.add_subparsers(dest='cmd')

    # list
    p = sub.add_parser('list', help='Listar creadores con filtros')
    p.add_argument('--tier', nargs='+')
    p.add_argument('--country')
    p.add_argument('--gender', choices=['f','m','unknown'])
    p.add_argument('--sideshift', action='store_true')
    p.add_argument('--platform')
    p.add_argument('--niche')
    p.add_argument('--tag')
    p.add_argument('--no-tier', dest='no_tier', action='store_true')
    p.add_argument('--missing-handles', dest='missing_handles', action='store_true')
    p.add_argument('--missing-niche', dest='missing_niche', action='store_true')
    p.add_argument('--include-archived', dest='include_archived', action='store_true')
    p.add_argument('--include-blacklisted', dest='include_blacklisted', action='store_true')

    # search
    p = sub.add_parser('search', help='Buscar por texto')
    p.add_argument('query', nargs='+')

    # show
    p = sub.add_parser('show', help='Ver perfil completo')
    p.add_argument('query')

    # add
    p = sub.add_parser('add', help='Añadir creador manualmente')
    p.add_argument('--name', required=True)
    p.add_argument('--email', required=True)
    p.add_argument('--phone'); p.add_argument('--country'); p.add_argument('--city')
    p.add_argument('--tier'); p.add_argument('--gender', choices=['f','m','unknown'])
    p.add_argument('--niche'); p.add_argument('--platforms')
    p.add_argument('--tiktok'); p.add_argument('--instagram')

    # update
    p = sub.add_parser('update', help='Actualizar campos de un creador')
    p.add_argument('query')
    p.add_argument('--tier'); p.add_argument('--country'); p.add_argument('--city')
    p.add_argument('--phone'); p.add_argument('--gender', choices=['f','m','unknown'])
    p.add_argument('--niche'); p.add_argument('--platforms'); p.add_argument('--highlights')
    p.add_argument('--tiktok'); p.add_argument('--instagram')
    p.add_argument('--sideshift', type=lambda x: x.lower() == 'true')

    # archive / restore / blacklist
    for cmd_name in ['archive', 'restore']:
        p = sub.add_parser(cmd_name)
        p.add_argument('query')

    p = sub.add_parser('blacklist')
    p.add_argument('query')
    p.add_argument('--reason')

    # tag
    p = sub.add_parser('tag', help='Añadir/remover tags')
    p.add_argument('query')
    p.add_argument('tags')
    p.add_argument('--remove', action='store_true')

    # note
    p = sub.add_parser('note', help='Añadir nota')
    p.add_argument('query')
    p.add_argument('text', nargs='+')

    # outreach
    p = sub.add_parser('outreach', help='Registrar contacto de outreach')
    p.add_argument('query')
    p.add_argument('--channel', required=True, choices=['email','dm','whatsapp','imessage','sideshift','call','other'])
    p.add_argument('--result', required=True)
    p.add_argument('--notes')

    # shortlist
    p = sub.add_parser('shortlist', help='Generar shortlist para campaña')
    p.add_argument('--tier', nargs='+'); p.add_argument('--gender', choices=['f','m','unknown'])
    p.add_argument('--country'); p.add_argument('--sideshift', action='store_true')
    p.add_argument('--niche'); p.add_argument('--tag')
    p.add_argument('--not-in-campaign', dest='not_in_campaign')
    p.add_argument('--limit', type=int); p.add_argument('--label')
    p.add_argument('--output')

    # export
    p = sub.add_parser('export', help='Exportar a CSV')
    p.add_argument('--tier', nargs='+'); p.add_argument('--gender', choices=['f','m','unknown'])
    p.add_argument('--country'); p.add_argument('--sideshift', action='store_true')
    p.add_argument('--include-archived', dest='include_archived', action='store_true')
    p.add_argument('--output')

    # stats
    sub.add_parser('stats', help='Estadísticas de la base de datos')

    # dedup
    sub.add_parser('dedup', help='Encontrar duplicados')

    # enrich
    p = sub.add_parser('enrich', help='Ver campos faltantes')
    p.add_argument('--field', choices=['tier','niche','handles','gender'])

    # sync
    sub.add_parser('sync', help='Sincronizar desde Done With You')

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    dispatch = {
        'list': cmd_list, 'search': cmd_search, 'show': cmd_show,
        'add': cmd_add, 'update': cmd_update, 'archive': cmd_archive,
        'restore': cmd_restore, 'blacklist': cmd_blacklist,
        'tag': cmd_tag, 'note': cmd_note, 'outreach': cmd_outreach,
        'shortlist': cmd_shortlist, 'export': cmd_export,
        'stats': cmd_stats, 'dedup': cmd_dedup, 'enrich': cmd_enrich,
        'sync': cmd_sync,
    }
    dispatch[args.cmd](args)


if __name__ == '__main__':
    main()
