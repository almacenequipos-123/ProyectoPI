import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def connect_sheets():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    service = build("sheets", "v4", credentials=creds)
    return service.spreadsheets()

def read_sheet(spreadsheet_id, range_name):
    sheet = connect_sheets()
    result = sheet.values().get(
        spreadsheetId=spreadsheet_id,
        range=range_name
    ).execute()
    return result.get("values", [])

def append_row(spreadsheet_id, range_name, row_data):
    sheet = connect_sheets()
    sheet.values().append(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body={"values": [row_data]}
    ).execute()
