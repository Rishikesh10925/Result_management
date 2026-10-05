from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def marksheet_pdf(name, student, sem, res):
    buf = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f'ResultCloud Sem {sem} - {student.sap_id}')

    info = [['Student Name', name], ['SAP ID', student.sap_id],
            ['Department', student.department.upper()], ['Semester', f'Semester {sem}']]
    rows = [['S.No.', 'Subject', 'Credits', 'Final Marks', 'Grade', 'Grade Point', 'Total']]
    for i, r in enumerate(res['rows'], 1):
        rows.append([i, r['subject'], r['credits'], r['final_marks'], r['grade'], r['grade_point'], r['total']])

    grid = TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                       ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                       ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                       ('FONTSIZE', (0, 0), (-1, -1), 9)])
    cgpa = f"{res['cgpa']:.2f}" if res['cgpa'] is not None else '-'
    doc.build([
        Paragraph('RESULTCLOUD', styles['Title']),
        Paragraph('Cloud-Based Student Result Management System', styles['Normal']),
        Spacer(1, 16),
        Table(info, colWidths=[110, 300], style=TableStyle([('FONTSIZE', (0, 0), (-1, -1), 10)])),
        Spacer(1, 16),
        Table(rows, colWidths=[35, 200, 45, 60, 40, 60, 40], style=grid),
        Spacer(1, 16),
        Paragraph(f"<b>SGPA:</b> {res['sgpa']:.2f} &nbsp;&nbsp; <b>CGPA:</b> {cgpa}", styles['Normal']),
    ])
    return buf.getvalue()
