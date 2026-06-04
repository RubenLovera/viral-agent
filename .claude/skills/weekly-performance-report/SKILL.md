# weekly-performance-report — Reporte Semanal de Campaña

Reporte de trends de la semana. Audiencia: Rubén + Head of UGC Operations (TVA).
Combina pipeline completo de creadores (iMessage) + analytics semanales de SideShift.
Formato: weekly review estructurado con métricas, pipeline y plan para la semana siguiente.

## Cuándo invocar

- "weekly report de [cliente]", "reporte semanal de SkinQueens"
- "cómo fue la semana", "resumen semanal", "weekly performance"
- "reporte para TVA", "qué le reporto a mi jefe esta semana"

---

## Paso 0 — Resolver el cliente

Extraer nombre del cliente del argumento. Default: cliente activo en CLAUDE.md.

```bash
grep -A3 "Cliente Activo\|Program ID" /Users/rubenlovera/VIRAL/CLAUDE.md | head -20
cat /Users/rubenlovera/VIRAL/clients/skinqueen/CLAUDE.md 2>/dev/null | head -50
```

**Mapping de clientes conocidos:**
| Cliente | iMessage keyword | SideShift Program ID |
|---------|-----------------|---------------------|
| SkinQueens | `skin\|queen` | `TB3foYXKIztJmVZmPkyJ` |

---

## Paso 1 — Estado completo de creadores (delegar a /imessage-report)

Invocar `/imessage-report` para obtener el pipeline completo de creadores del cliente.

El reporte semanal usa TODOS los datos de /imessage-report:
- Cuántos publicando activamente
- Cuántos en drafts/aprobación
- Cuántos en warm-up (con proyección de cuándo publican)
- Cuántos en outreach (pipeline entrante)
- Cuántos abandonaron esta semana
- Proyección: cuántos activos la semana siguiente

```bash
# Rango de la semana actual (Lunes a hoy)
WEEK_START=$(date -v-Mon +%Y-%m-%d 2>/dev/null || date -d 'last monday' +%Y-%m-%d 2>/dev/null)
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
  AND date(m.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime') BETWEEN '$WEEK_START' AND '$TODAY'
  AND m.text IS NOT NULL AND m.text != ''
ORDER BY c.display_name, m.date DESC;" 2>/dev/null
```

---

## Paso 2 — SideShift: analytics de la semana

```python
# Analytics generales del programa esta semana
mcp__sideshift__get_analytics_overview(programId="TB3foYXKIztJmVZmPkyJ")

# Top videos de la semana
mcp__sideshift__get_analytics_videos(programId="TB3foYXKIztJmVZmPkyJ")

# Performance por cuenta/creador
mcp__sideshift__get_analytics_accounts(programId="TB3foYXKIztJmVZmPkyJ")

# Reclutamiento: invites enviados y responses
mcp__sideshift__get_analytics_recruitment(programId="TB3foYXKIztJmVZmPkyJ")

# Pagos de la semana
mcp__sideshift__list_pending_payouts()
mcp__sideshift__list_payouts()

# Contratos activos vs total
mcp__sideshift__list_contracts()
```

---

## Paso 3 — Calcular métricas clave

Antes de formatear, calcular:

| Métrica | Cómo calcular |
|---------|--------------|
| CPM | Gasto total / (Views totales / 1,000) |
| Hook Rate | Views 3s / Views totales × 100 (si disponible) |
| Engagement Rate | (Likes + Comments) / Views × 100 |
| Avg views/post | Views totales / Posts totales |
| Creator activation rate | Creadores publicando / Contratos activos × 100 |

---

## Paso 4 — Generar el reporte

### Formato del Weekly Report

```markdown
## Weekly Performance Report — [Cliente]
**Período:** [Lunes] – [Domingo] | **Generado:** [fecha]

---
### Resumen Ejecutivo
[2-3 oraciones: qué pasó esta semana, cuál fue el logro más importante, qué viene]

---
### Métricas de Contenido
| Métrica | Esta semana | Benchmark |
|---------|------------|-----------|
| Posts publicados | N | — |
| Vistas totales | N | — |
| Engagement Rate | N% | 3–5% |
| Avg views/post | N | — |
| CPM | $N | <$5 |

TikTok vs Instagram:
[tabla comparativa]

---
### Pipeline de Creadores
| Estado | Esta semana | Proyección próxima semana |
|--------|------------|--------------------------|
| Publicando activamente | N | N |
| Drafts / Empezando | N | N |
| Warm-up en progreso | N | N |
| Outreach / Onboarding | N | N |
| Abandonaron | N | — |

---
### Top Performers de la Semana
[tabla: creador, views, posts, ER, plataforma destacada]

---
### Reclutamiento
- Responses esta semana: N
- Contratos activos: N de M totales
- Canal: [orgánico / SideShift invites]

---
### Pagos
[tabla de pending payouts si hay]

---
### La semana que viene
- [N] creadoras terminan warm-up → empiezan a publicar
- [N] contratos pendientes de firma
- [Acción prioritaria 1]
- [Acción prioritaria 2]
```

---

## Paso 5 — Guardar el reporte

```bash
SEMANA=$(date +%Y-W%V)
OUTFILE="/Users/rubenlovera/VIRAL/campaigns/skinqueens-weekly-${SEMANA}.md"
# Escribir con Write tool
```

---

## Notas técnicas

- **Rango semanal en iMessage:** usar `BETWEEN '$WEEK_START' AND '$TODAY'` en la query SQL
- **attributedBody:** si `m.text IS NULL`, ver script de extracción en /imessage-report SKILL.md
- **Semana ISO:** `date +%Y-W%V` da el número de semana del año (ej: 2026-W21)
- **Benchmark ER:** 3–5% = industria UGC, 8%+ = excelente, 15%+ = outlier
- **Creator activation rate:** si está por debajo del 25%, hay problema de onboarding
