import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Palette ────────────────────────────────────────────────────────────────────
NAVY        = colors.HexColor('#0A0F1E')
BLUE        = colors.HexColor('#3B82F6')
BLUE_LIGHT  = colors.HexColor('#EFF6FF')
BLUE_BORDER = colors.HexColor('#BFDBFE')
RED         = colors.HexColor('#EF4444')
ORANGE      = colors.HexColor('#F59E0B')
GREEN       = colors.HexColor('#10B981')
GRAY_900    = colors.HexColor('#111827')
GRAY_700    = colors.HexColor('#374151')
GRAY_500    = colors.HexColor('#6B7280')
GRAY_200    = colors.HexColor('#E5E7EB')
GRAY_100    = colors.HexColor('#F9FAFB')
WHITE       = colors.white
RED_TINT    = colors.HexColor('#FEF2F2')
ORANGE_TINT = colors.HexColor('#FFFBEB')
GREEN_TINT  = colors.HexColor('#F0FDF4')

PAGE_W, PAGE_H = letter   # 612, 792 pt
MARGIN    = 0.65 * inch
CONTENT_W = 7.3 * inch    # matches original PW


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
    t = Table(data, colWidths=[0.1 * inch, CONTENT_W - 0.1 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (0, 0),   BLUE),
        ('TOPPADDING',    (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('LEFTPADDING',   (1, 0), (1, 0),   8),
        ('TOPPADDING',    (1, 0), (1, 0),   4),
        ('BOTTOMPADDING', (1, 0), (1, 0),   4),
    ]))
    return t


def metric_card(label, value, value_style='value', width=1.7 * inch):
    s = S()
    data = [
        [Paragraph(label, s['label'])],
        [Paragraph(str(value), s[value_style])],
    ]
    t = Table(data, colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), GRAY_100),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('BOX',           (0, 0), (-1, -1), 0.5, GRAY_200),
    ]))
    return t


