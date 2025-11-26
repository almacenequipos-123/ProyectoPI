# streamlit_app.py
"""
App Streamlit para Inventario con:
 - lectura de catálogo (Google Sheets vía service account o publicación CSV pública)
 - cálculo de stock a partir de Movimientos
 - registrar movimientos (requiere service account en Streamlit Secrets)
 - fallback: entrada manual de código si pyzbar/cámara no está disponible
"""

import streamlit as st
from datetime import date, datetime
from PIL import Image, UnidentifiedImageError
import pandas as pd

# Import helper (asegúrate que sheets_helper.py está en la raíz)
from sheets_helper import read_sheet_as_df, append_row

# Intentar importar pyzbar (si falla, usar input manual / uploader)
try:
    from pyzbar.pyzbar import decode
    PYZBAR_AVAILABLE = True
except Exception:
    PYZBAR_AVAILABLE = False

st.set_page_config(page_title="Inventario WMS", layout="centered")
st.title("📦 Inventario (con Google Sheets)")

# ---------------------------------------------------------------------
# CONFIG: coloca tus IDs aquí (modifica si es necesario)
ID_CATALOGO = "18_5f4JASdhjZiXJ9FZ220klouRwHEAR29bGMJ3y4PLE"        # hoja con pestaña "Herramientas"
ID_MOVIMIENTOS = "1J0uvOek8KRZDq0sosg2fIF3sX0vHv_1XwaQruzyUOgc"     # hoja con pestaña "Movimientos"
RANGE_CATALOGO = "Herramientas!A:G"    # incluye la columna Fecha de creación
RANGE_MOVIMIENTOS = "Movimientos!A:I"
# Public CSV (opcional) - si tienes la hoja publicada, pega la URL CSV
PUBLIC_CSV_CATALOGO = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTctDNkN1aHFmtjf4Qfa5zy3U8k7vA-VE9rNRiLMz7hTYGmSaWi4fver5PWonwhQtBVolMwv0daZTMY/pub?gid=0&single=true&output=csv"
# ---------------------------------------------------------------------

st.markdown("Usa la cámara para escanear QR (si pyzbar está disponible) o ingresa el código manualmente.")

# --- Entrada: imagen por cámara o uploader ---
image = None
if PYZBAR_AVAILABLE:
    image = st.camera_input("Toma foto del QR o código (si tu dispositivo tiene cámara)")
else:
    st.info("pyzbar no está disponible en este entorno. Usa el campo 'Código manual' o sube una imagen.")
    image = st.file_uploader("Sube la imagen del QR/código (PNG, JPG)")

# --- Decodificar QR si hay imagen y pyzbar está disponible ---
codigo_detectado = None
if image is not None:
    try:
        img = Image.open(image)
        if PYZBAR_AVAILABLE:
            try:
                decoded = decode(img)
                if decoded:
                    codigo_detectado = decoded[0].data.decode("utf-8")
                    st.success(f"Código detectado: {codigo_detectado}")
                else:
                    st.warning("No se detectó código en la imagen. Comprueba calidad o usa el campo manual.")
            except Exception as e:
                st.error("Error decodificando imagen: " + str(e))
        else:
            st.info("Imagen cargada — pyzbar no disponible, por favor introduce el código manualmente si no se detecta.")
    except UnidentifiedImageError:
        st.error("No se pudo abrir la imagen. Usa otro archivo.")
    except Exception as e:
        st.error("Error procesando la imagen: " + str(e))

# Campo manual (si no se detectó)
codigo_manual = st.text_input("Código manual (si no se detectó por cámara)")
codigo = codigo_detectado if codigo_detectado else (codigo_manual.strip() or None)

# --- Función auxiliar: leer catálogo con fallback a CSV público ---
@st.cache_data(ttl=120)
def cargar_catalogo():
    # Primero intentar leer con la cuenta service account (read_sheet_as_df). Si no funciona, fallback a CSV público.
    try:
        df_cat = read_sheet_as_df(ID_CATALOGO, RANGE_CATALOGO)
        # normalizar columnas (strip)
        df_cat.columns = [c.strip() for c in df_cat.columns]
        return df_cat
    except Exception as e:
        # intentar lectura pública
        try:
            df_pub = pd.read_csv(PUBLIC_CSV_CATALOGO)
            df_pub.columns = [c.strip() for c in df_pub.columns]
            st.warning("Lectura vía API falló (posible falta de secret); usando catálogo público (solo lectura).")
            return df_pub
        except Exception as e2:
            # devolver DF vacío y propagar mensaje
            st.error("No se pudo leer catálogo ni por API ni por CSV público. Errores: API->" + str(e) + " | CSV->" + str(e2))
            return pd.DataFrame()

