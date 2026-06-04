# imessage-report — Reporte de Creadores desde iMessage

Skill para generar un reporte de estado de todos los creadores en los grupos de iMessage de SkinQueens (o cualquier cliente). Analiza los chats, extrae el estado actual de cada creador y clasifica en categorías accionables.

## Cuándo invocar este skill

Invocar como PRIMERA acción cuando Rubén mencione:
- "reporte de creadores", "estado de los creadores", "cómo están los creadores"
- "cuántos están publicando", "cuántos en warm-up", "cuántos en onboarding"
- "reporte de iMessage", "analiza los grupos", "revisa los chats"
- "cuántos creadores tengo activos", "pipeline de creadores"
- "reporte de SkinQueens", "health check de creadores"
- "cuántos van a publicar cuando terminen el warm-up"

---

## Fuente de datos

**iMessage DB:** `~/Library/Messages/chat.db` (SQLite)  
**Tablas clave:** `chat`, `message`, `chat_message_join`  
**Nota sobre formato:** Los mensajes recientes de iMessage usan `attributedBody` (binario) en lugar de `text`. Hay que extraer con `hex()` + `xxd -r -p` + `strings`.

---

## Paso 1 — Encontrar todos los grupos del cliente

```bash
# Buscar grupos por nombre del cliente (ej: SkinQueens)
sqlite3 ~/Library/Messages/chat.db "
SELECT ROWID, chat_identifier, display_name, style 
FROM chat 
WHERE display_name LIKE '%skin%' 
   OR display_name LIKE '%Skin%' 
   OR display_name LIKE '%queen%' 
   OR display_name LIKE '%Queen%'
ORDER BY ROWID DESC;"
```

Adaptar el `WHERE` al nombre del cliente activo.

---

## Paso 2 — Obtener conteo de mensajes por grupo

```bash
sqlite3 ~/Library/Messages/chat.db "
SELECT c.ROWID, c.display_name, count(m.ROWID) as msg_count,
  max(datetime(m.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime')) as last_msg
FROM chat c
JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
JOIN message m ON cmj.message_id = m.ROWID
WHERE (c.display_name LIKE '%skin%' OR c.display_name LIKE '%Skin%' 
    OR c.display_name LIKE '%queen%' OR c.display_name LIKE '%Queen%')
GROUP BY c.ROWID
ORDER BY c.ROWID DESC;"
```

Los grupos con `msg_count = 0` (0 mensajes en `chat_message_join`) son grupos vacíos — el chat existe pero no hay conversación registrada en este dispositivo.

---

## Paso 3 — Extraer mensajes de texto (formato clásico)

Para grupos con mensajes de texto normal (`text IS NOT NULL`):

```bash
sqlite3 ~/Library/Messages/chat.db "
SELECT 
  c.display_name,
  m.text,
  datetime(m.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime') as msg_date,
  m.is_from_me
FROM chat c
JOIN chat_message_join cmj ON c.ROWID = cmj.chat_id
JOIN message m ON cmj.message_id = m.ROWID
WHERE (c.display_name LIKE '%skin%' OR c.display_name LIKE '%Skin%' 
    OR c.display_name LIKE '%queen%' OR c.display_name LIKE '%Queen%')
  AND m.text IS NOT NULL AND m.text != ''
ORDER BY c.ROWID DESC, m.date DESC
LIMIT 500;"
```

---

## Paso 4 — Extraer mensajes de attributedBody (formato nuevo)

Los mensajes recientes de iMessage almacenan el texto en un blob binario (`attributedBody`). Para extraerlos:

```bash
# Por chat ID específico:
sqlite3 ~/Library/Messages/chat.db "
SELECT m.is_from_me,
  datetime(m.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime') as msg_date,
  hex(m.attributedBody)
FROM message m 
JOIN chat_message_join cmj ON m.ROWID = cmj.message_id 
WHERE cmj.chat_id = CHAT_ID
ORDER BY m.date DESC LIMIT 8;" | while IFS='|' read from_me date hexbody; do
  text=$(echo "$hexbody" | xxd -r -p 2>/dev/null | strings | \
    grep -v 'NSAttributedString\|NSObject\|NSString\|streamtyped\|NSMutable\|NSDictionary\|__kIM' | \
    grep -E '^.{5,}$' | head -3 | tr '\n' ' | ')
  echo "[from_me=$from_me][$date] $text"
done
```

**Script en loop para múltiples grupos:**

```bash
for id in ID1 ID2 ID3; do
  name=$(sqlite3 ~/Library/Messages/chat.db "SELECT display_name FROM chat WHERE ROWID=$id;" 2>/dev/null)
  echo "=== $name ($id) ==="
  sqlite3 ~/Library/Messages/chat.db "
  SELECT m.is_from_me,
    datetime(m.date/1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime') as msg_date,
    hex(m.attributedBody)
  FROM message m 
  JOIN chat_message_join cmj ON m.ROWID = cmj.message_id 
  WHERE cmj.chat_id = $id
  ORDER BY m.date DESC LIMIT 5;" 2>/dev/null | while IFS='|' read from_me date hexbody; do
    text=$(echo "$hexbody" | xxd -r -p 2>/dev/null | strings | \
      grep -v 'NSAttributedString\|NSObject\|NSString\|streamtyped\|NSMutable\|NSDictionary\|__kIM' | \
      grep -E '^.{5,}$' | head -3 | tr '\n' ' | ')
    echo "  [from_me=$from_me][$date] $text"
  done
done 2>/dev/null
```

