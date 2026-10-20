# Facturador 2.0 — Documentación Funcional

## Descripción general

Herramienta de línea de comandos para consultar, armar y generar facturas electrónicas (CFDI) de alumnos. Se conecta a **Oracle Banner** para datos fiscales y de cartera, a **SQL Server** para pagos web (ISM), y a **APIs REST** para consulta de histórico y generación de facturas.

Soporta tres instituciones: **ULA**, **UTC/CETC** y **UTG**, detectadas automáticamente por el prefijo de matrícula.

---

## Arquitectura del proyecto

```
Facturador2.0/
├── main.py               ← Punto de entrada, flujos principales
├── oracle_client.py       ← Conexión y queries a Oracle Banner
├── sqlserver_client.py    ← Conexión y queries a SQL Server (pagos web)
├── facturacion_api.py     ← Consumo de APIs REST (histórico + facturación)
├── csf.py                 ← Lector de Constancia de Situación Fiscal (PDF SAT)
├── txt_generator.py       ← Generador de archivos TXT para UTC/CETC
├── catalogos.py           ← Catálogos SAT, URLs, mapeos de empresa
├── utils.py               ← Funciones utilitarias compartidas
├── .env                   ← Credenciales (Oracle, SQL Server)
└── DOCUMENTACION.md       ← Este archivo
```

---

## Instrucciones de uso

| Entrada | Descripción |
|---|---|
| `MATRICULA,TRANSACCION` | Consulta normal de datos fiscales |
| `MATRICULA,TRANSACCION,w` | Flujo para pagos web (periodo W) |
| `MATRICULA,TRANSACCION,s` | Auto-facturación con confirmación |
| `MATRICULA,TRANSACCION,c` | Genera PDF del recibo desde Oracle |
| `#` | Cierra conexión y sale |

**Detección de empresa** (automática por matrícula):
- `U...` → ULA
- `G...` → UTG
- Numérica → UTC

---

## Validación de facturabilidad

**Antes de cualquier flujo**, el sistema valida que la transacción sea facturable consultando `TBRACCD_DETAIL_CODE` en Oracle Banner.

- Si el código de detalle **empieza con `4`** → el pago es facturable, se continúa al flujo.
- Si **no empieza con `4`** → se muestra `[NO FACTURABLE]` con el código de detalle y se detiene.
- Si no se encuentra la transacción → se muestra error.

---

## Flujos principales

### 1. Flujo Normal — `MATRICULA,TRANSACCION`

**Propósito:** Consultar datos fiscales del alumno y armar el body JSON para facturación manual.

```
Entrada → Validar facturabilidad → Consultar Oracle (QUERY_FACTURACION)
  ├─ Sin datos → Mensaje informativo
  ├─ Periodo con W → Redirige a Flujo W con Oracle
  └─ Datos normales → Arma JSON formato Receptor → Copia al portapapeles
```

**Formato de salida (no W):**
```json
{
  "Receptor": {
    "nombre": "...",
    "rfc": "...",
    "usocfdi": "G03",
    "regimenfiscal": "605",
    "cp": "22223",
    "domicilioreceptor": {
      "calle": "...", "NoExterior": "", "NoInterior": "",
      "colonia": "", "municipio": "...", "estado": "BCN",
      "pais": "MEX", "codigoPostal": "22223"
    }
  },
  "total": "590.36",
  "matricula": "U99452948",
  "TransaccionCargo": "3",
  "transactionPaid": 0
}
```

**Se copia al portapapeles:** JSON + matrícula + transacción (en secuencia).

---

### 2. Flujo W — `MATRICULA,TRANSACCION,w`

**Propósito:** Consultar datos de pagos realizados por plataforma web (periodo contiene "W"). Busca en SQL Server la tabla `ISM_facturacion`.

#### 2a. Con datos Oracle

```
Entrada → Validar facturabilidad → Oracle tiene datos con W
  → Buscar en SQL Server por nombre del alumno
  ├─ SQL Server encontró datos:
  │   ├─ Compara montos Oracle vs SQL Server
  │   ├─ UTC/CETC → Genera archivo TXT para facturación
  │   └─ Otra empresa → Imprime URL params + JSON formato CSF
  └─ SQL Server sin datos → JSON formato CSF solo con datos Oracle
```

#### 2b. Sin datos Oracle (forzado con `,w` o detectado desde `,s`)

