# VIRAL — Proyecto The Viral App
> Workspace de Rubén Lovera como UGC Manager en The Viral App (TVA).

---

## Contexto del Rol

**Empresa:** The Viral App (TVA) — Growth agency de UGC e influencer marketing para apps móviles.  
**Rol:** UGC Manager | **Ingreso:** 2026-05-06 | **Reporte a:** Head of UGC Operations

TVA ayuda a apps a escalar de cero a millones de MRR. Tres pilares: Creator Networks, Performance Systems, Repeatable Playbooks.

---

## Cliente Activo

**SkinQueens** — App de skincare IA (iOS + Android)
- **Tagline:** "Stop guessing. Start matching."
- **Core:** Usuario comparte TikTok → app analiza productos → cruza con Skin DNA → dice si hace match
- **Pricing:** $59.99/año (7 días gratis) | $9.99/mes
- **Contrato:** 20 creadores UGC + 3-4 AI accounts, ~750-800 piezas/mes
- **Contacto:** Joe Fleming (CEO)
- **Personas:** SkinTok Scroller (18-29, primario), Routine Builder, Cautious Buyer
- **SideShift Program ID:** `TB3foYXKIztJmVZmPkyJ` ← usar SIEMPRE este ID
- **Ver más:** `clients/skinqueen/CLAUDE.md`

---

## Arsenal Completo — 35 Capacidades

### A. Skills Claude (SKILL.md — invocar con Skill tool)

| Skill | Cuándo usarlo |
|-------|---------------|
| `/sideshift` | Cualquier consulta de datos de SideShift: analytics, posts, pagos, invites, reclutamiento |
| `/campaign-creation` | Crear campaña nueva, job listing, brief para creadores, calcular compensación |
| `/creator-db` | Gestionar la base de 187 creadores: filtrar, buscar, añadir, actualizar, shortlist |
| `/creator-outreach` | Redactar textos de contacto: email, DM, WhatsApp, iMessage, SideShift |

### B. Creator DB CLI — 16 Comandos (`python3 tools/creators.py <cmd>`)

| Categoría | Comando | Cuándo usar |
|-----------|---------|-------------|
| Consulta | `list [filtros]` | Listar creadores con filtros (tier, género, país, sideshift, niche, tag) |
| Consulta | `search <texto>` | Buscar por nombre, email, ciudad, niche, highlights |
| Consulta | `show <nombre>` | Ver perfil completo de un creador específico |
| Consulta | `stats` | Estadísticas generales de la base de datos |
| CRUD | `add` | Añadir creador manualmente |
| CRUD | `update <nombre>` | Actualizar campos de un creador (tier, niche, handles, etc.) |
| CRUD | `archive <nombre>` | Archivar (soft-delete) un creador |
| CRUD | `restore <nombre>` | Restaurar creador archivado |
| CRUD | `blacklist <nombre>` | Marcar como Do Not Contact con razón |
| Organización | `tag <nombre> <tags>` | Añadir/remover etiquetas libres |
| Organización | `note <nombre> <texto>` | Añadir nota con timestamp automático |
| Organización | `enrich [--field]` | Ver qué campos faltan (tier, niche, handles, género) |
| Organización | `dedup` | Detectar emails o nombres duplicados |
| Campañas | `shortlist [filtros]` | Generar shortlist filtrada para una campaña |
| Campañas | `export [filtros]` | Exportar a CSV |
| Campañas | `outreach` | Registrar contacto en historial del creador |
| Sync | `sync` | Sincronizar desde Done With You (preserva datos locales) |

### C. SideShift MCP Tools (`mcp__sideshift__*`)

| Tool | Cuándo usar |
|------|-------------|
| `list_programs` | Ver todas las campañas activas |
| `list_posts` | Ver posts con métricas — filtrar por programa, creador, fecha |
| `get_post` | Detalle completo de un post específico |
| `get_post_metrics_history` | Historial diario de métricas de un post |
| `get_kpis` | KPIs generales de la cuenta |
| `get_analytics_overview` | Overview de analytics del programa |
| `get_analytics_videos` | Analytics por video — ranking de performance |
| `get_analytics_accounts` | Analytics por cuenta de creador |
| `get_analytics_recruitment` | Invites enviados, responses, response rate |
| `list_payouts` | Pagos procesados |
| `list_pending_payouts` | Pagos pendientes de procesar |
| `list_creators` | Creadores registrados en SideShift |
| `list_contracts` | Contratos activos/pendientes con status |
| `list_invoices` | Facturas generadas |
| `create_program_invite` | Generar invite link para una campaña |

