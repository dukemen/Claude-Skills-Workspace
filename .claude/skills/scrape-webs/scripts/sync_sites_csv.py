#!/usr/bin/env python3
"""Mezcla el resultado de un run.py nuevo con el CSV actual de la hoja de Drive
"Sitios web desactualizados - Colombia" (upsert por URL — un re-chequeo más
reciente siempre pisa los datos viejos de puntaje/señales, pero conserva el
contacto ya enriquecido por scrape-leads si la fila ya existía).

Entrada:
  - CSV actual descargado de Drive (columnas: Prioridad,Ciudad,Rubro,Sitio web,
    Puntaje (0-100),Señales detectadas,Email,WhatsApp,Telefono)
  - JSON de salida de run.py (lista de {url, alcanzable, puntaje, señales, ...})
  - ciudad y rubro usados en esa corrida (run.py no los incluye en su salida)

Uso: uv run sync_sites_csv.py <hoja-actual.csv> <resultado-run.json> "<ciudad>" "<rubro>" > hoja-nueva.csv

Sitios con puntaje 0 (sin señales de desactualización) quedan fuera — no son leads.
"""

import csv
import io
import json
import sys

COLUMNAS = ["Prioridad", "Ciudad", "Rubro", "Sitio web", "Puntaje (0-100)",
            "Señales detectadas", "Email", "WhatsApp", "Telefono"]


def _prioridad(puntaje: int) -> str:
    if puntaje >= 30:
        return "🔴 Alta"
    if puntaje >= 15:
        return "🟡 Media"
    return "🟢 Baja"


def _leer_csv_existente(ruta: str) -> dict[str, dict]:
    filas: dict[str, dict] = {}
    try:
        with open(ruta, encoding="utf-8-sig", newline="") as f:
            for fila in csv.DictReader(f):
                url = fila.get("Sitio web", "").strip()
                if url:
                    filas[url] = fila
    except FileNotFoundError:
        pass
    return filas


def mezclar(csv_existente: str, resultados_json: str, ciudad: str, rubro: str) -> str:
    filas = _leer_csv_existente(csv_existente)

    with open(resultados_json, encoding="utf-8-sig") as f:
        nuevos = json.load(f)

    for r in nuevos:
        if r.get("puntaje", 0) <= 0:
            continue
        url = r["url"]
        previa = filas.get(url, {})
        señales = r.get("señales", [])
        if isinstance(señales, list):
            señales = " | ".join(señales)
        filas[url] = {
            "Prioridad": _prioridad(r["puntaje"]),
            "Ciudad": ciudad,
            "Rubro": rubro,
            "Sitio web": url,
            "Puntaje (0-100)": r["puntaje"],
            "Señales detectadas": señales,
            "Email": previa.get("Email", ""),
            "WhatsApp": previa.get("WhatsApp", ""),
            "Telefono": previa.get("Telefono", ""),
        }

    ordenadas = sorted(filas.values(), key=lambda f: int(f["Puntaje (0-100)"]), reverse=True)

    salida = io.StringIO()
    writer = csv.DictWriter(salida, fieldnames=COLUMNAS)
    writer.writeheader()
    writer.writerows(ordenadas)
    return salida.getvalue()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 5:
        print('Uso: uv run sync_sites_csv.py <hoja-actual.csv> <resultado-run.json> "<ciudad>" "<rubro>"',
              file=sys.stderr)
        sys.exit(1)
    print(mezclar(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]), end="")
