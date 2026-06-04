# Standups — Daily Stand Ups TVA

Directorio de daily stand ups generados por el skill `/tva-daily-standup`.

## Convención de nombres
`tva-standup-YYYY-MM-DD.md`

## Estructura de cada archivo
- COMPLETADO
- POSTS DEL DÍA (métricas SideShift)
- EN PROGRESO
- BLOQUEADO
- PARA MAÑANA
- DISTRIBUCIÓN DEL TIEMPO

## Sync al agente VIRAL
Cada standup generado se sincroniza automáticamente al VPS:
`/root/culver-os/viral-bot/knowledge/standups/`

El agente VIRAL (viral_bot.py) lee el standup más reciente y lo inyecta
en su contexto y en el morning report diario. Comando Telegram: `/standup`
