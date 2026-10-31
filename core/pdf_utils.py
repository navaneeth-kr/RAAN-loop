import io
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from core.models import SystemSetting

def _get_company_header():
    setting = SystemSetting.get_settings()
    return {
        'name': setting.company_name or "Brightloop Software",
        'email': setting.billing_email or "billing@brightloop.io",
        'support': setting.support_email or "support@brightloop.io",
        'currency': setting.currency_symbol or "$",
    }

def generate_invoice_pdf(invoice):
    """Generates an executive, professional PDF invoice for Brightloop Software."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    company = _get_company_header()
    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor('#0f172a')
    secondary_color = colors.HexColor('#475569')
    accent_color = colors.HexColor('#2563eb')
    border_color = colors.HexColor('#e2e8f0')

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=primary_color,
        leading=28,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=secondary_color,
        leading=12
    )
    badge_style = ParagraphStyle(
        'StatusBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white,
        alignment=1
    )
    header_col = ParagraphStyle(
        'HCol',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=secondary_color,
        leading=11
    )
    body_bold = ParagraphStyle(
        'BBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=primary_color,
        leading=12
    )
    body_normal = ParagraphStyle(
        'BNorm',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=primary_color,
        leading=12
    )

    story = []

    # 1. Header with Company Branding & Invoice Badge
    header_data = [
        [
            Paragraph(f"<b>{company['name']}</b><br/><font size=8 color='#64748b'>Enterprise Cloud & Subscription Billing<br/>{company['email']} | {company['support']}</font>", body_normal),
            Paragraph(f"<font size=20 color='#0f172a'><b>INVOICE</b></font><br/><font size=10 color='#2563eb'><b>#{invoice.invoice_number}</b></font><br/><font size=8 color='#64748b'>Status: <b>{invoice.get_status_display().upper()}</b></font>", ParagraphStyle('RAlign', parent=body_normal, alignment=2))
        ]
    ]
    t_header = Table(header_data, colWidths=[340, 200])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(t_header)

    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=15))

    # 2. Billed To & Invoice Metadata Table
    customer = invoice.customer
    bill_to_text = f"""<b>BILLED TO:</b><br/>
    <b>{customer.full_name}</b><br/>
    {customer.company_name or 'Individual Account'}<br/>
    {customer.email}<br/>
    {customer.phone or ''}<br/>
    {customer.address or ''} {customer.city or ''}
    """
    meta_text = f"""<b>INVOICE DETAILS:</b><br/>
    <b>Invoice Date:</b> {invoice.issued_date}<br/>
    <b>Payment Due:</b> {invoice.due_date}<br/>
    <b>Subscription Ref:</b> {invoice.subscription.subscription_id if invoice.subscription else 'Direct Service'}<br/>
    <b>Paid Amount:</b> {company['currency']}{invoice.paid_amount}<br/>
    <b>Balance Due:</b> <font color='#dc2626'><b>{company['currency']}{invoice.balance_due}</b></font>
    """
    info_data = [
        [Paragraph(bill_to_text, body_normal), Paragraph(meta_text, body_normal)]
    ]
    t_info = Table(info_data, colWidths=[270, 270])
    t_info.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 15))

    # 3. Line Items Table
    plan_name = invoice.subscription.plan.name if (invoice.subscription and invoice.subscription.plan) else "Brightloop Business Subscription"
    variant_name = f" ({invoice.subscription.variant.name})" if (invoice.subscription and invoice.subscription.variant) else ""
    qty = invoice.subscription.quantity if invoice.subscription else 1

    items_data = [
        [Paragraph("Item / Description", header_col), Paragraph("Qty", header_col), Paragraph("Unit Price", header_col), Paragraph("Amount", header_col)],
        [
            Paragraph(f"<b>{plan_name}{variant_name}</b><br/><font size=8 color='#64748b'>Recurring period service charges for {invoice.subscription.billing_cycle if invoice.subscription else 'subscription'}</font>", body_normal),
            Paragraph(str(qty), body_normal),
            Paragraph(f"{company['currency']}{invoice.amount}", body_normal),
            Paragraph(f"{company['currency']}{invoice.amount}", body_bold),
        ]
    ]

    t_items = Table(items_data, colWidths=[270, 60, 100, 110])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, border_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,1), (-1,-1), 8),
        ('BOTTOMPADDING', (0,1), (-1,-1), 8),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 10))

    # 4. Financial Summary
    summary_data = [
        ["", "", Paragraph("Subtotal:", body_bold), Paragraph(f"{company['currency']}{invoice.amount}", body_bold)],
        ["", "", Paragraph(f"Tax ({invoice.tax_rate.rate_percent if invoice.tax_rate else '0'}%):", body_normal), Paragraph(f"+{company['currency']}{invoice.tax_amount}", body_normal)],
        ["", "", Paragraph(f"Discount ({invoice.discount.code if invoice.discount else 'None'}):", body_normal), Paragraph(f"-{company['currency']}{invoice.discount_amount}", body_normal)],
        ["", "", Paragraph("<b>Final Total:</b>", title_style), Paragraph(f"<b>{company['currency']}{invoice.total_amount}</b>", title_style)],
    ]
    t_sum = Table(summary_data, colWidths=[170, 100, 160, 110])
    t_sum.setStyle(TableStyle([
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LINEABOVE', (2,3), (3,3), 1, primary_color),
    ]))
    story.append(t_sum)
    story.append(Spacer(1, 20))

    # 5. Notes / Terms
    notes_text = invoice.notes or "Thank you for partnering with Brightloop Software. Payment terms apply according to your subscription agreement. Invoices unpaid after grace period are subject to service suspension."
    story.append(Paragraph(f"<b>Payment Terms & Remarks:</b><br/><font size=8 color='#475569'>{notes_text}</font>", body_normal))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_quotation_pdf(quotation):
    """Generates an executive PDF quotation for Brightloop Software."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    company = _get_company_header()
    styles = getSampleStyleSheet()

    primary_color = colors.HexColor('#0f172a')
    secondary_color = colors.HexColor('#475569')
    accent_color = colors.HexColor('#0d9488')
    border_color = colors.HexColor('#e2e8f0')

    body_normal = ParagraphStyle('BNormQ', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=primary_color, leading=12)
    body_bold = ParagraphStyle('BBoldQ', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=primary_color, leading=12)
    header_col = ParagraphStyle('HColQ', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=secondary_color, leading=11)

    story = []

    # 1. Header
    header_data = [
        [
            Paragraph(f"<b>{company['name']}</b><br/><font size=8 color='#64748b'>Official Commercial Proposal<br/>{company['email']} | {company['support']}</font>", body_normal),
            Paragraph(f"<font size=20 color='#0f172a'><b>QUOTATION</b></font><br/><font size=10 color='#0d9488'><b>#{quotation.quotation_number}</b></font><br/><font size=8 color='#64748b'>Valid Until: <b>{quotation.valid_until}</b></font>", ParagraphStyle('RAlignQ', parent=body_normal, alignment=2))
        ]
    ]
    t_header = Table(header_data, colWidths=[340, 200])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=15))

    # 2. Recipient & Quote info
    customer = quotation.customer
    bill_to_text = f"""<b>PREPARED FOR:</b><br/>
    <b>{customer.full_name}</b><br/>
    {customer.company_name or 'Enterprise Client'}<br/>
    {customer.email} | {customer.phone or ''}
    """
    meta_text = f"""<b>PROPOSAL TERMS:</b><br/>
    <b>Issue Date:</b> {quotation.created_at.date()}<br/>
    <b>Validity:</b> {quotation.validity_days} Days (Expires: {quotation.valid_until})<br/>
    <b>Status:</b> <b>{quotation.get_status_display().upper()}</b><br/>
    <b>Plan:</b> {quotation.plan.name} ({quotation.plan.billing_frequency.title()})
    """
    info_data = [[Paragraph(bill_to_text, body_normal), Paragraph(meta_text, body_normal)]]
    t_info = Table(info_data, colWidths=[270, 270])
    t_info.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 15))

    # 3. Items
    items_data = [
        [Paragraph("Plan / Scope", header_col), Paragraph("Qty", header_col), Paragraph("Unit Price", header_col), Paragraph("Total", header_col)],
        [
            Paragraph(f"<b>{quotation.plan.name}</b><br/><font size=8 color='#64748b'>{quotation.plan.description or 'Dedicated cloud subscription tier'}</font>", body_normal),
            Paragraph(str(quotation.quantity), body_normal),
            Paragraph(f"{company['currency']}{quotation.unit_price or quotation.subtotal}", body_normal),
            Paragraph(f"{company['currency']}{quotation.subtotal or quotation.total_amount}", body_bold),
        ]
    ]
    t_items = Table(items_data, colWidths=[270, 60, 100, 110])
    t_items.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, border_color),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,1), (-1,-1), 8),
        ('BOTTOMPADDING', (0,1), (-1,-1), 8),
    ]))
    story.append(t_items)
    story.append(Spacer(1, 10))

    # 4. Summary
    sub = quotation.subtotal or quotation.total_amount
    summary_data = [
        ["", "", Paragraph("Subtotal:", body_bold), Paragraph(f"{company['currency']}{sub}", body_bold)],
        ["", "", Paragraph("Tax Amount:", body_normal), Paragraph(f"+{company['currency']}{quotation.tax_amount}", body_normal)],
        ["", "", Paragraph("Discount:", body_normal), Paragraph(f"-{company['currency']}{quotation.discount_amount}", body_normal)],
        ["", "", Paragraph("<b>Quotation Total:</b>", body_bold), Paragraph(f"<b>{company['currency']}{quotation.total_amount}</b>", body_bold)],
    ]
    t_sum = Table(summary_data, colWidths=[170, 100, 160, 110])
    t_sum.setStyle(TableStyle([
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('LINEABOVE', (2,3), (3,3), 1, primary_color),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_sum)
    story.append(Spacer(1, 20))

    if quotation.notes:
        story.append(Paragraph(f"<b>Quotation Notes & Inclusions:</b><br/><font size=8 color='#475569'>{quotation.notes}</font>", body_normal))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generate_payment_receipt_pdf(payment):
    """Generates an official payment confirmation receipt."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    company = _get_company_header()
    styles = getSampleStyleSheet()

    primary_color = colors.HexColor('#0f172a')
    success_color = colors.HexColor('#16a34a')
    border_color = colors.HexColor('#e2e8f0')

    body_normal = ParagraphStyle('BNormP', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=primary_color, leading=12)
    body_bold = ParagraphStyle('BBoldP', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, textColor=primary_color, leading=12)

    story = []

    # 1. Header
    header_data = [
        [
            Paragraph(f"<b>{company['name']}</b><br/><font size=8 color='#64748b'>Payment Settlement Receipt<br/>{company['email']}</font>", body_normal),
            Paragraph(f"<font size=20 color='#16a34a'><b>RECEIPT</b></font><br/><font size=10 color='#0f172a'><b>#{payment.payment_id}</b></font><br/><font size=8 color='#64748b'>Date: <b>{payment.payment_date.strftime('%Y-%m-%d %H:%M')}</b></font>", ParagraphStyle('RAlignP', parent=body_normal, alignment=2))
        ]
    ]
    t_header = Table(header_data, colWidths=[340, 200])
    t_header.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(t_header)
    story.append(HRFlowable(width="100%", thickness=1.5, color=success_color, spaceAfter=15))

    # 2. Receipt Grid
    receipt_data = [
        [Paragraph("<b>Customer Name:</b>", body_bold), Paragraph(payment.customer.full_name, body_normal)],
        [Paragraph("<b>Organization:</b>", body_bold), Paragraph(payment.customer.company_name or "Individual", body_normal)],
        [Paragraph("<b>Related Invoice:</b>", body_bold), Paragraph(payment.invoice.invoice_number if payment.invoice else "Direct Payment", body_normal)],
        [Paragraph("<b>Payment Method:</b>", body_bold), Paragraph(payment.get_payment_method_display(), body_normal)],
        [Paragraph("<b>Transaction Ref:</b>", body_bold), Paragraph(payment.transaction_reference or "N/A", body_normal)],
        [Paragraph("<b>Payment Status:</b>", body_bold), Paragraph(f"<font color='#16a34a'><b>{payment.get_status_display().upper()}</b></font>", body_normal)],
        [Paragraph("<b>Amount Paid:</b>", body_bold), Paragraph(f"<font size=14 color='#0f172a'><b>{company['currency']}{payment.amount}</b></font>", body_bold)],
    ]
    t_receipt = Table(receipt_data, colWidths=[150, 390])
    t_receipt.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(t_receipt)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
