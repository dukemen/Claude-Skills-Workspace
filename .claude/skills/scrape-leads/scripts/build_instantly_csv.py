#!/usr/bin/env python3
"""Convierte los leads enriquecidos (con email) al CSV que Instantly espera para
importar una campaña. Instantly identifica cada lead por email — los que no
tienen email no sirven para esta campaña (van a un canal de WhatsApp aparte).

Entrada esperada (JSON, un array): [{ email, url, ciudad, rubro, puntaje, señales }, ...]
Uso: uv run build_instantly_csv.py leads-enriquecidos.json > para-instantly.csv
"""

import csv
import io
import json
import sys
from urllib.parse import urlparse


def _dominio_como_empresa(url: str) -> str:
    host = urlparse(url).hostname or url
    return host.removeprefix("www.")


def construir_csv_instantly(leads: list[dict]) -> str:
    con_email = [l for l in leads if l.get("email")]
    salida = io.StringIO()
    writer = csv.writer(salida)
    writer.writerow(["email", "company", "website", "city", "category", "priority_score", "signals"])
    for l in con_email:
        señales = l.get("señales", "")
        if isinstance(señales, list):
            señales = " | ".join(señales)
        writer.writerow([
            l["email"],
            _dominio_como_empresa(l["url"]),
            l["url"],
            l.get("ciudad", ""),
            l.get("rubro", ""),
            l.get("puntaje", ""),
            señales,
        ])
    return salida.getvalue()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("Uso: uv run build_instantly_csv.py <leads-enriquecidos.json>", file=sys.stderr)
        sys.exit(1)
    with open(sys.argv[1], encoding="utf-8") as f:
        leads = json.load(f)
    print(construir_csv_instantly(leads))
    sin_email = len(leads) - len([l for l in leads if l.get("email")])
    if sin_email:
        print(f"Aviso: {sin_email} leads sin email quedaron fuera (no sirven para Instantly).", file=sys.stderr)
