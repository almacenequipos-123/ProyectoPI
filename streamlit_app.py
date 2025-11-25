# streamlit_app.py
import streamlit as st
from datetime import datetime, date
import pandas as pd
from sheets_helper import SheetDB
from PIL import Image
from pyzbar.pyzbar import decode
import io
import traceback

st.set_page_config(page_title="Inventario - Escaneo QR/Barcode", layout="wide")
st.title("📲 Inventario de Herramientas — Escaneo QR / Código de barras")

# ---------- Config ----------
SPREADSHEET_DEFAULT = "InventarioHerramientas"
HERRAMIENTAS_SHEET = "Herramientas"
MOVIMIENTOS_SHEET = "Movimientos"

st.sidebar.header("Configuración")
spreadsheet_name = st.sidebar.text_input("Nombre de la Google Sheet", value=SPREADSHEET_DEFAULT)

# Credenciales: usar st.secrets["gcp_service_account"] en Streamlit Cloud (recomendado)
if "gcp_service_account" in st.secrets:
    creds_mode = "secrets"
else:
    creds_mode = "local"
    creds_path = st.sidebar.text_input("Ruta al JSON (solo local)", value="")

if creds_mode == "local" and not creds_path:
    st.sidebar.warning("En local debes indicar la ruta al JSON de la cuenta de servicio.")
elif creds_mode == "secrets":
    st.sidebar.success("Conexión vía Streamlit Secrets detectada.")

# Conectar a Google Sheets
try:
    if creds_mode == "secrets":
        service_account_info = st.secrets["gcp_service_account"]
        db = SheetDB(spreadsheet_name, service_account_info=service_account_info)
    else:
        db = SheetDB(spreadsheet_name, creds_path=creds_path)

    db.ensure_sheets_exist([HERRAMIENTAS_SHEET, MOVIMIENTOS_SHEET])
except Exception as e:
    st.error("Error conectando a Google Sheets: " + str(e))
    st.write(traceback.format_exc())
    st.stop()

# ---------- Helpers ----------
def decode_barcode_from_pil(pil_image):
    """
    Devuelve lista de dicts: [{'type':..., 'data':...}, ...]
    """
    try:
        decoded = decode(pil_image)
    except Exception as e:
        # pyzbar puede lanzar si falta zbar
        st.error("Error en pyzbar: " + str(e))
        return []
    results = []
    for obj in decoded:
        data = obj.data.decode('utf-8')
        t = obj.type
        results.append({'type': t, 'data': data})
    return results

def register_movement_to_sheet(codigo, descripcion, tipo, usuario_nombre, cantidad, fecha_iso, registrado_por, observaciones):
    timestamp = datetime.utcnow().isoformat()
    # fila: timestamp,codigo,descripcion,tipo,usuario,cantidad,fecha,registrado_por,observaciones
    row = [timestamp, codigo, descripcion, tipo, usuario_nombre, int(cantidad), fecha_iso, registrado_por, observaciones]
    db.append_row(MOVIMIENTOS_SHEET, row)

# ---------- UI ----------
tab1, tab2, tab3 = st.tabs(["Escanear (cámara)", "Registrar manual / Scanner USB", "Catálogo / Movimientos"])

with tab1:
    st.subheader("Escanear QR o código de barras con la cámara (st.camera_input)")
    st.markdown(
        "- Usa un móvil o webcam. Toca el botón de la cámara, toma la foto enfocando el QR/barcode.\n"
        "- La app intentará decodificar automáticamente y te mostrará los datos.\n"
        "- Puedes confirmar y registrar como entrada o salida."
    )
    img_file_buffer = st.camera_input("Toma una foto del código QR / barcode")

    if img_file_buffer is not None:
        try:
            # leer imagen como PIL
            image = Image.open(img_file_buffer)
            results = decode_barcode_from_pil(image)
            if not results:
                st.warning("No se detectó QR/código o pyzbar no devolvió resultados. Puedes subir la imagen o usar scanner USB.")
                st.image(image, caption="Imagen tomada", use_column_width=True)
            else:
                st.image(image, caption="Imagen tomada", use_column_width=True)
                st.success(f"Se detectaron {len(results)} código(s).")
                for i, r in enumerate(results):
                    st.markdown(f"**{i+1}. Tipo:** {r['type']}  \n**Contenido:** `{r['data']}`")
                # si hay varios, tomar el primero como default
                code_value = results[0]['data']
                st.session_state['decoded_code'] = code_value
                st.markdown("### Confirmar y registrar movimiento")
                with st.form("confirm_form"):
                    codigo = st.text_input("Código detectado", value=st.session_state.get('decoded_code',''))
                    descripcion = st.text_input("Descripción (opcional)")
                    tipo = st.radio("Tipo", options=['salida','entrada'], horizontal=True)
                    usuario_nombre = st.text_input("Nombre del usuario")
                    cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
                    fecha_manual = st.date_input("Fecha", value=date.today())
                    obs = st.text_area("Observaciones (opcional)", value="")
                    registrado_por = st.text_input("Registrado por (usuario del sistema)", value="streamlit_user")
                    submit = st.form_submit_button("Registrar movimiento")
                    if submit:
                        if not codigo.strip() or not usuario_nombre.strip():
                            st.warning("Código y nombre del usuario son obligatorios.")
                        else:
                            try:
                                register_movement_to_sheet(codigo.strip(), descripcion, tipo, usuario_nombre.strip(), cantidad, fecha_manual.isoformat(), registrado_por.strip(), obs)
                                st.success(f"Movimiento registrado: {tipo} — {codigo.strip()} x{cantidad} por {usuario_nombre}")
                            except Exception as e:
                                st.error("Error registrando movimiento: " + str(e))
        except Exception as e:
            st.error("Error procesando la imagen: " + str(e))
            st.write(traceback.format_exc())

