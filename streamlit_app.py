import streamlit as st

from sheets_helper import get_sheets
from movimientos import registrar_movimiento


# ---------------------------
# Cacheamos la conexión a GS
# ---------------------------
@st.cache_resource
def load_sheets():
    return get_sheets()


def main():
    st.set_page_config(page_title="Almacén de herramientas", page_icon="🛠️")
    st.title("Almacén de herramientas - Registro de movimientos")

    sh_inventario, sh_movimientos = load_sheets()

    st.markdown("### Registrar movimiento")

    # Campo para el código (por ahora manual; luego lo llenaremos con QR)
    codigo = st.text_input("Código de la herramienta", key="codigo")

    col1, col2 = st.columns(2)
    with col1:
        tipo = st.selectbox("Tipo de movimiento", ["ENTRADA", "SALIDA"])
    with col2:
        cantidad = st.number_input("Cantidad", min_value=1, step=1, value=1)

    usuario = st.text_input("Usuario que realiza el movimiento")

    if st.button("Registrar movimiento"):
        try:
            nuevo_balance, ts = registrar_movimiento(
                sh_inventario=sh_inventario,
                sh_movimientos=sh_movimientos,
                codigo=codigo,
                tipo=tipo,
                cantidad=cantidad,
                usuario=usuario,
            )
            st.success(
                f"✅ Movimiento registrado a las {ts} (hora Colombia). "
                f"Nuevo balance para {codigo}: {nuevo_balance}."
            )
        except Exception as e:
            st.error(f"❌ Error al registrar el movimiento: {e}")

    st.markdown("---")
    st.markdown("### Consulta rápida de inventario")

    codigo_buscar = st.text_input(
        "Consultar herramienta por código", key="buscar_codigo"
    )
    if st.button("Buscar herramienta"):
        if not codigo_buscar.strip():
            st.warning("Ingresa un código para buscar.")
        else:
            celdas = sh_inventario.findall(codigo_buscar.strip())
            if not celdas:
                st.error(f"No se encontró el código {codigo_buscar} en Inventario.")
            else:
                fila = celdas[0].row
                codigo_val = sh_inventario.cell(fila, 1).value
                descripcion = sh_inventario.cell(fila, 2).value
                estado = sh_inventario.cell(fila, 3).value
                estante = sh_inventario.cell(fila, 4).value
                balance_actual = sh_inventario.cell(fila, 5).value

                st.info(
                    f"**Código:** {codigo_val}\n\n"
                    f"**Descripción:** {descripcion}\n\n"
                    f"**Estado:** {estado}\n\n"
                    f"**Estante:** {estante}\n\n"
                    f"**Balance actual:** {balance_actual}"
                )


if __name__ == "__main__":
    main()
