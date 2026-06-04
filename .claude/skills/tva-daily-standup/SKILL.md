# tva-daily-standup — Daily Stand Up para TVA

Genera el daily stand up diario de Rubén para el equipo de The Viral App.
Fuentes: iMessage (todos los clientes activos) + SideShift + input manual de Rubén.
Formato: COMPLETADO / EN PROGRESO / BLOQUEADO / PARA MAÑANA / DISTRIBUCIÓN DEL TIEMPO.

## Cuándo invocar

- "daily stand up", "daily standup", "standup de hoy"
- "arma el daily", "genera el daily para TVA"
- "qué reporte mando al equipo hoy"
- "daily de TVA", "reporte para el equipo"

---

## Paso 0 — Fecha y clientes activos

```bash
TODAY=$(date +%Y-%m-%d)
echo "Generando Daily Stand Up para: $TODAY"
# Leer clientes activos desde CLAUDE.md del proyecto
grep -A2 "Cliente Activo\|Program ID" /Users/rubenlovera/VIRAL/CLAUDE.md | head -30
```

**Clientes conocidos y sus keywords de iMessage:**
| Cliente | iMessage keyword | SideShift Program ID |
|---------|-----------------|---------------------|
| SkinQueens | `skin\|queen\|skinqueen` | `TB3foYXKIztJmVZmPkyJ` |

> Ampliar tabla cuando se agreguen nuevos clientes.

---

## Paso 1 — Leer iMessage de HOY (todos los clientes)

Buscar en TODOS los grupos relacionados con clientes TVA los mensajes enviados y recibidos hoy.

```bash
TODAY=$(date +%Y-%m-%d)

# Paso 1a: encontrar todos los grupos de clientes activos
sqlite3 ~/Library/Messages/chat.db "
SELECT ROWID, display_name, chat_identifier
FROM chat
WHERE display_name LIKE '%skin%'
   OR display_name LIKE '%queen%'
   OR display_name LIKE '%klover%'
   OR display_name LIKE '%wayk%'
   OR display_name LIKE '%tmo%'
ORDER BY ROWID DESC;" 2>/dev/null

# Paso 1b: mensajes de HOY con texto clásico
sqlite3 ~/Library/Messages/chat.db "
SELECT
  c.display_name,
  m.is_from_me,
  datetime(m.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime') as msg_date,
  substr(m.text, 1, 200) as text
FROM chat c
JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
JOIN message m ON cmj.message_id = m.ROWID
WHERE (c.display_name LIKE '%skin%' OR c.display_name LIKE '%queen%'
    OR c.display_name LIKE '%klover%' OR c.display_name LIKE '%wayk%'
    OR c.display_name LIKE '%tmo%')
  AND date(m.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime') = '$TODAY'
  AND m.text IS NOT NULL AND m.text != ''
ORDER BY c.display_name, m.date ASC;" 2>/dev/null
```

Para mensajes con `text IS NULL`, extraer `attributedBody`:
```bash
TODAY=$(date +%Y-%m-%d)
sqlite3 ~/Library/Messages/chat.db "
SELECT c.display_name, m.is_from_me,
  datetime(m.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime') as msg_date,
  hex(m.attributedBody)
FROM chat c
JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
JOIN message m ON cmj.message_id = m.ROWID
WHERE (c.display_name LIKE '%skin%' OR c.display_name LIKE '%queen%'
    OR c.display_name LIKE '%klover%' OR c.display_name LIKE '%wayk%'
    OR c.display_name LIKE '%tmo%')
  AND date(m.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime') = '$TODAY'
  AND m.text IS NULL
  AND m.attributedBody IS NOT NULL
ORDER BY c.display_name, m.date ASC;" 2>/dev/null | while IFS='|' read group from_me date hexbody; do
  text=$(echo "$hexbody" | xxd -r -p 2>/dev/null | strings | \
    grep -v 'NSAttributedString\|NSObject\|NSString\|streamtyped\|NSMutable\|NSDictionary\|__kIM' | \
    grep -E '^.{5,}$' | head -3 | tr '\n' ' | ')
  echo "[$group][from_me=$from_me][$date] $text"
done 2>/dev/null
```

---

## Paso 2 — SideShift: posts y métricas de hoy

```python
# Posts publicados hoy — filtrar por fecha = hoy
mcp__sideshift__list_posts(programId="TB3foYXKIztJmVZmPkyJ")
# → contar cuántos posts se publicaron hoy
# → sumar views totales del día
# → identificar el post con más views

# Analytics por video — ranking de hoy
mcp__sideshift__get_analytics_videos(programId="TB3foYXKIztJmVZmPkyJ")
# → top performers del día

# KPIs acumulados del programa (para contexto)
mcp__sideshift__get_kpis()
```

**Métricas a reportar:**
- Posts publicados hoy: N
- Views acumuladas del programa: N
- Top video del día (creador + views)
- Drafts aprobados hoy (si aplica)

