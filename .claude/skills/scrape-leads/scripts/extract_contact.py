#!/usr/bin/env python3
"""Visita un sitio (y sus páginas de contacto más comunes) y extrae email,
WhatsApp y teléfono. Heurístico: los sitios pequeños ponen esto en el footer o en
una página "Contacto" — no hay una estructura estándar, así que se prueban varias
rutas. Prioriza atributos estructurados (mailto:/tel:/wa.me) sobre regex de texto
libre, que trae falsos positivos (IDs de analytics, hashes, números de versión).
"""

import json
import re
import sys

import httpx

RUTAS_CONTACTO = ["", "/contacto", "/contact", "/contactenos", "/contactanos", "/nosotros"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; scrape-leads/1.0)"}

MAILTO_RE = re.compile(r"mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")
TEL_HREF_RE = re.compile(r'href=["\']tel:([+\d\s().-]{7,})["\']')
WHATSAPP_HREF_RE = re.compile(r"(?:wa\.me/|api\.whatsapp\.com/send\?phone=)(\+?\d{10,13})")

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
TELEFONO_RE = re.compile(r"(?:\+?57[\s.-]?)?3\d{2}[\s.-]?\d{3}[\s.-]?\d{4}\b")

EMAIL_DOMINIOS_IGNORAR = [
    "sentry.io", "wixpress.com", "example.com", "godaddy.com", "domain.com",
    "yourdomain.com", "email.com", "wordpress.com", "schema.org", "w3.org",
    "correoelectronico.com", "tuemail.com", "tucorreo.com", "correo.com",
    ".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif",
]

NUMEROS_PLACEHOLDER = {"5555551212", "1234567890", "0000000000"}
LIMITE_RUIDO = 5


def _limpiar_email(email: str) -> str | None:
    email = email.lower()
    return None if any(d in email for d in EMAIL_DOMINIOS_IGNORAR) else email


def _es_numero_valido(digitos10: str) -> bool:
    if digitos10 in NUMEROS_PLACEHOLDER:
        return False
    # Números de plantilla (demo) suelen tener 9+ de los 10 dígitos repetidos
    if digitos10 and max(digitos10.count(c) for c in set(digitos10)) >= 9:
        return False
    return True


def _extraer_emails(html: str) -> list[str]:
    estructurados = {e for m in MAILTO_RE.finditer(html) if (e := _limpiar_email(m.group(1)))}
    if estructurados:
        return list(estructurados)

    libres = {e for m in EMAIL_RE.finditer(html) if (e := _limpiar_email(m.group(0)))}
    return list(libres) if len(libres) <= LIMITE_RUIDO else []


def _normalizar_numero(digitos: str) -> str:
    digitos = re.sub(r"\D", "", digitos)
    if len(digitos) == 10:
        digitos = "57" + digitos  # asumir CO sin indicativo
    return "+" + digitos


def _extraer_whatsapp(html: str) -> list[str]:
    encontrados = set()
    for m in WHATSAPP_HREF_RE.finditer(html):
        d = re.sub(r"\D", "", m.group(1))[-10:]
        if _es_numero_valido(d):
            encontrados.add(_normalizar_numero(m.group(1)))
    return list(encontrados)


def _extraer_telefonos(html: str) -> list[str]:
    estructurados = set()
    for m in TEL_HREF_RE.finditer(html):
        d = re.sub(r"\D", "", m.group(1))[-10:]
        if len(d) >= 7 and _es_numero_valido(d):
            estructurados.add(d)
    if estructurados:
        return list(estructurados)

    libres = set()
    for m in TELEFONO_RE.finditer(html):
        d = re.sub(r"\D", "", m.group(0))[-10:]
        if _es_numero_valido(d):
            libres.add(d)
    return list(libres) if len(libres) <= LIMITE_RUIDO else []


def _fetch_texto(client: httpx.Client, url: str) -> str | None:
    try:
        res = client.get(url, timeout=12)
        return res.text if res.is_success else None
    except Exception:  # noqa: BLE001 — sitio caído/timeout, seguimos con la siguiente ruta
        return None


def extraer_contacto(url_base: str) -> dict:
    base = url_base.rstrip("/")
    emails: set[str] = set()
    whatsapps: set[str] = set()
    telefonos: set[str] = set()
    paginas_revisadas = 0

    with httpx.Client(headers=HEADERS) as client:
        for ruta in RUTAS_CONTACTO:
            html = _fetch_texto(client, base + ruta)
            if html is None:
                continue
            paginas_revisadas += 1
            emails.update(_extraer_emails(html))
            whatsapps.update(_extraer_whatsapp(html))
            telefonos.update(_extraer_telefonos(html))
            if emails and (whatsapps or telefonos):
                break

    return {
        "url": url_base,
        "paginasRevisadas": paginas_revisadas,
        "emails": list(emails),
        "whatsapps": list(whatsapps),
        "telefonos": [t for t in telefonos if not any(w.endswith(t) for w in whatsapps)],
    }


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("Uso: uv run extract_contact.py <url>", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(extraer_contacto(sys.argv[1]), indent=2, ensure_ascii=False))
