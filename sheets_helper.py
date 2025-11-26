# sheets_helper.py
import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheets_resource():
    """
    Crea y devuelve el recurso sheets (service.spreadsheets()) usando st.secrets["gcp_service_account"]
    """
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("No se encontró st.secrets['gcp_service_account']. Agrega el secret en Streamlit Cloud.")
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)
    return service.spreadsheets()

def read_sheet_as_df(spreadsheet_id, rango):
    """
    Lee un rango (incluye header en la fila 1) y devuelve DataFrame.
    """
    sheets = get_sheets_resource()
    res = sheets.values().get(spreadsheetId=spreadsheet_id, range=rango).execute()
    vals = res.get("values", [])
    if not vals:
        return pd.DataFrame()
    headers = vals[0]
    rows = vals[1:]
    return pd.DataFrame(rows, columns=headers)

def append_row(spreadsheet_id, rango, row_values):
    """
    Agrega una fila (row_values = lista) al rango indicado.
    """
    sheets = get_sheets_resource()
    body = {"values": [row_values]}
    sheets.values().append(
        spreadsheetId=spreadsheet_id,
        range=rango,
        valueInputOption="USER_ENTERED",
        body=body
    ).execute()
    return True
