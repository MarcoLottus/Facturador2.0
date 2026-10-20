"""
CSF Reader - Extrae datos fiscales de una Constancia de Situación Fiscal (PDF del SAT).
Uso standalone: python csf.py [archivo.pdf]
También se importa como módulo: from csf import extraer_datos_csf, pedir_csf_por_explorador
"""

import json
import re
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog

import pdfplumber

from catalogos import REGIMENES_FISCALES, ESTADOS_ABREVIATURA_SIN_ESPACIOS


# ─── Funciones de extracción ─────────────────────────────────────────────────

def extraer_valor(texto: str, prefijo: str) -> str:
    """Extrae el valor después de un prefijo, preservando espacios en el valor."""
    texto_linea = texto.replace("\n", " ").strip()
    prefijo_limpio = prefijo.replace(" ", "").rstrip(":")
    # Regex: cada carácter del prefijo con espacios opcionales, luego : opcional
    patron = r"\s*".join(re.escape(c) for c in prefijo_limpio) + r"\s*:?\s*"
    m = re.search(patron, texto_linea, re.IGNORECASE)
    if not m:
        return ""
    return texto_linea[m.end():].strip()


def buscar_regimen_codigo(nombre_regimen: str) -> str:
    """Busca el código de régimen fiscal a partir del nombre."""
    nombre_lower = nombre_regimen.lower().strip()
    for clave, codigo in REGIMENES_FISCALES.items():
        if clave in nombre_lower or nombre_lower in clave:
            return codigo
    for clave, codigo in REGIMENES_FISCALES.items():
        palabras_clave = [p for p in clave.split() if len(p) > 3]
        if not palabras_clave:
            continue
        coincidencias = sum(1 for p in palabras_clave if p in nombre_lower)
        if coincidencias >= len(palabras_clave) * 0.6:
            return codigo
    return ""


def buscar_estado_abreviatura(nombre_estado: str) -> str:
    """Convierte estado (texto pegado del PDF) a abreviatura SAT."""
    nombre_lower = nombre_estado.lower().strip().replace(" ", "")
    for clave, abrev in ESTADOS_ABREVIATURA_SIN_ESPACIOS.items():
        if clave == nombre_lower:
            return abrev
    for clave, abrev in ESTADOS_ABREVIATURA_SIN_ESPACIOS.items():
        if clave in nombre_lower or nombre_lower in clave:
            return abrev
    return nombre_estado.upper()


# ─── Limpieza de valores ─────────────────────────────────────────────────────

_BASURA_CSF = [
    re.compile(r"VALIDA\s+TU\s+INFORMACI[OÓ]N(\s+FISCAL)?", re.IGNORECASE),
    re.compile(r"CONSTANCIA\s+DE\s+SITUACI[OÓ]N(\s+FISCAL)?", re.IGNORECASE),
    re.compile(r"\b\d{8,}\b"),  # IDs numéricos largos del documento
]


def _limpiar_valor_csf(texto: str) -> str:
    """Limpia texto basura de un valor extraído de la CSF del SAT."""
    if not texto:
        return ""
    texto = texto.replace("\n", " ").strip()
    for patron in _BASURA_CSF:
        texto = patron.sub("", texto).strip()
    texto = re.sub(r"\s{2,}", " ", texto).strip()
    return texto


# ─── Extracción principal ────────────────────────────────────────────────────

