import pandas as pd
import io

def generate_excel(data: list[dict]) -> bytes:
    if not data:
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(data)
        
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
    return output.getvalue()