def _draw_page_header(canvas, page_num):
    """Navy header bar for pages 2+."""
    canvas.saveState()
    bar_h = 0.38 * inch
    y = PAGE_H - bar_h
    canvas.setFillColor(NAVY)
    canvas.rect(0, y, PAGE_W, bar_h, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont('Helvetica-Bold', 10)
    canvas.drawString(MARGIN, y + 0.12 * inch, 'PORTFOLIOSTRESS')
    canvas.setFont('Helvetica', 8.5)
    canvas.drawRightString(PAGE_W - MARGIN, y + 0.12 * inch, f'Page {page_num}')
    canvas.setStrokeColor(BLUE)
    canvas.setLineWidth(1)
    canvas.line(0, y, PAGE_W, y)
    canvas.restoreState()


def create_pdf_report(data: dict) -> str:
    output_path = os.path.join(tempfile.gettempdir(), 'stress_report.pdf')
    s = S()

    summary     = data.get('summary', {})
    positions   = data.get('positions', [])
    explanation = data.get('explanation', {})
    charts      = data.get('charts', {})
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
    client_name = summary.get('client_name', 'Client')

    sev_color  = RED if severity == 'Extreme' else ORANGE if severity == 'Severe' else GREEN
    sev_style  = 'value_red' if severity == 'Extreme' else \
                 'value_orange' if severity == 'Severe' else 'value_green'
    loss_style = 'value_red' if loss_pct < -15 else \
                 'value_orange' if loss_pct < -5 else 'value_green'
    ugl_style  = 'value_green' if ugl >= 0 else 'value_red'

    # ── Page callbacks ──────────────────────────────────────────────────────────
    def on_first_page(canvas, doc):
        canvas.saveState()

        # Full navy background
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

        # Branding — top left
        canvas.setFillColor(WHITE)
        canvas.setFont('Helvetica-Bold', 24)
        canvas.drawString(MARGIN, PAGE_H - 1.2 * inch, 'PORTFOLIOSTRESS')

        canvas.setFillColor(colors.HexColor('#94A3B8'))
        canvas.setFont('Helvetica', 12)
        canvas.drawString(MARGIN, PAGE_H - 1.65 * inch, 'Institutional Portfolio Stress Analysis')

        # Separator below branding
        canvas.setStrokeColor(colors.HexColor('#1E293B'))
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, PAGE_H - 1.9 * inch, PAGE_W - MARGIN, PAGE_H - 1.9 * inch)

        # Scenario name — center of page
        scenario_y = PAGE_H * 0.58
        canvas.setFillColor(WHITE)
        canvas.setFont('Helvetica-Bold', 18)
        scenario_display = scenario[:80] if len(scenario) > 80 else scenario
        canvas.drawCentredString(PAGE_W / 2, scenario_y, scenario_display)

        # Severity badge
        badge_w = 1.5 * inch
        badge_h = 0.32 * inch
        badge_x = PAGE_W / 2 - badge_w / 2
        badge_y = scenario_y - 0.58 * inch
        canvas.setFillColor(sev_color)
        canvas.roundRect(badge_x, badge_y, badge_w, badge_h, 4, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont('Helvetica-Bold', 9.5)
        canvas.drawCentredString(PAGE_W / 2, badge_y + 0.09 * inch, severity.upper())

        # 2x2 metric blocks — bottom third
        metrics = [
            ('PORTFOLIO VALUE', f"${total_value:,.0f}"),
            ('STRESSED VALUE',  f"${stressed:,.0f}"),
            ('TOTAL LOSS',      f"{loss_pct:.1f}%"),
            ('SEVERITY',        severity),
        ]
        block_w = 2.2 * inch
        block_h = 0.9 * inch
        gap_x   = 0.22 * inch
        gap_y   = 0.18 * inch
        grid_x  = (PAGE_W - 2 * block_w - gap_x) / 2
        grid_top = PAGE_H * 0.40

        for idx, (lbl, val) in enumerate(metrics):
            col = idx % 2
            row = idx // 2
            bx = grid_x + col * (block_w + gap_x)
            by = grid_top - row * (block_h + gap_y)

            canvas.setFillColor(colors.HexColor('#111827'))
            canvas.roundRect(bx, by - block_h, block_w, block_h, 6, fill=1, stroke=0)

            canvas.setFillColor(colors.HexColor('#6B7280'))
            canvas.setFont('Helvetica', 7.5)
            canvas.drawString(bx + 12, by - 16, lbl)

            val_color = WHITE
            if idx == 2:
                val_color = RED if loss_pct < -15 else ORANGE if loss_pct < -5 else GREEN
            elif idx == 3:
                val_color = sev_color
            canvas.setFillColor(val_color)
            canvas.setFont('Helvetica-Bold', 16)
            canvas.drawString(bx + 12, by - block_h + 16, val)

        # Confidential footer
        footer_y = 0.52 * inch
        canvas.setStrokeColor(colors.HexColor('#1E293B'))
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, footer_y + 0.18 * inch, PAGE_W - MARGIN, footer_y + 0.18 * inch)
        canvas.setFillColor(colors.HexColor('#6B7280'))
        canvas.setFont('Helvetica', 7.5)
        canvas.drawCentredString(
            PAGE_W / 2, footer_y,
            f'CONFIDENTIAL — Prepared for {client_name}  ·  {now}'
        )

        canvas.restoreState()

    def on_later_pages(canvas, doc):
        _draw_page_header(canvas, doc.page)

    # ── Document ────────────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        rightMargin=MARGIN, leftMargin=MARGIN,
        topMargin=0.75 * inch,   # clears the header bar on pages 2+
        bottomMargin=0.55 * inch,
    )

    story = []

    # ── PAGE 1: cover (drawn entirely by on_first_page callback) ────────────────
    story.append(Spacer(1, 0.01 * inch))
    story.append(PageBreak())

    # ── PAGE 2: Analysis ────────────────────────────────────────────────────────

    # Executive Summary
    story.append(section_header('EXECUTIVE SUMMARY', s))
    story.append(Spacer(1, 6))

    card_w = CONTENT_W / 4 - 0.05 * inch
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
        mr = Table([row_data], colWidths=[card_w] * 4)
        mr.setStyle(TableStyle([
            ('LEFTPADDING',   (0, 0), (-1, -1), 3),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(mr)
        story.append(Spacer(1, 5))

    # Scenario description box
    scen_box = Table([[
        Paragraph(f'<b>Scenario:</b>  {scenario[:200]}',
            ParagraphStyle('sd', fontSize=8, fontName='Helvetica',
                textColor=colors.HexColor('#1E40AF'), leading=12))
    ]], colWidths=[CONTENT_W])
    scen_box.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), BLUE_LIGHT),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING',   (0, 0), (-1, -1), 12),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
        ('BOX',           (0, 0), (-1, -1), 0.5, BLUE_BORDER),
    ]))
    story.append(Spacer(1, 8))
    story.append(scen_box)
    story.append(Spacer(1, 16))

    # Position Detail
    story.append(KeepTogether([section_header('POSITION DETAIL', s)]))
    story.append(Spacer(1, 6))

    headers = ['Ticker', 'Name', 'Sector', 'Wt%', 'Value', 'Stressed', 'Loss %', 'VaR95', 'Risk']
    col_w   = [0.55 * inch, 1.35 * inch, 1.15 * inch, 0.42 * inch,
               0.75 * inch, 0.75 * inch, 0.82 * inch, 0.55 * inch, 0.55 * inch]

    sorted_pos = sorted(positions, key=lambda x: x.get('loss_pct', 0))
    rows = [headers]
    for p in sorted_pos:
        lp = p.get('loss_pct', 0)
        filled = min(8, int(abs(lp) / 4))
        bar    = '▓' * filled + '░' * (8 - filled) + f'  {lp:.1f}%'
        rows.append([
            p.get('ticker', ''),
            (p.get('name', '') or '')[:20],
            (p.get('sector', '') or '')[:16],
            f"{p.get('weight', 0):.1f}",
            f"${p.get('value', 0):,.0f}",
            f"${p.get('stressed_value', 0):,.0f}",
            bar,
            f"{p.get('var_95', 0):.1f}%",
            p.get('risk_level', 'Medium'),
        ])

    pt = Table(rows, colWidths=col_w, repeatRows=1)
    pos_style = [
        ('BACKGROUND',    (0, 0), (-1, 0),  NAVY),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  WHITE),
        ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 7.5),
        ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
        ('TEXTCOLOR',     (0, 1), (-1, -1), GRAY_700),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [WHITE, GRAY_100]),
        ('GRID',          (0, 0), (-1, -1), 0.3, GRAY_200),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('ALIGN',         (3, 0), (-1, -1), 'RIGHT'),
    ]
    for i, p in enumerate(sorted_pos, 1):
        lp   = p.get('loss_pct', 0)
        risk = p.get('risk_level', 'Medium')
        lc       = RED    if lp   < -20 else ORANGE if lp   < -10 else GREEN
        risk_bg  = RED_TINT    if risk == 'High'   else ORANGE_TINT if risk == 'Medium' else GREEN_TINT
        risk_tc  = RED         if risk == 'High'   else ORANGE      if risk == 'Medium' else GREEN
        pos_style += [
            ('TEXTCOLOR',  (6, i), (6, i), lc),
            ('FONTNAME',   (6, i), (6, i), 'Helvetica-Bold'),
            ('BACKGROUND', (8, i), (8, i), risk_bg),
            ('TEXTCOLOR',  (8, i), (8, i), risk_tc),
            ('FONTNAME',   (8, i), (8, i), 'Helvetica-Bold'),
        ]
    pt.setStyle(TableStyle(pos_style))
    story.append(pt)
    story.append(Spacer(1, 16))

    # Sector Allocation
    sector_weights = charts.get('sector_weights', {})
    sector_stress  = charts.get('sector_stress', {})
    if sector_weights:
        story.append(section_header('SECTOR ALLOCATION', s))
        story.append(Spacer(1, 6))

        sorted_sectors = sorted(sector_weights.items(), key=lambda x: x[1], reverse=True)
        max_w = max(v for _, v in sorted_sectors) if sorted_sectors else 1

        sec_rows = []
        for sector, weight in sorted_sectors:
            filled = int(weight / max_w * 20)
            empty  = 20 - filled
            sw = sector_stress.get(sector)
            if sw is not None:
                diff     = sw - weight
                vs_str   = f"{diff:+.1f}%"
                vs_hex   = '#EF4444' if diff < -2 else '#10B981' if diff > 0 else '#6B7280'
            else:
                vs_str = '—'
                vs_hex = '#6B7280'

            sec_rows.append([
                Paragraph(sector, ParagraphStyle('sl', fontSize=8,
                    fontName='Helvetica', textColor=GRAY_900)),
                Paragraph(
                    f'<font color="#3B82F6">{"█" * filled}</font>'
                    f'<font color="#D1D5DB">{"█" * empty}</font>',
                    ParagraphStyle('bar', fontSize=11, fontName='Helvetica')),
                Paragraph(f"{weight:.1f}%", ParagraphStyle('sw', fontSize=8,
                    fontName='Helvetica-Bold', textColor=GRAY_900, alignment=TA_RIGHT)),
                Paragraph(vs_str, ParagraphStyle('vs', fontSize=8,
                    fontName='Helvetica-Bold',
                    textColor=colors.HexColor(vs_hex), alignment=TA_RIGHT)),
            ])

        st = Table(sec_rows, colWidths=[1.8 * inch, 3.4 * inch, 0.65 * inch, 0.8 * inch])
        st.setStyle(TableStyle([
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [WHITE, GRAY_100]),
            ('GRID',           (0, 0), (-1, -1), 0.3, GRAY_200),
            ('TOPPADDING',     (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING',  (0, 0), (-1, -1), 5),
            ('LEFTPADDING',    (0, 0), (-1, -1), 8),
            ('ALIGN',          (2, 0), (3, -1),  'RIGHT'),
            ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(st)

    story.append(PageBreak())

    # ── PAGE 3: AI Analysis & Recommendations ───────────────────────────────────

    # Risk Scorecard
    story.append(section_header('RISK SCORECARD', s))
    story.append(Spacer(1, 6))

    fdata = charts.get('factors', {})
    risk_factors = [
        ('Market Beta',   fdata.get('beta_exposure',      loss_pct * -0.1),
                          fdata.get('beta_stress',         loss_pct * 0.6)),
        ('Interest Rate', fdata.get('rate_exposure',       0),
                          fdata.get('rate_stress',          0)),
        ('Inflation',     fdata.get('inflation_exposure',  0),
                          fdata.get('inflation_stress',     0)),
        ('Credit',        fdata.get('credit_exposure',     0),
                          fdata.get('credit_stress',        0)),
        ('Liquidity',     fdata.get('liquidity_exposure',  0),
                          fdata.get('liquidity_stress',     0)),
    ]

    _hdr_style = lambda txt: Paragraph(txt, ParagraphStyle('rh', fontSize=8,
        fontName='Helvetica-Bold', textColor=WHITE, alignment=TA_CENTER))
    sc_rows = [[
        Paragraph('RISK FACTOR', ParagraphStyle('rh0', fontSize=8,
            fontName='Helvetica-Bold', textColor=WHITE)),
        _hdr_style('CURRENT EXPOSURE'),
        _hdr_style('STRESS IMPACT'),
    ]]
    for factor_name, exposure, stress_impact in risk_factors:
        abs_impact = abs(stress_impact) if isinstance(stress_impact, (int, float)) else 0
        row_bg = RED_TINT if abs_impact > 10 else ORANGE_TINT if abs_impact > 5 else GREEN_TINT
        row_tc = RED      if abs_impact > 10 else ORANGE      if abs_impact > 5 else GREEN
        exp_str = f"{exposure:.2f}" if isinstance(exposure, float) else str(exposure)
        imp_str = (f"{stress_impact:+.1f}%"
                   if isinstance(stress_impact, (int, float)) else str(stress_impact))
        sc_rows.append([
            Paragraph(factor_name, ParagraphStyle('rn', fontSize=8.5,
                fontName='Helvetica-Bold', textColor=GRAY_900)),
            Paragraph(exp_str, ParagraphStyle('re', fontSize=8.5, fontName='Helvetica',
                textColor=GRAY_700, alignment=TA_CENTER)),
            Paragraph(imp_str, ParagraphStyle('ri', fontSize=8.5, fontName='Helvetica-Bold',
                textColor=row_tc, alignment=TA_CENTER)),
        ])

    sc_col_w = [CONTENT_W * 0.40, CONTENT_W * 0.30, CONTENT_W * 0.30]
    sc_tbl = Table(sc_rows, colWidths=sc_col_w)
    sc_style = [
        ('BACKGROUND',    (0, 0), (-1, 0), NAVY),
        ('GRID',          (0, 0), (-1, -1), 0.3, GRAY_200),
        ('TOPPADDING',    (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
    ]
    for i, (_, _, stress_impact) in enumerate(risk_factors, 1):
        abs_impact = abs(stress_impact) if isinstance(stress_impact, (int, float)) else 0
        row_bg = RED_TINT if abs_impact > 10 else ORANGE_TINT if abs_impact > 5 else GREEN_TINT
        sc_style.append(('BACKGROUND', (0, i), (-1, i), row_bg))
    sc_tbl.setStyle(TableStyle(sc_style))
    story.append(sc_tbl)
    story.append(Spacer(1, 18))

    # AI Analyst Memo
    if explanation:
        story.append(section_header('AI ANALYST MEMO', s))
        story.append(Spacer(1, 8))

        for key, heading, style in [
            ('advisor_summary',    'ADVISOR SUMMARY',            'dark'),
            ('client_explanation', 'CLIENT EXPLANATION',         'light'),
            ('suggestions',        'REBALANCING RECOMMENDATIONS', 'light'),
        ]:
            text = explanation.get(key, '')
            if not text:
                continue

            hdr_bg = NAVY                          if style == 'dark' else BLUE_LIGHT
            hdr_tc = WHITE                         if style == 'dark' else colors.HexColor('#1E40AF')

            hdr_tbl = Table([[
                Paragraph(heading, ParagraphStyle('mh', fontSize=9,
                    fontName='Helvetica-Bold', textColor=hdr_tc))
            ]], colWidths=[CONTENT_W])
            hdr_tbl.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, -1), hdr_bg),
                ('TOPPADDING',    (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING',   (0, 0), (-1, -1), 12),
            ]))
            story.append(hdr_tbl)

            content_bg = colors.HexColor('#F8FAFC') if style == 'dark' else WHITE
            text_clean = text.replace('**', '').replace('## ', '').replace('# ', '')
            for para in text_clean.split('\n\n'):
                para = para.strip()
                if not para:
                    continue
                for line in para.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith(('•', '-', '*', '1.', '2.', '3.', '4.', '5.')):
                        clean = line.lstrip('•-* 0123456789.').strip()
                        if not clean:
                            continue
                        inner = Table([[
                            Paragraph('●', ParagraphStyle('cb', fontSize=7,
                                fontName='Helvetica-Bold', textColor=BLUE,
                                alignment=TA_CENTER)),
                            Paragraph(clean, ParagraphStyle('cl', fontSize=8.5,
                                fontName='Helvetica', textColor=GRAY_700, leading=13)),
                        ]], colWidths=[0.2 * inch, CONTENT_W - 0.2 * inch])
                        inner.setStyle(TableStyle([
                            ('TOPPADDING',    (0, 0), (-1, -1), 1),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
                        ]))
                        outer = Table([[inner]], colWidths=[CONTENT_W])
                        outer.setStyle(TableStyle([
                            ('BACKGROUND',    (0, 0), (-1, -1), content_bg),
                            ('LEFTPADDING',   (0, 0), (-1, -1), 12),
                            ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
                            ('TOPPADDING',    (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                        ]))
                        story.append(outer)
                    else:
                        row = Table([[
                            Paragraph(line, ParagraphStyle('cp', fontSize=8.5,
                                fontName='Helvetica', textColor=GRAY_700, leading=13,
                                spaceAfter=3))
                        ]], colWidths=[CONTENT_W])
                        row.setStyle(TableStyle([
                            ('BACKGROUND',    (0, 0), (-1, -1), content_bg),
                            ('LEFTPADDING',   (0, 0), (-1, -1), 12),
                            ('RIGHTPADDING',  (0, 0), (-1, -1), 12),
                            ('TOPPADDING',    (0, 0), (-1, -1), 2),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                        ]))
                        story.append(row)
            story.append(Spacer(1, 10))

    # Disclaimer & Signature
    story.append(Spacer(1, 14))
    story.append(divider(GRAY_200, 0.5))
    story.append(Paragraph(
        f'This report was prepared by PortfolioStress on {now}.  '
        'Analysis is based on historical scenario modeling and parametric assumptions.  '
        'Past performance does not guarantee future results. Not investment advice.',
        ParagraphStyle('disc', fontSize=7, fontName='Helvetica',
            textColor=GRAY_500, leading=11, spaceAfter=6)
    ))
    story.append(divider(GRAY_200, 0.5))
    story.append(Paragraph(
        'PortfolioStress  ·  stress-test-frontend-three.vercel.app',
        ParagraphStyle('sig', fontSize=7.5, fontName='Helvetica-Bold',
            textColor=GRAY_700, alignment=TA_CENTER)
    ))

    doc.build(story, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    return output_path
