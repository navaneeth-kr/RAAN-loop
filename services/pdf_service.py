"""
PDF generation service using ReportLab.
Generates a professional printable invoice PDF.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                Paragraph, Spacer, HRFlowable)
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from io import BytesIO
from flask import current_app


def generate_invoice_pdf(invoice):
    """
    Generate a PDF for the given Invoice ORM object.
    Returns a BytesIO buffer.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    brand_color = colors.HexColor('#2563EB')
    light_gray = colors.HexColor('#F3F4F6')
    mid_gray = colors.HexColor('#6B7280')

    title_style = ParagraphStyle('Title', parent=styles['Heading1'],
                                 fontSize=22, textColor=brand_color, spaceAfter=4)
    label_style = ParagraphStyle('Label', parent=styles['Normal'],
                                 fontSize=9, textColor=mid_gray)
    value_style = ParagraphStyle('Value', parent=styles['Normal'],
                                 fontSize=10, textColor=colors.black)
    right_style = ParagraphStyle('Right', parent=styles['Normal'],
                                 alignment=TA_RIGHT, fontSize=10)
    center_style = ParagraphStyle('Center', parent=styles['Normal'],
                                  alignment=TA_CENTER, fontSize=9)

    company_name = current_app.config.get('COMPANY_NAME', 'Company')
    company_address = current_app.config.get('COMPANY_ADDRESS', '')
    company_phone = current_app.config.get('COMPANY_PHONE', '')
    company_email = current_app.config.get('COMPANY_EMAIL', '')

    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    header_data = [
        [
            Paragraph(company_name, title_style),
            Paragraph(f'<b>INVOICE</b>', ParagraphStyle('INV', fontSize=24,
                       alignment=TA_RIGHT, textColor=brand_color)),
        ],
        [
            Paragraph(f'{company_address}<br/>{company_phone}<br/>{company_email}', label_style),
            Paragraph(f'<font color="grey">Invoice #</font><br/>'
                      f'<b>{invoice.invoice_number}</b>', right_style),
        ],
    ]
    header_table = Table(header_data, colWidths=[95 * mm, 85 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)
    story.append(HRFlowable(width='100%', thickness=2, color=brand_color, spaceAfter=10))

    # ── Bill To / Invoice Meta ───────────────────────────────────────────────
    customer = invoice.customer
    bill_to = (f'<b>Bill To:</b><br/>'
               f'{customer.name}<br/>'
               f'{customer.email}<br/>'
               f'{customer.phone or ""}<br/>'
               f'{customer.address or ""}'
               f'{", " + customer.city if customer.city else ""}'
               f'{", " + customer.country if customer.country else ""}')

    meta_lines = [
        f'<b>Invoice Date:</b> {invoice.invoice_date.strftime("%d %b %Y")}',
        f'<b>Due Date:</b> {invoice.due_date.strftime("%d %b %Y")}',
        f'<b>Status:</b> {invoice.status.upper()}',
    ]
    if invoice.subscription_id:
        meta_lines.append(f'<b>Subscription:</b> {invoice.subscription.subscription_number}')
    if invoice.billing_period_start:
        meta_lines.append(
            f'<b>Billing Period:</b> '
            f'{invoice.billing_period_start.strftime("%d %b %Y")} – '
            f'{invoice.billing_period_end.strftime("%d %b %Y") if invoice.billing_period_end else ""}')

    meta_text = '<br/>'.join(meta_lines)

    meta_table = Table(
        [[Paragraph(bill_to, value_style), Paragraph(meta_text, right_style)]],
        colWidths=[95 * mm, 85 * mm],
    )
    meta_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    story.append(meta_table)
    story.append(Spacer(1, 10 * mm))

    # ── Line Items Table ─────────────────────────────────────────────────────
    item_header = ['Description', 'Qty', 'Unit Price', 'Amount']
    amount = float(invoice.unit_price) * invoice.quantity
    item_row = [
        Paragraph(f'<b>{invoice.product_name}</b><br/>'
                  f'<font color="grey">{invoice.product_description or ""}</font>', value_style),
        str(invoice.quantity),
        f'${float(invoice.unit_price):,.2f}',
        f'${amount:,.2f}',
    ]

    items_data = [item_header, item_row]
    items_table = Table(items_data, colWidths=[90 * mm, 20 * mm, 35 * mm, 35 * mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), brand_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 1), (-1, -1), light_gray),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_gray]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D1D5DB')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6 * mm))

    # ── Totals ───────────────────────────────────────────────────────────────
    totals = [
        ['Subtotal', f'${float(invoice.subtotal):,.2f}'],
    ]
    if float(invoice.discount_percent or 0) > 0:
        totals.append([f'Discount ({invoice.discount_percent}%)', f'-${float(invoice.discount_amount):,.2f}'])
    if float(invoice.tax_rate or 0) > 0:
        totals.append([f'{invoice.tax_name or "Tax"} ({invoice.tax_rate}%)', f'${float(invoice.tax_amount):,.2f}'])
    totals.append(['', ''])  # spacer row
    totals.append([Paragraph('<b>TOTAL DUE</b>', ParagraphStyle('TotalLabel', fontSize=12, alignment=TA_RIGHT)),
                   Paragraph(f'<b>${float(invoice.total_amount):,.2f}</b>',
                             ParagraphStyle('TotalVal', fontSize=12, alignment=TA_RIGHT, textColor=brand_color))])

    totals_table = Table(totals, colWidths=[130 * mm, 50 * mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (-1, -1), (-1, -1), 1.5, brand_color),
    ]))
    story.append(totals_table)

    # ── Notes ────────────────────────────────────────────────────────────────
    if invoice.notes:
        story.append(Spacer(1, 8 * mm))
        story.append(HRFlowable(width='100%', thickness=0.5, color=mid_gray))
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph('<b>Notes:</b>', label_style))
        story.append(Paragraph(invoice.notes, value_style))

    # ── Footer ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=mid_gray))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(f'Thank you for your business! | {company_email}', center_style))

    doc.build(story)
    buffer.seek(0)
    return buffer

