# /tiktok-research — Motor de Investigación TikTok

**Proyecto:** VIRAL / The Viral App  
**Invocación:** `/tiktok-research <query en lenguaje natural>`

## Cuándo usar este skill

Cualquier pregunta de investigación sobre TikTok:
- "busca los videos más virales de OnSkin"
- "cuáles son los creadores UGC que más views tienen para SkinQueens"
- "qué sonidos están en tendencia para skincare AI app"
- "cuáles son los comentarios más comunes en videos de Lóvi"
- "qué hashtags usa @onskin.app en sus videos"
- "busca videos de competidores de SkinQueens con más de 100K views"

---

## PASO 0 — Leer contexto del proyecto

Antes de empezar:
```bash
cat ~/VIRAL/clients/skinqueen/CLAUDE.md 2>/dev/null | head -20
```
Esto da contexto sobre el cliente activo (SkinQueens), competidores conocidos (OnSkin, Lóvi, SkinSort), y el niche (skincare AI app). Úsalo para enriquecer el análisis.

---

## PASO 1 — Detectar el intent

Clasificar la query del usuario en uno de estos intents:

| Intent | Keywords clave | Output principal |
|--------|---------------|-----------------|
| **VIDEOS** | "videos", "viral", "contenido", "publicaciones", "posts" | Tabla de videos con métricas |
| **CREATORS** | "creadores", "creator", "cuentas", "quién publica", "influencers", "ugc" | Lista de creadores con stats |
| **SOUNDS** | "sonidos", "audio", "música", "sound", "trending sound" | Lista de audios en tendencia |
| **COMMENTS** | "comentarios", "comments", "qué dicen", "reacciones" | Clusters de comentarios |
| **TRENDS** | "tendencias", "trending", "qué está pegando", "qué funciona" | Hashtags + formatos + hooks |
| **HASHTAGS** | "hashtags", "tags", "#", "etiquetas" | Lista de hashtags con frecuencia |

Mostrar al inicio: `🔍 INTENT DETECTADO: [TIPO] | Target: [target identificado]`

---

## PASO 2 — Cadena de Fallback (ejecutar en orden, sin pedir confirmación)

Ejecutar los métodos en orden. Parar cuando se obtengan datos suficientes. Al final, reportar qué método funcionó.

### Método 1: Chrome cookies + browse (MÁXIMA COMPLETENESS)

```bash
B="$HOME/.claude/skills/gstack/browse/dist/browse"
$B goto "https://www.tiktok.com" 2>/dev/null | head -1
$B cookie-import-browser chrome --domain tiktok.com 2>&1
```

Si los cookies importados son > 0:
- Para VIDEOS/CREATORS: `$B goto "https://www.tiktok.com/@[handle]"`  → esperar 3s → `$B text` → extraer lista de videos con métricas
- Para COMMENTS: ir al video específico → scrollear comentarios → `$B text`
- Para SOUNDS/TRENDS: `$B goto "https://www.tiktok.com/explore"` → extraer trending

Si cookies = 0: continuar al Método 2.

---

### Método 2: WebSearch site:tiktok.com (RÁPIDO, CONFIABLE)

```python
# Para VIDEOS:
WebSearch: "site:tiktok.com @[handle] [keywords]"
WebSearch: "site:tiktok.com [brand name] [intent keywords] 2025 OR 2026"

# Para CREATORS:
WebSearch: "site:tiktok.com [brand] skincare ugc creator review"

# Para SOUNDS:
WebSearch: "trending tiktok sound [niche] 2026"
WebSearch: "site:tiktok.com [niche] viral sound trending"

# Para COMMENTS:
WebSearch: "site:tiktok.com [brand] [product] comments reactions"

# Para HASHTAGS:
WebSearch: "site:tiktok.com [brand OR niche] popular hashtags"
```

Con cada URL de TikTok encontrada → ejecutar Método 3 para obtener métricas del DOM.

---

### Método 3: browse headless → DOM del video (MÉTRICAS DEL HTML)

Para cada URL de video TikTok encontrada:
```bash
B="$HOME/.claude/skills/gstack/browse/dist/browse"
$B goto "[TIKTOK_VIDEO_URL]" 2>/dev/null
sleep 4
$B text 2>/dev/null | grep -E "([0-9]+\.[0-9]+[KkMm]|[0-9]+[KkMm]|Like|Comment|Share|Paid)" | head -10
```

