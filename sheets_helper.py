# sheets_helper.py
import gspread
import pandas as pd

class SheetDB:
    def __init__(self, spreadsheet_name, service_account_info=None, creds_path=None):
        if service_account_info:
            self.gc = gspread.service_account_from_dict(service_account_info)
        elif creds_path:
            self.gc = gspread.service_account(filename=creds_path)
        else:
            raise ValueError("Proveer service_account_info o creds_path.")
        self.spreadsheet = self.gc.open(spreadsheet_name)

    def read_sheet_df(self, sheet_name):
        try:
            ws = self.spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            return pd.DataFrame()
        data = ws.get_all_records()
        return pd.DataFrame(data)

    def append_row(self, sheet_name, row_values):
        try:
            ws = self.spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            ws = self.spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
        ws.append_row(row_values, value_input_option='USER_ENTERED')

    def ensure_sheets_exist(self, sheet_names):
        existing = [ws.title for ws in self.spreadsheet.worksheets()]
        for name in sheet_names:
            if name not in existing:
                self.spreadsheet.add_worksheet(title=name, rows="1000", cols="20")

    def compute_stock_from_movements(self, herramientas_sheet='Herramientas', movimientos_sheet='Movimientos'):
        tools = self.read_sheet_df(herramientas_sheet)
        mov = self.read_sheet_df(movimientos_sheet)
        if tools.empty:
            return pd.DataFrame(columns=['codigo','nombre','descripcion','ubicacion','stock_inicial'])
        if mov.empty:
            mov = pd.DataFrame(columns=['timestamp','codigo','descripcion','tipo','usuario','cantidad','fecha','registrado_por','observaciones'])
        mov['cantidad'] = pd.to_numeric(mov['cantidad'], errors='coerce').fillna(0)
        entradas = mov.loc[mov['tipo']=='entrada'].groupby('codigo')['cantidad'].sum()
        salidas = mov.loc[mov['tipo']=='salida'].groupby('codigo')['cantidad'].sum()
        delta = (entradas - salidas).fillna(0)
        tools = tools.set_index('codigo')
        tools['stock_inicial'] = pd.to_numeric(tools.get('stock_inicial', 0), errors='coerce').fillna(0)
        tools['delta_mov'] = delta.reindex(tools.index).fillna(0)
        tools['stock_actual'] = tools['stock_inicial'] + tools['delta_mov']
        tools = tools.reset_index()
        return tools
