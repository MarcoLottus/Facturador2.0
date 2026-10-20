"""
Generación de archivos TXT de facturación para UTC/CETC.
"""

import os
from datetime import datetime

from utils import mapear_metodo_pago, mapear_campus, obtener_emisor, prefijo_folio


def generar_txt(datos_sql, datos_receptor, compania_str):
    """Genera el contenido del TXT de facturación y lo guarda en archivo.

    datos_sql: dict con datos de SQL Server
    datos_receptor: dict con datos fiscales del receptor
    compania_str: compañía del pago (UTC, CETC)

    Retorna (ruta_archivo, contenido).
    """
    ahora = datetime.now()
    fecha_enc = ahora.strftime("%d/%m/%Y %H:%M:%S")
    fecha_archivo = ahora.strftime("%d-%m-%Y--%H-%M-%S")

    folio_pago = datos_sql.get("foliopago", "")
    ref_unica = datos_sql.get("referenciaUnica", "")
    cantidad = datos_sql.get("cantidadpago", "0")
    metodo_str = datos_sql.get("metodopago", "")
    campus_str = datos_sql.get("campus", "")

    # Mapeos
    prefijo = prefijo_folio(compania_str)
    folio_doc = f"{prefijo}{folio_pago}"
    metodo_codigo = mapear_metodo_pago(metodo_str)
    campus_codigo = mapear_campus(campus_str)
    rfc_emisor, nombre_emisor = obtener_emisor(compania_str)

    compania_upper = compania_str.upper().strip()
    compania_txt = "CETC" if compania_upper in ("CETC", "CET") else "UTC"

    # Datos del receptor
    rfc_receptor = datos_receptor.get("rfc", "")
    nombre_receptor = datos_receptor.get("nombre", "")
    uso_cfdi = datos_receptor.get("usoCFDI", "")
    regimen_fiscal = datos_receptor.get("regimenFiscal", "")
    cp_receptor = datos_receptor.get("cp", "")
    calle = datos_receptor.get("calle", "")
    municipio = datos_receptor.get("municipio", "")
    estado = datos_receptor.get("estado", "")
    pais = datos_receptor.get("pais", "")

    # Formatear cantidad
    try:
        monto = f"{abs(float(cantidad)):.2f}"
    except (ValueError, TypeError):
        monto = "0.00"

    # Construir líneas
    lineas = [
        f"DOC(+){folio_doc}|0|SF|ISM",
        f"ENC(+)|{folio_doc}|{fecha_enc}|{metodo_codigo}||0|MXN|PUE|06600|I|{monto}|0.00|{monto}||01|",
        "CFDIREL(+)|",
        f"EMISOR(+){rfc_emisor}|{nombre_emisor}|601|{campus_codigo}|",
        f"RECEPTOR(+){rfc_receptor}|{nombre_receptor}|||{uso_cfdi}||||{calle}|||||{municipio}|{estado}|{pais}|{cp_receptor}|||||{regimen_fiscal}|",
        f"FH(+)ALU|000000000|{nombre_receptor}|",
        f"FH(+)UNIQUECODE|{ref_unica}|",
        f"L(+)1|86121701|1|E48|SERVICIO|PLAN|COLEGIATURA|{monto}|{monto}||C|02",
        f"LIMPTRA(+)1|{monto}|002|Exento|||",
        "TOTIMP(+)0.0|0|",
        "A.TYPE = IEDU",
    ]

    contenido = "\n".join(lineas)

    # Guardar archivo
    nombre_archivo = f"F-{folio_pago}---{fecha_archivo}_{compania_txt}_ISM.txt"
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre_archivo)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)

    return ruta, contenido
