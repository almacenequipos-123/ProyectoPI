# json_to_toml_for_streamlit.py
import json
import sys
p = ".streamlit/service_account.json"

try:
    with open(p, "r", encoding="utf-8") as f:
        obj = json.load(f)
except FileNotFoundError:
    print("ERROR: no se encontró .streamlit/service_account.json. Coloca tu JSON allí y vuelve a ejecutar.")
    sys.exit(1)

# Reemplazar saltos reales por \n para que la clave se guarde como una sola línea en TOML
pk = obj.get("private_key", "").replace("\n", "\\n")

print("[gcp_service_account]")
for k, v in obj.items():
    if k == "private_key":
        print(f'private_key = "{pk}"')
    else:
        sval = str(v).replace('"', '\\"')
        print(f'{k} = "{sval}"')