```
Entrada → Validar facturabilidad → Oracle NO tiene datos
  → Buscar nombre por SPRIDEN → Buscar en SQL Server
  ├─ UTC/CETC → Pide CSF por explorador → Genera TXT
  └─ Otra empresa → URL params → Pide CSF por explorador
      ├─ CSF cargada → JSON formato CSF con datos fiscales completos
      └─ CSF cancelada → JSON formato CSF con datos vacíos
```

**Formato de salida W:**
```
&fechaTicket=2026-10-05&folioInt=00202871&folio=99000105427145990516

{
  "rfc": "",
  "nombre": "SAMANTHA MEZA BALTAZAR",
  "domicilioFiscal": "",
  "regimenFiscal": "",
  "usoCFDI": "G03",
  "email": "smeza.55@gmail.com",
  "curp": "",
  "responseType": "xml",
  "domicilioReceptor": {
    "calle": "", "municipio": "", "pais": "MEX",
    "codigoPostal": "", "estado": ""
  }
}
```

**Este flujo NUNCA hace POST. Solo arma datos y copia al portapapeles.**

---

### 3. Flujo S — Auto-facturación — `MATRICULA,TRANSACCION,s`

**Propósito:** Generar factura completa de forma semi-automática. Revisa si ya existe, arma el body, pide confirmación y envía POST a la API.

```
Entrada → Validar facturabilidad
  → Consultar histórico (API REST)
  ├─ Ya facturada → Muestra PDF/XML existentes → FIN
  └─ No facturada → Consultar Oracle
      ├─ Periodo con W → Delega a Flujo W (sin POST) → FIN
      ├─ Con datos Oracle → Arma body formato Receptor
      └─ Sin datos Oracle → Obtiene total + periodo
          ├─ Periodo con W → Delega a Flujo W (sin POST) → FIN
          └─ No W → Pide CSF por explorador → Arma body Receptor
  → Muestra body → Pide confirmación (s/n)
  → POST a API de facturación → Muestra respuesta
```

**Comportamiento con W:** Si en cualquier punto detecta periodo W, delega al flujo W correspondiente. Arma el body en formato CSF/W, lo muestra y copia al portapapeles, pero **nunca hace POST**.

---

### 4. Flujo C — Generar PDF del recibo — `MATRICULA,TRANSACCION,c`

**Propósito:** Extraer el HTML del recibo almacenado en `TZRCFDP_EMAIL_HTML` (Oracle) y convertirlo a PDF.

```
Entrada → Validar facturabilidad
  → Consultar TZRCFDP_EMAIL_HTML + TZRCFDP_IDINTERNO
  ├─ Sin datos → Mensaje informativo
  └─ Con datos → Limpia comillas simples del HTML
      → Abre explorador "Guardar como" (nombre sugerido: {matricula}_{idInterno}.pdf)
      → Genera PDF con xhtml2pdf
      → Copia ruta del PDF al portapapeles
```

**Query utilizado:**
```sql
WITH ALUMNO AS (
    SELECT SPRIDEN_PIDM FROM SPRIDEN
    WHERE SPRIDEN_ID = :matricula AND SPRIDEN_CHANGE_IND IS NULL
)
SELECT TZRCFDP_EMAIL_HTML, TZRCFDP_IDINTERNO
FROM TZRCFDP
JOIN ALUMNO A ON TZRCFDP_PIDM = A.SPRIDEN_PIDM
WHERE TZRCFDP_RECEIPT_NUMBER = (
    SELECT TBRACCD_RECEIPT_NUMBER FROM TBRACCD
    WHERE TBRACCD_PIDM = A.SPRIDEN_PIDM
      AND TBRACCD_TRAN_NUMBER = :transaccion
)
AND TZRCFDP_PIDM = A.SPRIDEN_PIDM
```

---

## Generador de TXT (UTC/CETC)

Para pagos web de UTC y CETC, genera un archivo TXT con formato específico para carga en el sistema de facturación. Incluye:

- Datos del documento (folio, fecha, método de pago)
- Datos del emisor (RFC, nombre de la empresa)
- Datos del receptor (RFC, nombre, dirección, régimen fiscal)
- Datos de la línea de pago (cantidad, clave SAT, concepto)

**Nombre del archivo:** `F-{folioPago}---{fecha}_{compañía}_ISM.txt`

---

## Lector de CSF (Constancia de Situación Fiscal)

Extrae datos fiscales de un PDF de la CSF emitida por el SAT usando `pdfplumber`.

