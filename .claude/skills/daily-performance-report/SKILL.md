# daily-performance-report — Reporte Diario de Campaña

Reporte operacional de las últimas 24h. Audiencia: Rubén (uso interno).
Combina estado de creadores (iMessage) + actividad de hoy en SideShift.
Formato: semáforo de alertas + action items concretos.

## Cuándo invocar

- "daily report de [cliente]", "cómo va hoy [cliente]"
- "qué necesito hacer hoy", "reporte diario de SkinQueens"
- "cómo estuvo hoy la campaña", "resumen del día"

---

## Paso 0 — Resolver el cliente

Extraer el nombre del cliente del argumento. Si no se especifica, usar el cliente activo en CLAUDE.md.

```bash
# Leer cliente activo y su Program ID desde CLAUDE.md
grep -A3 "Cliente Activo\|Program ID\|iMessage" /Users/rubenlovera/VIRAL/CLAUDE.md | head -20
# Leer config específica del cliente
cat /Users/rubenlovera/VIRAL/clients/skinqueen/CLAUDE.md 2>/dev/null | head -50
```

**Mapping de clientes conocidos:**
| Cliente | iMessage keyword | SideShift Program ID |
|---------|-----------------|---------------------|
| SkinQueens | `skin\|queen` | `TB3foYXKIztJmVZmPkyJ` |

---

## Paso 1 — Estado de creadores (delegar a /imessage-report)

Invocar el skill `/imessage-report` pasando el keyword del cliente para filtrar solo sus grupos.

El skill `/imessage-report` se encarga de:
- Encontrar todos los grupos de iMessage del cliente
- Clasificar creadores: Publicando / Drafts / Warm-up / Outreach / Abandonando
- Detectar grupos vacíos y duplicados

**Para el daily report, enfocarse en:**
- ¿Quién debería haber publicado hoy y no lo hizo? (Publicando activos sin link enviado hoy)
- ¿Qué drafts llevan más de 24h esperando aprobación?
- ¿Algún creador envió señal de abandono hoy?

```bash
# Query iMessage para actividad de HOY específicamente
TODAY=$(date +%Y-%m-%d)
sqlite3 ~/Library/Messages/chat.db "
SELECT c.display_name,
  substr(m.text,1,100) as text,
  datetime(m.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime') as msg_date,
  m.is_from_me
FROM chat c
JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
JOIN message m ON cmj.message_id = m.ROWID
WHERE (c.display_name LIKE '%skin%' OR c.display_name LIKE '%queen%')
  AND date(m.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime') = '$TODAY'
  AND m.text IS NOT NULL AND m.text != ''
ORDER BY c.display_name, m.date DESC;" 2>/dev/null
```

---

## Paso 2 — SideShift: actividad de hoy

```python
# Traer posts publicados HOY
mcp__sideshift__list_posts(programId="TB3foYXKIztJmVZmPkyJ")
# Filtrar por fecha = hoy

# Pagos urgentes (vencen en 24-48h)
mcp__sideshift__list_pending_payouts()

# KPIs generales (para contexto)
mcp__sideshift__get_kpis()
```

---

## Paso 3 — Generar el reporte

### Formato del Daily Report

```markdown
## Daily Report — [Cliente] — [Fecha]
**Generado:** [hora]

### Semáforo del día
🔴 URGENTE  — [N items que necesitan acción inmediata]
🟡 ATENCIÓN — [N items a revisar hoy]
🟢 ON TRACK — [N creadores funcionando bien]

### Posts publicados hoy
[lista de creadores que publicaron + links]
Total: N posts (N TikTok + N IG)

### Alertas operativas
- [Creador X] no ha publicado en 2 días — último contacto: [fecha]
- [Draft de Y] lleva [N] horas esperando aprobación
- [Pago de $Z] vence mañana — [creador] sin Stripe configurado
- [Creador W] envió señal de abandono — requiere atención

### Creadores en warm-up (esperados publicar esta semana)
[lista con fecha proyectada de primer post]

### Action items para hoy
1. [acción específica]
2. [acción específica]
```

---

## Paso 4 — Guardar el reporte

```bash
FECHA=$(date +%Y-%m-%d)
OUTFILE="/Users/rubenlovera/VIRAL/campaigns/skinqueens-daily-${FECHA}.md"
# Escribir el reporte al archivo con Write tool
```

---

## Notas técnicas

- **iMessage hoy:** usar `date(...) = '$TODAY'` en la query SQL para filtrar solo mensajes de hoy
- **attributedBody:** si `m.text IS NULL`, extraer con `hex(m.attributedBody)` + `xxd -r -p` + `strings` (ver /imessage-report para el script completo)
- **Señales de abandono:** texto que contenga "remove", "cancel", "not interested", "leaving"
- **Señal de publicación:** mensaje contiene `tiktok.com/t/` o `instagram.com/reel/`
- **Drafts pendientes:** creador envió video (attachment) y no hay respuesta "Draft approved ✅" después
