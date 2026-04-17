import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Palette ────────────────────────────────────────────────────────────────────
NAVY     = colors.HexColor('#0A0F1E')
BLUE     = colors.HexColor('#3B82F6')
RED      = colors.HexColor('#EF4444')
ORANGE   = colors.HexColor('#F59E0B')
GREEN    = colors.HexColor('#10B981')
GRAY_900 = colors.HexColor('#111827')
GRAY_700 = colors.HexColor('#374151')
GRAY_500 = colors.HexColor('#6B7280')
GRAY_200 = colors.HexColor('#E5E7EB')
GRAY_100 = colors.HexColor('#F9FAFB')
WHITE    = colors.white

PW = 7.3 * inch

def S():
    return {
        'h1': ParagraphStyle('h1', fontSize=11, fontName='Helvetica-Bold',
            textColor=WHITE, spaceAfter=0, leading=14),
        'h2': ParagraphStyle('h2', fontSize=9, fontName='Helvetica',
            textColor=colors.HexColor('#94A3B8'), spaceAfter=0, leading=12),
        'section': ParagraphStyle('section', fontSize=10, fontName='Helvetica-Bold',
            textColor=NAVY, spaceAfter=6, spaceBefore=4, leading=13),
        'label': ParagraphStyle('label', fontSize=7.5, fontName='Helvetica-Bold',
            textColor=GRAY_700, spaceAfter=1, leading=10),
        'value': ParagraphStyle('value', fontSize=13, fontName='Helvetica-Bold',
            textColor=GRAY_900, spaceAfter=0, leading=16),
        'value_red': ParagraphStyle('value_red', fontSize=13, fontName='Helvetica-Bold',
            textColor=RED, spaceAfter=0, leading=16),
        'value_green': ParagraphStyle('value_green', fontSize=13, fontName='Helvetica-Bold',
            textColor=GREEN, spaceAfter=0, leading=16),
        'value_orange': ParagraphStyle('value_orange', fontSize=13, fontName='Helvetica-Bold',
            textColor=ORANGE, spaceAfter=0, leading=16),
        'body': ParagraphStyle('body', fontSize=8.5, fontName='Helvetica',
            textColor=GRAY_700, spaceAfter=5, leading=13),
        'body_bold': ParagraphStyle('body_bold', fontSize=8.5, fontName='Helvetica-Bold',
            textColor=GRAY_900, spaceAfter=3, leading=13),
        'footer': ParagraphStyle('footer', fontSize=7, fontName='Helvetica',
            textColor=GRAY_500, alignment=TA_CENTER, leading=10),
    }

def divider(color=GRAY_200, t=0.75):
    return HRFlowable(width='100%', thickness=t, color=color,
                      spaceAfter=8, spaceBefore=4)

def section_header(title, s):
    data = [['', Paragraph(title, s['section'])]]
    t = Table(data, colWidths=[0.1*inch, PW - 0.1*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (0,0),  BLUE),
        ('TOPPADDING',    (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
        ('RIGHTPADDING',  (0,0), (-1,-1), 0),
        ('LEFTPADDING',   (1,0), (1,0),  8),
        ('TOPPADDING',    (1,0), (1,0),  4),
        ('BOTTOMPADDING', (1,0), (1,0),  4),
    ]))
    return t

def metric_card(label, value, value_style='value', width=1.7*inch):
    s = S()
    data = [
        [Paragraph(label, s['label'])],
        [Paragraph(str(value), s[value_style])],
    ]
    t = Table(data, colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), GRAY_100),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('BOX',           (0,0), (-1,-1), 0.5, GRAY_200),
    ]))
    return t