**Parsing del DOM de TikTok:**
El texto del DOM de TikTok devuelve los números en este orden antes de "CommentsYou may like":
`[likes][shares][saves][comments]Comments`

Ejemplo: `41K651502109Comments` = 41K likes, 65 shares, 150 saves, 2109 (?)

Interpretar: el número más grande con K/M al inicio = likes (el más prominente).

---

### Método 4: TikTok oEmbed API (ENRIQUECIMIENTO — siempre correr como complemento)

Para cualquier URL de TikTok encontrada, enriquecer con título completo y hashtags:
```bash
curl -s "https://www.tiktok.com/oembed?url=[TIKTOK_VIDEO_URL]" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('TITLE:', d.get('title','')[:100])
print('AUTHOR:', d.get('author_name',''))
print('AUTHOR_ID:', d.get('author_unique_id',''))
"
```

Este método NO da views/likes pero sí da el título completo con todos los hashtags. Usar SIEMPRE como enriquecimiento de cualquier video encontrado.

---

### Método 5: browse --headed (ANTI-BOT)

Solo si Métodos 1-3 fallaron completamente:
```bash
B="$HOME/.claude/skills/gstack/browse/dist/browse"
$B disconnect 2>/dev/null
sleep 2
$B --headed goto "https://www.tiktok.com/@[handle]" 2>&1 | head -3
sleep 5
$B text 2>/dev/null | head -60
```

---

### Método 6: Exolyt.com (ANALYTICS DE TERCEROS — para CREATORS intent)

```bash
B="$HOME/.claude/skills/gstack/browse/dist/browse"
$B goto "https://exolyt.com/user/[handle_sin_arroba]" 2>/dev/null
sleep 3
$B text 2>/dev/null | grep -E "(views|followers|likes|videos|engagement|top)" | head -20
```

Útil para: stats de perfil de creador, promedio de views, top videos, tasa de engagement.

---

### Método 7: YouTube reposts (PROXY DE VIRALIDAD)

```bash
# WebSearch en YouTube para contenido reposteado
WebSearch: "youtube.com [brand] tiktok viral [year]"
WebSearch: "[brand] tiktok repost views [year]"
```

Ver ~/VIRAL/research/competitor-benchmark-skinqueen-EN.md para contexto de qué buscar.

---

## PASO 3 — Clasificar formato de cada video

Para cada video encontrado, clasificar el formato basándose en el título y hashtags:

| Formato | Señales en título/hashtags |
|---------|--------------------------|
| **Talking Head** | "grwm", "story time", "honest review", "let me tell you", habla a cámara, sin demo visible |
| **Scan Demo** | "scanning", "check", "score", "rating", "toxic or not", muestra la app en uso |
| **Reaction** | "react", "reacting", "pov", "watching", "split screen" |
| **GRWM** | "grwm", "get ready with me", "morning/night routine" |
| **Haul** | "haul", "unboxing", "i bought", "testing" |
| **Transformation** | "before/after", "results", "30 days", "i cleared my" |
| **Educational** | "did you know", "ingredients", "why", "how to", "tip" |
| **Unknown** | No encaja en ninguna categoría |

---

## PASO 4 — Construir el output

### Para intent VIDEOS:

```
🔍 TIKTOK RESEARCH — VIDEOS | Método: [MÉTODO USADO] | Completeness: [HIGH/MEDIUM/LOW]
Target: [brand/handle] | Query: "[query original]"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Top Videos

| # | Creador | Likes | Views | Formato | Hook (título) | Link |
|---|---------|-------|-------|---------|---------------|------|
| 1 | @handle | 41K | - | Talking Head | "Definitely recommend the app onskin" | [ver](URL) |
| ... |

## Análisis de Patrones

**Formato ganador:** [X] — representa el Y% de los top videos
**Hook pattern más repetido:** [patrón]
**Hashtags más usados:** #tag1, #tag2, #tag3
**Paid vs orgánico:** X% son paid partnerships

## Para replicar en SkinQueens:
- [recomendación 1 basada en los patrones encontrados]
- [recomendación 2]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
¿Guardar como .md en ~/VIRAL/research/? (responde "sí" para guardar)
```

### Para intent CREATORS:

