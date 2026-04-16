from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

def create_pdf_report(data: dict) -> str:
    output_path = '/tmp/stress_report.pdf'
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('Title', fontSize=20,
                                  textColor=colors.HexColor('#1E2A3A'),
                                  spaceAfter=12, fontName='Helvetica-Bold')
    story.append(Paragraph('Portfolio Stress Test Report', title_style))
    story.append(Paragraph(f"Scenario: {data['summary']['scenario_text']}",
                            styles['Normal']))
    story.append(Spacer(1, 0.3*inch))

    summary = data['summary']
    metrics = [
        ['Metric', 'Value'],
        ['Portfolio Value', f"${summary['total_value']:,.0f}"],
        ['Stressed Value', f"${summary['stressed_value']:,.0f}"],
        ['Total Loss', f"{summary['total_loss_pct']:.1f}%"],
        ['Sharpe Before', str(summary['sharpe_before'])],
        ['Sharpe After', str(summary['sharpe_after'])],
        ['Severity', summary['severity_label']],
    ]
    t = Table(metrics, colWidths=[3*inch, 3*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E2A3A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#F9FAFB')),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.3*inch))

    story.append(Paragraph('Client Explanation', styles['Heading2']))
    story.append(Paragraph(data['explanation']['client_explanation'], styles['Normal']))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph('Rebalancing Suggestions', styles['Heading2']))
    story.append(Paragraph(data['explanation']['suggestions'], styles['Normal']))

    doc.build(story)
    return output_path