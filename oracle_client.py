"""
Conexión y queries a Oracle (Banner).
"""

import os
from dotenv import load_dotenv
import oracledb

from utils import limpiar, abreviar_estado, abreviar_pais

load_dotenv()

ORACLE_USER = os.getenv("BANNER_USER")
ORACLE_PASSWORD = os.getenv("BANNER_PASSWORD")
ORACLE_DSN = os.getenv("BANNER_DSN")

# ─── Queries ─────────────────────────────────────────────────────────────────

QUERY_FACTURACION = """
WITH PARAMETROS AS (
    SELECT :matricula AS MATRICULA, :transaccion AS TRANSACCION FROM DUAL
),
ALUMNO AS (
    SELECT *
    FROM SPRIDEN S
    CROSS JOIN PARAMETROS P
    WHERE S.SPRIDEN_ID = P.MATRICULA
    and SPRIDEN_CHANGE_IND is NULL
),
datos_facturacion AS (
    SELECT *
    FROM GORADID G
    JOIN ALUMNO A ON G.GORADID_PIDM = A.SPRIDEN_PIDM
),
nombre_factura AS (
    SELECT *
    FROM SPREMRG N
    JOIN ALUMNO A ON N.SPREMRG_PIDM = A.SPRIDEN_PIDM
    WHERE N.SPREMRG_RELT_CODE = 'Z'
)
SELECT DISTINCT
    n.SPREMRG_FIRST_NAME AS NOMBRE,
    (SELECT GORADID_ADDITIONAL_ID FROM datos_facturacion WHERE GORADID_ADID_CODE = 'RFC') AS RFC,
    (SELECT GORADID_ADDITIONAL_ID FROM datos_facturacion WHERE GORADID_ADID_CODE = 'UCFD') AS UCFD,
    (SELECT GORADID_ADDITIONAL_ID FROM datos_facturacion WHERE GORADID_ADID_CODE = 'RFIS') AS RFIS,
    n.SPREMRG_ZIP AS CP,
    n.SPREMRG_STREET_LINE1,
    n.SPREMRG_STREET_LINE2,
    n.SPREMRG_STREET_LINE3,
    n.SPREMRG_CITY,
    stzat.STVSTAT_DESC AS ESTADO,
    natn.STVNATN_NATION AS PAIS,
    tbra.TBRACCD_AMOUNT AS TOTAL,
    a.SPRIDEN_ID AS MATRICULA,
    tbra.TBRACCD_TRAN_NUMBER AS TRANSACCIONCARGO,
    tbra.TBRACCD_TRAN_NUMBER_PAID AS TRANSACTIONPAID,
    tbra.TBRACCD_PERIOD AS PERIODO,
    (SELECT GORADID_ADDITIONAL_ID FROM datos_facturacion WHERE GORADID_ADID_CODE = 'CURP') AS CURP
FROM ALUMNO a
CROSS JOIN PARAMETROS p
JOIN datos_facturacion f ON f.GORADID_PIDM = a.SPRIDEN_PIDM
JOIN nombre_factura n ON n.SPREMRG_PIDM = a.SPRIDEN_PIDM
JOIN STVSTAT stzat ON stzat.STVSTAT_CODE = n.SPREMRG_STAT_CODE
JOIN STVNATN natn ON natn.STVNATN_CODE = n.SPREMRG_NATN_CODE
JOIN TBRACCD tbra ON tbra.TBRACCD_PIDM = a.SPRIDEN_PIDM
    AND tbra.TBRACCD_TRAN_NUMBER = p.TRANSACCION
"""

QUERY_RECIBO_HTML = """
WITH ALUMNO AS (
    SELECT SPRIDEN_PIDM
    FROM SPRIDEN
    WHERE SPRIDEN_ID = :matricula
      AND SPRIDEN_CHANGE_IND IS NULL
)
SELECT TZRCFDP_EMAIL_HTML, TZRCFDP_IDINTERNO
FROM TZRCFDP
JOIN ALUMNO A ON TZRCFDP_PIDM = A.SPRIDEN_PIDM
WHERE TZRCFDP_RECEIPT_NUMBER = (
    SELECT TBRACCD_RECEIPT_NUMBER
    FROM TBRACCD
    WHERE TBRACCD_PIDM = A.SPRIDEN_PIDM
      AND TBRACCD_TRAN_NUMBER = :transaccion
)
AND TZRCFDP_PIDM = A.SPRIDEN_PIDM
"""

QUERY_NOMBRE_SIMPLE = """
SELECT SPRIDEN_FIRST_NAME, SPRIDEN_LAST_NAME
FROM SPRIDEN
WHERE SPRIDEN_ID = :matricula
  AND SPRIDEN_CHANGE_IND IS NULL
"""

QUERY_TOTAL_SIMPLE = """
SELECT TBRACCD_AMOUNT, TBRACCD_TRAN_NUMBER_PAID, TBRACCD_PERIOD
FROM TBRACCD
WHERE TBRACCD_PIDM IN (
    SELECT SPRIDEN_PIDM FROM SPRIDEN
    WHERE SPRIDEN_ID = :matricula AND SPRIDEN_CHANGE_IND IS NULL
)
AND TBRACCD_TRAN_NUMBER = :transaccion
"""

QUERY_DETAIL_CODE = """
SELECT TBRACCD_DETAIL_CODE
FROM TBRACCD
WHERE TBRACCD_PIDM IN (
    SELECT SPRIDEN_PIDM FROM SPRIDEN
    WHERE SPRIDEN_ID = :matricula AND SPRIDEN_CHANGE_IND IS NULL
)
AND TBRACCD_TRAN_NUMBER = :transaccion
"""


# ─── Conexión ────────────────────────────────────────────────────────────────

