# creator-db — Creator Database Operations

Skill para gestionar la base de datos de creadores del proyecto VIRAL.
Fuente: `creators/creators.json` | CLI: `python3 tools/creators.py`

## Cuándo invocar este skill

Invocar como PRIMERA acción cuando Rubén mencione:
- "base de datos de creadores", "creator directory", "directorio de creadores"
- "busca creadores", "filtra creadores", "muéstrame creadores"
- "cuántas mujeres", "cuántos tier S", "creadores de US"
- "añade un creador", "actualiza a [creador]", "archiva a [creador]"
- "shortlist para [campaña]", "exporta la lista", "genera un listado"
- "estadísticas de creadores", "stats de la DB"
- "enriquece el perfil", "falta info", "niche de creadores"
- "taguea a [creador]", "nota sobre [creador]"
- "blacklistea a [creador]", "no contactar a [creador]"
- "registra outreach", "contacté a [creador]"
- "sincroniza la DB", "actualiza desde Done With You"
- "duplicados", "dedup"

---

## Comandos disponibles

### Consulta y filtros
```bash
# Listar con filtros
python3 tools/creators.py list
python3 tools/creators.py list --gender f
python3 tools/creators.py list --tier S A --country US
python3 tools/creators.py list --sideshift --gender f
python3 tools/creators.py list --niche skincare
python3 tools/creators.py list --tag skinqueens
python3 tools/creators.py list --no-tier          # sin tier asignado
python3 tools/creators.py list --missing-handles  # sin TikTok/IG handle
python3 tools/creators.py list --missing-niche    # sin niche definido

# Buscar por texto libre
python3 tools/creators.py search "nombre o email o ciudad o niche"

# Ver perfil completo
python3 tools/creators.py show "mackenzi"
python3 tools/creators.py show "mackenzi_cox@icloud.com"

# Estadísticas generales
python3 tools/creators.py stats

# Detectar duplicados
python3 tools/creators.py dedup

# Ver qué campos faltan para enriquecer
python3 tools/creators.py enrich
python3 tools/creators.py enrich --field tier
python3 tools/creators.py enrich --field niche
python3 tools/creators.py enrich --field handles
```

### CRUD
```bash
# Añadir creador nuevo
python3 tools/creators.py add \
  --name "Ana García" --email "ana@gmail.com" \
  --phone "+1 555 0000" --country US --city "Los Angeles" \
  --tier B --gender f --niche "skincare,beauty" \
  --platforms "tiktok,instagram" --tiktok anagarcia --instagram anagarcia

# Actualizar campos
python3 tools/creators.py update "mackenzi" --tier S --niche "skincare,beauty"
python3 tools/creators.py update "mackenzi" --tiktok mackenzi_tiktok --instagram mackenzi_ig
python3 tools/creators.py update "mackenzi" --sideshift true

# Archivar / restaurar
python3 tools/creators.py archive "nombre o email"
python3 tools/creators.py restore "nombre o email"

# Blacklist (Do Not Contact)
python3 tools/creators.py blacklist "nombre" --reason "fue grosera, no responde"
```

### Tags y notas
```bash
# Añadir tags (para organizar por campaña, niche, etc.)
python3 tools/creators.py tag "mackenzi" "skinqueens,beauty"
python3 tools/creators.py tag "mackenzi" "skinqueens" --remove

# Añadir notas con timestamp automático
python3 tools/creators.py note "mackenzi" Llamé hoy, está interesada en skincare
python3 tools/creators.py note "lily" No responde mensajes, intentar por email
```

### Outreach tracking
```bash
python3 tools/creators.py outreach "mackenzi" \
  --channel email \
  --result "Respondió, interesada" \
  --notes "Le mandé el brief de SkinQueens"

python3 tools/creators.py outreach "lily" \
  --channel sideshift \
  --result "Invitación enviada"
```

### Shortlist para campaña
```bash
# Mujeres US tier S/A con SideShift para SkinQueens
python3 tools/creators.py shortlist \
  --gender f --country US --tier S A \
  --sideshift \
  --label "SkinQueens — Batch 2" \
  --output creators/exports/skinqueens-shortlist.md

# Todas las mujeres US sin importar tier, que no estén ya en la campaña
python3 tools/creators.py shortlist \
  --gender f --country US \
  --not-in-campaign "TikTok UGC Creators for AI Skincare App — SkinQueens" \
  --label "SkinQueens — Nuevas"
```

### Exportar
```bash
# Exportar a CSV
python3 tools/creators.py export --gender f --country US
python3 tools/creators.py export --tier S A --output creators/exports/top-tier.csv

# Regenerar el markdown desde el JSON
python3 tools/creators.py list  # cualquier comando actualiza el MD
```

### Sincronizar con Done With You
```bash
python3 tools/creators.py sync
# Preserva enriquecimientos locales (niche, tags, notas, handles)
# Solo sobreescribe los campos que vienen de la fuente
```

---

## Flujo recomendado para SkinQueens

1. Generar shortlist de candidatas:
   ```bash
   python3 tools/creators.py shortlist --gender f --country US --sideshift --label "SkinQueens"
   ```
2. Revisar perfiles de las top candidates en TikTok/IG con `/browse`
3. Actualizar niche de las que encajan:
   ```bash
   python3 tools/creators.py update "nombre" --niche "skincare,beauty"
   python3 tools/creators.py tag "nombre" "skinqueens-prospect"
   ```
4. Generar shortlist final con tag:
   ```bash
   python3 tools/creators.py shortlist --tag "skinqueens-prospect" --label "SkinQueens Final"
   ```
5. Enviar invites vía SideShift (`/sideshift`)

---

## Archivos del sistema

| Archivo | Descripción |
|---------|-------------|
| `creators/creators.json` | Source of truth — JSON con todos los campos |
| `creators/creator-directory.md` | Vista markdown generada automáticamente |
| `creators/exports/` | Shortlists y exports generados |
| `tools/creators.py` | CLI principal |
| `tools/sync-creators.py` | Sync legacy (usar `creators.py sync` en su lugar) |
