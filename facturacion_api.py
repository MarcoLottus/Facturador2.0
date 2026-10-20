"""
Consulta de histórico y generación de facturas vía API REST.
"""

import requests

from catalogos import URLS_FACTURACION


def consultar_historico(empresa, matricula, transaccion):
    """Consulta el histórico de facturas y verifica si la transacción ya fue facturada.
    Retorna (ya_facturada: bool, datos_factura: dict o None).
    """
    urls = URLS_FACTURACION.get(empresa)
    if not urls:
        print(f"[ERROR] No hay URLs configuradas para {empresa}.")
        return False, None

    url = f"{urls['historico']}?matricula={matricula}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"[ERROR] No se pudo consultar histórico: {e}")
        return False, None

    # UTG tiene estructura diferente: { "FacturaRegistradas": [...] }
    if empresa == "UTG":
        facturas = data.get("FacturaRegistradas", []) if isinstance(data, dict) else []
        campo_tx = "numero_transaccion"
    else:
        facturas = data if isinstance(data, list) else []
        campo_tx = "Numero_Transaccion"

    for factura in facturas:
        tx = factura.get(campo_tx)
        if tx is not None and int(tx) == int(transaccion):
            return True, factura

    return False, None


def solicitar_factura(empresa, matricula, transaccion, body):
    """Hace POST para generar la factura. Retorna la respuesta o None."""
    urls = URLS_FACTURACION.get(empresa)
    if not urls:
        print(f"[ERROR] No hay URLs configuradas para {empresa}.")
        return None

    url = f"{urls['factura']}?matricula={matricula}&transaccion={transaccion}"
    try:
        resp = requests.post(url, json=body, timeout=30)
        return resp
    except requests.RequestException as e:
        print(f"[ERROR] No se pudo solicitar la factura: {e}")
        return None
