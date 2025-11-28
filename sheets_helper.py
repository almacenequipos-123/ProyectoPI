import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# Alcances necesarios para Google Sheets y Drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_gspread_client() -> gspread.Client:
    """
    Crea y devuelve un cliente de gspread usando las credenciales
    almacenadas en st.secrets["gcp_service_account"].
    """
    service_account_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    return client


def get_sheets():
    """
    Devuelve las hojas de trabajo de Inventario y Movimientos.
    El nombre del archivo se toma de st.secrets["gsheets"]["spreadsheet_name"].
    """
    client = get_gspread_client()
    spreadsheet_name = st.secrets["gsheets"]["spreadsheet_name"]

    sh = client.open(spreadsheet_name)
    sh_inventario = sh.worksheet("Inventario")
    sh_movimientos = sh.worksheet("Movimientos")

    return sh_inventario, sh_movimientos
