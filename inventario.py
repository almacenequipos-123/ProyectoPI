miimport streamlit as st
from sheets_helper import read_sheet

SPREADSHEET_ID = st.secrets["inventario_spreadsheet_id"]
INVENTARIO_SHEET = "InventarioHerramientas"

def cargar_inventario():
    data = read_sheet(SPREADSHEET_ID, INVENTARIO_SHEET)

    if not data:
        st.error("No se pudo leer la hoja de inventario.")
        return []

    headers = data[0]
    rows = data[1:]

    inventario = []
    for r in rows:
        fila = dict(zip(headers, r))
        inventario.append(fila)

    return inventario


def mostrar_inventario():
    st.subheader("📦 Inventario Actual")

    inventario = cargar_inventario()

    if not inventario:
        st.warning("No hay datos para mostrar.")
        return

    st.dataframe(inventario)
