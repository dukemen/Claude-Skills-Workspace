---
name: scrape-leads
description: Use when a scrape-webs run produced a list of outdated-website leads and the next step is extracting their email/WhatsApp contact info and preparing a cold-email import for Instantly. Also use to re-enrich a lead list that's missing contact data.
---

# scrape-leads

## Overview

Toma la salida de [[scrape-webs]] (lista de sitios desactualizados) y la enriquece
con datos de contacto (email, WhatsApp, teléfono) extraídos del propio sitio del
negocio. Con eso arma el CSV listo para importar una campaña de cold email en
Instantly.

No usa APIs de pago — extrae contacto por scraping directo del HTML (enlaces
`mailto:`, `tel:`, `wa.me`), sin servicios de enriquecimiento de terceros.

## Cuándo usar

- Ya corriste `scrape-webs` y tenés la hoja de Drive con sitios desactualizados,
  y necesitás sus datos de contacto para armar una campaña.
- La hoja ya tiene columnas Email/WhatsApp/Teléfono pero quedaron vacías o
  desactualizadas y hay que re-correr el enriquecimiento.
- Vas a lanzar una campaña de outreach por email (Instantly) sobre estos leads.

No usar para encontrar los sitios en sí — eso es responsabilidad de `scrape-webs`.

## Quick Reference

| Script | Qué hace |
|---|---|
| `scripts/extract_contact.py <url>` | Visita el sitio (home + rutas de contacto comunes) y devuelve email/WhatsApp/teléfono encontrados |
| `scripts/sync_contacts_csv.py <hoja.csv> <contactos.json>` | Mezcla contacto extraído en el CSV de "Sitios web desactualizados - Colombia" (upsert por URL) |
| `scripts/build_instantly_csv.py <leads.json>` | Convierte una lista de leads enriquecidos (JSON) al CSV que espera Instantly |
| `scripts/sync_instantly_csv.py <instantly.csv> <leads.json>` | Mezcla leads nuevos en el CSV de "Leads para Instantly - Colombia" (upsert por email) |

Ejecutar siempre con `uv run` desde la raíz del workspace (`Claude-Skills-Workspace/`),
que resuelve `httpx`/`beautifulsoup4` desde `pyproject.toml` sin activar venv a mano.

## Flujo típico

Ambas hojas viven en la carpeta de Drive `1n_oFh5VPnxuLPYUUAOsL9WK0ZwZxgPUh`. La API
de Drive no permite reemplazar contenido in situ, así que cada sync es
**buscar → descargar → mezclar → trash del viejo → crear uno nuevo con el mismo
título** — y como el fileId cambia en cada sync, **nunca hardcodearlo**: resolverlo
por título con `search_files` justo antes de usarlo.

1. `search_files` por `title = 'Sitios web desactualizados - Colombia' and
   parentId = '1n_oFh5VPnxuLPYUUAOsL9WK0ZwZxgPUh'`, bajar esa hoja como CSV con
   `download_file_content` y quedarte con las filas sin contacto (o todas, si vas
   a re-chequear).
2. Por cada lead, correr `extraer_contacto(url)` (importable desde
   `extract_contact.py`) para obtener `emails`/`whatsapps`/`telefonos`.
3. Mezclar con `sync_contacts_csv.py` (upsert por URL — **el contacto nuevo
   siempre pisa** el viejo) y volver a subir con `create_file` (mismo título,
   mismo `parentId`) + `trash_file` sobre el fileId del paso 1.
4. Generar el CSV para Instantly con `construir_csv_instantly(leads)` — **solo
   incluye leads con email**; los que solo tienen WhatsApp/teléfono quedan fuera
   porque Instantly es una plataforma de cold email, no de WhatsApp.
5. `search_files` por `title = 'Leads para Instantly - Colombia' and parentId =
   '1n_oFh5VPnxuLPYUUAOsL9WK0ZwZxgPUh'`, descargar, mezclar con
   `sync_instantly_csv.py` y subir con el mismo patrón create_file + trash_file.

Esto se hace apenas termina de correr el enriquecimiento — no esperar a que el
usuario lo pida.

```bash
uv run .claude/skills/scrape-leads/scripts/extract_contact.py "https://ejemplo.com"
uv run .claude/skills/scrape-leads/scripts/sync_contacts_csv.py hoja-actual.csv contactos.json > hoja-nueva.csv
uv run .claude/skills/scrape-leads/scripts/build_instantly_csv.py leads-enriquecidos.json > para-instantly.csv
uv run .claude/skills/scrape-leads/scripts/sync_instantly_csv.py instantly-actual.csv leads-enriquecidos.json > instantly-nuevo.csv
```

## Cómo extrae los datos

Prioriza atributos estructurados del HTML (mucho más confiables que buscar
patrones en texto libre):

1. `mailto:` → email
2. `href="tel:..."` → teléfono
3. `wa.me/<numero>` o `api.whatsapp.com/send?phone=<numero>` → WhatsApp

Si no hay atributos estructurados, cae a un regex de texto libre (emails,
celulares colombianos `3XXXXXXXXX`), pero **descarta el hallazgo si aparece más
de 5 veces en una sola página** — eso casi siempre es ruido (scripts de
analytics, hashes, IDs), no contacto real.

También filtra números placeholder de plantillas sin editar: `5555551212`,
`1234567890`, `0000000000`, o cualquier número con 9+ de sus 10 dígitos
repetidos (`3333333333`, etc.) — muy común en sitios que nunca actualizaron el
template de contacto, que es justo el tipo de sitio que este flujo encuentra.

## Formato del CSV para Instantly

Columnas: `email, company, website, city, category, priority_score, signals`.
`company` se deriva del dominio (sin `www.`). Las columnas además de `email` son
variables personalizables en la plantilla de Instantly (`{{company}}`,
`{{city}}`, etc.) para dar contexto específico en el primer correo — por
ejemplo, mencionar la ciudad y el rubro del negocio.

## Common Mistakes

- Enviar por Instantly datos de WhatsApp — Instantly es cold email, esos leads
  van a un canal aparte (WhatsApp Business, envío manual).
- No revisar manualmente los emails "raros" antes de la campaña (ej. un dominio
  de email que no coincide con el dominio del sitio, como
  `james@colombiavisas.com` para un sitio de `abogadosmedellin.com`) — puede ser
  legítimo (persona real con dominio propio) o resto de una plantilla mal
  editada; verificar antes de enviar en volumen.
- Confiar en el primer teléfono/email libre sin filtrar ruido — por eso el
  script prioriza `mailto:`/`tel:`/`wa.me` y descarta patrones que aparecen
  demasiadas veces en una página.
