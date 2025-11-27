import streamlit as st
from sheets_helper import read_sheet, append_row, get_column_index

SPREADSHEET_ID = st.secrets["spreadsheet_id"]
INVENTARIO_SHEET = "Inventario"
MOVIMIENTOS_SHEET = "Movimientos"


def registrar_movimiento(codigo, tipo, cantidad, usuario):
    inventario = read_sheet(SPREADSHEET_ID, INVENTARIO_SHEET)

    if not inventario:
        st.error("No se pudo leer inventario.")
        return

    headers = inventario[0]

    col_codigo = get_column_index(headers, "Codigo")
    col_balance = get_column_index(headers, "Balance actual")

    fila_encontrada = None
    index_fila = None

    for idx, row in enumerate(inventario[1:], start=1):
        if row[col_codigo] == codigo:
            fila_encontrada = row
            index_fila = idx
            break

    if not fila_encontrada:
        st.error("No existe ese código en el inventario.")
        return

    balance_actual = float(fila_encontrada[col_balance])

    if tipo == "Salida":
        nuevo_balance = balance_actual - cantidad
        if nuevo_balance < 0:
            st.error("No hay suficientes unidades para realizar la salida.")
            return
    else:
        nuevo_balance = balance_actual + cantidad

    fila_encontrada[col_balance] = str(nuevo_balance)

    # Append en Movimientos
    append_row(
        SPREADSHEET_ID,
        MOVIMIENTOS_SHEET,
        [codigo, tipo, cantidad, usuario, nuevo_balance]
    )

    st.success("Movimiento registrado correctamente.")
