"""
Facturador 2.0 - Consulta de datos de facturación.
Modularizado: cada responsabilidad en su archivo.
"""

import json
import os
import time
from datetime import datetime

from xhtml2pdf import pisa

from catalogos import INSTRUCCIONES
from utils import limpiar, copiar_al_portapapeles, abreviar_estado, abreviar_pais, determinar_empresa
from oracle_client import (
    conectar, consultar_facturacion, consultar_nombre, consultar_total,
    consultar_recibo_html, es_facturable,
    tiene_periodo_w, construir_json, construir_json_csf, extraer_datos_receptor,
)
from sqlserver_client import buscar_pago, imprimir_datos_sql
from facturacion_api import consultar_historico, solicitar_factura
from txt_generator import generar_txt
from csf import pedir_csf_por_explorador


# ─── Flujo normal ────────────────────────────────────────────────────────────

def flujo_normal(connection, empresa, matricula, transaccion, forzar_w):
    """Consulta Oracle, detecta W, genera JSON o TXT según corresponda."""
    row = consultar_facturacion(connection, empresa, matricula, transaccion)

    if row is None:
        if forzar_w:
            flujo_w_sin_oracle(connection, empresa, matricula, transaccion)
        else:
            print(f"[INFO] Sin resultados para matrícula={matricula}, transacción={transaccion}\n")
        return

    if tiene_periodo_w(row) or forzar_w:
        flujo_w_con_oracle(row, empresa, matricula)
    else:
        resultado = construir_json(row)
        json_str = json.dumps(resultado, indent=2, ensure_ascii=False)
        print(json_str)

        copiar_al_portapapeles(str(transaccion))
        time.sleep(0.1)
        copiar_al_portapapeles(matricula)
        time.sleep(0.1)
        copiar_al_portapapeles(json_str)
        print("[CLIPBOARD] JSON, matrícula y transacción copiados al portapapeles.\n")


# ─── Flujo W con datos Oracle ────────────────────────────────────────────────

def flujo_w_con_oracle(row, empresa, matricula):
    """PERIOD tiene W y Oracle devolvió datos."""
    periodo = limpiar(row[15])
    nombre = limpiar(row[0]).upper()
    print(f"[AVISO] PERIOD contiene 'W' ({periodo})")

    print(f"[INFO] Buscando en SQL Server por nombre: {nombre}...")
    datos_sql = buscar_pago(nombre)

    if datos_sql:
        imprimir_datos_sql(datos_sql)

        # Comparar cantidades
        total_oracle = abs(float(limpiar(row[11]) or 0))
        total_sql = abs(float(datos_sql["cantidadpago"] or 0))
        if total_oracle == total_sql:
            print(f"\n  [✓] Cantidades coinciden: ${total_oracle:.2f}")
        else:
            print(f"\n  [✗] Cantidades NO coinciden:")
            print(f"      Oracle:     ${total_oracle:.2f}")
            print(f"      SQL Server: ${total_sql:.2f}")

        compania = datos_sql.get("compania", "").upper().strip()

        if empresa == "UTC" or compania in ("UTC", "CETC", "CET"):
            datos_receptor = extraer_datos_receptor(row)
            ruta_txt, contenido_txt = generar_txt(datos_sql, datos_receptor, compania or "UTC")
            print(f"\n[TXT] Archivo generado: {ruta_txt}")
            print(f"\n{contenido_txt}")
            copiar_al_portapapeles(contenido_txt)
            print("\n[CLIPBOARD] Contenido del TXT copiado al portapapeles.\n")
            return
        else:
            _imprimir_url_params(datos_sql)

    else:
        print("[SQL SERVER] No se encontró registro en ISM_facturacion.")

    resultado = construir_json_csf(row, datos_sql)
    json_str = json.dumps(resultado, indent=2, ensure_ascii=False)
    print(json_str)

    copiar_al_portapapeles(json_str)
    print("[CLIPBOARD] JSON copiado al portapapeles.\n")


# ─── Flujo W sin datos Oracle ────────────────────────────────────────────────