# --- Si hay código, buscar en catálogo y mostrar info ---
if codigo:
    st.info(f"Consultando catálogo para: {codigo}")
    catalogo_df = cargar_catalogo()

    if catalogo_df is None or catalogo_df.empty:
        st.warning("El catálogo está vacío o no se pudo cargar.")
    else:
        # localizar columna 'Codigo' (case-insensitive)
        cols_lower = [c.lower() for c in catalogo_df.columns]
        if 'codigo' in cols_lower:
            codigo_col = catalogo_df.columns[cols_lower.index('codigo')]
        elif 'code' in cols_lower:
            codigo_col = catalogo_df.columns[cols_lower.index('code')]
        else:
            st.error("La hoja de catálogo no tiene una columna llamada 'Codigo' o 'code'. Revisa encabezados.")
            codigo_col = None

        if codigo_col:
            match = catalogo_df[catalogo_df[codigo_col].astype(str) == str(codigo)]
            if match.empty:
                st.warning("Código no está en el catálogo.")
            else:
                row = match.iloc[0]
                # helpers para columnas opcionales
                def get_val(r, name, default=""):
                    name = name.lower()
                    for c in r.index:
                        if c.lower() == name:
                            return r[c]
                    return default

                nombre = get_val(row, "nombre", "")
                descripcion = get_val(row, "descripcion", "")
                ubicacion = get_val(row, "ubicacion", "")
                unidad = get_val(row, "unidad", "")
                try:
                    stock_inicial = int(get_val(row, "stock", 0))
                except Exception:
                    stock_inicial = 0
                fecha_creacion = get_val(row, "fecha de creación", get_val(row, "fecha_creacion", ""))

                st.subheader("📌 Información del recurso")
                st.write(f"**Código:** {codigo}")
                st.write(f"**Nombre:** {nombre}")
                st.write(f"**Descripción:** {descripcion}")
                st.write(f"**Ubicación:** {ubicacion}")
                st.write(f"**Unidad:** {unidad}")
                st.write(f"**Stock inicial:** {stock_inicial}")
                if fecha_creacion:
                    st.write(f"**Fecha creación:** {fecha_creacion}")

                # Calcular stock actual leyendo Movimientos (si es posible)
                entradas = 0
                salidas = 0
                try:
                    movs_df = read_sheet_as_df(ID_MOVIMIENTOS, RANGE_MOVIMIENTOS)
                    if movs_df is not None and not movs_df.empty:
                        cols_mov = [c.lower() for c in movs_df.columns]
                        # buscar columnas codigo,tipo,cantidad
                        if 'codigo' in cols_mov and 'tipo' in cols_mov and 'cantidad' in cols_mov:
                            ccol = movs_df.columns[cols_mov.index('codigo')]
                            tcol = movs_df.columns[cols_mov.index('tipo')]
                            qcol = movs_df.columns[cols_mov.index('cantidad')]
                            entradas = movs_df[(movs_df[ccol].astype(str)==str(codigo)) & (movs_df[tcol].str.lower()=='entrada')][qcol].astype(int).sum() if not movs_df.empty else 0
                            salidas = movs_df[(movs_df[ccol].astype(str)==str(codigo)) & (movs_df[tcol].str.lower()=='salida')][qcol].astype(int).sum() if not movs_df.empty else 0
                        else:
                            st.info("Hoja Movimientos no contiene las columnas 'codigo','tipo','cantidad' necesarias para calcular stock dinámico.")
                    else:
                        st.info("No hay registros en Movimientos (o no se pudieron leer).")
                except Exception as e:
                    st.warning("No se pudo leer Movimientos para calcular stock: " + str(e))

                stock_actual = stock_inicial + entradas - salidas
                st.metric("Stock actual", stock_actual)

                # --- Formulario para registrar movimiento (requiere service account para escribir)
                st.markdown("---")
                st.markdown("### Registrar movimiento")
                with st.form("form_mov"):
                    tipo = st.radio("Tipo", ["entrada", "salida"])
                    usuario = st.text_input("Nombre del usuario")
                    cantidad = st.number_input("Cantidad", min_value=1, value=1)
                    obs = st.text_area("Observaciones")
                    fecha = st.date_input("Fecha del movimiento", value=date.today())
                    enviado = st.form_submit_button("Registrar movimiento")

                    if enviado:
                        fila = [
                            datetime.utcnow().isoformat(),  # timestamp
                            codigo,
                            descripcion,
                            tipo,
                            usuario or "Sin nombre",
                            int(cantidad),
                            fecha.isoformat(),
                            "streamlit",
                            obs or ""
                        ]
                        try:
                            append_row(ID_MOVIMIENTOS, RANGE_MOVIMIENTOS, fila)
                            st.success("✅ Movimiento registrado correctamente.")
                        except Exception as e:
                            st.error("No se pudo registrar movimiento. Revisa que la cuenta de servicio esté en Streamlit Secrets y que tenga permisos Editor en la hoja. Error: " + str(e))

# --- Mostrar catálogo (opcional)
st.markdown("---")
st.subheader("Catálogo (preview)")
try:
    df_preview = cargar_catalogo()
    if df_preview is not None and not df_preview.empty:
        st.dataframe(df_preview.head(50))
    else:
        st.info("Catálogo vacío o no disponible.")
except Exception as e:
    st.error("Error mostrando catálogo: " + str(e))

# Nota final de ayuda
st.info("Si no puedes escribir movimientos, revisa que en Streamlit Cloud -> Settings -> Secrets exista 'gcp_service_account' y que el 'client_email' esté agregado como Editor en Google Sheets.")