---

## Routing Autónomo — Lógica de Decisión

**REGLA FUNDAMENTAL:** Claude debe identificar el contexto e invocar las herramientas correctas **sin esperar que Rubén las pida explícitamente**. Leer el intent, no las palabras exactas.

---

### 1. Cuando Rubén pregunta sobre performance / métricas / campaña

**Acción automática:** Llamar SideShift MCP sin que te lo pidan.

| Intent detectado | Herramientas a usar (en orden) |
|-----------------|-------------------------------|
| "cómo va la campaña" / "cómo estamos" / "qué tal SkinQueens" | `get_analytics_overview` → `get_analytics_videos` → invocar `/sideshift` |
| "top videos" / "mejores posts" / "qué está funcionando" | `get_analytics_videos` → `list_posts` |
| "cuántas views" / "cuántos likes" / "métricas" | `get_kpis` → `get_analytics_overview` |
| "pagos" / "cuánto se ha pagado" / "pendientes de pago" | `list_pending_payouts` → `list_payouts` |
| "cuántos creadores activos" / "contratos" | `list_contracts` → `list_creators` |
| "cómo va el reclutamiento" / "cuántas invites" | `get_analytics_recruitment` |
| "invite link" / "invitar a [creador]" a SideShift | `create_program_invite` con ID `TB3foYXKIztJmVZmPkyJ` |

---

### 2. Cuando Rubén menciona un creador por nombre

**Acción automática:** Buscar en la DB local PRIMERO, luego en SideShift si aplica.

```
Si menciona nombre/email de creador:
  1. python3 tools/creators.py show "<nombre>"
  2. Si está en SideShift: mcp__sideshift__list_posts --creator [id]
  3. Presentar: perfil local + performance en SideShift si existe
```

---

### 3. Cuando Rubén quiere encontrar / seleccionar / invitar creadoras

**Acción automática:** Consultar DB local + generar shortlist lista para usar.

| Intent | Flujo automático |
|--------|-----------------|
| "busca creadoras para SkinQueens" | `list --gender f --country US` → shortlist → preguntar si verificar perfiles en TikTok |
| "quiero invitar más creadoras" | `list --gender f --sideshift` → `shortlist` → `create_program_invite` |
| "creadoras de tier S/A" | `list --tier S A` directo |
| "creadoras que ya están en SideShift" | `list --sideshift` |
| "creadoras de beauty/skincare" | `list --niche skincare` (o `search skincare`) |
| "dame una lista de contactos" | `shortlist --gender f --country US --output creators/exports/[nombre].md` |
| "filtra por [criterio]" | Mapear criterio a flag del CLI y ejecutar |

---

### 4. Cuando Rubén quiere escribirle a un creador

**Acción automática:** Buscar perfil + invocar `/creator-outreach` con contexto precargado.

```
Si intent = contactar/escribir/DM/email a creador:
  1. python3 tools/creators.py show "<nombre>"  ← precarga contexto
  2. Invocar /creator-outreach con: nombre, email, canal, cliente (SkinQueens), escenario
  3. Registrar outreach automáticamente después: creators.py outreach ...
```

---

### 5. Cuando Rubén quiere crear una nueva campaña

**Acción automática:** Cargar contexto del cliente + invocar `/campaign-creation`.

```
Si intent = nueva campaña / brief / job listing:
  1. Leer clients/skinqueen/CLAUDE.md (o cliente mencionado)
  2. Consultar vault: git submodule update --remote vault
  3. Invocar /campaign-creation con contexto del cliente
```

---

### 6. Cuando Rubén actualiza info de un creador

**Acción automática:** Update en la DB + registrar en historial.