def extraer_datos_csf(ruta_pdf: str) -> dict:
    """Extrae todos los datos fiscales de un PDF de CSF del SAT."""
    datos = {
        "rfc": "",
        "nombre": "",
        "domicilioFiscal": "",
        "regimenFiscal": "",
        "usoCFDI": "G03",
        "email": "",
        "curp": "",
        "responseType": "xml",
        "domicilioReceptor": {
            "calle": "",
            "municipio": "",
            "pais": "MEX",
            "codigoPostal": "",
            "estado": "",
        },
    }

    with pdfplumber.open(ruta_pdf) as pdf:
        if not pdf.pages:
            print("[ERROR] El PDF no tiene páginas.", file=sys.stderr)
            return datos

        tablas_p1 = pdf.pages[0].extract_tables()

        # ── Datos de identidad (RFC, nombre, CURP) ──
        _nombre_pf = ""   # Nombre(s) — persona física
        _apellido1 = ""   # Primer apellido
        _apellido2 = ""   # Segundo apellido

        for tabla in tablas_p1:
            for fila in tabla:
                if fila is None:
                    continue
                celda0 = str(fila[0] or "").strip()
                celda1 = str(fila[1] or "").strip() if len(fila) > 1 and fila[1] else ""
                celda0_norm = celda0.lower().replace(" ", "").replace("\n", "")

                # RFC
                if celda0_norm.startswith("rfc:"):
                    datos["rfc"] = _limpiar_valor_csf(celda1) or celda0.split(":", 1)[-1].strip()

                # Persona moral: Denominación / Razón Social
                if "denominación" in celda0_norm or "razónsocial" in celda0_norm:
                    val = _limpiar_valor_csf(celda1) or _limpiar_valor_csf(celda0.split(":", 1)[-1])
                    if val:
                        datos["nombre"] = val

                # Persona física: Nombre(s)
                if "nombre(s)" in celda0_norm:
                    val = _limpiar_valor_csf(celda1) or _limpiar_valor_csf(celda0.split(":", 1)[-1])
                    if val:
                        _nombre_pf = val

                # Primer Apellido
                if "primerapellido" in celda0_norm:
                    val = _limpiar_valor_csf(celda1) or _limpiar_valor_csf(celda0.split(":", 1)[-1])
                    if val:
                        _apellido1 = val

                # Segundo Apellido
                if "segundoapellido" in celda0_norm:
                    val = _limpiar_valor_csf(celda1) or _limpiar_valor_csf(celda0.split(":", 1)[-1])
                    if val:
                        _apellido2 = val

                # CURP
                if celda0_norm.startswith("curp:"):
                    datos["curp"] = _limpiar_valor_csf(celda1) or celda0.split(":", 1)[-1].strip()

        # Persona física: construir nombre completo
        if _nombre_pf or _apellido1:
            partes = [p for p in [_nombre_pf, _apellido1, _apellido2] if p]
            datos["nombre"] = " ".join(partes)

        # Limpieza final del nombre
        datos["nombre"] = _limpiar_valor_csf(datos["nombre"])

        for tabla in tablas_p1:
            for fila in tabla:
                if fila is None:
                    continue
                for celda in fila:
                    if celda is None:
                        continue
                    c = str(celda)
                    c_lower = c.replace(" ", "").replace("\n", "").lower()

                    if "códigopostal:" in c_lower or "codigopostal:" in c_lower:
                        cp = extraer_valor(c, "CódigoPostal:") or extraer_valor(c, "CodigoPostal:")
                        if cp:
                            datos["domicilioFiscal"] = cp
                            datos["domicilioReceptor"]["codigoPostal"] = cp

                    if "nombredevialidad:" in c_lower:
                        datos["domicilioReceptor"]["calle"] = extraer_valor(c, "NombredeVialidad:")

                    if "municipio" in c_lower and ("demarcación" in c_lower or "demarcacion" in c_lower or "territorial" in c_lower):
                        val = c.split(":")[-1].replace("\n", " ").strip()
                        if val:
                            datos["domicilioReceptor"]["municipio"] = val.replace(" ", "")

                    if "entidadfederativa:" in c_lower:
                        estado_raw = extraer_valor(c, "NombredelaEntidadFederativa:") or extraer_valor(c, "EntidadFederativa:")
                        datos["domicilioReceptor"]["estado"] = buscar_estado_abreviatura(estado_raw)

        if len(pdf.pages) >= 2:
            tablas_p2 = pdf.pages[1].extract_tables()
            for tabla in tablas_p2:
                for fila in tabla:
                    if fila is None:
                        continue
                    primera = str(fila[0] or "").strip().lower()
                    if primera in ("régimen", "regimen", "regímenes:", "orden",
                                   "obligaciones:", "descripción de la obligación", ""):
                        continue
                    if len(fila) >= 2 and fila[1]:
                        segunda = str(fila[1]).strip()
                        if re.match(r"\d{2}/\d{2}/\d{4}", segunda):
                            codigo = buscar_regimen_codigo(primera)
                            if codigo:
                                datos["regimenFiscal"] = codigo
                                break
                if datos["regimenFiscal"]:
                    break

    return datos


# ─── Explorador de archivos ──────────────────────────────────────────────────

