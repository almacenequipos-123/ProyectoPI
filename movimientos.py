from datetime import datetime, timedelta, timezone
from typing import Tuple

import gspread


def _now_colombia() -> datetime:
    """
    Devuelve la hora actual en Colombia (UTC-5) como datetime timezone-aware.
    Lo hago restando 5 horas a UTC para evitar dependencias extra.
    """
    now_utc = datetime.now(timezone.utc)
    colombia_time = now_utc - timedelta(hours=5)
    return colombia_time


def obtener_timestamp_colombia() -> Tuple[str, str]:
    """
    Devuelve (timestamp, fecha) en hora de Colombia.
    timestamp: YYYY-MM-DD HH:MM:SS (formato 24h)
    fecha: YYYY-MM-DD
    """
    ahora = _now_colombia()
    timestamp = ahora.strftime("%Y-%m-%d %H:%M:%S")
    fecha = ahora.date().isoformat()
    return timestamp, fecha


def registrar_movimiento(
    sh_inventario: gspread.Worksheet,
    sh_movimientos: gspread.Worksheet,
    codigo: str,
    tipo: str,
    cantidad: int,
    usuario: str,
) -> Tuple[int, str]:
    """
    Registra un movimiento de ENTRADA o SALIDA en la hoja 'Movimientos'
    y actualiza el balance_actual en 'Inventario'.

    Estructura de INVENTARIO:
    A: codigo
    B: descripcion
    C: estado
    D: estante
    E: balance_actual
    F: recuento_fisico
    G: fecha_recuento

    Estructura de MOVIMIENTOS:
    timestamp | codigo | descripcion | usuario | tipo | cantidad | fecha
    """
    codigo = codigo.strip()
    tipo = tipo.strip().upper()

    if not codigo:
        raise ValueError("El código no puede estar vacío.")

    if tipo not in ("ENTRADA", "SALIDA"):
        raise ValueError("El tipo de movimiento debe ser ENTRADA o SALIDA.")

    try:
        cantidad = int(cantidad)
    except ValueError:
        raise ValueError("La cantidad debe ser un número entero.")

    if cantidad <= 0:
        raise ValueError("La cantidad debe ser mayor que cero.")

    if not usuario:
        raise ValueError("El usuario no puede estar vacío.")

    # 1. Buscar el código en Inventario
    celdas = sh_inventario.findall(codigo)
    if not celdas:
        raise ValueError(f"El código {codigo} no existe en el inventario.")

    fila = celdas[0].row

    # 2. Leer descripción y balance_actual
    descripcion = sh_inventario.cell(fila, 2).value or ""
    balance_actual_str = sh_inventario.cell(fila, 5).value or "0"

    try:
        balance_antes = int(balance_actual_str)
    except ValueError:
        raise ValueError(
            f"El balance_actual de {codigo} no es un número válido: {balance_actual_str}"
        )

    # 3. Calcular nuevo balance
    if tipo == "ENTRADA":
        balance_despues = balance_antes + cantidad
    else:  # SALIDA
        balance_despues = balance_antes - cantidad

    if balance_despues < 0:
        raise ValueError(
            f"Stock insuficiente para {codigo}. "
            f"Balance actual: {balance_antes}, intentas sacar: {cantidad}."
        )

    # 4. Timestamp y fecha en hora Colombia
    timestamp, fecha = obtener_timestamp_colombia()

    # 5. Registrar el movimiento
    nueva_fila = [
        timestamp,      # timestamp
        codigo,         # codigo
        descripcion,    # descripcion
        usuario,        # usuario
        tipo,           # tipo (ENTRADA/SALIDA)
        cantidad,       # cantidad
        fecha,          # fecha (solo día)
    ]
    sh_movimientos.append_row(nueva_fila)

    # 6. Actualizar balance_actual en Inventario
    sh_inventario.update_cell(fila, 5, balance_despues)

    return balance_despues, timestamp
