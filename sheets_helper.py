# sheets_helper.py

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# Permisos para Google Sheets y Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_sheets():
    """
    Crea el cliente de gspread usando st.secrets
    y devuelve las hojas Inventario y Movimientos.
    Requiere que en st.secrets existan:
      - st.secrets["gcp_service_account"]
      - st.secrets["gsheets"]["spreadsheet_name"]
    """
    service_account_info = st.secrets["gcp_service_account"]
    gsheets_cfg = st.secrets["gsheets"]

    spreadsheet_name = gsheets_cfg["spreadsheet_name"]

    # Credenciales del service account
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES
    )
    client = gspread.authorize(creds)

    # Abrir el archivo de Google Sheets por nombre
    sh = client.open(spreadsheet_name)

    # Hojas: Inventario y Movimientos
    sh_inventario = sh.worksheet("inventario")
    sh_movimientos = sh.worksheet("movimientos")

    return sh_inventario, sh_movimientos
