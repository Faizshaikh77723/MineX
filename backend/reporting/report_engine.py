import os
import re
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

REPORTS_DIR = Path("data/generated_reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def escape_for_reportlab(text: str) -> str:
    """
    1. Escapes XML special characters so ReportLab doesn't crash on '&' or '<'.
    2. Converts Markdown bold (**text**) to ReportLab bold (<b>text</b>).
    """
    # Fix the XML breaking characters
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Correctly parse bold tags
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    return text

def create_pdf_report(title: str, query: str, content_markdown: str) -> str:
    """
    Builds a statutory-style Ministry of Coal PDF report.
    Returns the absolute path of the generated PDF.
    """
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"MineX_Report_{timestamp_str}.pdf"
    filepath = REPORTS_DIR / filename

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom Government Letterhead Styles
    title_style = ParagraphStyle(
        'GovTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0b3c5d"),
        alignment=1 # Centered
    )
    
    subtitle_style = ParagraphStyle(
        'GovSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#5a6268"),
        alignment=1
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0b3c5d"),
        spaceBefore=14,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'GovBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#212529"),
        spaceAfter=6
    )

    meta_style = ParagraphStyle(
        'GovMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1d2731")
    )

    story = []

    # 1. Header Banner
    story.append(Paragraph("MINISTRY OF COAL • GOVERNMENT OF INDIA", title_style))
    story.append(Paragraph("MineX Autonomous Document Intelligence & Statutory Reporting System", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0b3c5d"), spaceAfter=15))

    # 2. Metadata Block
    ref_id = f"MOC/MINEX/STAT-REP/{datetime.now().strftime('%Y%m')}/{timestamp_str[-4:]}"
    meta_table_data = [
        [
            Paragraph(f"<b>DOCUMENT REF:</b> {ref_id}", meta_style),
            Paragraph(f"<b>DATE:</b> {datetime.now().strftime('%d %B %Y')}", meta_style)
        ],
        [
            Paragraph(f"<b>SUBJECT:</b> {escape_for_reportlab(title.upper()[:60])}...", meta_style),
            Paragraph("<b>SECURITY:</b> RESTRICTED (INTERNAL USE ONLY)", meta_style)
        ]
    ]
    t = Table(meta_table_data, colWidths=[300, 215])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f4f6f9")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#dcdfe3")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#dcdfe3")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    # 3. Process Content Lines
    lines = content_markdown.split("\n")
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            story.append(Spacer(1, 4))
            continue
        
        # Headings (Catches Markdown headers OR bolded lines standing alone)
        if line.startswith("#") or (line.startswith("**") and not line.startswith("** ")):
            clean_heading = line.replace("#", "").replace("*", "").strip()
            # Escape ampersands for the heading!
            clean_heading = clean_heading.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(clean_heading, section_heading))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dcdfe3"), spaceAfter=6))
            
        # Bullet Points
        elif line.startswith("- ") or line.startswith("* "):
            clean_bullet = escape_for_reportlab(line[2:])
            story.append(Paragraph(f"• {clean_bullet}", body_style))
            
        # Standard Text
        else:
            clean_text = escape_for_reportlab(line)
            story.append(Paragraph(clean_text, body_style))

    # 4. Official Sign-Off Block
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0b3c5d"), spaceAfter=15))
    sign_data = [
        [
            Paragraph("<b>Generated By:</b> MineX Document Synthesis Engine (SIH26023)", subtitle_style),
            Paragraph("<b>Verification:</b> Automated Statutory Cross-Verification (ChromaDB)", subtitle_style)
        ]
    ]
    sign_table = Table(sign_data, colWidths=[260, 255])
    story.append(sign_table)

    # Build PDF
    doc.build(story)
    return filename