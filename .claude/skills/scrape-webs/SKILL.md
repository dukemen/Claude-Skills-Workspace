---
name: scrape-webs
description: Use when prospecting for web-development clients and needing to find businesses in Colombia whose website is outdated — no HTTPS, not mobile-responsive, table-based layouts, Flash, old jQuery, stale copyright years, or the site is down entirely. Starts scoped to Bucaramanga, then expands nationally.
---

# scrape-webs

## Overview

Encuentra negocios con sitios web desactualizados (candidatos a servicio de rediseño),
primero en Bucaramanga y luego a nivel nacional en Colombia. Combina una búsqueda de
candidatos por rubro/ciudad con un analizador heurístico que puntúa qué tan
desactualizado luce cada sitio.

No usa APIs de pago ni claves — la búsqueda de candidatos usa DuckDuckGo HTML
(`html.duckduckgo.com`), sin scraping de Google (evita bloqueos por ToS/captcha).

## Cuándo usar

- Prospección B2B: "necesito una lista de restaurantes en Bucaramanga con sitios viejos".
- Expansión de mercado: repetir el mismo rubro cambiando la ciudad o usando "Colombia"
  para barrer a nivel nacional.
- Cualificar leads antes de una campaña de outreach (WhatsApp, email, llamada en frío).

No usar para negocios que no tienen sitio web propio (el script no los encuentra;
esos son leads de un tipo distinto, sin sitio que analizar).

## Quick Reference

| Script | Qué hace |
|---|---|
| `scripts/find_candidates.py "<rubro>" "<ciudad>"` | Devuelve dominios únicos candidatos, filtrando redes sociales/directorios/medios |
| `scripts/check_outdated.py "<url>"` | Analiza un sitio y devuelve puntaje 0-100 + señales detectadas |
| `scripts/run.py "<rubro>" "<ciudad>"` | Orquesta ambos: busca candidatos, los analiza todos y los ordena de más a menos desactualizado |
| `scripts/sync_sites_csv.py <hoja.csv> <resultado.json> "<ciudad>" "<rubro>"` | Mezcla un resultado de `run.py` en el CSV de la hoja de Drive (upsert por URL) |

Ejecutar siempre con `uv run` desde la raíz del workspace (`Claude-Skills-Workspace/`),
que resuelve `httpx`/`beautifulsoup4` desde `pyproject.toml` sin activar venv a mano.

## Flujo típico

```bash
# Bucaramanga primero
uv run .claude/skills/scrape-webs/scripts/run.py "restaurantes" "Bucaramanga" > resultados-restaurantes-bga.json

# Expandir ciudad por ciudad (no usar "Colombia" como ciudad — ver limitación abajo)
uv run .claude/skills/scrape-webs/scripts/run.py "restaurantes" "Bogota" > resultados-restaurantes-bogota.json

# Analizar un sitio puntual que ya tienes de otra fuente
uv run .claude/skills/scrape-webs/scripts/check_outdated.py "http://ejemplo.com.co"
```

El JSON de `run.py` va a stdout (para redirigir a archivo); el progreso y el ranking
final legible van a stderr (se ven en pantalla aunque redirijas stdout).

## Actualización automática de la hoja de Drive

Al terminar cada corrida de `run.py`, el resultado se sincroniza con la hoja de Google
Sheets **"Sitios web desactualizados - Colombia"** en la carpeta de Drive
`1n_oFh5VPnxuLPYUUAOsL9WK0ZwZxgPUh`. La API de Drive no soporta reemplazar el
contenido de un archivo existente in-situ, así que el patrón es
**buscar → descargar → mezclar → trash del viejo → crear uno nuevo con el mismo
título** — y como `create_file`/`trash_file` cambian el fileId en cada sync, **nunca
hardcodear el fileId**: siempre resolverlo por título justo antes de usarlo.

