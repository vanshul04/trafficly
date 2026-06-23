import os
import random
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
import qrcode

def sanitize_vehicle_number(vehicle_no, track_id):
    """
    Validation Rule: If vehicle_no is empty, unreadable, or 'UNKNOWN',
    automatically substitute it with: 'KA-MOCK-[TRACK_ID]'.
    """
    if not vehicle_no:
        return f"KA-MOCK-{track_id}"
    cleaned = str(vehicle_no).strip().upper()
    cleaned = "".join(c for c in cleaned if c.isalnum() or c == '-')
    if not cleaned or "UNKNOWN" in cleaned or len(cleaned) < 3:
        return f"KA-MOCK-{track_id}"
    return cleaned

def create_official_pdf(vehicle_no, violation_reason, track_id, location, output_path):
    """
    Trafficly Citation Generator
    Compiles a premium, formal PDF Notice for BTP ASTraM enforcement,
    specifically tailored for No Helmet offenses with hardcoded UPI routing.
    """
    # Create directory if missing
    pdf_dir = os.path.dirname(output_path)
    if pdf_dir and not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir, exist_ok=True)
        
    sanitized_plate = sanitize_vehicle_number(vehicle_no, track_id)
    
    # Offense parameters: No Helmet fine is ₹500 under Sec 129 r/w 177 MVA
    fine_amount = 500
    section_code = "Sec 129 r/w 177 MVA"
    legal_act = "Motor Vehicles Act, 1988"
    
    timestamp = datetime.datetime.now()
    challan_id = f"TRF-2026-{track_id}-{random.randint(1000, 9999)}"
    time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    # Hardcoded Payment Routing
    upi_uri = f"upi://pay?pa=vanshullalwani2-3@okhdfcbank&pn=Bengaluru%20Traffic%20Police&am={fine_amount}&cu=INR&tn={challan_id}"
    
    # Generate temporary QR image in output directory
    qr_img_path = output_path.replace(".pdf", "_qr.png")
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(upi_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(qr_img_path)
    
    # Setup document document templates
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Design palette styling
    NAVY = HexColor("#0A2540")      # Trafficly Brand Navy
    RED = HexColor("#FF4B4B")       # Crimson Offense Accent
    TEXT_COLOR = HexColor("#334155")
    LINE_COLOR = HexColor("#E2E8F0")
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=NAVY,
        alignment=1
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=RED,
        alignment=1
    )
    
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=NAVY,
        spaceAfter=5
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=TEXT_COLOR
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
        textColor=HexColor("#475569")
    )
    
    story = []
    
    # Notice Header
    story.append(Paragraph("GOVERNMENT OF KARNATAKA", title_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph("BENGALURU TRAFFIC POLICE (ASTraM AUTOMATED UNIT)", subtitle_style))
    story.append(Spacer(1, 2))
    story.append(Paragraph("TRAFFIC CITATION & NOTICE OF FINE / E-CHALLAN", ParagraphStyle('NoticeTitle', parent=title_style, fontSize=11, leading=14, textColor=HexColor('#1E293B'))))
    story.append(Spacer(1, 8))
    
    # 2px Brand Navy Divider
    div_table = Table([['']], colWidths=[540], rowHeights=[2])
    div_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), NAVY)]))
    story.append(div_table)
    story.append(Spacer(1, 10))
    
    # Notice Details Table
    info_data = [
        [
            Paragraph("<b>Challan Ref Number:</b>", body_style), Paragraph(challan_id, body_bold),
            Paragraph("<b>Citation Date & Time:</b>", body_style), Paragraph(time_str, body_style)
        ],
        [
            Paragraph("<b>Vehicle Registration:</b>", body_style), Paragraph(sanitized_plate, body_bold),
            Paragraph("<b>Camera Track ID:</b>", body_style), Paragraph(str(track_id), body_style)
        ],
        [
            Paragraph("<b>Enforcement Location:</b>", body_style), Paragraph(location, body_style),
            Paragraph("<b>Total Fine Demand:</b>", body_style), Paragraph(f"<b>Rs. {fine_amount:.2f}</b>", body_bold)
        ]
    ]
    
    info_table = Table(info_data, colWidths=[110, 160, 120, 150])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BACKGROUND', (0,0), (-1,-1), HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 0.5, HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.25, HexColor('#E2E8F0')),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 12))
    
    # Violation details table
    story.append(Paragraph("INFRACTION CITATION SUMMARY", section_title))
    
    headers = [
        Paragraph("<b>Sl No.</b>", body_bold),
        Paragraph("<b>Offense Registered / Violation Reason</b>", body_bold),
        Paragraph("<b>Section / Legal Code</b>", body_bold),
        Paragraph("<b>Fine Demand</b>", body_bold)
    ]
    
    row1 = [
        Paragraph("1", body_style),
        Paragraph(violation_reason, body_style),
        Paragraph(section_code, body_style),
        Paragraph(f"Rs. {fine_amount:.2f}", body_bold)
    ]
    
    summary_row = [
        Paragraph("", body_style),
        Paragraph("<b>TOTAL UNPAID DEMAND</b>", body_bold),
        Paragraph("", body_style),
        Paragraph(f"<b>Rs. {fine_amount:.2f}</b>", body_bold)
    ]
    
    table_data = [headers, row1, summary_row]
    fine_table = Table(table_data, colWidths=[40, 250, 150, 100])
    fine_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#F1F5F9')),
        ('TEXTCOLOR', (0, 0), (-1, 0), NAVY),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -2), 0.5, HexColor('#CBD5E1')),
        ('LINEBELOW', (0, -1), (-1, -1), 1.5, NAVY),
    ]))
    story.append(fine_table)
    story.append(Spacer(1, 12))
    
    # Locate photographic evidence crop inside output/crops folder
    evidence_crop_path = os.path.join("C:\\Users\\Vansh\\gridlock_hackathon\\output\\crops", f"track_{track_id}_{violation_reason.replace(' ', '_').replace('-', '_')}.jpg")
    
    # Try dynamic scan if exact pattern match fails
    if not os.path.exists(evidence_crop_path):
        crops_dir = "C:\\Users\\Vansh\\gridlock_hackathon\\output\\crops"
        if os.path.exists(crops_dir):
            for filename in os.listdir(crops_dir):
                if filename.startswith(f"track_{track_id}_") and filename.endswith(".jpg"):
                    evidence_crop_path = os.path.join(crops_dir, filename)
                    break

    if os.path.exists(evidence_crop_path):
        story.append(Paragraph("CAMERA RECORD EVIDENCE (PLATE & RIDER CAPTURE)", section_title))
        try:
            evidence_img = Image(evidence_crop_path, width=200, height=110)
            evidence_img.hAlign = 'LEFT'
            story.append(evidence_img)
            story.append(Spacer(1, 10))
        except Exception as e:
            print(f"[PDF COMPILER ERROR] Failed to draw crop evidence: {e}")
            
    story.append(Spacer(1, 4))
    
    legal_text = (
        "<b>Important Notice:</b> The citation has been compiled automatically by the Trafficly Radar Engine "
        "deployed at Bengaluru Traffic Police ASTraM Unit. You are required to settle this fine within 15 days "
        "of notice. Secure payment is routed instantly via SBI payment gateway. Payee Address: <b>vanshullalwani2-3@okhdfcbank</b>.<br/>"
        "Unpaid challans will be registered for judicial prosecution at the Hon'ble Traffic Courts."
    )
    
    try:
        qr_flowable = Image(qr_img_path, width=80, height=80)
        qr_flowable.hAlign = 'CENTER'
    except Exception as e:
        print(f"[PDF COMPILER ERROR] Failed to draw QR flowable: {e}")
        qr_flowable = Paragraph("<b>[QR Code Image Error]</b>", body_style)
        
    sig_text = (
        "<br/>"
        "<b>Inspector of Police</b><br/>"
        "Trafficly Enforcement Unit<br/>"
        "Bengaluru Traffic Police"
    )
    
    bottom_data = [
        [
            Paragraph(legal_text, legal_style),
            qr_flowable,
            Paragraph(sig_text, body_style)
        ]
    ]
    
    bottom_table = Table(bottom_data, colWidths=[290, 110, 140])
    bottom_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    
    divider = Table([['']], colWidths=[540], rowHeights=[0.5])
    divider.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), LINE_COLOR)]))
    
    story.append(divider)
    story.append(Spacer(1, 8))
    story.append(Paragraph("UPI SECURE PAYMENT GATEWAY & SIGNATURE", section_title))
    story.append(Spacer(1, 4))
    story.append(bottom_table)
    
    doc.build(story)
    
    return sanitized_plate, challan_id
