import os
from typing import Tuple

import gspread
import streamlit as st
import toml
from google.oauth2.service_account import Credentials

# Alcances necesarios para Google Sheets y Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _load_config_from_file() -> Tuple[dict, dict]:
    """
    Intenta cargar la configuración desde un archivo secrets.toml
    en distintas ubicaciones típicas del proyecto.
    Devuelve (config_gsheets, config_service_account).
    """
    possible_paths = [
        "./.streamlit/secrets.toml",
        "./streamlit/secrets.toml",
        "./secrets.toml",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            data = toml.load(path)

            if "gsheets" not in data or "gcp_service_account" not in data:
                raise RuntimeError(
                    f"El archivo {path} existe pero no contiene las secciones "
                    "[gsheets] y [gcp_service_account]."
                )

            return data["gsheets"], data["gcp_service_account"]

    raise RuntimeError(
        "No se encontró archivo secrets.toml con las secciones "
        "[gsheets] y [gcp_service_account]. "
        "Revisa la ubicación y el contenido del archivo."
    )


def _load_config() -> Tuple[dict, dict]:
    """
    Intenta cargar configuración de dos formas:
    1. Desde st.secrets (modo recomendado en Streamlit Cloud).
    2. Si falla, desde un archivo secrets.toml en el proyecto.
    Devuelve (config_gsheets, config_service_account).
    """
    try:
        gsheets_cfg = st.secrets["gsheets"]
        sa_info = st.secrets["gcp_service_account"]
        return gsheets_cfg, sa_info
    except Exception:
        # Fallback a archivo local secrets.toml
        return _load_config_from_file()


def get_gspread_client() -> gspread.Client:
    """
    Crea y devuelve un cliente de gspread usando las credenciales
    ya sea de st.secrets o de secrets.toml.
    """
    gsheets_cfg, sa_info = _load_config()

    creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client


def get_sheets():
    """
    Devuelve las hojas de trabajo de Inventario y Movimientos.
    El nombre del archivo se toma de:
        [gsheets]
        spreadsheet_name = "NOMBRE_EN_DRIVE"
    """
    client = get_gspread_client()
    gsheets_cfg, _ = _load_config()
    spreadsheet_name = gsheets_cfg["spreadsheet_name"]

    sh = client.open(spreadsheet_name)
    sh_inventario = sh.worksheet("Inventario")
    sh_movimientos = sh.worksheet("Movimientos")

    return sh_inventario, sh_movimientos