def conectar():
    """Crea y retorna una conexión a Oracle."""
    return oracledb.connect(
        user=ORACLE_USER,
        password=ORACLE_PASSWORD,
        dsn=ORACLE_DSN,
    )


def establecer_contexto(cursor, empresa):
    """Establece el contexto de empresa en Oracle."""
    cursor.execute(f"BEGIN baninst1.contexto.empresa('{empresa}'); END;")


# ─── Consultas ───────────────────────────────────────────────────────────────

def consultar_facturacion(connection, empresa, matricula, transaccion):
    """Ejecuta el query completo de facturación. Retorna la fila o None."""
    cursor = connection.cursor()
    establecer_contexto(cursor, empresa)
    cursor.execute(QUERY_FACTURACION, matricula=matricula, transaccion=transaccion)
    row = cursor.fetchone()
    cursor.close()
    return row


def consultar_recibo_html(connection, empresa, matricula, transaccion):
    """Consulta el HTML del recibo (TZRCFDP_EMAIL_HTML) y el ID interno. Retorna (html, id_interno) o None."""
    cursor = connection.cursor()
    establecer_contexto(cursor, empresa)
    cursor.execute(QUERY_RECIBO_HTML, matricula=matricula, transaccion=transaccion)
    row = cursor.fetchone()
    cursor.close()
    if row is None or row[0] is None:
        return None
    # Oracle puede envolver el CLOB en comillas simples
    html = str(row[0]).strip().strip("'")
    receipt_number = str(row[1]).strip() if row[1] else "sin_id"
    return html, receipt_number


def consultar_nombre(connection, empresa, matricula):
    """Busca nombre y apellido por matrícula. Retorna (first, last) o None."""
    cursor = connection.cursor()
    establecer_contexto(cursor, empresa)
    cursor.execute(QUERY_NOMBRE_SIMPLE, matricula=matricula)
    row = cursor.fetchone()
    cursor.close()
    if row is None:
        return None
    return limpiar(row[0]).upper(), limpiar(row[1]).upper()


def consultar_total(connection, empresa, matricula, transaccion):
    """Busca total, transactionPaid y periodo. Retorna (total, tx_paid, periodo) o None."""
    cursor = connection.cursor()
    establecer_contexto(cursor, empresa)
    cursor.execute(QUERY_TOTAL_SIMPLE, matricula=matricula, transaccion=transaccion)
    row = cursor.fetchone()
    cursor.close()
    if row is None:
        return None
    total = limpiar(row[0])
    tx_paid = int(row[1]) if row[1] else 0
    periodo = limpiar(row[2]) if row[2] else ""
    return total, tx_paid, periodo


def es_facturable(connection, empresa, matricula, transaccion):
    """Verifica si el código de detalle empieza con '4'. Retorna (bool, detail_code)."""
    cursor = connection.cursor()
    establecer_contexto(cursor, empresa)
    cursor.execute(QUERY_DETAIL_CODE, matricula=matricula, transaccion=transaccion)
    row = cursor.fetchone()
    cursor.close()
    if row is None or row[0] is None:
        return False, None
    detail_code = str(row[0]).strip()
    return detail_code.startswith("4"), detail_code


# ─── Construcción de JSON ────────────────────────────────────────────────────

def tiene_periodo_w(row):
    """Verifica si TBRACCD_PERIOD (row[15]) contiene 'W'."""
    return "W" in limpiar(row[15]).upper()


def construir_json(row):
    """Transforma una fila del query completo en el JSON de facturación."""
    return {
        "Receptor": {
            "nombre": limpiar(row[0]).upper(),
            "rfc": limpiar(row[1]),
            "usocfdi": limpiar(row[2]),
            "regimenfiscal": limpiar(row[3]),
            "cp": limpiar(row[4]),
            "domicilioreceptor": {
                "calle": limpiar(row[5]),
                "NoExterior": limpiar(row[6]),
                "NoInterior": limpiar(row[7]),
                "colonia": limpiar(row[8]),
                "municipio": limpiar(row[8]),
                "estado": limpiar(row[9]),
                "pais": limpiar(row[10]),
                "codigoPostal": limpiar(row[4]),
            },
        },
        "total": limpiar(row[11]),
        "matricula": limpiar(row[12]),
        "TransaccionCargo": limpiar(row[13]),
        "transactionPaid": int(row[14]) if row[14] else 0,
    }


def construir_json_csf(row, datos_sqlserver=None):
    """Transforma una fila en formato CSF (pagos con W)."""
    email = ""
    curp = limpiar(row[16])
    if datos_sqlserver:
        email = datos_sqlserver.get("correo", "")

    return {
        "rfc": limpiar(row[1]),
        "nombre": limpiar(row[0]).upper(),
        "domicilioFiscal": limpiar(row[4]),
        "regimenFiscal": limpiar(row[3]),
        "usoCFDI": limpiar(row[2]),
        "email": email,
        "curp": curp,
        "responseType": "xml",
        "domicilioReceptor": {
            "calle": limpiar(row[5]),
            "municipio": limpiar(row[8]),
            "pais": abreviar_pais(limpiar(row[10])),
            "codigoPostal": limpiar(row[4]),
            "estado": abreviar_estado(limpiar(row[9])),
        },
    }


def extraer_datos_receptor(row):
    """Extrae datos del receptor de una fila Oracle para generar TXT."""
    return {
        "rfc": limpiar(row[1]),
        "nombre": limpiar(row[0]).upper(),
        "usoCFDI": limpiar(row[2]),
        "regimenFiscal": limpiar(row[3]),
        "cp": limpiar(row[4]),
        "calle": limpiar(row[5]),
        "municipio": limpiar(row[8]),
        "estado": abreviar_estado(limpiar(row[9])),
        "pais": abreviar_pais(limpiar(row[10])),
    }
