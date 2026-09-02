import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter


def generar_excel(rows, anio=None) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = f"Aportaciones {anio or 'todas'}"

    # Cabecera
    headers = [
        "ID", "Fecha", "Hora de registro", "Año campaña", "Calle", "Portal", "Piso", "Puerta",
        "Nombre persona", "Origen", "Equipo", "Importe (€)", "Forma pago", "Observaciones", "Resultado Visita"
    ]

    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # Datos
    for row_idx, data in enumerate(rows, 2):
        ws.cell(row=row_idx, column=1, value=data["id"])
        ws.cell(row=row_idx, column=2, value=data["fecha"])
        ws.cell(row=row_idx, column=3, value=data["creado_en"].strftime("%H:%M:%S %d/%m/%Y") if data["creado_en"] else "")
        ws.cell(row=row_idx, column=4, value=data["anio_campania"])
        ws.cell(row=row_idx, column=5, value=data["calle_nombre"])
        ws.cell(row=row_idx, column=6, value=data["portal"])
        ws.cell(row=row_idx, column=7, value=data["piso"])
        ws.cell(row=row_idx, column=8, value=data["puerta"])
        ws.cell(row=row_idx, column=9, value=data["nombre_persona"])
        ws.cell(row=row_idx, column=10, value=data["origen"])
        ws.cell(row=row_idx, column=11, value=data["equipo_nombre"])
        ws.cell(row=row_idx, column=12, value=data["importe"] if data["importe"] is not None else "")
        ws.cell(row=row_idx, column=13, value=data["forma_pago"])
        ws.cell(row=row_idx, column=14, value=data["observaciones"])
        ws.cell(row=row_idx, column=15, value=data["resultado_visita"])

        # Formato numérico para importe
        if data["importe"] is not None:
            ws.cell(row=row_idx, column=12).number_format = "#,##0.00 €"

    # Auto-ajustar anchura de columnas
    for col in ws.columns:
        max_len = max((len(str(cell.value or "")) for cell in col), default=10)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 40)

    # Fila de total al final
    total_row = ws.max_row + 1
    ws.cell(row=total_row, column=11, value="TOTAL").font = Font(bold=True)
    ws.cell(row=total_row, column=12, value=f"=SUM(L2:L{ws.max_row - 1})").number_format = "#,##0.00 €"
    ws.cell(row=total_row, column=12).font = Font(bold=True)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