---

## Paso 3 — Input manual de Rubén (OBLIGATORIO)

**Antes de generar el reporte, preguntar vía Spokenly:**

```
mcp__spokenly__ask_user_dictation(
  question="¿Qué más hiciste hoy que no esté en iMessage ni en SideShift? Cuéntame también qué está bloqueado, qué queda para mañana, y cómo distribuiste tu tiempo entre clientes."
)
```

Escuchar y registrar la respuesta. Incorporar al reporte en las secciones correspondientes.

---

## Paso 4 — Clasificar actividades del día

Analizar toda la información recopilada (iMessage + SideShift + input manual) y clasificar en estas categorías:

### COMPLETADO
Acciones terminadas y cerradas hoy:
- Contratos firmados (creador confirmó, SideShift activo)
- Onboardings completados (creador tiene instrucciones, cuenta lista)
- Drafts validados/aprobados hoy
- Master sheets actualizadas
- Pagos procesados

**Señales iMessage de completado:**
- `from_me=1` con "Contract signed ✅", "Welcome to the program", "Draft approved ✅"
- `from_me=0` con "I signed", "Done!", "I posted", "Here's my video", link de TikTok/IG
- Creador envió `tiktok.com/t/` o `instagram.com/reel/`

### EN PROGRESO
Acciones iniciadas pero no cerradas:
- Mensajes enviados esperando respuesta
- Instrucciones de warm-up enviadas (proceso en curso)
- Negociaciones abiertas
- Creadores con dudas respondidas pero sin confirmar

**Señales iMessage:**
- `from_me=1` hoy sin respuesta posterior del creador
- Conversaciones con ida y vuelta activa

### BLOQUEADO
Items que no pueden avanzar por causa externa:
- Esperando pago/acción de otro miembro del equipo
- Creador no responde hace +24h
- Problema técnico en SideShift/plataforma
- Esperando aprobación o materiales

### PARA MAÑANA
Items detectados como pendientes:
- Seguimientos que no se cerraron hoy
- Creadores en warm-up que publicarán mañana
- Tareas mencionadas por Rubén en el input manual

### DISTRIBUCIÓN DEL TIEMPO
Estimar basándose en:
- Volumen de mensajes por cliente
- Tareas completadas por cliente
- Lo que Rubén mencionó en el input manual

---

## Paso 5 — Generar el reporte

### Formato output

```
DAILY STAND UP — [FECHA]

COMPLETADO
- [Acción concreta] → [resultado específico, número cuando aplique]
- [Acción concreta] → [resultado específico]

EN PROGRESO
- [Acción en curso] → [estado actual, qué falta]
- [Acción en curso] → [estado actual]

BLOQUEADO
- [Item bloqueado] → [razón, quién debe desbloquearlo]

PARA MAÑANA
- [Tarea pendiente]
- [Tarea pendiente]

DISTRIBUCIÓN DEL TIEMPO
- XX% [Cliente A]
- XX% [Cliente B]
- XX% [Otro]
```

**Reglas de redacción:**
- Tono: directo, profesional, sin relleno
- Español neutro (el equipo de TVA es multilatino)
- Números concretos cuando existan: "1 contrato firmado", "+10 drafts validados", "+20 creadores contactados"
- Una línea por item — no párrafos
- No mencionar nombres completos de creadores si son confidenciales, usar "creador X" o el handle si ya es público

---

## Paso 6 — Guardar el reporte y sincronizar al agente VIRAL

```bash
FECHA=$(date +%Y-%m-%d)
OUTFILE="/Users/rubenlovera/VIRAL/standups/tva-standup-${FECHA}.md"
# Escribir con Write tool
```

Después de guardar, sincronizar al VPS:

```bash
export SSHPASS='Dios-Es-Amor123'
sshpass -e ssh -o StrictHostKeyChecking=no root@187.127.255.6 \
  "mkdir -p /root/culver-os/viral-bot/knowledge/standups"
sshpass -e rsync -az -e "ssh -o StrictHostKeyChecking=no" \
  /Users/rubenlovera/VIRAL/standups/ \
  root@187.127.255.6:/root/culver-os/viral-bot/knowledge/standups/
```

Mostrar el reporte en pantalla listo para copiar/pegar en Slack o WhatsApp del equipo.

---

## Notas técnicas

- **iMessage Full Disk Access:** si falla la query, pedir a Rubén que otorgue permiso en System Settings → Privacy & Security → Full Disk Access → Terminal/Claude
- **`text IS NULL`:** siempre intentar `attributedBody` como fallback
- **Múltiples clientes:** ampliar los `LIKE` en la query de iMessage cuando se agreguen nuevos clientes
- **Zona horaria:** usar `'localtime'` en las queries SQLite para que "hoy" corresponda a Pacific Time
- **SideShift "hoy":** filtrar posts/contracts por `created_at` o `posted_at` = fecha de hoy
