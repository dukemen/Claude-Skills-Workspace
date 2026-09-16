#!/usr/bin/env python3
"""Mezcla leads nuevos (con email) en el CSV actual de "Leads para Instantly -
Colombia" — upsert por email, siempre pisa con el dato más reciente. Solo
incluye leads con email (Instantly es cold email, no WhatsApp).

Entrada:
  - CSV actual de la hoja de Instantly (columnas: email,company,website,city,
    category,priority_score,signals)
  - JSON con leads enriquecidos: [{email, url, ciudad, rubro, puntaje,
    señales}, ...] — mismo formato que espera build_instantly_csv.py

Uso: uv run sync_instantly_csv.py <instantly-actual.csv> <leads-enriquecidos.json> > instantly-nuevo.csv
"""

import csv
import io
import json
import sys
from urllib.parse import urlparse

COLUMNAS = ["email", "company", "website", "city", "category", "priority_score", "signals"]


def _dominio_como_empresa(url: str) -> str:
    host = urlparse(url).hostname or url
    return host.removeprefix("www.")


def _leer_csv(ruta: str) -> dict[str, dict]:
    try:
        with open(ruta, encoding="utf-8-sig", newline="") as f:
            return {fila["email"]: fila for fila in csv.DictReader(f) if fila.get("email")}
    except FileNotFoundError:
        return {}


def mezclar(csv_actual: str, leads_json: str) -> str:
    filas = _leer_csv(csv_actual)

    with open(leads_json, encoding="utf-8-sig") as f:
        leads = json.load(f)

    sin_email = 0
    for l in leads:
        if not l.get("email"):
            sin_email += 1
            continue
        señales = l.get("señales", "")
        if isinstance(señales, list):
            señales = " | ".join(señales)
        filas[l["email"]] = {
            "email": l["email"],
            "company": _dominio_como_empresa(l["url"]),
            "website": l["url"],
            "city": l.get("ciudad", ""),
            "category": l.get("rubro", ""),
            "priority_score": l.get("puntaje", ""),
            "signals": señales,
        }

    ordenadas = sorted(filas.values(), key=lambda f: int(f["priority_score"] or 0), reverse=True)

    salida = io.StringIO()
    writer = csv.DictWriter(salida, fieldnames=COLUMNAS)
    writer.writeheader()
    writer.writerows(ordenadas)

    if sin_email:
        print(f"Aviso: {sin_email} leads sin email quedaron fuera.", file=sys.stderr)

    return salida.getvalue()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3:
        print("Uso: uv run sync_instantly_csv.py <instantly-actual.csv> <leads-enriquecidos.json>", file=sys.stderr)
        sys.exit(1)
    print(mezclar(sys.argv[1], sys.argv[2]), end="")