def create_pdf_report(data: dict) -> str:
    output_path = os.path.join(tempfile.gettempdir(), 'stress_report.pdf')
    s = S()

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        rightMargin=0.65*inch, leftMargin=0.65*inch,
        topMargin=0.55*inch, bottomMargin=0.55*inch,
    )

    summary     = data.get('summary', {})
    positions   = data.get('positions', [])
    explanation = data.get('explanation', {})
    now         = datetime.now().strftime('%B %d, %Y')

    total_value = summary.get('total_value', 0)
    stressed    = summary.get('stressed_value', 0)
    loss_pct    = summary.get('total_loss_pct', 0)
    severity    = summary.get('severity_label', 'Moderate')
    cost_basis  = summary.get('total_cost_basis', 0)
    ugl         = summary.get('total_unrealized_gl', 0)
    tax_impact  = summary.get('total_tax_impact', 0)
    scenario    = summary.get('scenario_text', 'N/A')
    sharpe_b    = summary.get('sharpe_before', 0)
    sharpe_a    = summary.get('sharpe_after', 0)

    sev_style  = 'value_red' if severity == 'Extreme' else \
                 'value_orange' if severity == 'Severe' else 'value_green'
    loss_style = 'value_red' if loss_pct < -15 else \
                 'value_orange' if loss_pct < -5 else 'value_green'
    ugl_style  = 'value_green' if ugl >= 0 else 'value_red'

    story = []

    # ── Cover ──────────────────────────────────────────────────────────────────
    cover = Table([[
        [
            Paragraph('PORTFOLIOSTRESS', s['h1']),
            Spacer(1, 3),
            Paragraph('Institutional Stress Test Report', s['h2']),
        ],
        [
            Paragraph(now, ParagraphStyle('r', fontSize=8, fontName='Helvetica',
                textColor=colors.HexColor('#94A3B8'), alignment=TA_RIGHT)),
        ]
    ]], colWidths=[PW * 0.65, PW * 0.35])
    cover.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 18),
        ('BOTTOMPADDING', (0,0), (-1,-1), 18),
        ('LEFTPADDING',   (0,0), (-1,-1), 16),
        ('RIGHTPADDING',  (0,0), (-1,-1), 16),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(cover)
    story.append(Spacer(1, 6))

    # Scenario bar
    scenario_bar = Table([[
        Paragraph('SCENARIO', ParagraphStyle('sl', fontSize=7,
            fontName='Helvetica-Bold', textColor=BLUE)),
        Paragraph(scenario[:140], ParagraphStyle('sv', fontSize=8,
            fontName='Helvetica', textColor=GRAY_700)),
    ]], colWidths=[0.75*inch, PW - 0.75*inch])
    scenario_bar.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), GRAY_100),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
        ('BOX',           (0,0), (-1,-1), 0.5, GRAY_200),
    ]))
    story.append(scenario_bar)
    story.append(Spacer(1, 14))

    # ── Metrics ────────────────────────────────────────────────────────────────
    story.append(section_header('EXECUTIVE SUMMARY', s))
    story.append(Spacer(1, 6))

    card_w = PW / 4 - 0.05*inch
    for row_data in [
        [
            metric_card('Portfolio Value', f"${total_value:,.0f}", 'value', card_w),
            metric_card('Stressed Value',  f"${stressed:,.0f}",    'value_red', card_w),
            metric_card('Total Loss',      f"{loss_pct:.1f}%",     loss_style, card_w),
            metric_card('Severity',        severity,                sev_style, card_w),
        ],
        [
            metric_card('Cost Basis',     f"${cost_basis:,.0f}" if cost_basis else 'N/A',
                        'value', card_w),
            metric_card('Unrealized G/L', f"${ugl:,.0f}" if ugl else 'N/A',
                        ugl_style, card_w),
            metric_card('Tax Impact',     f"${abs(tax_impact):,.0f}" if tax_impact else 'N/A',
                        'value_orange', card_w),
            metric_card('Sharpe Ratio',   f"{sharpe_b:.2f} → {sharpe_a:.2f}",
                        'value_red' if sharpe_a < 0 else 'value', card_w),
        ],
    ]:
        mr = Table([row_data], colWidths=[card_w]*4)
        mr.setStyle(TableStyle([
            ('LEFTPADDING',  (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING',   (0,0), (-1,-1), 0),
            ('BOTTOMPADDING',(0,0), (-1,-1), 0),
        ]))
        story.append(mr)
        story.append(Spacer(1, 5))

    story.append(Spacer(1, 10))

    # ── Position Table ─────────────────────────────────────────────────────────
    story.append(KeepTogether([section_header('POSITION DETAIL', s)]))
    story.append(Spacer(1, 6))

    headers = ['Ticker', 'Name', 'Sector', 'Wt%', 'Value', 'Stressed', 'Loss%', 'VaR95', 'Risk']
    col_w   = [0.55*inch, 1.2*inch, 1.1*inch, 0.4*inch,
               0.75*inch, 0.75*inch, 0.55*inch, 0.55*inch, 0.5*inch]

    rows = [headers]
    for p in sorted(positions, key=lambda x: x.get('loss_pct', 0)):
        lp = p.get('loss_pct', 0)
        rows.append([
            p.get('ticker', ''),
            (p.get('name', '') or '')[:16],
            (p.get('sector', '') or '')[:14],
            f"{p.get('weight', 0):.1f}",
            f"${p.get('value', 0):,.0f}",
            f"${p.get('stressed_value', 0):,.0f}",
            f"{lp:.1f}%",
            f"{p.get('var_95', 0):.1f}%",
            p.get('risk_level', 'Medium'),
        ])

    pt = Table(rows, colWidths=col_w, repeatRows=1)
    pos_style = [
        ('BACKGROUND',    (0,0), (-1,0),  NAVY),
        ('TEXTCOLOR',     (0,0), (-1,0),  WHITE),
        ('FONTNAME',      (0,0), (-1,0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0,0), (-1,-1), 7.5),
        ('FONTNAME',      (0,1), (-1,-1), 'Helvetica'),
        ('TEXTCOLOR',     (0,1), (-1,-1), GRAY_700),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, GRAY_100]),
        ('GRID',          (0,0), (-1,-1), 0.3, GRAY_200),
        ('TOPPADDING',    (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING',   (0,0), (-1,-1), 5),
        ('ALIGN',         (3,0), (-1,-1), 'RIGHT'),
    ]
    for i, p in enumerate(sorted(positions, key=lambda x: x.get('loss_pct', 0)), 1):
        lp   = p.get('loss_pct', 0)
        risk = p.get('risk_level', 'Medium')
        lc = RED if lp < -20 else ORANGE if lp < -10 else GREEN
        rc = RED if risk == 'High' else ORANGE if risk == 'Medium' else GREEN
        pos_style += [
            ('TEXTCOLOR', (6,i), (6,i), lc),
            ('FONTNAME',  (6,i), (6,i), 'Helvetica-Bold'),
            ('TEXTCOLOR', (8,i), (8,i), rc),
            ('FONTNAME',  (8,i), (8,i), 'Helvetica-Bold'),
        ]
    pt.setStyle(TableStyle(pos_style))
    story.append(pt)
    story.append(Spacer(1, 14))

    # ── Sector Allocation ──────────────────────────────────────────────────────
    charts = data.get('charts', {})
    sector_weights = charts.get('sector_weights', {})
    if sector_weights:
        story.append(section_header('SECTOR ALLOCATION', s))
        story.append(Spacer(1, 6))

        sorted_sectors = sorted(sector_weights.items(), key=lambda x: x[1], reverse=True)
        max_w = max(v for _, v in sorted_sectors) if sorted_sectors else 1

        sec_rows = []
        for sector, weight in sorted_sectors:
            bar_pct   = weight / max_w
            filled    = int(bar_pct * 20)
            empty     = 20 - filled
            sec_rows.append([
                Paragraph(sector, ParagraphStyle('sl', fontSize=8,
                    fontName='Helvetica', textColor=GRAY_900)),
                Paragraph(
                    f'<font color="#3B82F6">{"█" * filled}</font>'
                    f'<font color="#D1D5DB">{"█" * empty}</font>',
                    ParagraphStyle('bar', fontSize=8.5, fontName='Helvetica')),
                Paragraph(f"{weight:.1f}%", ParagraphStyle('sw', fontSize=8,
                    fontName='Helvetica-Bold', textColor=GRAY_900,
                    alignment=TA_RIGHT)),
            ])

        st = Table(sec_rows, colWidths=[1.8*inch, 4.0*inch, 0.6*inch])
        st.setStyle(TableStyle([
            ('ROWBACKGROUNDS', (0,0), (-1,-1), [WHITE, GRAY_100]),
            ('GRID',           (0,0), (-1,-1), 0.3, GRAY_200),
            ('TOPPADDING',     (0,0), (-1,-1), 5),
            ('BOTTOMPADDING',  (0,0), (-1,-1), 5),
            ('LEFTPADDING',    (0,0), (-1,-1), 8),
            ('ALIGN',          (2,0), (2,-1),  'RIGHT'),
            ('VALIGN',         (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(st)
        story.append(Spacer(1, 14))

    # ── AI Analysis ────────────────────────────────────────────────────────────
    if explanation:
        story.append(section_header('AI ANALYSIS', s))
        story.append(Spacer(1, 6))

        for key, heading in [
            ('advisor_summary',    'Advisor Summary'),
            ('client_explanation', 'Client Explanation'),
            ('suggestions',        'Rebalancing Recommendations'),
        ]:
            text = explanation.get(key, '')
            if not text:
                continue

            sh = Table([[Paragraph(heading, ParagraphStyle('sh',
                fontSize=8.5, fontName='Helvetica-Bold', textColor=BLUE,
                spaceBefore=6, spaceAfter=4))
            ]], colWidths=[PW])
            sh.setStyle(TableStyle([
                ('TOPPADDING',    (0,0), (-1,-1), 4),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('LEFTPADDING',   (0,0), (-1,-1), 0),
            ]))
            story.append(sh)

            text = text.replace('**', '').replace('## ', '').replace('# ', '')
            for para in text.split('\n\n'):
                para = para.strip()
                if not para:
                    continue
                lines = para.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')):
                        clean = line.lstrip('•-* 0123456789.').strip()
                        if clean:
                            bullet = Table([[
                                Paragraph('•', ParagraphStyle('b', fontSize=8.5,
                                    fontName='Helvetica-Bold', textColor=BLUE)),
                                Paragraph(clean, s['body']),
                            ]], colWidths=[0.15*inch, PW - 0.15*inch])
                            bullet.setStyle(TableStyle([
                                ('TOPPADDING',    (0,0), (-1,-1), 1),
                                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                                ('LEFTPADDING',   (0,0), (-1,-1), 0),
                                ('VALIGN',        (0,0), (-1,-1), 'TOP'),
                            ]))
                            story.append(bullet)
                    else:
                        story.append(Paragraph(line, s['body']))
            story.append(Spacer(1, 8))

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 10))
    story.append(divider(GRAY_200, 0.5))
    footer_table = Table([[
        Paragraph('PortfolioStress · Institutional Risk Platform',
            ParagraphStyle('fl', fontSize=7, fontName='Helvetica-Bold',
                textColor=GRAY_500)),
        Paragraph('For informational purposes only. Not financial advice.',
            ParagraphStyle('fr', fontSize=7, fontName='Helvetica',
                textColor=GRAY_500, alignment=TA_RIGHT)),
    ]], colWidths=[PW * 0.5, PW * 0.5])
    footer_table.setStyle(TableStyle([
        ('TOPPADDING',    (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING',   (0,0), (-1,-1), 0),
        ('RIGHTPADDING',  (0,0), (-1,-1), 0),
    ]))
    story.append(footer_table)

    doc.build(story)
    return output_path