def flujo_w_sin_oracle(connection, empresa, matricula, transaccion):
    """Forzó ,w pero Oracle no devolvió datos de facturación."""
    nombre_result = consultar_nombre(connection, empresa, matricula)
    if nombre_result is None:
        print(f"[INFO] No se encontró la matrícula {matricula} en Oracle.\n")
        return

    first_name, last_name = nombre_result
    nombre = f"{first_name} {last_name}"
    print(f"[AVISO] Sin datos de facturación, pero se forzó W")
    print(f"[INFO] Nombre encontrado: {nombre}")
    print(f"[INFO] Buscando en SQL Server...")
    datos_sql = buscar_pago(first_name, last_name)

    if not datos_sql:
        print("[SQL SERVER] No se encontró registro en ISM_facturacion.\n")
        return

    imprimir_datos_sql(datos_sql)
    compania = datos_sql.get("compania", "").upper().strip()

    if empresa == "UTC" or compania in ("UTC", "CETC", "CET"):
        print("\n[INFO] No hay datos fiscales en Oracle. Carga la CSF del receptor...")
        datos_receptor = pedir_csf_por_explorador()
        if not datos_receptor:
            print("[INFO] No se cargó CSF. No se puede generar TXT.\n")
            return

        ruta_txt, contenido_txt = generar_txt(datos_sql, datos_receptor, compania or "UTC")
        print(f"\n[TXT] Archivo generado: {ruta_txt}")
        print(f"\n{contenido_txt}")
        copiar_al_portapapeles(contenido_txt)
        print("\n[CLIPBOARD] Contenido del TXT copiado al portapapeles.")
    else:
        _imprimir_url_params(datos_sql)

        print("\n[INFO] Carga la CSF del receptor para completar los datos fiscales...")
        datos_csf = pedir_csf_por_explorador()

        if datos_csf:
            resultado = {
                "rfc": datos_csf.get("rfc", ""),
                "nombre": datos_csf.get("nombre", "") or nombre,
                "domicilioFiscal": datos_csf.get("cp", ""),
                "regimenFiscal": datos_csf.get("regimenFiscal", ""),
                "usoCFDI": datos_csf.get("usoCFDI", "G03"),
                "email": datos_sql.get("correo", ""),
                "curp": "",
                "responseType": "xml",
                "domicilioReceptor": {
                    "calle": datos_csf.get("calle", ""),
                    "municipio": datos_csf.get("municipio", ""),
                    "pais": datos_csf.get("pais", "MEX"),
                    "codigoPostal": datos_csf.get("cp", ""),
                    "estado": datos_csf.get("estado", ""),
                },
            }
        else:
            print("[INFO] No se cargó CSF. Se arma JSON con datos disponibles.")
            resultado = {
                "rfc": "", "nombre": nombre, "domicilioFiscal": "", "regimenFiscal": "",
                "usoCFDI": "G03", "email": datos_sql.get("correo", ""), "curp": "",
                "responseType": "xml",
                "domicilioReceptor": {
                    "calle": "", "municipio": "", "pais": "MEX", "codigoPostal": "", "estado": "",
                },
            }
        json_str = json.dumps(resultado, indent=2, ensure_ascii=False)
        print(json_str)
        copiar_al_portapapeles(json_str)
        print("[CLIPBOARD] JSON copiado al portapapeles.")
    print()


# ─── Flujo S → Auto-facturación ──────────────────────────────────────────────

