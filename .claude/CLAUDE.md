# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Claude-Skills-Workspace

Workspace de skills reutilizables de Kevin (IA SIN FRONTERAS / PidiendoIA), independiente
de cualquier proyecto cliente. No es un producto con build/deploy propio — cada skill en
`skills/<nombre>/` es autocontenida (`SKILL.md` en la raíz + `scripts/` si aplica).

## Skills

- **[scrape-webs](skills/scrape-webs/SKILL.md)** — encuentra negocios en Colombia (Bucaramanga
  primero, luego por ciudad: Bogotá, Medellín, Cali...) con sitios web desactualizados, para
  prospección de servicios de rediseño web.
- **[scrape-leads](skills/scrape-leads/SKILL.md)** — toma la salida de `scrape-webs` y extrae
  contacto (email/WhatsApp/teléfono) de cada sitio, para armar la campaña de cold email en
  Instantly. Skill separado porque es una responsabilidad distinta (enriquecimiento de contacto
  vs. detección de sitios desactualizados).

## Convenciones

- Cada skill nueva: carpeta propia en `skills/<nombre>/`, con `SKILL.md` en la raíz y
  `scripts/` solo si tiene herramientas ejecutables reutilizables.
- **Python + `uv`** (no Node) — coincide con el stack habitual de Kevin. Un solo
  `pyproject.toml` en la raíz del workspace, compartido por todos los skills; correr scripts
  con `uv run .claude/skills/<skill>/scripts/<archivo>.py` desde la raíz del workspace.
- Scripts en `snake_case.py`, sin frameworks — `httpx` para requests, `beautifulsoup4` solo
  si hace falta parsear DOM (los heurísticos de texto/regex ya cubren la mayoría de casos).
- Nueva dependencia: `uv add <paquete>` desde la raíz (actualiza `pyproject.toml` +
  `uv.lock`). Sin dependencias sin justificación explícita.
- Si un sitio bloquea o renderiza contenido vía JavaScript (el fetch plano trae HTML vacío),
  agregar `playwright` puntualmente para ese caso — no adoptar un servicio de scraping de pago
  (Apify u otro) para el volumen actual de este workspace.
- Comentarios de código y mensajes de error en español, identificadores en inglés técnico.
- En Windows, forzar `sys.stdout.reconfigure(encoding="utf-8")` al inicio de cualquier script
  que imprima JSON/texto con tildes o emoji — la consola por defecto no es UTF-8 y corrompe
  caracteres especiales silenciosamente (no truena, solo se ve mal).

## Comandos

Todo se corre desde la raíz del workspace (`Claude-Skills-Workspace/`, un nivel arriba de
este archivo). No hay suite de tests ni linter configurados; se verifica corriendo el script
contra una entrada real.

```bash
uv sync                                   # instala httpx + beautifulsoup4 (Python >=3.13)
uv run .claude/skills/scrape-webs/scripts/run.py "restaurantes" "Bucaramanga" > out.json
uv run .claude/skills/scrape-webs/scripts/check_outdated.py "http://ejemplo.com.co"   # un solo sitio
uv run .claude/skills/scrape-leads/scripts/extract_contact.py "https://ejemplo.com"
```

`run.py` emite el JSON por stdout y el progreso/ranking por stderr — redirigir solo stdout.
Los `sync_*_csv.py` y `build_instantly_csv.py` leen archivos locales y emiten el CSV nuevo por stdout.

## Arquitectura (pipeline entre skills)

```
find_candidates → check_outdated → run.py ─┐   (scrape-webs: JSON de sitios con puntaje)
                                           ▼
                     sync_sites_csv.py  →  hoja Drive "Sitios web desactualizados - Colombia"
                                           ▼
extract_contact  →  sync_contacts_csv.py   (scrape-leads: mismo CSV, upsert por URL)
                 →  build_instantly_csv / sync_instantly_csv → hoja "Leads para Instantly - Colombia"
```

- Los scripts son **stdin/stdout puros sobre archivos locales**; no hablan con Drive. La
  sincronización con Drive la hace el agente con las tools del conector (buscar → descargar
  CSV → mezclar con el script → `create_file` + `trash_file`), tal como describe cada `SKILL.md`.
  Los SKILL.md son la fuente de verdad del flujo — léelos antes de tocar un script.
- Los scripts de un mismo skill se importan entre sí por nombre de módulo (`from check_outdated
  import analizar_sitio` en `run.py`), no como paquete: funcionan porque `uv run` pone el
  directorio del script en `sys.path`. No importar entre skills distintos.
- Las hojas usan upsert con dueño de columnas: `scrape-webs` es dueño de
  Prioridad/Ciudad/Rubro/Puntaje/Señales, `scrape-leads` de Email/WhatsApp/Telefono. Cada sync
  pisa solo sus columnas; `COLUMNAS` está duplicado en los `sync_*` — si cambia el esquema,
  actualizar todos.
- El fileId de las hojas de Drive cambia en cada sync (create+trash): resolver por título, nunca hardcodear.

### Git Worktree Workflow

Los worktrees dan a cada agente un directorio de trabajo aislado que comparte el mismo
historial de git. Usarlos solo cuando un fan-out de subagentes va a editar archivos en
paralelo: lanzar cada subagente con `isolation: "worktree"`. Un solo agente, o agentes
que solo leen, trabajan en la carpeta principal.

- Cada worktree necesita su propio `uv sync` (`.venv` no se comparte).
- Una rama solo puede estar checked out en un worktree a la vez.
- Los cambios de cada subagente quedan en su rama; revisar y hacer merge a `main` a mano.

## Notas

- `.claude/agent-memory/` y `.claude/rules/` existen vacíos; el global de Kevin ahora nombra
  la carpeta `agents/`. Renombrar solo si se va a usar.