| Intent | Comando automático |
|--------|--------------------|
| "el tier de [nombre] es A" | `update "<nombre>" --tier A` |
| "su niche es skincare" | `update "<nombre>" --niche skincare,beauty` |
| "su TikTok es @handle" | `update "<nombre>" --tiktok handle` |
| "ya entró a SideShift" | `update "<nombre>" --sideshift true` |
| "no quiero trabajar más con [nombre]" | `blacklist "<nombre>" --reason "..."` |
| "le mandé invite" / "la contacté" | `outreach "<nombre>" --channel [canal] --result "Invite enviado"` |

---

### 7. Cuando Rubén pide research / scouting de nuevos creadores

**Acción automática:** Usar `/browse` para ir a TikTok/IG + comparar con DB existente.

```
Si intent = scouting / buscar nuevas creadoras / investigar perfil:
  1. Invocar /browse → navegar perfil de TikTok/IG
  2. Evaluar contra criterios de SkinQueens (skinTok, beauty, autenticidad)
  3. Si aplica: creators.py add --name ... --niche skincare --tag skinqueens-prospect
  4. Si no aplica: explicar por qué no cumple los criterios
```

---

### 8. Cuando Rubén pide estadísticas o resumen de la DB

**Acción automática:** `stats` + formato limpio sin preguntas.

```
Si intent = stats / cuántos / distribución / resumen de creadores:
  → python3 tools/creators.py stats
  → Presentar resultado formateado
```

---

## Flujos Automáticos Compuestos

Estos flujos se ejecutan completos sin esperar confirmación paso a paso:

### Flujo: Health Check de Campaña
*Trigger: "cómo estamos", "dame un resumen", "health check de SkinQueens"*
1. `get_analytics_overview` (program: `TB3foYXKIztJmVZmPkyJ`)
2. `get_analytics_videos` — top 5 posts
3. `list_pending_payouts` — pagos pendientes
4. `list_contracts` — contratos activos vs pendientes
5. Presentar resumen ejecutivo en una respuesta

### Flujo: Shortlist para Nueva Batch
*Trigger: "quiero invitar más creadoras", "necesito creadoras para SkinQueens"*
1. `list_contracts` → identificar cuántas hay activas
2. `creators.py list --gender f --country US` → pool disponible
3. `creators.py shortlist --gender f --country US --not-in-campaign "TikTok UGC Creators for AI Skincare App — SkinQueens"` → candidatas nuevas
4. Presentar tabla con nombre, email, tier, SideShift status
5. Preguntar: ¿verifico perfiles en TikTok?

### Flujo: Onboarding de Creador Nuevo
*Trigger: "vamos a onboardear a [nombre]", "nueva creadora aceptó"*
1. `creators.py show "<nombre>"` — ver si ya está en la DB
2. Si no está: `creators.py add` con datos disponibles
3. `creators.py tag "<nombre>" "onboarding"` — marcar estado
4. Invocar `/creator-outreach` — mensaje de bienvenida
5. Recordar: contrato antes de producir contenido

### Flujo: Enriquecimiento de Perfil
*Trigger: "vamos a enriquecer perfiles", "necesito saber el niche de las creadoras"*
1. `creators.py enrich --field niche` → lista de pendientes
2. Para cada una: `/browse` → ir a TikTok → evaluar niche
3. `creators.py update "<nombre>" --niche "..."` → guardar
4. `creators.py tag "<nombre>" "verificada"` → marcar como verificada

---

## Comportamiento Proactivo — Reglas Siempre Activas

Estas reglas aplican en TODO momento, sin que Rubén las pida:

1. **Si Rubén menciona una creadora por nombre** → ejecutar `creators.py show` antes de responder cualquier cosa sobre ella.

2. **Si la pregunta involucra datos de SideShift** → usar MCP tools para traer datos reales, nunca inventar métricas.

3. **Si Rubén toma una decisión sobre un creador** → actualizar la DB automáticamente al final de la respuesta (`update`, `note`, `tag`, `outreach` según corresponda).

4. **Si hay un outreach** → después de generar el texto, preguntar si quiere registrarlo: `creators.py outreach`.

