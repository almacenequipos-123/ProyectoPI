import streamlit as st
from sheet_helper import read_sheet, append_row
from datetime import date, datetime
from PIL import Image
from pyzbar.pyzbar import decode

# IDs de tus dos spreadsheets
ID_CATALOGO = "18_5f4JASdhjZiXJ9FZ220klouRwHEAR29bGMJ3y4PLE"
ID_MOVIMIENTOS = "1J0uvOek8KRZDq0sosg2fIF3sX0vHv_1XwaQruzyUOgc"

RANGE_CATALOGO = "Herramientas!A:F"       # ajusta según tus columnas
RANGE_MOVIMIENTOS = "Movimientos!A:I"     # ajusta según tus columnas

st.title("Inventario (con dos Google Sheets)")

# Escaneo QR / Barcode
img = st.camera_input("Toma foto del QR o código")
if img:
    image = Image.open(img)
    decoded = decode(image)
    if decoded:
        codigo = decoded[0].data.decode("utf-8")
        st.write(f"Código detectado: {codigo}")

        # Buscar en catálogo
        catalogo = read_sheet(ID_CATALOGO, RANGE_CATALOGO)
        headers = catalogo[0]
        rows = catalogo[1:]
        encontrado = None
        for r in rows:
            if r[0] == codigo:
                encontrado = r
                break

        if encontrado:
            nombre = encontrado[1]
            descripcion = encontrado[2]
            ubicacion = encontrado[3] if len(encontrado) > 3 else ""
            stock_inicial = float(encontrado[4]) if len(encontrado) > 4 else 0
            st.write("**Recurso encontrado:**")
            st.write(f"Nombre: {nombre}")
            st.write(f"Descripción: {descripcion}")
            st.write(f"Ubicación: {ubicacion}")
            st.write(f"Stock inicial: {stock_inicial}")
        else:
            st.warning("Código no está en el catálogo.")

        # Formulario para registrar movimiento
        with st.form("mov"):
            tipo = st.radio("Tipo", ["entrada", "salida"])
            usuario = st.text_input("Nombre del usuario")
            cantidad = st.number_input("Cantidad", min_value=1, value=1)
            obs = st.text_area("Observaciones")
            fecha = st.date_input("Fecha movimiento", value=date.today())
            enviado = st.form_submit_button("Registrar")

            if enviado:
                timestamp = datetime.utcnow().isoformat()
                fila = [timestamp, codigo, descripcion, tipo, usuario, cantidad, fecha.isoformat(), "streamlit", obs]
                append_row(ID_MOVIMIENTOS, RANGE_MOVIMIENTOS, fila)
                st.success("Movimiento registrado.")

    else:
        st.error("No se detectó ningún código.")
