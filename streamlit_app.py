# streamlit_app.py
"""
App Streamlit para Inventario con:
 - lectura de catálogo (Google Sheets vía service account o publicación CSV pública)
 - cálculo de stock a partir de Movimientos
 - registrar movimientos (requiere service account en Streamlit Secrets)
 - fallback: entrada manual de código si pyzbar/cámara no está disponible
"""
# DEBUG credenciales - BORRAR LUEGO
import streamlit as st, traceback
st.write("DEBUG: st.secrets keys:", list(st.secrets.keys()))
info = st.secrets.get("gcp_service_account")
if not info:
    st.error("No existe st.secrets['gcp_service_account']")
else:
    st.write("DEBUG client_email:", info.get("client_email"))
    try:
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        st.success("Credentials OK")
    except Exception as e:
        st.error("Credentials error: " + str(e))
        st.code(traceback.format_exc())
st.stop()

import streamlit as st
from datetime import date, datetime, timezone
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
    """
    Intenta leer catálogo vía API (sheets). Si falla, usa CSV público.
    Normaliza encabezados y fija la fila de encabezado correcta si pandas no la detectó.
    Devuelve DataFrame ya limpio con columnas normalizadas (minúsculas, sin tildes).
    """
    import unicodedata
    def normalize_col(c):
        c = str(c).strip()
        c = unicodedata.normalize("NFKD", c).encode("ASCII", "ignore").decode("ASCII")
        c = c.replace(" ", "_").replace("-", "_").replace(".", "_")
        return c.lower()

    # 1) Intentar leer por API (service account)
    try:
        df_cat = read_sheet_as_df(ID_CATALOGO, RANGE_CATALOGO)
        if df_cat is None or df_cat.empty or df_cat.shape[1] == 0:
            raise RuntimeError("API devolvió DF vacío")
        df_cat.columns = [str(c).strip() for c in df_cat.columns]
        df_cat.rename(columns={c: normalize_col(c) for c in df_cat.columns}, inplace=True)
        return df_cat
    except Exception as e_api:
        # 2) Fallback: lectura CSV pública
        try:
            df = pd.read_csv(PUBLIC_CSV_CATALOGO, dtype=str).fillna("")
        except Exception as e_csv:
            st.error("No se pudo leer catálogo ni por API ni por CSV público. API error: "
                     + str(e_api) + " | CSV error: " + str(e_csv))
            return pd.DataFrame()

        df.dropna(axis=1, how="all", inplace=True)
        cols = list(df.columns)
        unnamed = any([str(c).lower().startswith("unnamed") or c.strip()=="" for c in cols])
        first_row_values = df.iloc[0].tolist() if not df.empty else []
        plausible_headers = sum(1 for v in first_row_values if isinstance(v, str) and v.strip()!="")
        if unnamed and plausible_headers >= max(2, len(cols)//3):
            new_header = [str(x).strip() for x in df.iloc[0].tolist()]
            df = df[1:].copy()
            df.columns = new_header

        df.dropna(axis=1, how="all", inplace=True)
        df.columns = [str(c).strip() for c in df.columns]
        norm_map = {c: normalize_col(c) for c in df.columns}
        df.rename(columns=norm_map, inplace=True)
        df = df.loc[:, [col for col in df.columns if not col.lower().startswith("unnamed") and col.strip()!=""]]
        df = df.reset_index(drop=True)
        return df

# --- Si hay código, buscar en catálogo y mostrar info ---
if codigo:
    st.info(f"Consultando catálogo para: {codigo}")
    catalogo_df = cargar_catalogo()

    if catalogo_df is None or catalogo_df.empty:
        st.warning("El catálogo está vacío o no se pudo cargar.")
    else:
        # BUSCAR columna código entre posibles variantes
        possible_code_cols = {"codigo","cod","code","código"}
        catalog_cols = [c.lower() for c in catalogo_df.columns]
        codigo_col = None
        for cand in possible_code_cols:
            if cand in catalog_cols:
                codigo_col = catalogo_df.columns[catalog_cols.index(cand)]
                break

        if codigo_col is None:
            st.error("La hoja de catálogo no tiene una columna identificable como 'codigo' (busqué: codigo, código, cod, code). Revisa encabezados.")
        else:
            match = catalogo_df[catalogo_df[codigo_col].astype(str).str.strip() == str(codigo).strip()]
            if match.empty:
                st.warning("Código no está en el catálogo.")
            else:
                row = match.iloc[0]
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
                        timestamp = datetime.now(timezone.utc).isoformat()
                        fila = [
                            timestamp,  # timestamp (timezone-aware)
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
