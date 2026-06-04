# monthly-performance-report — Reporte Mensual de Campaña

Narrativa ejecutiva del mes. Audiencia: Cliente / Founder (ej: Joe Fleming, CEO SkinQueens).
Combina pipeline de creadores (iMessage) + analytics completos del mes (SideShift).
Formato: reporte en INGLÉS, narrativa profesional, listo para enviar al cliente.

## Cuándo invocar

- "monthly report de [cliente]", "reporte mensual de SkinQueens"
- "reporte para el cliente", "reporte para Joe", "reporte para el founder"
- "performance del mes", "cómo fue el mes", "qué le mando a Joe"

---

## Paso 0 — Resolver el cliente

Extraer nombre del cliente del argumento. Default: cliente activo en CLAUDE.md.

```bash
grep -A5 "Cliente Activo\|Program ID\|Contacto" /Users/rubenlovera/VIRAL/CLAUDE.md | head -30
cat /Users/rubenlovera/VIRAL/clients/skinqueen/CLAUDE.md 2>/dev/null
```

**Mapping de clientes conocidos:**
| Cliente | iMessage keyword | SideShift Program ID | Founder | Email |
|---------|-----------------|---------------------|---------|-------|
| SkinQueens | `skin\|queen` | `TB3foYXKIztJmVZmPkyJ` | Joe Fleming | — |

---

## Paso 1 — Estado del pipeline (delegar a /imessage-report)

Invocar `/imessage-report` para el pipeline completo del mes.

Para el monthly report, /imessage-report provee:
- Total de creadores en el pipeline al cierre del mes
- Cuántos están publicando activamente
- Cuántos completaron el warm-up y empezaron a publicar en el mes
- Cuántos abandonaron / cancelaron
- Proyección para el mes siguiente

```bash
# Rango del mes (1ro del mes a hoy)
MONTH_START=$(date +%Y-%m-01)
TODAY=$(date +%Y-%m-%d)

sqlite3 ~/Library/Messages/chat.db "
SELECT c.display_name,
  substr(m.text,1,120) as text,
  datetime(m.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime') as msg_date,
  m.is_from_me
FROM chat c
JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
JOIN message m ON cmj.message_id = m.ROWID
WHERE (c.display_name LIKE '%skin%' OR c.display_name LIKE '%queen%')
  AND date(m.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime') BETWEEN '$MONTH_START' AND '$TODAY'
  AND m.text IS NOT NULL AND m.text != ''
ORDER BY c.display_name, m.date DESC;" 2>/dev/null
```

---

## Paso 2 — SideShift: analytics completos del mes

```python
# Overview completo del programa
mcp__sideshift__get_analytics_overview(programId="TB3foYXKIztJmVZmPkyJ")

# Top videos del mes (ranking completo)
mcp__sideshift__get_analytics_videos(programId="TB3foYXKIztJmVZmPkyJ")

# Performance desglosado por cuenta
mcp__sideshift__get_analytics_accounts(programId="TB3foYXKIztJmVZmPkyJ")

# Reclutamiento del mes
mcp__sideshift__get_analytics_recruitment(programId="TB3foYXKIztJmVZmPkyJ")

# Todos los posts del mes
mcp__sideshift__list_posts(programId="TB3foYXKIztJmVZmPkyJ")

# Pagos procesados en el mes
mcp__sideshift__list_payouts()
mcp__sideshift__list_pending_payouts()

# Contratos: activos / cancelados / pendientes
mcp__sideshift__list_contracts()

# KPIs del programa
mcp__sideshift__get_kpis()
```

---

## Paso 3 — Nota sobre datos parciales

Si SideShift no tiene todos los posts (el cliente informó que no se han subido todos):
- Anotar en el reporte: "Note: SideShift tracks [N] posts. Additional posts were published this month that are pending upload to the platform. Actual metrics are higher."
- Usar los datos de iMessage como indicador del volumen real de actividad

---

## Paso 4 — Generar el reporte en INGLÉS

El monthly report se genera siempre en inglés — es para el cliente/founder.

### Formato del Monthly Report

```markdown
# Performance Report — [Client Name] UGC Campaign
**Period:** [Month] [Year] (Day 1 – Day N)
**Prepared by:** Rubén Lovera, UGC Manager — The Viral App
**For:** [Founder Name], CEO [Client Name]

---
## Executive Summary
[3-4 sentences: what the month was, top achievement, key metric highlight,
what's coming next month. Professional, direct, no fluff.]

---
## Pipeline Status — End of Month
[Visual pipeline with counts per stage]
[Projection for next month]

Creators publishing today: [list names]

---
## Content Metrics
[Full metrics table: posts, views, ER, likes, comments, shares, bookmarks]
[TikTok vs Instagram breakdown]
[Note about SideShift partial data if applicable]

---
## Top Performers
[Full ranking table with views, posts, avg/post, ER]
[Highlight standout performers with why they worked]

---
## Recruitment — Month Overview
[Table: total responses, contracts active/pending/cancelled, acquisition channel]

---
## Contracts & Payments
[Contracts table]
[Payments table: processed + pending]

---
## Context: Why Numbers Look The Way They Do
[Explain the campaign model — new accounts, warm-up, why volume ramps over time.
This section manages expectations for month 1 vs month 2+.]

---
## Outlook — Next Month
[What's coming: creators finishing warm-up, expected volume, optimization focus]

---
## Summary
[2-column table: What's working | What's coming]
```

---

## Paso 5 — Guardar el reporte

```bash
MES=$(date +%Y-%m)
OUTFILE="/Users/rubenlovera/VIRAL/campaigns/skinqueens-monthly-${MES}.md"
# Escribir con Write tool
```

---

## Notas técnicas

- **Idioma:** SIEMPRE en inglés — es para el founder, no uso interno
- **Datos parciales de SideShift:** Siempre añadir la nota si el cliente mencionó posts sin subir
- **Rango mensual en iMessage:** `BETWEEN '$MONTH_START' AND '$TODAY'` en la query SQL
- **attributedBody:** ver script de extracción en /imessage-report SKILL.md
- **Tono:** Profesional pero directo. No corporate speak. Mostrar los números reales aunque sean bajos con contexto honesto de por qué.
- **Narrativa de "por qué los números crecen":** Explicar siempre el modelo de warm-up — el founder necesita entender que mes 1 es setup, mes 2 es momentum
