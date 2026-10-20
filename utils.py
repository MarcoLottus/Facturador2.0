"""
Funciones utilitarias compartidas.
"""

import subprocess

from catalogos import ESTADOS_ABREVIATURA, ESTADOS_ABREVIATURA_SIN_ESPACIOS, PAISES_CODIGO, METODOS_PAGO, CAMPUS_CODIGO, EMISORES


def limpiar(valor):
    """Convierte a string y elimina espacios al inicio y final."""
    return str(valor or "").strip()


def abreviar_estado(nombre_estado):
    """Convierte el nombre del estado a su abreviatura SAT."""
    nombre_lower = nombre_estado.lower().strip()
    if nombre_lower in ESTADOS_ABREVIATURA:
        return ESTADOS_ABREVIATURA[nombre_lower]
    for clave, abrev in ESTADOS_ABREVIATURA.items():
        if clave in nombre_lower or nombre_lower in clave:
            return abrev
    return nombre_estado.upper()


def abreviar_estado_sin_espacios(nombre_estado):
    """Convierte estado sin espacios (de CSF) a abreviatura SAT."""
    nombre_lower = nombre_estado.lower().strip().replace(" ", "")
    for clave, abrev in ESTADOS_ABREVIATURA_SIN_ESPACIOS.items():
        if clave == nombre_lower:
            return abrev
    for clave, abrev in ESTADOS_ABREVIATURA_SIN_ESPACIOS.items():
        if clave in nombre_lower or nombre_lower in clave:
            return abrev
    return nombre_estado.upper()


def abreviar_pais(nombre_pais):
    """Convierte el nombre del país a su código ISO."""
    nombre_lower = nombre_pais.lower().strip()
    if nombre_lower in PAISES_CODIGO:
        return PAISES_CODIGO[nombre_lower]
    for clave, codigo in PAISES_CODIGO.items():
        if clave in nombre_lower or nombre_lower in clave:
            return codigo
    return nombre_pais.upper()


def copiar_al_portapapeles(texto):
    """Copia un texto al portapapeles de Windows usando clip."""
    proceso = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
    proceso.communicate(texto.encode("utf-16le"))


def mapear_metodo_pago(metodo_str):
    """Convierte el método de pago de SQL Server al código SAT."""
    metodo_upper = metodo_str.upper().strip()
    for clave, codigo in METODOS_PAGO.items():
        if clave in metodo_upper:
            return codigo
    return "01"


def mapear_campus(campus_str):
    """Extrae el código de campus del string 'A DISTANCIA-DIS' → 'DIS' y lo mapea."""
    campus_str = campus_str.strip()
    if "-" in campus_str:
        codigo = campus_str.rsplit("-", 1)[-1].strip()
    else:
        codigo = campus_str
    return CAMPUS_CODIGO.get(codigo, codigo)


def obtener_emisor(compania_str):
    """Retorna (rfc, nombre) del emisor según la compañía."""
    compania_upper = compania_str.upper().strip()
    emisor = EMISORES.get(compania_upper)
    if emisor:
        return emisor["rfc"], emisor["nombre"]
    return "UTC9903183C7", "UNIVERSIDAD DE LAS TRES CULTURAS"


def prefijo_folio(compania_str):
    """Retorna el prefijo del folio: C para UTC, I para CETC."""
    compania_upper = compania_str.upper().strip()
    if compania_upper in ("CETC", "CET"):
        return "I"
    return "C"


def determinar_empresa(matricula):
    """Determina la empresa según el primer carácter de la matrícula.
    Retorna (empresa, error_msg). Si hay error, empresa es None.
    """
    primer_char = matricula[0].upper()
    if primer_char == "U":
        return "ULA", None
    elif primer_char == "G":
        return "UTG", None
    elif primer_char.isdigit():
        return "UTC", None
    else:
        return None, f"No se puede determinar la empresa para matrícula que inicia con '{primer_char}'."