with tab2:
    st.subheader("Registro manual o con scanner USB (keyboard wedge)")
    st.markdown(
        "- Si tu scanner USB actúa como teclado, coloca el cursor en 'Código' y escanea: el valor quedará en el input.\n"
        "- Rellena los demás campos y pulsa 'Registrar movimiento'."
    )
    with st.form("manual_form"):
        codigo = st.text_input("Código (o escanea con scanner USB)", key="manual_codigo")
        descripcion = st.text_input("Descripción (opcional)")
        tipo = st.radio("Tipo", options=['salida','entrada'], horizontal=True)
        usuario_nombre = st.text_input("Nombre del usuario")
        cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
        fecha_manual = st.date_input("Fecha", value=date.today())
        obs = st.text_area("Observaciones (opcional)")
        registrado_por = st.text_input("Registrado por (usuario del sistema)", value="streamlit_user")
        submit2 = st.form_submit_button("Registrar movimiento")
        if submit2:
            if not codigo.strip() or not usuario_nombre.strip():
                st.warning("Código y nombre del usuario son obligatorios.")
            else:
                try:
                    register_movement_to_sheet(codigo.strip(), descripcion, tipo, usuario_nombre.strip(), cantidad, fecha_manual.isoformat(), registrado_por.strip(), obs)
                    st.success(f"Movimiento registrado: {tipo} — {codigo.strip()} x{cantidad} por {usuario_nombre}")
                    st.experimental_rerun()
                except Exception as e:
                    st.error("Error registrando movimiento: " + str(e))

with tab3:
    st.subheader("Catálogo y Movimientos")
    try:
        tools_df = db.compute_stock_from_movements(herramientas_sheet=HERRAMIENTAS_SHEET, movimientos_sheet=MOVIMIENTOS_SHEET)
        if tools_df.empty:
            st.info("La hoja 'Herramientas' está vacía. Pega el CSV de ejemplo en la hoja.")
        else:
            st.dataframe(tools_df[['codigo','nombre','descripcion','ubicacion','stock_inicial','delta_mov','stock_actual']].fillna(''))
            csv = tools_df.to_csv(index=False)
            st.download_button("⬇️ Descargar catálogo (CSV)", csv, file_name="catalogo_herramientas.csv", mime="text/csv")
    except Exception as e:
        st.error("Error calculando stock: " + str(e))

    st.markdown("---")
    st.markdown("Últimos movimientos:")
    try:
        mov_df = db.read_sheet_df(MOVIMIENTOS_SHEET)
        if mov_df.empty:
            st.info("No hay movimientos registrados aún.")
        else:
            if 'timestamp' in mov_df.columns:
                mov_df['timestamp_parsed'] = pd.to_datetime(mov_df['timestamp'], errors='coerce')
                mov_df = mov_df.sort_values('timestamp_parsed', ascending=False)
            st.dataframe(mov_df.head(300))
            st.download_button("⬇️ Descargar Movimientos (CSV)", mov_df.to_csv(index=False), file_name="movimientos.csv", mime="text/csv")
    except Exception as e:
        st.error("Error leyendo Movimientos: " + str(e))

# Footer / tips
st.info(
    "Tips:\n"
    "- Si pyzbar muestra error en deploy (falta la lib zbar), usa el modo 'Registro manual' o un scanner USB.\n"
    "- Puedes generar etiquetas QR con el contenido del campo 'codigo' y pegarlas a las herramientas.\n"
    "- Si quieres, te doy el script para autogenerar los PNG de QR en lote."
)
