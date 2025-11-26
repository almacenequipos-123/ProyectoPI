# streamlit_app.py (versión corregida)
import streamlit as st
from sheets_helper import read_sheet, append_row    # usa el nombre real de tu helper
from datetime import date, datetime
from PIL import Image, UnidentifiedImageError

# intento importar pyzbar, si no está disponible mostramos un mensaje y usamos input manual
try:
    from pyzbar.pyzbar import decode
    PYZBAR_AVAILABLE = True
except Exception:
    PYZBAR_AVAILABLE = False

# IDs de tus dos spreadsheets
ID_CATALOGO = "18_5f4JASdhjZiXJ9FZ220klouRwHEAR29bGMJ3y4PLE"
ID_MOVIMIENTOS = "1J0uvOek8KRZDq0sosg2fIF3sX0vHv_1XwaQruzyUOgc"

RANGE_CATALOGO = "Herramientas!A:F"       # ajusta según tus columnas
RANGE_MOVIMIENTOS = "Movimientos!A:I"     # ajusta según tus columnas

st.title("Inventario (con dos Google Sheets)")

# Cámara / subida
st.subheader("Escanear QR / Código de barras")
if PYZBAR_AVAILABLE:
    img = st.camera_input("Toma foto del QR o código (o sube una imagen)", help="Usa cámara o sube PNG/JPG")
else:
    st.warning("pyzbar no está disponible en este entorno. Usa el campo 'Código manual' o sube imagen y regístrala manualmente.")
    img = st.file_uploader("Sube la imagen del QR/código (PNG, JPG)")

codigo_detectado = None

if img is not None:
    try:
        image = Image.open(img)
    except UnidentifiedImageError:
        st.error("No se pudo abrir la imagen. Intenta con otro archivo.")
        image = None

    if image is not None and PYZBAR_AVAILABLE:
        try:
            decoded = decode(image)
        except Exception as e:
            st.error("Error al decodificar la imagen con pyzbar: " + str(e))
            decoded = []

        if decoded:
            codigo_detectado = decoded[0].data.decode("utf-8")
            st.success(f"Código detectado: {codigo_detectado}")
        else:
            st.warning("No se detectó QR/código en la imagen. Puedes ingresar el código manualmente abajo.")
elif not PYZBAR_AVAILABLE:
    # si pyzbar no está disponible, dejamos opción manual
    st.info("Introduce el código manualmente si no puedes usar la cámara/pyzbar.")

# Campo manual (si no se detectó)
codigo_manual = st.text_input("Código manual (si no se detectó por cámara)", value="")
codigo = codigo_detectado if codigo_detectado else (codigo_manual.strip() or None)

# Si hay código, consultar catálogo y mostrar disponibilidad
if codigo:
    st.info(f"Consultando catálogo para: {codigo}")
    try:
        catalogo_df = read_sheet(ID_CATALOGO, RANGE_CATALOGO)  # devuelve DataFrame
    except Exception as e:
        st.error("No se pudo leer la hoja de catálogo: " + str(e))
        catalogo_df = None

    if catalogo_df is None or catalogo_df.empty:
        st.warning("El catálogo está vacío o no se pudo leer. Verifica el nombre de la hoja y permisos.")
    else:
        # Asegurarnos de que exista la columna 'codigo' (case-insensitive)
        cols_lower = [c.lower() for c in catalogo_df.columns]
        if 'codigo' in cols_lower:
            codigo_col = catalogo_df.columns[cols_lower.index('codigo')]
        else:
            st.error("La hoja 'Herramientas' no contiene una columna llamada 'codigo' en la primera fila.")
            codigo_col = None

        if codigo_col:
            match = catalogo_df[catalogo_df[codigo_col].astype(str) == str(codigo)]
            if not match.empty:
                row = match.iloc[0]
                # leer campos con fallback si faltan columnas
                def get_col_val(df_row, colname, default=""):
                    cols_l = [c.lower() for c in df_row.index]
                    if colname in cols_l:
                        return df_row[df_row.index[cols_l.index(colname)]]
                    return default

                nombre = get_col_val(row, 'nombre', '')
                descripcion = get_col_val(row, 'descripcion', '')
                ubicacion = get_col_val(row, 'ubicacion', '')
                try:
                    stock_inicial = int(get_col_val(row, 'stock_inicial', 0))
                except Exception:
                    stock_inicial = 0

                st.markdown("**Recurso encontrado:**")
                st.write(f"- **Nombre:** {nombre}")
                st.write(f"- **Descripción:** {descripcion}")
                st.write(f"- **Ubicación:** {ubicacion}")
                st.write(f"- **Stock inicial:** {stock_inicial}")

                # Calcular stock actual leyendo movimientos (si existe)
                try:
                    movs_df = read_sheet(ID_MOVIMIENTOS, RANGE_MOVIMIENTOS)
                    if movs_df is None or movs_df.empty:
                        entradas = 0
                        salidas = 0
                    else:
                        # asegurar columnas mínimas
                        cols_mov = [c.lower() for c in movs_df.columns]
                        # buscar column names posibles: 'codigo','tipo','cantidad'
                        if 'codigo' in cols_mov and 'tipo' in cols_mov and 'cantidad' in cols_mov:
                            ccol = movs_df.columns[cols_mov.index('codigo')]
                            tcol = movs_df.columns[cols_mov.index('tipo')]
                            qcol = movs_df.columns[cols_mov.index('cantidad')]
                            entradas = movs_df[(movs_df[ccol].astype(str)==str(codigo)) & (movs_df[tcol]=='entrada')][qcol].astype(int).sum() if not movs_df.empty else 0
                            salidas = movs_df[(movs_df[ccol].astype(str)==str(codigo)) & (movs_df[tcol]=='salida')][qcol].astype(int).sum() if not movs_df.empty else 0
                        else:
                            entradas = 0
                            salidas = 0
                    stock_actual = stock_inicial + entradas - salidas
                    st.metric("Stock actual", stock_actual)
                except Exception as e:
                    st.warning("No se pudo calcular stock desde Movimientos: " + str(e))

                # Formulario para registrar movimiento
                with st.form("mov"):
                    tipo = st.radio("Tipo", ["entrada", "salida"], index=1 if stock_inicial==0 else 0)
                    usuario = st.text_input("Nombre del usuario")
                    cantidad = st.number_input("Cantidad", min_value=1, value=1)
                    obs = st.text_area("Observaciones")
                    fecha = st.date_input("Fecha movimiento", value=date.today())
                    enviado = st.form_submit_button("Registrar")

                    if enviado:
                        timestamp = datetime.utcnow().isoformat()
                        fila = [timestamp, codigo, descripcion, tipo, usuario, cantidad, fecha.isoformat(), "streamlit", obs]
                        try:
                            append_row(ID_MOVIMIENTOS, RANGE_MOVIMIENTOS, fila)
                            st.success("Movimiento registrado.")
                        except Exception as e:
                            st.error("Error registrando movimiento: " + str(e))

            else:
                st.warning("Código no está en el catálogo.")
        # end if codigo_col
# fin if codigo
