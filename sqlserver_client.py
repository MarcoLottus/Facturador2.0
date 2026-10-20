"""
Conexión y queries a SQL Server (Simulador_UAT).
"""

import os
from dotenv import load_dotenv
import pymssql

load_dotenv()

SQLSERVER_HOST = os.getenv("SQLSERVER_HOST", "LSTSQL2017")
SQLSERVER_PORT = int(os.getenv("SQLSERVER_PORT", "1433"))
SQLSERVER_DB = os.getenv("SQLSERVER_DB", "Simulador_UAT")
SQLSERVER_USER = os.getenv("SQLSERVER_USER")
SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD")


def buscar_pago(first_name, last_name=None):
    """Busca datos de pago en SQL Server por nombre de usuario.
    Prueba 'FIRST LAST' y luego 'LAST FIRST'.
    Retorna un dict con los datos encontrados o None.
    """
    intentos = []
    if first_name and last_name:
        intentos.append(f"{first_name} {last_name}")
        intentos.append(f"{last_name} {first_name}")
    else:
        intentos.append(first_name)

    try:
        conn = pymssql.connect(
            server=SQLSERVER_HOST,
            port=SQLSERVER_PORT,
            user=SQLSERVER_USER,
            password=SQLSERVER_PASSWORD,
            database=SQLSERVER_DB,
        )
        cursor = conn.cursor(as_dict=True)

        for nombre in intentos:
            cursor.execute(
                "SELECT fecha, foliopago, referenciaUnica, cantidadpago, "
                "nombreUsuario, Correousuario, metodopago, campus, compania "
                "FROM ISM_facturacion "
                "WHERE nombreUsuario LIKE %s",
                (f"%{nombre}%",),
            )
            row = cursor.fetchone()
            if row:
                cursor.close()
                conn.close()
                return {
                    "fecha": str(row.get("fecha", "")),
                    "foliopago": str(row.get("foliopago", "")),
                    "referenciaUnica": str(row.get("referenciaUnica", "")),
                    "cantidadpago": str(row.get("cantidadpago", "")),
                    "nombreUsuario": str(row.get("nombreUsuario", "")),
                    "correo": str(row.get("Correousuario", "")),
                    "metodopago": str(row.get("metodopago", "")),
                    "campus": str(row.get("campus", "")),
                    "compania": str(row.get("compania", "")),
                }

        cursor.close()
        conn.close()
        return None

    except pymssql.Error as e:
        print(f"[ERROR] SQL Server: {e}")
        return None


def imprimir_datos_sql(datos_sql):
    """Imprime los datos de SQL Server en consola."""
    print(f"[SQL SERVER] Registro encontrado:")
    print(f"  Fecha:           {datos_sql['fecha']}")
    print(f"  Folio Pago:      {datos_sql['foliopago']}")
    print(f"  Ref. Única:      {datos_sql['referenciaUnica']}")
    print(f"  Cantidad Pago:   {datos_sql['cantidadpago']}")
    print(f"  Nombre Usuario:  {datos_sql['nombreUsuario']}")
    print(f"  Correo:          {datos_sql['correo']}")
    print(f"  Método Pago:     {datos_sql['metodopago']}")
    print(f"  Campus:          {datos_sql['campus']}")
    print(f"  Compañía:        {datos_sql['compania']}")