**Datos extraídos:**
- RFC
- Nombre completo (persona física: Nombre + Apellidos; persona moral: Denominación/Razón Social)
- CURP
- Código Postal
- Calle (nombre de vialidad)
- Municipio
- Estado (convertido a abreviatura SAT)
- Régimen fiscal (código SAT)

**Limpieza automática:**
- Elimina texto basura del PDF ("VALIDA TU INFORMACIÓN FISCAL", IDs numéricos largos)
- Preserva espacios en valores extraídos (ej: "AVENIDA REFORMA", no "AVENIDAREFORMA")
- Muestra resumen de datos extraídos para verificación visual

**Resumen visual al cargar CSF:**
```
──────────────────────────────────────────────────
  DATOS EXTRAÍDOS DE LA CSF
──────────────────────────────────────────────────
  Nombre:          JUAN CARLOS GARCIA LOPEZ
  RFC:             GALJ900101ABC
  Régimen Fiscal:  612
  Uso CFDI:        G03
  Código Postal:   06600
  Calle:           AVENIDA REFORMA
  Municipio:       CUAUHTEMOC
  Estado:          CMX
  País:            MEX
──────────────────────────────────────────────────
```

---

## Fuentes de datos

| Fuente | Tecnología | Uso |
|---|---|---|
| Oracle Banner | `oracledb` | Datos fiscales, cartera (TBRACCD), identidad (SPRIDEN), recibos (TZRCFDP) |
| SQL Server | `pymssql` | Pagos web (`ISM_facturacion` en Simulador_UAT) |
| API REST | `requests` | Histórico de facturas + generación de CFDI |
| PDF CSF | `pdfplumber` | Extracción de datos fiscales de constancia SAT |
| HTML→PDF | `xhtml2pdf` | Conversión de recibos HTML a PDF |

---

## Tablas Oracle consultadas

| Tabla | Descripción |
|---|---|
| `SPRIDEN` | Identidad del alumno (matrícula, PIDM, nombre) |
| `TBRACCD` | Cartera/cuentas por cobrar (transacciones, montos, periodo, detail code, receipt number) |
| `GORADID` | IDs adicionales (RFC, CURP, uso CFDI, régimen fiscal) |
| `SPREMRG` | Contacto de facturación (nombre, dirección, CP) |
| `STVSTAT` / `STVNATN` | Catálogos de estados y países |
| `TZRCFDP` | Recibos digitales (HTML del recibo, ID interno) — tabla custom |

---

## Dependencias Python

| Paquete | Uso |
|---|---|
| `oracledb` | Conexión a Oracle Banner |
| `pymssql` | Conexión a SQL Server |
| `requests` | Consumo de APIs REST |
| `pdfplumber` | Lectura de PDFs (CSF del SAT) |
| `xhtml2pdf` | Generación de PDF desde HTML |
| `python-dotenv` | Variables de entorno (.env) |

---

## Diagrama de flujo general

```
                    ┌──────────────────────┐
                    │  Matrícula,TX[,flag]  │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Detectar empresa      │
                    │ (U→ULA, G→UTG, #→UTC)│
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ ¿Es facturable?       │
                    │ (detail code → 4xxx)  │
                    └───┬──────────────┬───┘
                     NO │              │ SÍ
                  ┌─────▼─────┐  ┌─────▼─────┐
                  │   STOP    │  │ ¿Qué flag? │
                  └───────────┘  └──┬──┬──┬───┘
                         ┌──────────┘  │  └──────────┐
                         │             │             │
                    ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
                    │ (ninguno│  │   ,s    │  │   ,c    │
                    │  o ,w)  │  │         │  │         │
                    └────┬────┘  └────┬────┘  └────┬────┘
                         │            │            │
                    ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
                    │  Flujo  │  │  Flujo  │  │  Flujo  │
                    │ Normal  │  │   S     │  │   C     │
                    │ (o W)   │  │         │  │  (PDF)  │
                    └────┬────┘  └────┬────┘  └─────────┘
                         │            │
                    ┌────▼────┐  ┌────▼────────────┐
                    │ ¿Es W?  │  │ Histórico → W?  │
                    └──┬───┬──┘  └──┬────────┬─────┘
                    SÍ │   │ NO  SÍ │        │ NO
                  ┌────▼┐ ┌▼────┐┌──▼───┐ ┌──▼─────────┐
                  │CSF  │ │JSON ││CSF   │ │Confirmar   │
                  │+ URL│ │Recv ││+ URL │ │→ POST API  │
                  │params││     ││params│ │→ Factura   │
                  └─────┘ └─────┘└──────┘ └────────────┘
```
