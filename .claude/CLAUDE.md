# CLAUDE.md — Claude-Skills-Workspace

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
