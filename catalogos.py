"""
Catálogos centralizados del SAT y mapeos de empresa.
"""

# ─── Estados → abreviatura SAT ───────────────────────────────────────────────
ESTADOS_ABREVIATURA = {
    "aguascalientes": "AGU",
    "baja california": "BCN",
    "baja california sur": "BCS",
    "campeche": "CAM",
    "chiapas": "CHP",
    "chihuahua": "CHH",
    "ciudad de mexico": "CDMX",
    "ciudad de méxico": "CDMX",
    "coahuila": "COA",
    "coahuila de zaragoza": "COA",
    "colima": "COL",
    "durango": "DUR",
    "estado de mexico": "MEX",
    "estado de méxico": "MEX",
    "guanajuato": "GUA",
    "guerrero": "GRO",
    "hidalgo": "HID",
    "jalisco": "JAL",
    "mexico": "MEX",
    "méxico": "MEX",
    "michoacan": "MIC",
    "michoacán": "MIC",
    "michoacan de ocampo": "MIC",
    "michoacán de ocampo": "MIC",
    "morelos": "MOR",
    "nayarit": "NAY",
    "nuevo leon": "NLE",
    "nuevo león": "NLE",
    "oaxaca": "OAX",
    "puebla": "PUE",
    "queretaro": "QUE",
    "querétaro": "QUE",
    "quintana roo": "ROO",
    "san luis potosi": "SLP",
    "san luis potosí": "SLP",
    "sinaloa": "SIN",
    "sonora": "SON",
    "tabasco": "TAB",
    "tamaulipas": "TAM",
    "tlaxcala": "TLA",
    "veracruz": "VER",
    "veracruz de ignacio de la llave": "VER",
    "yucatan": "YUC",
    "yucatán": "YUC",
    "zacatecas": "ZAC",
}

# ─── Estados sin espacios (para CSF donde texto viene pegado) ────────────────
ESTADOS_ABREVIATURA_SIN_ESPACIOS = {
    k.replace(" ", ""): v for k, v in ESTADOS_ABREVIATURA.items()
}

# ─── Países → código ISO 3166 ────────────────────────────────────────────────
PAISES_CODIGO = {
    "mexico": "MEX",
    "méxico": "MEX",
    "estados unidos": "USA",
    "estados unidos de america": "USA",
    "canada": "CAN",
    "canadá": "CAN",
}

# ─── Regímenes fiscales del SAT ──────────────────────────────────────────────
REGIMENES_FISCALES = {
    "general de ley personas morales": "601",
    "personas morales con fines no lucrativos": "603",
    "sueldos y salarios e ingresos asimilados a salarios": "605",
    "arrendamiento": "606",
    "regimen de enajenacion o adquisicion de bienes": "607",
    "demás ingresos": "608",
    "consolidación": "609",
    "residentes en el extranjero sin establecimiento permanente en méxico": "610",
    "ingresos por dividendos (socios y accionistas)": "611",
    "personas físicas con actividades empresariales y profesionales": "612",
    "ingresos por intereses": "614",
    "regimen de los ingresos por obtención de premios": "615",
    "sin obligaciones fiscales": "616",
    "sociedades cooperativas de producción que optan por diferir sus ingresos": "620",
    "incorporación fiscal": "621",
    "actividades agrícolas, ganaderas, silvícolas y pesqueras": "622",
    "opcional para grupos de sociedades": "623",
    "coordinados": "624",
    "régimen de las actividades empresariales con ingresos a través de plataformas tecnológicas": "625",
    "simplified trust": "626",
    "régimen simplificado de confianza": "626",
    "simplificado de confianza": "626",
    "hidrocarburos": "628",
    "de los regímenes fiscales preferentes y de las empresas multinacionales": "629",
    "enajenación de acciones en bolsa de valores": "630",
}

# ─── Métodos de pago → código SAT ────────────────────────────────────────────
METODOS_PAGO = {
    "DEBITO": "28",
    "CREDITO": "04",
    "EFECTIVO": "01",
    "PREPAGO": "01",
    "TRANSFERENCIA": "03",
    "CHEQUE": "02",
}

# ─── Campus → código corto para TXT ──────────────────────────────────────────
CAMPUS_CODIGO = {
    "ZRB": "HV",
    "ZRS": "ZR",
    "COA": "COA",
    "TOL": "TL",
    "ATZ": "ATZ",
    "NEZ": "NZ",
    "CUA": "CUA",
    "CHL": "CH",
    "TOR": "TR",
    "ECA": "ECT",
    "IZT": "IZT",
    "RPA": "RPA",
    "IXT": "IXTL",
    "TLA": "TLNP",
    "DIS": "UDIS",
    "TPN": "TPN",
}

# ─── Emisor por compañía ─────────────────────────────────────────────────────
EMISORES = {
    "UTC": {"rfc": "UTC9903183C7", "nombre": "UNIVERSIDAD DE LAS TRES CULTURAS"},
    "CETC": {"rfc": "CET0810145K6", "nombre": "CENTRO EDUCATIVO TRES CULTURAS"},
    "CET": {"rfc": "CET0810145K6", "nombre": "CENTRO EDUCATIVO TRES CULTURAS"},
}

# ─── URLs de facturación por empresa ─────────────────────────────────────────
URLS_FACTURACION = {
    "ULA": {
        "historico": "https://alumnos.ula.edu.mx/facturacion/api/Historico",
        "factura": "https://alumnos.ula.edu.mx/facturacion/api/Factura",
    },
    "UTC": {
        "historico": "https://alumnos.utc.mx/facturacion/api/Historico",
        "factura": "https://alumnos.utc.mx/facturacion/api/factura",
    },
    "UTG": {
        "historico": "https://administrativos.utc.mx/UTEG_Facturacion/api/listado",
        "factura": "https://alumnos.uteg.edu.mx/UTEG_Facturacion/api/factura",
    },
}

# ─── Instrucciones de uso ────────────────────────────────────────────────────
INSTRUCCIONES = """
  ┌─────────────────────────────────────────────────────────┐
  │  INSTRUCCIONES DE USO                                   │
  ├─────────────────────────────────────────────────────────┤
  │                                                         │
  │  MATRICULA,TRANSACCION                                  │
  │    Consulta datos de facturación desde Oracle.           │
  │    Ejemplo: 260169562,83                                │
  │                                                         │
  │  MATRICULA,TRANSACCION,w                                │
  │    Busca pago web en SQL Server (pagos con W).          │
  │    Si es UTC/CETC genera TXT, si no genera JSON CSF.    │
  │    Ejemplo: U99451813,13,w                              │
  │                                                         │
  │  MATRICULA,TRANSACCION,s                                │
  │    Auto-facturación: revisa si ya existe, si no la      │
  │    genera con confirmación. NO aplica para pagos con W. │
  │    Ejemplo: U99999999,48,s                              │
  │                                                         │
  │  MATRICULA,TRANSACCION,c                                │
  │    Genera PDF del recibo (TZRCFDP_EMAIL_HTML).          │
  │    Se guarda en la carpeta 'recibos/'.                  │
  │    Ejemplo: U99308683,148,c                             │
  │                                                         │
  │  #  →  Cerrar conexión y salir.                         │
  └─────────────────────────────────────────────────────────┘
"""
