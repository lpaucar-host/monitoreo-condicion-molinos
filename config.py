from pathlib import Path

APP_TITLE = "Monitoreo de Condición · Molinos"
DATA_DIR = Path(__file__).resolve().parent / "data"
EXCEL_NAME = "MONITOREO_MOLINOS.xlsx"
EXCEL_PATH = DATA_DIR / EXCEL_NAME

SHEETS_MEDICION = ["Mo 1A", "Mo 1", "MS N°2", "MS N°3", "MR N°4"]
SHEET_EQUIPOS = "DIM_EQUIPO"
SHEET_PUNTOS = "DIM_PUNTO"

# Nombres visibles para gestión. El TAG se conserva como dato secundario.
EQUIPO_CORTO = {
    "MOL-RD08-YA": "Molino 1A",
    "MOL-RD01-YA": "Molino 1",
    "MOL-BO01-YA": "Molino 2",
    "MOL-BO02-YA": "Molino 3",
    "MOL-BO03-YA": "Molino 4",
}

# Orden global: Molino 1A siempre primero.
ORDEN_EQUIPO = {
    "MOL-RD08-YA": 1,
    "MOL-RD01-YA": 2,
    "MOL-BO01-YA": 3,
    "MOL-BO02-YA": 4,
    "MOL-BO03-YA": 5,
}

# Límites oficiales
LIMITES = {
    "Vibracion-Velocidad": {
        "unidad": "mm/s",
        "cortes": [3.0, 5.0, 7.0],
        "estados": ["NORMAL", "TOLERABLE", "ALERTA", "PELIGRO"],
    },
    "Vibracion-Aceleracion": {
        "unidad": "gE",
        "cortes": [0.75, 1.0, 3.0],
        "estados": ["NORMAL", "TOLERABLE", "ALERTA", "PELIGRO"],
    },
    "Temperatura": {
        "unidad": "°C",
        "cortes": [45.0, 60.0],
        "estados": ["ACEPTADO", "MODERADO", "CRITICO"],
    },
}

# Paleta única de semáforo
COLORES = {
    "NORMAL": "#2E7D32",
    "ACEPTADO": "#2E7D32",
    "TOLERABLE": "#F9A825",
    "MODERADO": "#F9A825",
    "ALERTA": "#EF6C00",
    "PELIGRO": "#C62828",
    "CRITICO": "#C62828",
    "SIN DATO": "#78909C",
}

AZUL = "#123A63"
AZUL_CLARO = "#EAF2F8"

# Diseño ejecutivo V2
UI = {
    "navy": "#123A63",
    "navy_dark": "#0B2A45",
    "bg": "#F5F7FA",
    "surface": "#FFFFFF",
    "border": "#D9E2EC",
    "text": "#17212B",
    "muted": "#64748B",
    "green": "#2E7D32",
    "amber": "#D99A00",
    "orange": "#E86A12",
    "red": "#C62828",
    "blue": "#2563EB",
}