def flujo_s(connection, empresa, matricula, transaccion):
    """Consulta histórico, arma body, pide confirmación y genera factura."""
    print(f"[INFO] Modo auto-facturación para {matricula}, tx={transaccion}")

    # 1. Histórico
    print(f"[INFO] Consultando histórico de {empresa}...")
    ya_facturada, datos_factura = consultar_historico(empresa, matricula, transaccion)

    if ya_facturada:
        print(f"\n[AVISO] La transacción {transaccion} YA ESTABA facturada:")
        if empresa == "UTG":
            pdf = datos_factura.get("UrlPdf", "")
            xml = datos_factura.get("UrlXml", "")
        else:
            pdf = datos_factura.get("URL_PDF", "")
            xml = datos_factura.get("URL_XML", "")
        print(f"  PDF: {pdf}")
        print(f"  XML: {xml}")
        factura_str = json.dumps(datos_factura, indent=2, ensure_ascii=False)
        print(f"\n{factura_str}")
        print("\nFavor de descargar la factura, revisarla y hacérsela llegar al usuario.")
        clipboard_txt = f"Favor de descargar la factura, revisarla y hacérsela llegar al usuario.\n\n{factura_str}"
        copiar_al_portapapeles(clipboard_txt)
        print("[CLIPBOARD] Mensaje y datos copiados al portapapeles.\n")
        return

    print(f"[OK] Transacción {transaccion} NO está facturada. Preparando body...")

    # 2. Oracle
    row = consultar_facturacion(connection, empresa, matricula, transaccion)

    if row is None:
        # Sin datos completos → query simple
        print(f"[INFO] Sin datos de facturación completos en Oracle.")
        print(f"[INFO] Obteniendo total de la transacción...")

        total_result = consultar_total(connection, empresa, matricula, transaccion)
        if total_result is None:
            print(f"[ERROR] No se encontró la transacción {transaccion} para {matricula}.\n")
            return

        total, tx_paid, periodo = total_result

        if "W" in periodo.upper():
            print(f"[AVISO] Pago con 'W' ({periodo}). Armando body en formato W (sin POST).")
            flujo_w_sin_oracle(connection, empresa, matricula, transaccion)
            return

        # No es W → CSF + body Receptor para facturar
        print("[INFO] Carga la CSF del receptor para armar el body...")
        datos_csf = pedir_csf_por_explorador()
        if not datos_csf:
            print("[INFO] No se cargó CSF. No se puede continuar.\n")
            return

        body = {
            "Receptor": {
                "nombre": datos_csf.get("nombre", ""),
                "rfc": datos_csf.get("rfc", ""),
                "usocfdi": datos_csf.get("usoCFDI", "G03"),
                "regimenfiscal": datos_csf.get("regimenFiscal", ""),
                "cp": datos_csf.get("cp", ""),
                "domicilioreceptor": {
                    "calle": datos_csf.get("calle", ""),
                    "NoExterior": "",
                    "NoInterior": "",
                    "colonia": "",
                    "municipio": datos_csf.get("municipio", ""),
                    "estado": datos_csf.get("estado", ""),
                    "pais": datos_csf.get("pais", "MEX"),
                    "codigoPostal": datos_csf.get("cp", ""),
                },
            },
            "total": total,
            "matricula": matricula,
            "TransaccionCargo": str(transaccion),
            "transactionPaid": tx_paid,
        }
    else:
        if tiene_periodo_w(row):
            print(f"[AVISO] Pago con 'W' ({limpiar(row[15])}). Armando body en formato W (sin POST).")
            flujo_w_con_oracle(row, empresa, matricula)
            return
        body = construir_json(row)

    # 3. Mostrar body
    body_str = json.dumps(body, indent=2, ensure_ascii=False)
    print(f"\n{'=' * 60}")
    print("  BODY DE FACTURACIÓN")
    print(f"{'=' * 60}")
    print(body_str)

    # 4. Confirmación
    print()
    confirma = input("¿Generar factura? (s/n): ").strip().lower()
    if confirma != "s":
        print("[INFO] Facturación cancelada.\n")
        return

    # 5. POST
    print(f"[INFO] Solicitando factura a {empresa}...")
    resp = solicitar_factura(empresa, matricula, transaccion, body)

    if resp is None:
        print("[ERROR] No se obtuvo respuesta.\n")
        return

    print(f"\n[FACTURADA] Factura generada exitosamente:")
    print(f"[RESPUESTA] Status: {resp.status_code}")
    try:
        resp_json = resp.json()
        resp_str = json.dumps(resp_json, indent=2, ensure_ascii=False)
        print(resp_str)
        print("\nFavor de descargar la factura, revisarla y hacérsela llegar al usuario.")
        clipboard_txt = f"Favor de descargar la factura, revisarla y hacérsela llegar al usuario.\n\n{resp_str}"
        copiar_al_portapapeles(clipboard_txt)
        print("[CLIPBOARD] Mensaje y respuesta copiados al portapapeles.")
    except Exception:
        print(resp.text)
        copiar_al_portapapeles(resp.text)
    print()


# ─── Flujo C → Generar PDF del recibo ────────────────────────────────────────

