# streamlit_app.py

import streamlit as st

from sheets_helper import get_sheets
from movimientos import registrar_movimiento

# Imports para QR por cámara
from streamlit_webrtc import webrtc_streamer, WebRtcMode
import cv2
import av


@st.cache_resource
def load_sheets():
    """
    Carga y cachea las hojas de Google Sheets:
    - Inventario
    - Movimientos
    """
    return get_sheets()


def qr_video_frame_callback(frame):
    """
    Callback que procesa cada frame de la cámara,
    detecta códigos QR con OpenCV y actualiza st.session_state["codigo"].
    """
    img = frame.to_ndarray(format="bgr24")

    # Detector de QR de OpenCV
    detector = cv2.QRCodeDetector()

    data, points, _ = detector.detectAndDecode(img)

    if points is not None and data:
        qr_text = data.strip()

        # Guardamos el código leído en session_state
        st.session_state["codigo"] = qr_text
        st.session_state["qr_scanned"] = qr_text

        # Dibujar bordes alrededor del QR
        pts = points[0].astype(int)
        for i in range(4):
            pt1 = tuple(pts[i])
            pt2 = tuple(pts[(i + 1) % 4])
            cv2.line(img, pt1, pt2, (0, 255, 0), 2)

        cv2.putText(
            img,
            qr_text,
            (pts[0][0], pts[0][1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

    return av.VideoFrame.from_ndarray(img, format="bgr24")


def main():
    st.set_page_config(page_title="Almacén de herramientas", page_icon="🛠️")
    st.title("Almacén de herramientas - Registro de movimientos")

    # Cargar hojas de Google Sheets
    try:
        sh_inventario, sh_movimientos = load_sheets()
    except Exception as e:
        st.error(
            "❌ Error al conectar con Google Sheets.\n\n"
            f"Detalles: {e}"
        )
        return

    # Inicializar estado para QR
    if "codigo" not in st.session_state:
        st.session_state["codigo"] = ""
    if "qr_scanned" not in st.session_state:
        st.session_state["qr_scanned"] = ""

    st.markdown("### Registrar movimiento")

    # Campo de código (manual o desde QR)
    codigo = st.text_input(
        "Código de la herramienta",
        key="codigo",
        placeholder="Escribe el código o escanéalo con la cámara",
    )

    # --- Sección de cámara para leer QR ---
    with st.expander("Escanear código QR con la cámara"):
        st.markdown(
            "Apunta la cámara al QR de la herramienta. "
            "Cuando se lea correctamente, el código aparecerá en el campo de arriba."
        )
        webrtc_streamer(
            key="qr-scanner",
            mode=WebRtcMode.LIVE,
            video_frame_callback=qr_video_frame_callback,
            media_stream_constraints={"video": True, "audio": False},
        )

        if st.session_state.get("qr_scanned"):
            st.info(f"Código leído desde QR: **{st.session_state['qr_scanned']}**")

    col1, col2 = st.columns(2)
    with col1:
        tipo = st.selectbox("Tipo de movimiento", ["ENTRADA", "SALIDA"])
    with col2:
        cantidad = st.number_input("Cantidad", min_value=1, step=1, value=1)

    usuario = st.text_input("Usuario que realiza el movimiento")

    if st.button("Registrar movimiento"):
        if not codigo.strip():
            st.error("Por favor ingresa o escanea un código de herramienta.")
        elif not usuario.strip():
            st.error("Por favor ingresa el nombre del usuario.")
        else:
            try:
                nuevo_balance, ts = registrar_movimiento(
                    sh_inventario=sh_inventario,
                    sh_movimientos=sh_movimientos,
                    codigo=codigo.strip(),
                    tipo=tipo,
                    cantidad=cantidad,
                    usuario=usuario.strip(),
                )
                st.success(
                    f"✅ Movimiento registrado a las {ts} (hora Colombia). "
                    f"Nuevo balance para {codigo.strip()}: {nuevo_balance}."
                )
                # Limpiamos el último QR leído para evitar confusiones
                st.session_state["qr_scanned"] = ""
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
            try:
                celdas = sh_inventario.findall(codigo_buscar.strip())
            except Exception as e:
                st.error(f"Error al buscar en Inventario: {e}")
            else:
                if not celdas:
                    st.error(
                        f"No se encontró el código {codigo_buscar.strip()} en la hoja Inventario."
                    )
                else:
                    fila = celdas[0].row
                    # Estructura de Inventario:
                    # A: codigo | B: descripcion | C: estado | D: estante | E: balance_actual
                    codigo_val = sh_inventario.cell(fila, 1).value
                    descripcion = sh_inventario.cell(fila, 2).value
                    estado = sh_inventario.cell(fila, 3).value
                    estante = sh_inventario.cell(fila, 4).value
                    balance_actual = sh_inventario.cell(fila, 5).value
                    recuento_fisico = sh_inventario.cell(fila, 6).value
                    fecha_recuento = sh_inventario.cell(fila, 7).value

                    if recuento_fisico is None:
                        recuento_fisico = ""
                    if fecha_recuento is None:
                        fecha_recuento = ""

                    st.info(
                        f"**Código:** {codigo_val}\n\n"
                        f"**Descripción:** {descripcion}\n\n"
                        f"**Estado:** {estado}\n\n"
                        f"**Estante:** {estante}\n\n"
                        f"**Balance actual:** {balance_actual}\n\n"
                        f"**Recuento físico:** {recuento_fisico or '—'}\n\n"
                        f"**Fecha de recuento:** {fecha_recuento or '—'}"
                    )


if __name__ == "__main__":
    main()