def seleccionar_pdf() -> str:
    """Abre un explorador de archivos para seleccionar un PDF."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    ruta = filedialog.askopenfilename(
        title="Selecciona la Constancia de Situación Fiscal (CSF)",
        filetypes=[("Archivos PDF", "*.pdf")],
    )
    root.destroy()
    return ruta


def pedir_csf_por_explorador():
    """Abre explorador, extrae datos, muestra resumen y retorna dict con datos del receptor."""
    ruta = seleccionar_pdf()
    if not ruta:
        return None

    datos = extraer_datos_csf(ruta)

    resultado = {
        "rfc": datos.get("rfc", ""),
        "nombre": datos.get("nombre", ""),
        "usoCFDI": datos.get("usoCFDI", "G03"),
        "regimenFiscal": datos.get("regimenFiscal", ""),
        "cp": datos.get("domicilioFiscal", ""),
        "calle": datos.get("domicilioReceptor", {}).get("calle", ""),
        "municipio": datos.get("domicilioReceptor", {}).get("municipio", ""),
        "estado": datos.get("domicilioReceptor", {}).get("estado", ""),
        "pais": datos.get("domicilioReceptor", {}).get("pais", "MEX"),
    }

    # Mostrar resumen de la CSF extraída
    print(f"\n{'─' * 50}")
    print("  DATOS EXTRAÍDOS DE LA CSF")
    print(f"{'─' * 50}")
    print(f"  Nombre:          {resultado['nombre'] or '⚠ No detectado'}")
    print(f"  RFC:             {resultado['rfc'] or '⚠ No detectado'}")
    print(f"  Régimen Fiscal:  {resultado['regimenFiscal'] or '⚠ No detectado'}")
    print(f"  Uso CFDI:        {resultado['usoCFDI']}")
    print(f"  Código Postal:   {resultado['cp'] or '⚠ No detectado'}")
    print(f"  Calle:           {resultado['calle'] or '⚠ No detectado'}")
    print(f"  Municipio:       {resultado['municipio'] or '⚠ No detectado'}")
    print(f"  Estado:          {resultado['estado'] or '⚠ No detectado'}")
    print(f"  País:            {resultado['pais']}")
    print(f"{'─' * 50}\n")

    return resultado


# ─── Ejecución standalone ───────────────────────────────────────────────────

def main():
    if len(sys.argv) >= 2:
        ruta_pdf = sys.argv[1]
    else:
        print("Selecciona el archivo PDF de la CSF...")
        ruta_pdf = seleccionar_pdf()
        if not ruta_pdf:
            print("[INFO] No se seleccionó ningún archivo.")
            sys.exit(0)

    try:
        datos = extraer_datos_csf(ruta_pdf)

        print("=" * 60)
        print("  FORMATO CSF (reducido)")
        print("=" * 60)
        json_csf = json.dumps(datos, indent=2, ensure_ascii=False)
        print(json_csf)

        datos_completo = {
            "Receptor": {
                "nombre": datos["nombre"],
                "rfc": datos["rfc"],
                "usocfdi": datos["usoCFDI"],
                "regimenfiscal": datos["regimenFiscal"],
                "cp": datos["domicilioFiscal"],
                "domicilioreceptor": {
                    "calle": datos["domicilioReceptor"]["calle"],
                    "NoExterior": "",
                    "NoInterior": "",
                    "colonia": "",
                    "municipio": datos["domicilioReceptor"]["municipio"],
                    "estado": datos["domicilioReceptor"]["estado"],
                    "pais": datos["domicilioReceptor"]["pais"],
                    "codigoPostal": datos["domicilioReceptor"]["codigoPostal"],
                },
            },
            "total": "",
            "matricula": "",
            "TransaccionCargo": "",
            "transactionPaid": "",
        }
        print("\n" + "=" * 60)
        print("  FORMATO COMPLETO (con transacción)")
        print("=" * 60)
        json_completo = json.dumps(datos_completo, indent=2, ensure_ascii=False)
        print(json_completo)

        proceso = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
        proceso.communicate(json_csf.encode("utf-16le"))
        print("\n[CLIPBOARD] JSON formato CSF copiado al portapapeles.")
    except FileNotFoundError:
        print(f"[ERROR] No se encontró el archivo: {ruta_pdf}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
