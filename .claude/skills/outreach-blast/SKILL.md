# Skill: outreach-blast
> Envío masivo de invites a creadoras — iMessage + Gmail — para campañas de TVA.

---

## Qué hace este skill

Ejecuta un blast de outreach personalizado a todas las creadoras elegibles de la Creator DB:
1. Genera el shortlist filtrado (género, país, campaña, tier)
2. Crea el invite link en SideShift para el programa target
3. Arma el mensaje personalizado (nombre + contexto TVA)
4. Envía iMessages via AppleScript a todos los teléfonos
5. Crea un Gmail draft con todos los emails en BCC

---

## Script principal

```bash
cd ~/VIRAL

# Dry run primero (siempre)
python3 tools/send-imessages.py --dry-run

# Envío real
python3 tools/send-imessages.py

# Reanudar desde un número específico si se interrumpe
python3 tools/send-imessages.py --start=25
```

---

## Flujo completo para una nueva campaña

### 1. Generar shortlist

```bash
python3 tools/creators.py shortlist \
  --gender f \
  --country US \
  --not-in-campaign "NOMBRE EXACTO DE LA CAMPAÑA EN SIDESHIFT" \
  --output creators/exports/[campaña]-candidates.md
```

### 2. Generar invite link en SideShift

```python
# Via MCP tool:
mcp__sideshift__create_program_invite(programId="PROGRAM_ID")
# Guardar el link resultante
```

### 3. Actualizar tools/send-imessages.py

Editar las 3 constantes en la parte superior:
```python
INVITE_LINK = "https://app.sideshift.app/program-invite/TOKEN"
CREATOR_KIT = "https://obsidian-beauty-f48.notion.site/..."
DELAY_SECONDS = 3  # segundos entre mensajes
```

Y la lista `CREATORS` con los pares `(first_name, phone)` del shortlist.

Para regenerar la lista desde la DB:
```bash
python3 - <<'EOF'
import json, re

with open("creators/creators.json") as f:
    data = json.load(f)

batch_names = ["Nombre1", "Nombre2"]  # creadoras ya en la campaña

def normalize(p):
    d = re.sub(r'\D', '', p)
    if len(d) == 11 and d.startswith('1'): return f"+{d}"
    if len(d) == 10: return f"+1{d}"
    return None

seen = set()
for c in data.get("creators", []):
    if c.get("status") != "active": continue
    if c.get("gender","").lower() != "f": continue
    if "US" not in c.get("country","").upper(): continue
    if c.get("name","") in batch_names: continue
    phone = normalize(c.get("phone","").strip())
    if not phone or phone in seen: continue
    seen.add(phone)
    print(f'    ("{c["name"].split()[0].title()}", "{phone}"),')
EOF
```

### 4. Actualizar el mensaje en build_message()

El mensaje base actual (SkinQueens):
```
Hi {name},

My name is Ruben Lovera — I'm a UGC Manager at The Viral App.
I found your contact through our creator database, as you've previously
collaborated with TVA, and I genuinely think you'd be a great fit for
one of our new clients.

Please join the [CAMPAIGN] campaign here as soon as you receive this
communication:

{INVITE_LINK}

Once you're in, I also put together a Creator Kit with an intro video
from me, the full content brief, brand assets, and a step-by-step
onboarding guide so you can get fully up to speed before our call:

Creator Kit:

{CREATOR_KIT}

If you'd like to chat before getting started, you can also book a call
with me here:

https://calendar.app.google/yHuW8GUYoURd8jy99

That said, the Creator Kit is pretty complete — everything you need to
join the campaign and start creating is already in there.

If you have any questions, feel free to reply here. See you soon!

Best regards,

Ruben Lovera
UGC Manager — The Viral App
ruben@theviralapp.com
```

### 5. Enviar Gmail draft

```python
# Via MCP tool mcp__claude_ai_Gmail__create_draft:
# - to: ["ruben@beetransfer.net"]
# - bcc: [lista de emails]
# - subject: "You're invited — [CAMPAIGN] UGC Campaign"
# - htmlBody: mismo mensaje en HTML
```

### 6. Dry run → test con número propio → blast completo

```bash
# 1. Verificar lista
python3 tools/send-imessages.py --dry-run

# 2. Test con número de Rubén
# Cambiar temporalmente CREATORS = [("Ruben", "+16466620346")]

# 3. Confirmar mensaje OK → blast completo
python3 tools/send-imessages.py
```

---

## Requisitos

- **Messages.app** debe estar abierto con iMessage activo
- **iMessage** debe estar logueado con Apple ID
- **Gmail MCP** conectado (para el draft)
- **SideShift MCP** conectado (para generar invite link)

---

## Historial de uso

| Fecha | Campaña | Enviados | Resultado |
|-------|---------|----------|-----------|
| 2026-05-18 | SkinQueens Batch 2 | 61 iMessages + 47 emails (draft) | 61/61 ✓ |

---

## Archivos relacionados

- `tools/send-imessages.py` — script ejecutable
- `creators/creators.json` — source of truth de creadoras
- `tools/creators.py shortlist` — genera el pool de elegibles
- `clients/skinqueen/CLAUDE.md` — contexto del cliente activo
