# sheets_helper.py
"""
Helper para Google Sheets usando una Service Account guardada en Streamlit Secrets.
Funciones públicas:
 - read_sheet_as_df(spreadsheet_id, sheet_range) -> pandas.DataFrame
 - append_row(spreadsheet_id, sheet_range, row_values) -> True (lanza excepción si falla)

Comportamiento:
 - Intenta leer credenciales desde st.secrets["gcp_service_account"].
 - Si no existe y hay un archivo local .streamlit/service_account.json lo usará (solo para desarrollo local).
 - Si no encuentra credenciales lanza RuntimeError con mensaje claro.
"""

import os
import json
import streamlit as st
import pandas as pd

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# ---------------------------
# Credenciales / Servicio
# ---------------------------
def _load_service_account_info():
    """
    Retorna el dict con la información de la cuenta de servicio.
    Prioridad:
      1) st.secrets["gcp_service_account"]
      2) archivo local .streamlit/service_account.json (solo para desarrollo)
    Lanza RuntimeError si no hay credenciales.
    """
    if "gcp_service_account" in st.secrets:
        info = st.secrets["gcp_service_account"]
        return info

    # Fallback local (DESARROLLO). NO subir este archivo a repositorios públicos.
    local_path = os.path.join(".streamlit", "service_account.json")
    if os.path.exists(local_path):
        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f)

    raise RuntimeError(
        "No se encontraron credenciales de service account. "
        "Agrega 'gcp_service_account' en Streamlit Secrets o coloca .streamlit/service_account.json (solo local)."
    )

def _get_sheets_resource():
    """
    Construye y devuelve el objeto service.spreadsheets() de la API.
    """
    info = _load_service_account_info()
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)
    return service.spreadsheets()

# ---------------------------
# Operaciones principales
# ---------------------------
def read_sheet_as_df(spreadsheet_id: str, sheet_range: str) -> pd.DataFrame:
    """
    Lee un rango de Google Sheets y devuelve un DataFrame con la primera fila como header.
    spreadsheet_id: ID del spreadsheet (la parte entre /d/ y /edit)
    sheet_range: rango tipo "Sheet1!A:Z" o "Hoja!A1:Z100"
    """
    sheets = _get_sheets_resource()
    res = sheets.values().get(spreadsheetId=spreadsheet_id, range=sheet_range).execute()
    values = res.get("values", [])
    if not values:
        return pd.DataFrame()

    headers = values[0]
    rows = values[1:]
    # Asegurar consistent dtype y rellenar vacíos
    df = pd.DataFrame(rows, columns=headers)
    df = df.replace({None: ""})
    return df

def append_row(spreadsheet_id: str, sheet_range: str, row_values: list) -> bool:
    """
    Agrega una fila al sheet con valueInputOption = USER_ENTERED
    row_values: lista simple con los valores de la fila (en el orden de columnas del rango)
    Retorna True si se ejecutó correctamente. Lanza excepción si hubo error.
    """
    sheets = _get_sheets_resource()
    body = {"values": [row_values]}
    sheets.values().append(
        spreadsheetId=spreadsheet_id,
        range=sheet_range,
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()
    return True
