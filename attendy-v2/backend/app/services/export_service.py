import io

from openpyxl import Workbook
from openpyxl.styles import Font

from app.schemas.attendance import AttendanceRow


def build_attendance_workbook(event_date: str, rows: list[AttendanceRow]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = f"Attendance {event_date}"

    headers = ["Name", "Roll No.", "Class", "Status", "Marked At", "Source", "Confidence"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for row in rows:
        ws.append(
            [
                row.name,
                row.roll_number,
                row.class_section.label,
                row.status.capitalize(),
                row.event_time.strftime("%Y-%m-%d %H:%M:%S") if row.event_time else "",
                row.source or "",
                round(row.confidence, 4) if row.confidence is not None else "",
            ]
        )

    for column_cells in ws.columns:
        length = max(len(str(cell.value)) for cell in column_cells if cell.value is not None) if any(
            cell.value is not None for cell in column_cells
        ) else 10
        ws.column_dimensions[column_cells[0].column_letter].width = max(10, length + 2)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
