#!/usr/bin/env python3
"""Busca candidatos (dominios de negocios) para un rubro + ciudad usando la búsqueda
HTML de DuckDuckGo (no requiere API key). Filtra dominios repetidos y agregadores
conocidos (redes sociales, directorios, sitios institucionales) que no son "el sitio
propio del negocio".
"""

import json
import re
import sys
from urllib.parse import quote_plus, unquote, urlparse

import httpx

AGREGADORES = [
    "facebook.com", "instagram.com", "twitter.com", "x.com", "tiktok.com",
    "paginasamarillas.com.co", "linkedin.com", "youtube.com", "wikipedia.org",
    "tripadvisor.", "google.com", "maps.google.com", "wa.me", "whatsapp.com",
    "mercadolibre.com", "rappi.com", "restaurantguru.com", "minube.",
    "wanderlog.com", "reservandonos.com", "opentable.com", "booking.com",
    "eltiempo.com", "vanguardia.com", "elespectador.com",
    # Directorios/agregadores de negocios (no son "el sitio propio")
    "directorio", "empresite", "locanto", "infoisinfo", "doctoralia",
    "topdoctors", "medicosdoc", "nexdu.com", "findglocal", "horariosytiendas",
    "lawzana", "legal500", "legalrank", "ramajudicial.gov.co", "ciencuadras",
    "mejorescolombia", "digitalescolombia", "edurank", "gomechanics",
    "pitts.app", "redtalleres", "redeurotaller", "todoslostalleres",
    "mecanicos.com.co", "buscovets", "colegiode", "federacion",
    "aulapro.co", "tecnicolaboral", "losestudiantes", "universoptimum",
    "facmedicine",
    # Dominios institucionales / gubernamentales / educativos
    ".gov.co", ".edu.co",
]

UDDG_RE = re.compile(r"uddg=([^&\"]+)")


def es_agregador(host: str) -> bool:
    return any(dominio in host for dominio in AGREGADORES)


def buscar_candidatos(termino: str, ciudad: str | None = None, limite: int = 20) -> list[str]:
    query = f"{termino} {ciudad}" if ciudad else termino
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    with httpx.Client(headers={"User-Agent": "Mozilla/5.0 (compatible; scrape-webs/1.0; +prospeccion-la22)"}) as client:
        res = client.get(url, timeout=15)
    res.raise_for_status()
    html = res.text

    vistos: set[str] = set()
    candidatos: list[str] = []
    for m in UDDG_RE.finditer(html):
        try:
            parsed = urlparse(unquote(m.group(1)))
        except ValueError:
            continue
        if not parsed.hostname:
            continue
        host = parsed.hostname.removeprefix("www.")
        if es_agregador(host) or host in vistos:
            continue
        vistos.add(host)
        candidatos.append(f"{parsed.scheme}://{parsed.hostname}")
        if len(candidatos) >= limite:
            break
    return candidatos


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print('Uso: uv run find_candidates.py "<termino>" ["<ciudad>"]', file=sys.stderr)
        sys.exit(1)
    termino = sys.argv[1]
    ciudad = sys.argv[2] if len(sys.argv) > 2 else None
    print(json.dumps(buscar_candidatos(termino, ciudad), indent=2, ensure_ascii=False))
