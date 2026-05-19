#!/usr/bin/env python3
"""
Sync creator directory from TVA Done With You internal app.
Usage: python3 tools/sync-creators.py
"""
import json
import urllib.request
import urllib.error
import base64
from datetime import date
from collections import defaultdict
from pathlib import Path

BASE_URL = "https://done-with-you-production.up.railway.app"
USER = "admin"
PASS = "TVA@dmin2026!"
OUTPUT = Path(__file__).parent.parent / "creators" / "creator-directory.md"

TIER_ORDER = ['S', 'A', 'B', 'C', 'D', '']
TIER_LABELS = {
    'S': 'Tier S — Top Performers',
    'A': 'Tier A — High Performers',
    'B': 'Tier B — Sólidos',
    'C': 'Tier C — En Desarrollo',
    'D': 'Tier D — Nuevos / Por Evaluar',
    '':  'Sin Tier Asignado',
}

def fetch(path):
    token = base64.b64encode(f"{USER}:{PASS}".encode()).decode()
    req = urllib.request.Request(f"{BASE_URL}{path}", headers={"Authorization": f"Basic {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def get_profile(c, by_email, by_name):
    return by_email.get(c['email']) or by_name.get(c['name'].lower().strip())

def build_md(creators, profiles):
    by_email = {p['email']: p for p in profiles}
    by_name  = {p['name'].lower().strip(): p for p in profiles}
    by_tier  = defaultdict(list)
    for c in creators:
        by_tier[c.get('tier', '')].append(c)

    today = date.today().isoformat()
    lines = [
        f"---",
        f"created: {today}",
        f"updated: {today}",
        f"tags: [creators, database, ugc, tva]",
        f"status: active",
        f"source: {BASE_URL}/done-with-you/creators",
        f"---",
        f"",
        f"# Creator Directory — TVA",
        f"",
        f"Base de datos completa de creadores veteados de The Viral App.",
        f"**Total: {len(creators)} creadores** | Última sync: {today}",
        f"",
        f"> Fuente: Done With You internal app. Re-sincronizar con: `python3 tools/sync-creators.py`",
        f"",
        f"---",
        f"",
        f"## Distribución",
        f"",
        f"| Tier | Descripción | Cantidad |",
        f"|------|-------------|----------|",
    ]
    for tier in TIER_ORDER:
        count = len(by_tier[tier])
        if count:
            label = TIER_LABELS[tier]
            desc = label.split(" — ")[1] if " — " in label else label
            lines.append(f"| {tier or '—'} | {desc} | {count} |")

    lines += ["", "---", ""]

    for tier in TIER_ORDER:
        group = by_tier[tier]
        if not group:
            continue
        lines.append(f"## {TIER_LABELS[tier]}")
        lines.append("")
        lines.append("| Nombre | Email | Teléfono | País | Ciudad | Plataformas | Apps | SideShift | Highlights |")
        lines.append("|--------|-------|----------|------|--------|-------------|------|-----------|------------|")
        for c in sorted(group, key=lambda x: x['name']):
            p = get_profile(c, by_email, by_name)
            platforms  = ', '.join(p['platforms']) if p and p.get('platforms') else '—'
            apps       = ', '.join(p['apps'])      if p and p.get('apps')      else '—'
            sideshift  = '✓' if p and p.get('sideshift') else '—'
            highlights = (p.get('highlights') or '—').replace('|', '/') if p else '—'
            lines.append(
                f"| {c['name']} | {c['email']} | {c.get('phone') or '—'} "
                f"| {c.get('country') or '—'} | {c.get('city') or '—'} "
                f"| {platforms} | {apps} | {sideshift} | {highlights} |"
            )
        lines.append("")

    return "\n".join(lines)

if __name__ == "__main__":
    print("Fetching creators...")
    creators = fetch("/api/creators")["creators"]
    print(f"  {len(creators)} creadores")

    print("Fetching profiles...")
    profiles = fetch("/api/creator-profiles")["profiles"]
    print(f"  {len(profiles)} perfiles extendidos")

    md = build_md(creators, profiles)
    OUTPUT.write_text(md)
    print(f"Guardado en: {OUTPUT}")