```
🔍 TIKTOK RESEARCH — CREATORS | Método: [MÉTODO] | Completeness: [HIGH/MEDIUM/LOW]
Target: [brand] | Query: "[query]"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Creadores Encontrados

| # | Handle | Avg Views | Likes Totales | Nicho | Formato | Paid? | Link Perfil |
|---|--------|-----------|---------------|-------|---------|-------|------------|
| 1 | @handle | ~50K | 120K | skincare | Talking Head | Sí | [ver](URL) |
| ... |

## Análisis
**Perfil del creador que performa:** [descripción]
**Commonalities:** [qué tienen en común]
**¿Vale contactar alguno para SkinQueens?** [recomendación]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
¿Guardar como .md en ~/VIRAL/research/? (responde "sí" para guardar)
```

### Para intent SOUNDS:

```
🔍 TIKTOK RESEARCH — SOUNDS | Método: [MÉTODO] | Completeness: [MEDIUM/LOW]
Nota: datos de audio sin autenticación son aproximados.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Sonidos en Tendencia

| # | Sonido | Artista/Original | Usado en | Vibe | Ejemplo de video |
|---|--------|-----------------|----------|------|-----------------|
| 1 | "nombre del audio" | @creator | videos de skincare | aspiracional | [ver](URL) |
| ... |

## Recomendación para SkinQueens:
[qué sonido usar y por qué]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Para intent COMMENTS:

```
🔍 TIKTOK RESEARCH — COMMENTS | Método: [MÉTODO] | Completeness: [HIGH/LOW]
Nota: sin autenticación solo se ve el primer batch de comentarios del DOM.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Comentarios más comunes

**Cluster 1: [Tema]** (X% del total)
> "[cita representativa]"
> "[cita representativa]"

**Cluster 2: [Tema]**
> ...

## Sentimiento General: [POSITIVO / MIXTO / NEGATIVO]
## Lo que el público quiere saber: [insight]
## Hook para SkinQueens basado en esto: [recomendación]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## PASO 5 — Guardar .md (solo si el usuario confirma)

Si el usuario responde "sí", "si", "save", "guardar":

```bash
# Generar nombre de archivo
DATE=$(date +%Y-%m-%d)
TARGET=$(echo "[target]" | tr '[:upper:]' '[:lower:]' | sed 's/[@# ]/-/g')
OUTPUT_FILE="$HOME/VIRAL/research/tiktok-${TARGET}-${DATE}.md"

# El contenido del .md es el output completo del PASO 4
# Escribir con Write tool
```

Confirmar: `✅ Guardado en ~/VIRAL/research/tiktok-[target]-[fecha].md`

---

## PASO 6 — Reportar completeness

Al final de cada research, mostrar:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 DATA QUALITY REPORT
Método principal: [MÉTODO USADO]
Completeness: HIGH / MEDIUM / LOW

HIGH  = cookies de Chrome activas → acceso total
MEDIUM = WebSearch + DOM → métricas parciales (likes sin views en algunos)
LOW   = oEmbed + YouTube → solo títulos y proxy de viralidad

Para mejorar a HIGH: abrir TikTok en Chrome (tiktok.com), hacer login,
y volver a correr el skill. Los cookies se importarán automáticamente.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Limitaciones conocidas

| Intent | Limitación | Workaround |
|--------|-----------|-----------|
| SOUNDS | TikTok no expone datos de audio sin auth | Buscar via WebSearch + YouTube, datos aproximados |
| COMMENTS | Solo primer batch sin cookies | Abrir Chrome con TikTok logueado para completeness HIGH |
| VIDEOS (cuenta privada) | DOM no carga contenido | Solo oEmbed + YouTube reposts disponibles |
| TRENDS (tiempo real) | Sin auth no accede a Discover | WebSearch es suficiente para tendencias recientes |

---

## Ejemplos de uso

```bash
# Research de competidores
/tiktok-research busca los videos más virales de OnSkin en TikTok

# Research de creadores UGC
/tiktok-research cuáles son los creadores UGC que más views tienen para la marca SkinQueens

# Research de comentarios
/tiktok-research cuáles son los comentarios más comunes en los videos de Lóvi

# Research de sonidos
/tiktok-research qué sonidos están en tendencia para videos de skincare AI app en TikTok

# Research de hashtags
/tiktok-research qué hashtags usa @onskin.app en sus videos más virales

# Research combinado
/tiktok-research analiza todo el contenido de OnSkin: videos virales, formatos, hooks, y creadores que los usan
```
