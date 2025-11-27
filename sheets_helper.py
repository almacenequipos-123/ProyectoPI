import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build


def get_service():
    """Crea el cliente autorizado para Google Sheets usando Streamlit Secrets."""
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds)


def read_sheet(spreadsheet_id, sheet_name):
    """Lee toda la hoja y devuelve filas completas."""
    service = get_service()
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}")
        .execute()
    )
    return result.get("values", [])


def append_row(spreadsheet_id, sheet_name, row_values):
    """Agrega una fila al final de una hoja."""
    service = get_service()
    body = {"values": [row_values]}

    result = (
        service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
            valueInputOption="USER_ENTERED",
            body=body,
        )
        .execute()
    )

    return result


def get_column_index(headers, column_name):
    """Devuelve el índice de una columna basado en su nombre."""
    try:
        return headers.index(column_name)
    except ValueError:
        raise Exception(f"❌ La columna '{column_name}' no existe en la hoja.")