def flujo_c(connection, empresa, matricula, transaccion):
    """Consulta TZRCFDP_EMAIL_HTML y genera un PDF con el contenido."""
    print(f"[INFO] Modo recibo PDF para {matricula}, tx={transaccion}")

    resultado = consultar_recibo_html(connection, empresa, matricula, transaccion)

    if resultado is None:
        print(f"[INFO] No se encontró recibo HTML para matrícula={matricula}, transacción={transaccion}\n")
        return

    html, id_interno = resultado

    # Abrir explorador para elegir dónde guardar el PDF
    nombre_default = f"{matricula}_{id_interno}.pdf"
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        ruta_pdf = filedialog.asksaveasfilename(
            title="Guardar recibo PDF",
            initialfile=nombre_default,
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        root.destroy()
    except Exception:
        ruta_pdf = ""

    if not ruta_pdf:
        print("[INFO] Guardado cancelado.\n")
        return

    try:
        with open(ruta_pdf, "w+b") as pdf_file:
            status = pisa.CreatePDF(html, dest=pdf_file)
        if status.err:
            print(f"[ERROR] xhtml2pdf reportó errores al generar el PDF.\n")
            return
        print(f"[OK] PDF generado: {ruta_pdf}")
        copiar_al_portapapeles(ruta_pdf)
        print("[CLIPBOARD] Ruta del PDF copiada al portapapeles.\n")
    except Exception as e:
        print(f"[ERROR] No se pudo generar el PDF: {e}\n")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _imprimir_url_params(datos_sql):
    """Imprime los parámetros de URL de SQL Server."""
    fecha_raw = datos_sql["fecha"]
    try:
        fecha_dt = datetime.strptime(fecha_raw[:10], "%Y-%m-%d")
        fecha_fmt = fecha_dt.strftime("%Y-%m-%d")
    except Exception:
        fecha_fmt = fecha_raw[:10]

    url_params = (
        f"&fechaTicket={fecha_fmt}"
        f"&folioInt={datos_sql['foliopago']}"
        f"&folio={datos_sql['referenciaUnica']}"
    )
    print(f"\n{url_params}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  FACTURADOR 2.0 - Consulta de datos de facturación")
    print("  Escribe '#' para cerrar la conexión y salir.")
    print("=" * 60)

    try:
        connection = conectar()
        print("\n[OK] Conexión a Oracle establecida.\n")
    except Exception as e:
        print(f"\n[ERROR] No se pudo conectar a Oracle: {e}")
        return

    try:
        while True:
            entrada = input("Matrícula,Transacción (o '#' para salir): ").strip()

            if entrada == "#":
                print("\n[INFO] Cerrando conexión...")
                break

            partes = entrada.split(",")
            if len(partes) < 2 or len(partes) > 3:
                print(INSTRUCCIONES)
                continue

            matricula = partes[0].strip()
            flag = partes[2].strip().upper() if len(partes) == 3 else ""
            forzar_w = flag == "W"
            forzar_s = flag == "S"
            forzar_c = flag == "C"

            if flag and flag not in ("W", "S", "C"):
                print(f"[ERROR] Flag '{partes[2].strip()}' no reconocido. Usa 'w', 's' o 'c'.")
                print(INSTRUCCIONES)
                continue

            try:
                transaccion = int(partes[1].strip())
            except ValueError:
                print("[ERROR] La transacción debe ser un número entero.")
                print(INSTRUCCIONES)
                continue

            empresa, error = determinar_empresa(matricula)
            if error:
                print(f"[ERROR] {error}\n")
                continue

            try:
                # Validar si el pago es facturable (detail code empieza con 4)
                facturable, detail_code = es_facturable(connection, empresa, matricula, transaccion)
                if not facturable:
                    if detail_code is None:
                        print(f"[ERROR] No se encontró la transacción {transaccion} para {matricula}.\n")
                    else:
                        print(f"[NO FACTURABLE] El código de detalle '{detail_code}' no empieza con 4. Este pago no es facturable.\n")
                    continue

                print(f"[✓] Código de detalle: {detail_code} — facturable.")

                if forzar_s:
                    flujo_s(connection, empresa, matricula, transaccion)
                elif forzar_c:
                    flujo_c(connection, empresa, matricula, transaccion)
                else:
                    flujo_normal(connection, empresa, matricula, transaccion, forzar_w)
            except Exception as e:
                print(f"[ERROR] {e}\n")

    except (KeyboardInterrupt, EOFError):
        print("\n\n[INFO] Interrupción detectada. Cerrando...")
    finally:
        connection.close()
        print("[OK] Conexión cerrada. Hasta luego.")


if __name__ == "__main__":
    main()
