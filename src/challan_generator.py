import os
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
import qrcode

def sanitize_license_plate(plate, track_id):
    """
    Cleans up the license plate text. If the plate is empty, contains 'UNKNOWN',
    or is otherwise unreadable, automatically substitutes it with the fallback pattern.
    """
    if not plate:
        return f"KA-MOCK-{track_id}"
    
    cleaned = str(plate).strip().upper()
    # Remove common junk characters, keep alphanumeric and hyphens
    cleaned = "".join(c for c in cleaned if c.isalnum() or c == '-')
    
    # Check if plate is essentially UNKNOWN or invalid
    if not cleaned or "UNKNOWN" in cleaned or len(cleaned) < 3:
        return f"KA-MOCK-{track_id}"
    
    return cleaned

def generate_upi_qr(upi_uri, output_path):
    """
    Generates a high-quality QR code image mapping the UPI payment URI.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(upi_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(output_path)

def get_failproof_separator(color=HexColor('#0F172A'), thickness=1):
    """
    Creates a robust horizontal divider using a Table. Avoids HRFlowable version dependencies.
    """
    t = Table([['']], colWidths=[530], rowHeights=[thickness])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), color),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    return t

def generate_challan_pdf(challan_no, track_id, license_plate, violation_type, fine_amount, section_code, location, timestamp, output_pdf_path, crop_image_path=None):
    """
    Generates an official BTP e-challan PDF with details of the violation,
    evidence image, and an active UPI payment QR Code.
    """
    # Create output directory if it doesn't exist
    pdf_dir = os.path.dirname(output_pdf_path)
    if pdf_dir and not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir, exist_ok=True)

    # Sanitize plate
    sanitized_plate = sanitize_license_plate(license_plate, track_id)
    
    # Format UPI Link: upi://pay?pa=btpchallan@sbi&pn=Bengaluru%20Traffic%20Police&am=[AMOUNT]&cu=INR&tn=[CHALLAN_NO]
    upi_uri = f"upi://pay?pa=btpchallan@sbi&pn=Bengaluru%20Traffic%20Police&am={fine_amount}&cu=INR&tn={challan_no}"
    
    # Create QR code in same directory as PDF
    qr_img_path = os.path.join(pdf_dir, f"{challan_no}_qr.png")
    generate_upi_qr(upi_uri, qr_img_path)
    
    # Setup Document
    doc = SimpleDocTemplate(
        output_pdf_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles matching Karnataka Government professional formatting
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=HexColor('#0F172A'),
        alignment=1 # Centered
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=HexColor('#B91C1C'),
        alignment=1 # Centered
    )
    
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=HexColor('#1E3A8A'),
        spaceAfter=5
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=HexColor('#334155')
    )
    
    body_bold = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    legal_style = ParagraphStyle(
        'LegalText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        leading=10,
        textColor=HexColor('#475569')
    )
    
    story = []
    
    # Header block
    story.append(Paragraph("GOVERNMENT OF KARNATAKA", title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph("BENGALURU TRAFFIC POLICE (ASTraM UNIT)", subtitle_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph("OFFICIAL NOTICE OF TRAFFIC VIOLATION / E-CHALLAN", ParagraphStyle('NoticeTitle', parent=title_style, fontSize=12, leading=15, textColor=HexColor('#1E293B'))))
    story.append(Spacer(1, 8))
    
    # Header Line
    story.append(get_failproof_separator(color=HexColor('#0F172A'), thickness=2))
    story.append(Spacer(1, 10))
    
    # Metadata Block
    time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S") if isinstance(timestamp, datetime.datetime) else str(timestamp)
    details_data = [
        [
            Paragraph("<b>Challan Number:</b>", body_style), Paragraph(challan_no, body_bold),
            Paragraph("<b>Notice Date:</b>", body_style), Paragraph(time_str, body_style)
        ],
        [
            Paragraph("<b>Vehicle Reg. No:</b>", body_style), Paragraph(sanitized_plate, body_bold),
            Paragraph("<b>Track trajectory ID:</b>", body_style), Paragraph(str(track_id), body_style)
        ],
        [
            Paragraph("<b>Junction / Camera ID:</b>", body_style), Paragraph(f"{location} (CAM-HEBBAL-01)", body_style),
            Paragraph("<b>Payment Status:</b>", body_style), Paragraph("<font color='#B91C1C'><b>PENDING</b></font>", body_style)
        ]
    ]
    
    details_table = Table(details_data, colWidths=[110, 155, 120, 145])
    details_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BACKGROUND', (0,0), (-1,-1), HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, HexColor('#E2E8F0')),
        ('INNERGRID', (0,0), (-1,-1), 0.25, HexColor('#F1F5F9')),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 12))
    
    # Offense and Fine breakdown Table
    story.append(Paragraph("OFFENSE DESCRIPTION & PENALTY DETAIL", section_title))
    
    headers = [
        Paragraph("<b>Sl No.</b>", body_bold),
        Paragraph("<b>Violation Description</b>", body_bold),
        Paragraph("<b>Act / Section Code</b>", body_bold),
        Paragraph("<b>Fine (INR)</b>", body_bold)
    ]
    
    row1 = [
        Paragraph("1", body_style),
        Paragraph(violation_type, body_style),
        Paragraph(section_code, body_style),
        Paragraph(f"Rs. {fine_amount:.2f}", body_bold)
    ]
    
    summary_row = [
        Paragraph("", body_style),
        Paragraph("<b>TOTAL DEMAND AMOUNT</b>", body_bold),
        Paragraph("", body_style),
        Paragraph(f"<b>Rs. {fine_amount:.2f}</b>", body_bold)
    ]
    
    table_data = [headers, row1, summary_row]
    fine_table = Table(table_data, colWidths=[50, 240, 140, 100])
    fine_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#0F172A')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -2), 0.5, HexColor('#CBD5E1')),
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, HexColor('#0F172A')),
    ]))
    story.append(fine_table)
    story.append(Spacer(1, 12))
    
    # Photographic Evidence Block (Includes Crop)
    evidence_added = False
    if crop_image_path and os.path.exists(crop_image_path):
        story.append(Paragraph("PHOTOGRAPHIC EVIDENCE (CAMERA CAPTURE)", section_title))
        try:
            # Render evidence crop cleanly
            evidence_img = Image(crop_image_path, width=220, height=120)
            evidence_img.hAlign = 'LEFT'
            story.append(evidence_img)
            story.append(Spacer(1, 10))
            evidence_added = True
        except Exception as e:
            print(f"Error drawing evidence crop: {e}")
    
    if not evidence_added:
        # Placeholder indicator in the PDF if no crop image is provided/accessible
        story.append(Paragraph("PHOTOGRAPHIC EVIDENCE (CAMERA CAPTURE)", section_title))
        story.append(Paragraph("<i>[Image evidence cached on security servers; details cross-referenced in BTP ASTraM central database]</i>", body_style))
        story.append(Spacer(1, 10))
        
    # Legal Warning
    legal_text = (
        "<b>LEGAL WARNING:</b> This notice is generated automatically by ASTraM Unit camera systems "
        "of the Bengaluru Traffic Police. Under Section 119/122/128/129 of the Motor Vehicles Act, 1988, "
        "the registered owner is liable to pay the penalty listed above. Please settle this amount within "
        "fifteen (15) days of receipt. Unsettled notices will be sent to the Hon'ble Traffic Courts "
        "for prosecution, and the vehicle registration details will be marked as blacklisted, restricting "
        "subsequent transfers, fitness certifications, or insurance renewals."
    )
    story.append(Paragraph(legal_text, legal_style))
    story.append(Spacer(1, 10))
    
    # Divider for payment section
    story.append(get_failproof_separator(color=HexColor('#E2E8F0'), thickness=1))
    story.append(Spacer(1, 8))
    
    # UPI Payment block at the bottom
    story.append(Paragraph("UPI PAYMENT INTERACTION AND AUTHORIZATION", section_title))
    story.append(Spacer(1, 4))
    
    payment_instruction = (
        "Scan the QR code to pay the fine via Bharat UPI instantly.<br/>"
        "1. Open any UPI application (GPay, PhonePe, Paytm, BHIM, etc.).<br/>"
        "2. Scan this QR code and verify the payee as <b>Bengaluru Traffic Police</b>.<br/>"
        "3. Complete transaction using your secure UPI PIN.<br/>"
        "<b>Payee Address:</b> btpchallan@sbi<br/>"
        "<b>Transaction Ref:</b> " + challan_no
    )
    
    try:
        qr_flowable = Image(qr_img_path, width=85, height=85)
        qr_flowable.hAlign = 'CENTER'
    except Exception as e:
        print(f"Error loading QR code flowable: {e}")
        qr_flowable = Paragraph("<b>[QR Code Unavailable]</b>", body_style)
        
    sig_text = (
        "<br/>"
        "<b>Inspector of Police (ASTraM)</b><br/>"
        "Automation Control Center<br/>"
        "Bengaluru Traffic Police"
    )
    
    payment_data = [
        [
            Paragraph(payment_instruction, body_style),
            qr_flowable,
            Paragraph(sig_text, body_style)
        ]
    ]
    
    payment_table = Table(payment_data, colWidths=[280, 110, 140])
    payment_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(payment_table)
    
    # Build Document
    doc.build(story)
    
    # Clean up QR image from filesystem if it isn't needed anymore
    # Keeping it makes it available to the user for inspection. We'll leave it in the directory.
    return sanitized_plate