1. `search_files` con `title = 'Sitios web desactualizados - Colombia' and parentId
   = '1n_oFh5VPnxuLPYUUAOsL9WK0ZwZxgPUh'` para obtener el fileId actual (o
   `title contains` si el título exacto puede variar).
2. Descargar esa hoja como CSV con `download_file_content` (`exportMimeType:
   text/csv`) y guardarla en un archivo local.
3. Mezclar con `sync_sites_csv.py` (upsert por `Sitio web`/URL — **el run nuevo
   siempre pisa** puntaje/señales/prioridad de la fila existente; el contacto
   Email/WhatsApp/Telefono ya enriquecido por `scrape-leads` se conserva porque
   `run.py` no lo toca; puntaje 0 queda excluido, no son leads).
4. Subir el CSV mezclado con `create_file` (`title: "Sitios web desactualizados -
   Colombia"`, `parentId: 1n_oFh5VPnxuLPYUUAOsL9WK0ZwZxgPUh`, `contentMimeType:
   text/csv` — Drive lo convierte automático a Google Sheets).
5. `trash_file` sobre el fileId obtenido en el paso 1 (el viejo).

Esto se hace apenas termina de guardarse el resultado de cada corrida — no esperar a
que el usuario lo pida.

## Señales de desactualización (heurística, no exacta)

Puntaje 0-100, más alto = más desactualizado:

- Sin HTTPS (20 pts)
- Sin `<meta viewport>` → no responsive (20 pts)
- Etiquetas obsoletas: `<marquee>`, `<blink>`, `<font>`, `<frameset>`, `<applet>` (20 pts)
- Layout con 3+ `<table>` (15 pts)
- Referencias a Flash (`.swf`) (15 pts)
- Año de copyright con 4+ años de antigüedad (15 pts)
- jQuery 1.x/2.x (10 pts)
- Generado por FrontPage/Word/Dreamweaver (10 pts)
- Sitio inalcanzable (dominio caído, certificado vencido, timeout) → 90 pts automático,
  es en sí misma la señal más fuerte de un negocio que descuidó su presencia web

Es heurística de priorización para prospección, no un diagnóstico técnico certero —
revisar manualmente los top del ranking antes de contactar.

## Limitación conocida de la búsqueda

Buscar literalmente `"<rubro> Colombia"` para alcance nacional **no funciona bien**:
trae sobre todo marcas grandes/franquicias (Zara, Marval, Constructora Bolívar) y
sitios institucionales (universidades, `.gov.co`, `.edu.co`) — no son leads útiles.
Lo correcto es repetir la búsqueda **ciudad por ciudad** (Bogotá, Medellín, Cali,
Barranquilla, Cartagena...) en vez de usar "Colombia" como ubicación.

Además, para rubros genéricos ("restaurantes Bucaramanga"), DuckDuckGo suele rankear
directorios/agregadores (TripAdvisor, RestaurantGuru, prensa local) por encima de los
sitios propios de cada negocio. `find_candidates.py` ya filtra los dominios agregadores
conocidos (constante `AGREGADORES`), pero si aparecen resultados vacíos o pocos:

- Usar términos más específicos: nombre de barrio, tipo de comida, o el nombre del
  negocio si ya se conoce por otra fuente (Google Maps, cámara de comercio).
- Ampliar `limite` en `buscar_candidatos` si se necesitan más candidatos por corrida.
- Añadir dominios nuevos a la lista `AGREGADORES` en `find_candidates.py` si aparecen
  directorios no filtrados.

## Common Mistakes

- Correr `run.py` sin pausa entre requests → ya tiene 1.5s de pausa por sitio, no
  quitarla (evita saturar sitios pequeños o que DuckDuckGo bloquee por rate limit).
- Confundir puntaje alto con "sitio caído" — revisar el campo `señales` para saber si
  es inalcanzable o simplemente visualmente anticuado; el approach de venta es distinto.
- Tratar el ranking como definitivo sin abrir el sitio — el heurístico puede dar falsos
  positivos (p. ej. un sitio nuevo pero minimalista sin viewport explícito por error).