---

## Paso 5 — Clasificar creadores

Leer los mensajes y clasificar cada creador en una de estas categorías:

### Categoría A — PUBLICANDO ACTIVAMENTE
**Señales:** enviaron links de TikTok/IG hoy, "Draft approved ✅ → Post now", posteando múltiples veces, enviando links para interacción.

Palabras clave: `tiktok.com/t/`, `instagram.com/reel/`, "posting now", "I am posting", "just posted", "Draft approved", "Post this now"

### Categoría B — APROBANDO DRAFTS / EMPEZANDO A PUBLICAR
**Señales:** tienen drafts aprobados, se les dijo "start posting tomorrow/Monday", warm-up recién completado hoy.

Palabras clave: "Draft approved ✅", "Both drafts are approved", "start posting tomorrow", "warm-up done", "account is warmed up", "remember we should start posting"

### Categoría C — WARM-UP EN PROGRESO
**Señales:** preguntando sobre el proceso de warm-up, confirmando que están haciendo warm-up, cuentas recién creadas, esperando días para publicar.

Palabras clave: "warm up", "warming up", "new TikTok", "new Instagram", "new accounts", "algorithm", "40 minutes", "20 minutes per account", "3 days"

### Categoría D — OUTREACH / ONBOARDING
**Señales:** primer contacto hoy, recibiendo info del programa, sin confirmar participación, negociando términos, no han creado cuentas nuevas.

Palabras clave: "Will you join", "First steps", "Compensation", "Hi [name]! How are you?", "I'll send you information", grupos con muy pocos mensajes (< 5)

### Categoría E — ABANDONANDO
**Señales:** quieren salir, preguntan cómo remover la campaña, rechazan condiciones terminantemente.

Palabras clave: "remove the campaign", "not interested", "remove from SideShift", "cannot move forward"

### Categoría F — GRUPOS VACÍOS / SIN RESPUESTA
`chat_message_join` tiene 0 mensajes para ese `chat_id`.

---

## Paso 6 — Identificar duplicados y grupos internos

- **Duplicados:** misma creadora con dos grupos (buscar mismo nombre). Contar solo el más activo (mayor `msg_count` o `last_msg` más reciente).
- **Grupo interno TVA:** grupo sin creador externo (ej: "SkinQueens - TVA"). Excluir del conteo.
- **Chats de coordinación:** grupos con solo mensajes `from_me=0` del mismo Tomas/coordinador sin respuesta del creador → son outreach.

---

## Formato del reporte final

```markdown
## Reporte de Creadores [Cliente] — iMessage Groups
**Fecha:** [HOY] | **Grupos analizados:** [N] chats ([M] creadores únicos, [X] duplicados, [Y] grupo interno)

### Resumen Ejecutivo
| Categoría | Cantidad |
|-----------|----------|
| Total creadores únicos en grupos | N |
| Publicando activamente | N |
| Aprobando drafts / empezando | N |
| Warm-up en progreso | N |
| Outreach / onboarding | N |
| Abandonando campaña | N |
| Sin mensajes / vacíos | N |

### PUBLICANDO ACTIVAMENTE (N)
| Creador | Evidencia |
...

### APROBANDO DRAFTS / EMPEZANDO (N)
| Creador | Cuándo publica |
...

### WARM-UP EN PROGRESO (N)
| Creador | Estado warm-up | Proyección publicación |
...

### EN OUTREACH / ONBOARDING (N)
| Creador | Status |
...

### ABANDONANDO (N)
| Creador | Status |
...

### SIN MENSAJES — GRUPOS VACÍOS (N)
Lista de nombres

### Proyección: cuando todos los warm-ups estén completos
Activos HOY + Empezando este finde + Warm-up completando esta semana = TOTAL PROYECTADO
```

---

## Datos del cliente activo (SkinQueens)

- **Nombre en grupos:** "SkinQueens", "Skin Queens", "skin queens", "skinqueen"
- **WHERE clause:** `LIKE '%skin%' OR LIKE '%queen%'` (case insensitive)
- **Warm-up estándar:** 3 días mínimo antes de publicar
- **Cadencia target:** 1 video/día = 2 posts/día (TikTok + IG)
- **Señal de publicación confirmada:** creador envía `tiktok.com/t/` o `instagram.com/reel/` link

---

## Notas técnicas importantes

1. **`text IS NULL` no significa sin mensaje** — puede tener `attributedBody`. Verificar ambos.
2. **`from_me=0` puede ser del equipo** — si el texto dice "Tomas from Skin Queens here", es del coordinador, no del creador.
3. **`chat_message_join` vacío (0 rows)** = grupo fantasma, no contar en ninguna categoría activa.
4. **Reacciones (tapbacks)** — aparecen como mensajes pero con texto tipo "Liked "texto"". Son señal de engagement, no de acción.
5. **La DB requiere permiso de Full Disk Access** en macOS — si falla, pedir al usuario que lo otorgue en System Settings → Privacy & Security.
