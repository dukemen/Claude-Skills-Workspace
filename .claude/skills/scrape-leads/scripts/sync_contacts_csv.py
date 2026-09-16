#!/usr/bin/env python3
"""Mezcla contacto recién extraído (extract_contact.py) en el CSV de la hoja
"Sitios web desactualizados - Colombia" — upsert por URL, pisa siempre
Email/WhatsApp/Telefono de la fila existente (un re-chequeo es más confiable
que el dato viejo), sin tocar las demás columnas (Prioridad/Ciudad/Rubro/
Puntaje/Señales, que son responsabilidad de scrape-webs).

Entrada:
  - CSV actual de la hoja (mismas columnas que sync_sites_csv.py)
  - JSON con la lista de contactos extraídos: [{url, emails, whatsapps,
    telefonos}, ...] — la salida cruda de extraer_contacto() por cada lead
    (se usa el primer valor de cada lista, si hay varios)

Uso: uv run sync_contacts_csv.py <hoja-actual.csv> <contactos.json> > hoja-nueva.csv

Solo actualiza filas cuya URL ya existe en la hoja — este script no agrega
sitios nuevos (eso es trabajo de scrape-webs).
"""

import csv
import io
import json
import sys

COLUMNAS = ["Prioridad", "Ciudad", "Rubro", "Sitio web", "Puntaje (0-100)",
            "Señales detectadas", "Email", "WhatsApp", "Telefono"]


def _primero(valores) -> str:
    if isinstance(valores, list):
        return valores[0] if valores else ""
    return valores or ""


def _leer_csv(ruta: str) -> dict[str, dict]:
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return {fila["Sitio web"]: fila for fila in csv.DictReader(f) if fila.get("Sitio web")}


def mezclar(csv_actual: str, contactos_json: str) -> str:
    filas = _leer_csv(csv_actual)

    with open(contactos_json, encoding="utf-8-sig") as f:
        contactos = json.load(f)

    sin_fila = []
    for c in contactos:
        url = c["url"]
        if url not in filas:
            sin_fila.append(url)
            continue
        filas[url]["Email"] = _primero(c.get("emails"))
        filas[url]["WhatsApp"] = _primero(c.get("whatsapps"))
        filas[url]["Telefono"] = _primero(c.get("telefonos"))

    if sin_fila:
        print(f"Aviso: {len(sin_fila)} URLs sin fila previa en la hoja, ignoradas: {sin_fila}",
              file=sys.stderr)

    ordenadas = sorted(filas.values(), key=lambda f: int(f["Puntaje (0-100)"]), reverse=True)

    salida = io.StringIO()
    writer = csv.DictWriter(salida, fieldnames=COLUMNAS)
    writer.writeheader()
    writer.writerows(ordenadas)
    return salida.getvalue()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if len(sys.argv) < 3:
        print("Uso: uv run sync_contacts_csv.py <hoja-actual.csv> <contactos.json>", file=sys.stderr)
        sys.exit(1)
    print(mezclar(sys.argv[1], sys.argv[2]), end="")