5. **Si el program ID de SkinQueens es necesario** → siempre usar `TB3foYXKIztJmVZmPkyJ`, nunca el ID viejo.

6. **Si Rubén pregunta algo que requiere datos de la DB** → ejecutar el CLI primero, responder basado en datos reales.

7. **Antes de cualquier tarea de campaña** → consultar `clients/skinqueen/CLAUDE.md` y vault si es necesario.

8. **Si Rubén menciona un niche, tag o criterio nuevo** → sugerir añadirlo a la DB con `creators.py tag` o `update --niche`.

---

## Estructura del Proyecto

```
VIRAL/
├── vault/                    # Second brain TVA (git submodule — read only)
├── clients/skinqueen/        # Contexto completo de SkinQueens
├── creators/
│   ├── creators.json         # SOURCE OF TRUTH — 187 creadores
│   ├── creator-directory.md  # Vista markdown (auto-generada)
│   └── exports/              # Shortlists y CSVs exportados
├── briefs/                   # Briefs por campaña
├── campaigns/                # Estado de campañas activas
├── research/                 # Scouting y format research
└── tools/
    ├── creators.py           # CLI de la creator DB (16 comandos)
    ├── sync-creators.py      # Sync legacy
    └── sideshift-mcp/        # Servidor MCP de SideShift
```

---

## SideShift MCP — Configuración

**Program ID SkinQueens:** `TB3foYXKIztJmVZmPkyJ` ← SIEMPRE este ID  
**API key:** `$SIDESHIFT_API_KEY` en `~/.zshrc`  
**Server:** `~/VIRAL/tools/sideshift-mcp/index.js`  
**Config:** `.mcp.json` en la raíz del proyecto  
**Si no carga:** reiniciar Claude Code  
**NUNCA** hacer llamadas manuales a la API — siempre usar los MCP tools

---

## Creator DB — Configuración

**Source of truth:** `creators/creators.json` — 187 creadores  
**CLI:** `python3 tools/creators.py <comando>`  
**Sync desde Done With You:**
```bash
python3 tools/creators.py sync
# o manualmente:
curl -u "admin:TVA@dmin2026!" https://done-with-you-production.up.railway.app/api/creators
```
**SKILL:** `.claude/skills/creator-db/SKILL.md`

---

## Knowledge Base / Vault

```bash
git submodule update --remote vault   # actualizar antes de tareas de campaña
```
Consultar vault para: playbooks, SOPs, templates, historial de campañas, info de clientes.

---

## KPIs y Estándares de Calidad

| KPI | Excelente | Bueno | Mínimo |
|-----|-----------|-------|--------|
| Videos on time | 90%+ | 80-89% | 70-79% |
| Draft approval rate | 70%+ | 55-69% | 40-54% |
| Creator retention | 80%+ | 65-79% | 50-64% |
| Content quality score | 4.0+ / 5 | 3.5-3.9 | 3.0-3.4 |
| Response time | <2h | 2-4h | 4-8h |

**Métricas SideShift:**
| Métrica | Cómo calcular | Target |
|---------|--------------|--------|
| CPM | Gasto / (Views / 1,000) | <$5 (<$2 excelente) |
| Hook Rate | Views 3s / Views totales | 40%+ TikTok |
| Engagement Rate | (Likes + Comments) / Views × 100 | 3%+ TikTok |

---

## Reglas de Brief (nunca violar)

> **"Deciles qué LOGRAR, no qué DECIR."**

- Contenido scriptado performa 60-80% peor que auténtico
- Aprobar: hook fuerte en 1-2s, app visible, video <30s TikTok / <60s Reels, audio limpio, CTA presente
- Rechazar: off-brief, competencia visible, calidad pésima, creador no usó el producto
- Feedback: específico con timestamps, tono positivo, nunca reescribir el script

---

## gstack (REQUIRED)

```bash
test -d ~/.claude/skills/gstack/bin && echo "GSTACK_OK" || echo "GSTACK_MISSING"
```
Si GSTACK_MISSING: STOP. Instalar antes de continuar.
Usar `/browse` para TODA navegación web. Nunca `mcp__claude-in-chrome__*`.
