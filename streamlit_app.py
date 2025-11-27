import streamlit as st
from inventario import mostrar_inventario
from movimientos import registrar_movimiento

# CONFIGURACIÓN DE LA APP
st.set_page_config(
    page_title="WMS de Herramientas",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔧 Sistema de Inventario de Herramientas")

# MENÚ LATERAL
menu = st.sidebar.radio(
    "Menú principal",
    ["📦 Inventario", "➕ Registrar Movimiento"]
)

# ---- PÁGINA: INVENTARIO ----
if menu == "📦 Inventario":
    st.header("📦 Inventario Actual")
    st.info("Esta vista muestra el inventario completo directamente desde Google Sheets.")
    mostrar_inventario()

# ---- PÁGINA: REGISTRAR MOVIMIENTO ----
elif menu == "➕ Registrar Movimiento":
    st.header("➕ Registrar Entrada / Salida")

    codigo = st.text_input("Código de herramienta", placeholder="Ej: 500018")
    tipo = st.selectbox("Tipo de movimiento", ["Entrada", "Salida"])
    cantidad = st.number_input("Cantidad", min_value=1, step=1)
    usuario = st.text_input("Usuario que registra", placeholder="Nombre o iniciales")

    if st.button("Registrar movimiento"):
        if codigo.strip() == "" or usuario.strip() == "":
            st.error("Debes completar todos los campos.")
        else:
            registrar_movimiento(codigo, tipo, cantidad, usuario)
