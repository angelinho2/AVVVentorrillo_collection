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
        "ID", "Fecha de pago", "Hora de registro", "Año campaña", "Calle", "Portal", "Piso", "Puerta",
        "Nombre persona", "Origen", "Equipo", "Importe (€)", "Forma pago", "Observaciones",
    ]

    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    # Datos
    for row_idx, (aportacion, vivienda, calle, equipo) in enumerate(rows, 2):
        ws.cell(row=row_idx, column=1, value=aportacion.id)
        ws.cell(row=row_idx, column=2, value=str(aportacion.fecha))
        ws.cell(row=row_idx, column=3, value=aportacion.creado_en.strftime("%H:%M:%S %d/%m/%Y") if aportacion.creado_en else "")
        ws.cell(row=row_idx, column=4, value=aportacion.anio_campania)
        ws.cell(row=row_idx, column=5, value=calle.nombre if calle else "")
        ws.cell(row=row_idx, column=6, value=vivienda.portal if vivienda else "")
        ws.cell(row=row_idx, column=7, value=vivienda.piso if vivienda else "")
        ws.cell(row=row_idx, column=8, value=vivienda.puerta if vivienda else "")
        ws.cell(row=row_idx, column=9, value=aportacion.nombre_persona or "")
        ws.cell(row=row_idx, column=10, value=aportacion.origen.value)
        ws.cell(row=row_idx, column=11, value=equipo.nombre)
        ws.cell(row=row_idx, column=12, value=float(aportacion.importe))
        ws.cell(row=row_idx, column=13, value=aportacion.forma_pago.value)
        ws.cell(row=row_idx, column=14, value=aportacion.observaciones or "")

        # Formato numérico para importe
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
