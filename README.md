# Agente Social Analysis (Local)

Este proyecto genera un reporte de análisis de redes sociales en formato:
- `outputs/report.json`
- `outputs/report.md`

El reporte está diseñado para que otro software lo consuma y construya una página.

## Inputs
- Platform (por ahora: Instagram / TikTok / YouTube / Facebook — empezamos con 1)
- Handle o URL del perfil
- (Opcional) Competidores (lista de handles/URLs)
- (Opcional) Rango de posts a analizar (ej. últimos 12)

## Output
- `outputs/raw.json` → datos crudos obtenidos (públicos)
- `outputs/report.json` → reporte estructurado (schema estable)
- `outputs/report.md` → reporte Markdown con imágenes por URL

## Nota sobre imágenes
MVP: usamos URLs públicas (no CDN propio).
Luego: opción para descargar imágenes a `assets/` o subir a CDN.

## Estado
MVP local: análisis con datos públicos + reporte estable.
