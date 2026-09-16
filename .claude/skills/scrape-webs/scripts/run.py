#!/usr/bin/env python3
"""Orquesta el flujo completo: busca candidatos para un rubro+ciudad, analiza cada
uno y devuelve un ranking ordenado de más a menos desactualizado. Pausa entre
requests para no saturar los sitios ni la búsqueda.
"""

import json
import sys
import time

from check_outdated import analizar_sitio
from find_candidates import buscar_candidatos

PAUSA_S = 1.5


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print('Uso: uv run run.py "<rubro/termino>" ["<ciudad>"]', file=sys.stderr)
        print('Ejemplo: uv run run.py "restaurantes" "Bucaramanga"', file=sys.stderr)
        sys.exit(1)

    termino = sys.argv[1]
    ciudad = sys.argv[2] if len(sys.argv) > 2 else None

    print(f'Buscando candidatos: "{termino}"' + (f" en {ciudad}..." if ciudad else "..."), file=sys.stderr)
    candidatos = buscar_candidatos(termino, ciudad, limite=20)
    print(f"Encontrados {len(candidatos)} dominios únicos. Analizando...", file=sys.stderr)

    resultados = []
    for i, url in enumerate(candidatos, 1):
        print(f"  [{i}/{len(candidatos)}] {url}", file=sys.stderr)
        resultados.append(analizar_sitio(url))
        time.sleep(PAUSA_S)

    resultados.sort(key=lambda r: r["puntaje"], reverse=True)

    print(json.dumps(resultados, indent=2, ensure_ascii=False))
    print("\nRanking (mayor puntaje = más desactualizado):", file=sys.stderr)
    for r in resultados:
        print(f"  {r['puntaje']:>3} | {r['url']}", file=sys.stderr)


if __name__ == "__main__":
    main()
