# sheets_helper.py

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# Solo Google Sheets API
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_sheets():
    """
    Crea el cliente de gspread usando st.secrets
    y devuelve las hojas Inventario y Movimientos.

    Requiere en st.secrets:
      [gsheets]
      spreadsheet_id = "18_5f4JASdhjZiXJ9FZ220klouRwHEAR29bGMJ3y4PLE"

      [gcp_service_account]
      ...datos del JSON...
    """
    service_account_info = st.secrets["gcp_service_account"]
    gsheets_cfg = st.secrets["gsheets"]

    spreadsheet_id = gsheets_cfg["spreadsheet_id"]

    # Credenciales del service account
    creds = Credentials.from_service_account_info(
        service_account_info,
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)

    # Abrir el archivo de Google Sheets por ID
    sh = client.open_by_key(spreadsheet_id)

    # Hojas: Inventario y Movimientos
    sh_inventario = sh.worksheet("Inventario")
    sh_movimientos = sh.worksheet("Movimientos")

    return sh_inventario, sh_movimientos
