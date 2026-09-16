#!/usr/bin/env python3
"""Analiza una URL y calcula un puntaje de "desactualización" (0-100, más alto =
más desactualizado) a partir de señales visibles en el HTML/HTTP. Heurístico, no
exacto: sirve para priorizar prospección, no como diagnóstico técnico definitivo.
"""

import json
import re
import sys
from datetime import datetime

import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; scrape-webs/1.0)"}


def _sin_https(url: str, html: str) -> bool:
    return url.startswith("http://")


def _sin_viewport(url: str, html: str) -> bool:
    return not re.search(r'<meta[^>]+name=["\']viewport["\']', html, re.I)


def _tablas_layout(url: str, html: str) -> bool:
    return len(re.findall(r"<table", html, re.I)) >= 3


def _tags_obsoletos(url: str, html: str) -> bool:
    return bool(re.search(r"<marquee|<blink|<font[\s>]|frameset|<applet", html, re.I))


def _flash(url: str, html: str) -> bool:
    return bool(re.search(r"\.swf\b|application/x-shockwave-flash", html, re.I))


def _jquery_antiguo(url: str, html: str) -> bool:
    return bool(re.search(r"jquery[.-](1\.[0-9]+|2\.[0-9]+)", html, re.I))


def _copyright_viejo(url: str, html: str) -> bool:
    m = re.search(r"(?:copyright|©|&copy;)[^0-9]{0,15}(20[0-2][0-9])", html, re.I)
    if not m:
        return False
    return datetime.now().year - int(m.group(1)) >= 4


def _generador_viejo(url: str, html: str) -> bool:
    return bool(re.search(r"generator[\"'\s:=]+(frontpage|microsoft word|dreamweaver)", html, re.I))


SEÑALES = [
    (_sin_https, 20, "No usa HTTPS"),
    (_sin_viewport, 20, "Sin meta viewport (no responsive / no mobile-friendly)"),
    (_tablas_layout, 15, "Layout basado en tablas (técnica de finales de los 2000)"),
    (_tags_obsoletos, 20, "Usa etiquetas HTML obsoletas (marquee/blink/font/frameset/applet)"),
    (_flash, 15, "Referencias a Adobe Flash"),
    (_jquery_antiguo, 10, "jQuery muy antiguo (1.x/2.x)"),
    (_copyright_viejo, 15, "Año de copyright con 4+ años de antigüedad"),
    (_generador_viejo, 10, "Generado por herramientas obsoletas (FrontPage/Word/Dreamweaver)"),
]


def analizar_sitio(url: str) -> dict:
    resultado = {"url": url, "alcanzable": False, "puntaje": 0, "señales": [], "error": None}
    try:
        with httpx.Client(follow_redirects=True, timeout=15, headers=HEADERS) as client:
            res = client.get(url)
        resultado["alcanzable"] = res.is_success
        resultado["statusHttp"] = res.status_code
        html = res.text
        url_final = str(res.url)

        for detectar, puntos, descripcion in SEÑALES:
            if detectar(url_final, html):
                resultado["señales"].append(descripcion)
                resultado["puntaje"] += puntos
        resultado["puntaje"] = min(100, resultado["puntaje"])
    except Exception as err:  # noqa: BLE001 — heurística, cualquier fallo de red es señal
        resultado["error"] = str(err)
        resultado["puntaje"] = 90
        resultado["señales"].append(f"No se pudo cargar ({err})")
    return resultado


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("Uso: uv run check_outdated.py <url>", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(analizar_sitio(sys.argv[1]), indent=2, ensure_ascii=False))
