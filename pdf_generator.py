""" 

Generates a formatted discharge summary PDF from the JSON output. 

Uses reportlab to produce a clean, clinically structured document. 

""" 

 

import os 

import json 

from datetime import datetime 

from reportlab.lib.pagesizes import A4 

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle 

from reportlab.lib.units import cm 

from reportlab.lib import colors 

from reportlab.platypus import ( 

    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 

    HRFlowable, KeepTogether 

) 

from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT 

 

 

# ── Colour palette ── 

DARK_BLUE   = colors.HexColor("#1a3a5c") 

MID_BLUE    = colors.HexColor("#2d6a9f") 

LIGHT_BLUE  = colors.HexColor("#ebf8ff") 

RED         = colors.HexColor("#e53e3e") 

AMBER       = colors.HexColor("#d69e2e") 

GREEN       = colors.HexColor("#276749") 

LIGHT_RED   = colors.HexColor("#fff0f0") 

LIGHT_AMBER = colors.HexColor("#fffbeb") 

LIGHT_GREEN = colors.HexColor("#f0fff4") 

LIGHT_GREY  = colors.HexColor("#f7fafc") 

BORDER_GREY = colors.HexColor("#e2e8f0") 

TEXT_GREY   = colors.HexColor("#4a5568") 

 

 

def build_styles(): 

    base = getSampleStyleSheet() 

    styles = {} 

 

    styles["title"] = ParagraphStyle( 

        "title", parent=base["Normal"], 

        fontSize=18, textColor=colors.white, 

        fontName="Helvetica-Bold", alignment=TA_CENTER, 

        spaceAfter=4, 

    ) 

    styles["subtitle"] = ParagraphStyle( 

        "subtitle", parent=base["Normal"], 

        fontSize=9, textColor=colors.HexColor("#bee3f8"), 

        fontName="Helvetica", alignment=TA_CENTER, 

        spaceAfter=0, 

    ) 

    styles["section_header"] = ParagraphStyle( 

        "section_header", parent=base["Normal"], 

        fontSize=11, textColor=colors.white, 

        fontName="Helvetica-Bold", spaceAfter=4, 

        spaceBefore=12, 

    ) 

    styles["field_label"] = ParagraphStyle( 

        "field_label", parent=base["Normal"], 

        fontSize=8, textColor=TEXT_GREY, 

        fontName="Helvetica-Bold", spaceAfter=1, 

    ) 

    styles["field_value"] = ParagraphStyle( 

        "field_value", parent=base["Normal"], 

        fontSize=9, textColor=colors.HexColor("#2d3748"), 

        fontName="Helvetica", spaceAfter=4, leading=13, 

    ) 

    styles["flag_critical"] = ParagraphStyle( 

        "flag_critical", parent=base["Normal"], 

        fontSize=8.5, textColor=RED, 

        fontName="Helvetica-Bold", spaceAfter=3, leading=12, 

    ) 

    styles["flag_warning"] = ParagraphStyle( 

        "flag_warning", parent=base["Normal"], 

        fontSize=8.5, textColor=colors.HexColor("#b7791f"), 

        fontName="Helvetica", spaceAfter=3, leading=12, 

    ) 

    styles["flag_info"] = ParagraphStyle( 

        "flag_info", parent=base["Normal"], 

        fontSize=8.5, textColor=colors.HexColor("#2c7a7b"), 

        fontName="Helvetica", spaceAfter=3, leading=12, 

    ) 

    styles["disclaimer"] = ParagraphStyle( 

        "disclaimer", parent=base["Normal"], 

        fontSize=8, textColor=colors.HexColor("#744210"), 

        fontName="Helvetica-Bold", alignment=TA_CENTER, 

        spaceAfter=0, 

    ) 

    styles["footer"] = ParagraphStyle( 

        "footer", parent=base["Normal"], 

        fontSize=7.5, textColor=TEXT_GREY, 

        fontName="Helvetica", alignment=TA_CENTER, 

    ) 

    styles["icd_code"] = ParagraphStyle( 

        "icd_code", parent=base["Normal"], 

        fontSize=8, textColor=MID_BLUE, 

        fontName="Helvetica-Bold", 

    ) 

    styles["med_item"] = ParagraphStyle( 

        "med_item", parent=base["Normal"], 

        fontSize=8.5, textColor=colors.HexColor("#2d3748"), 

        fontName="Helvetica", spaceAfter=2, leading=12, 

        leftIndent=8, 

    ) 

    return styles 

 

 

def section_header(text: str, styles) -> list: 

    """Returns a coloured section header bar.""" 

    return [ 

        Spacer(1, 0.2 * cm), 

        Table( 

            [[Paragraph(f"  {text}", styles["section_header"])]], 

            colWidths=["100%"], 

            style=TableStyle([ 

                ("BACKGROUND", (0, 0), (-1, -1), MID_BLUE), 

                ("TOPPADDING", (0, 0), (-1, -1), 6), 

                ("BOTTOMPADDING", (0, 0), (-1, -1), 6), 

                ("LEFTPADDING", (0, 0), (-1, -1), 8), 

                ("ROUNDEDCORNERS", [4, 4, 4, 4]), 

            ]), 

        ), 

        Spacer(1, 0.15 * cm), 

    ] 

 

 

def info_row(label: str, value: str, styles) -> Table: 

    """Returns a two-cell label/value row.""" 

    return Table( 

        [[ 

            Paragraph(label, styles["field_label"]), 

            Paragraph(str(value) if value else "—", styles["field_value"]), 

        ]], 

        colWidths=[3.5 * cm, 13.5 * cm], 

        style=TableStyle([ 

            ("VALIGN", (0, 0), (-1, -1), "TOP"), 

            ("TOPPADDING", (0, 0), (-1, -1), 2), 

            ("BOTTOMPADDING", (0, 0), (-1, -1), 2), 

        ]), 

    ) 

 

 

def two_col_table(rows: list, styles) -> Table: 

    """Renders a simple two-column key/value table.""" 

    table_data = [] 

    for label, value in rows: 

        table_data.append([ 

            Paragraph(label, styles["field_label"]), 

            Paragraph(str(value) if value else "—", styles["field_value"]), 

        ]) 

    return Table( 

        table_data, 

        colWidths=[5 * cm, 12 * cm], 

        style=TableStyle([ 

            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY), 

            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GREY, colors.white]), 

            ("GRID", (0, 0), (-1, -1), 0.3, BORDER_GREY), 

            ("VALIGN", (0, 0), (-1, -1), "TOP"), 

            ("TOPPADDING", (0, 0), (-1, -1), 5), 

            ("BOTTOMPADDING", (0, 0), (-1, -1), 5), 

            ("LEFTPADDING", (0, 0), (-1, -1), 8), 

            ("RIGHTPADDING", (0, 0), (-1, -1), 8), 

        ]), 

    ) 

 

 

def generate_pdf(summary: dict, output_path: str) -> str: 

    """ 

    Generates a formatted discharge summary PDF from a summary dict. 

    Returns the output path. 

    """ 

    os.makedirs(os.path.dirname(output_path), exist_ok=True) 

 

    doc = SimpleDocTemplate( 

        output_path, 

        pagesize=A4, 

        rightMargin=1.8 * cm, 

        leftMargin=1.8 * cm, 

        topMargin=1.5 * cm, 

        bottomMargin=1.5 * cm, 

        title="Clinical Discharge Summary", 

    ) 

 

    styles = build_styles() 

    story = [] 

 

    # ── Header ── 

    header_data = [[ 

        Paragraph("CLINICAL DISCHARGE SUMMARY", styles["title"]), 

    ]] 

    header_table = Table( 

        header_data, 

        colWidths=["100%"], 

        style=TableStyle([ 

            ("BACKGROUND", (0, 0), (-1, -1), DARK_BLUE), 

            ("TOPPADDING", (0, 0), (-1, -1), 14), 

            ("BOTTOMPADDING", (0, 0), (-1, -1), 6), 

            ("ROUNDEDCORNERS", [6, 6, 6, 6]), 

        ]), 

    ) 

    story.append(header_table) 

 

    # Disclaimer banner 

    disclaimer_table = Table( 

        [[Paragraph("⚠  AI-GENERATED DRAFT — REQUIRES CLINICIAN REVIEW BEFORE ANY CLINICAL USE  ⚠", styles["disclaimer"])]], 

        colWidths=["100%"], 

        style=TableStyle([ 

            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fefcbf")), 

            ("TOPPADDING", (0, 0), (-1, -1), 6), 

            ("BOTTOMPADDING", (0, 0), (-1, -1), 6), 

            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#f6e05e")), 

        ]), 

    ) 

    story.append(disclaimer_table) 

    story.append(Spacer(1, 0.3 * cm)) 

 

    # Generated timestamp 

    story.append(Paragraph( 

        f"Generated: {datetime.now().strftime('%d %B %Y %H:%M')}", 

        styles["footer"] 

    )) 

    story.append(Spacer(1, 0.3 * cm)) 

 

    # ── CRITICAL FLAGS ── 

    critical = [f for f in summary.get("clinician_flags", []) 

                if "CRITICAL" in f or "DISCHARGE AGAINST" in f or "CONFLICT" in f or "DRUG INTERACTION" in f] 

    if critical: 

        story += section_header("🚨  CRITICAL CLINICIAN FLAGS", styles) 

        flag_rows = [] 

        for flag in critical: 

            if "CRITICAL" in flag or "DISCHARGE AGAINST" in flag: 

                icon, style_key = "🔴", "flag_critical" 

            elif "CONFLICT" in flag: 

                icon, style_key = "🔵", "flag_warning" 

            else: 

                icon, style_key = "🟠", "flag_warning" 

            flag_rows.append([Paragraph(f"{icon}  {flag}", styles[style_key])]) 

 

        flag_table = Table( 

            flag_rows, 

            colWidths=["100%"], 

            style=TableStyle([ 

                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_RED), 

                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_RED, colors.HexColor("#fff8f8")]), 

                ("LEFTPADDING", (0, 0), (-1, -1), 10), 

                ("RIGHTPADDING", (0, 0), (-1, -1), 10), 

                ("TOPPADDING", (0, 0), (-1, -1), 5), 

                ("BOTTOMPADDING", (0, 0), (-1, -1), 5), 

                ("BOX", (0, 0), (-1, -1), 0.5, RED), 

                ("ROUNDEDCORNERS", [4, 4, 4, 4]), 

            ]), 

        ) 

        story.append(flag_table) 

 

    # ── PATIENT DEMOGRAPHICS ── 

    story += section_header("👤  PATIENT DEMOGRAPHICS", styles) 

    demo = summary.get("patient_demographics", {}) 

    demo_rows = [ 

        ["Name", demo.get("name", "[MISSING]")], 

        ["Gender", demo.get("gender", "[MISSING]")], 

        ["Age", demo.get("age", "[MISSING]")], 

        ["Weight", demo.get("weight", "[MISSING]")], 

        ["Admission Date", summary.get("admission_date", "[MISSING]")], 

        ["Discharge Date", summary.get("discharge_date", "[MISSING]")], 

        ["Discharge Circumstances", summary.get("discharge_circumstances", "[MISSING]")], 

    ] 

    story.append(two_col_table(demo_rows, styles)) 

 

    # ── DIAGNOSES ── 

    story += section_header("🔬  DIAGNOSES", styles) 

    diagnoses = summary.get("diagnoses", {}) 

    primary = diagnoses.get("primary", {}) 

    diag_data = [] 

 

    if primary: 

        diag_data.append([ 

            Paragraph("Primary", styles["field_label"]), 

            Paragraph(primary.get("name", "N/A"), styles["field_value"]), 

            Paragraph(f"ICD-10: {primary.get('icd10_code','N/A')}", styles["icd_code"]), 

            Paragraph(primary.get("icd10_description", ""), styles["field_value"]), 

        ]) 

 

    for i, sec in enumerate(diagnoses.get("secondary", [])): 

        diag_data.append([ 

            Paragraph(f"Secondary {i+1}", styles["field_label"]), 

            Paragraph(sec.get("name", "N/A"), styles["field_value"]), 

            Paragraph(f"ICD-10: {sec.get('icd10_code','N/A')}", styles["icd_code"]), 

            Paragraph(sec.get("icd10_description", ""), styles["field_value"]), 

        ]) 

 

    if diag_data: 

        story.append(Table( 

            diag_data, 

            colWidths=[2.5 * cm, 5.5 * cm, 3 * cm, 6 * cm], 

            style=TableStyle([ 

                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BLUE), 

                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BLUE, colors.white]), 

                ("GRID", (0, 0), (-1, -1), 0.3, BORDER_GREY), 

                ("VALIGN", (0, 0), (-1, -1), "TOP"), 

                ("TOPPADDING", (0, 0), (-1, -1), 6), 

                ("BOTTOMPADDING", (0, 0), (-1, -1), 6), 

                ("LEFTPADDING", (0, 0), (-1, -1), 8), 

            ]), 

        )) 

 

    # ── HISTORY ── 

    story += section_header("📋  HISTORY", styles) 

    story.append(two_col_table([ 

        ["Presenting Complaint", summary.get("history", "[MISSING]")], 

        ["Past History", summary.get("past_history", "[MISSING]")], 

        ["Allergies", summary.get("allergies", "[MISSING — REQUIRES CLINICIAN REVIEW]")], 

    ], styles)) 

 

    # ── HOSPITAL COURSE ── 

    story += section_header("🏥  HOSPITAL COURSE", styles) 

    course = summary.get("hospital_course", "[MISSING]") 

    story.append(Table( 

        [[Paragraph(course, styles["field_value"])]], 

        colWidths=["100%"], 

        style=TableStyle([ 

            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY), 

            ("BOX", (0, 0), (-1, -1), 0.3, BORDER_GREY), 

            ("TOPPADDING", (0, 0), (-1, -1), 8), 

            ("BOTTOMPADDING", (0, 0), (-1, -1), 8), 

            ("LEFTPADDING", (0, 0), (-1, -1), 10), 

            ("RIGHTPADDING", (0, 0), (-1, -1), 10), 

        ]), 

    )) 

 

    # ── PROCEDURES ── 

    story += section_header("🔧  PROCEDURES", styles) 

    proc_text = "\n".join([f"• {p}" for p in summary.get("procedures", [])]) 

    story.append(Table( 

        [[Paragraph(proc_text, styles["field_value"])]], 

        colWidths=["100%"], 

        style=TableStyle([ 

            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY), 

            ("BOX", (0, 0), (-1, -1), 0.3, BORDER_GREY), 

            ("TOPPADDING", (0, 0), (-1, -1), 8), 

            ("BOTTOMPADDING", (0, 0), (-1, -1), 8), 

            ("LEFTPADDING", (0, 0), (-1, -1), 10), 

        ]), 

    )) 

 

    # ── KEY INVESTIGATIONS ── 

    story += section_header("🧪  KEY INVESTIGATIONS", styles) 

    inv_rows = [[k, v] for k, v in summary.get("key_investigations", {}).items()] 

    if inv_rows: 

        story.append(two_col_table(inv_rows, styles)) 

 

    # ── DISCHARGE MEDICATIONS ── 

    story += section_header("💊  DISCHARGE MEDICATIONS", styles) 

    med_data = [] 

    for i, med in enumerate(summary.get("discharge_medications", []), 1): 

        med_data.append([ 

            Paragraph(str(i), styles["field_label"]), 

            Paragraph(med, styles["med_item"]), 

        ]) 

    if med_data: 

        story.append(Table( 

            med_data, 

            colWidths=[0.8 * cm, 16.2 * cm], 

            style=TableStyle([ 

                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GREY, colors.white]), 

                ("GRID", (0, 0), (-1, -1), 0.3, BORDER_GREY), 

                ("VALIGN", (0, 0), (-1, -1), "TOP"), 

                ("TOPPADDING", (0, 0), (-1, -1), 5), 

                ("BOTTOMPADDING", (0, 0), (-1, -1), 5), 

                ("LEFTPADDING", (0, 0), (-1, -1), 8), 

            ]), 

        )) 

 

    # ── PENDING RESULTS ── 

    story += section_header("⏳  PENDING RESULTS AT DISCHARGE", styles) 

    pending = summary.get("pending_results", []) 

    if pending: 

        pending_data = [[Paragraph(f"⏳  {r}", styles["flag_warning"])] for r in pending] 

        story.append(Table( 

            pending_data, 

            colWidths=["100%"], 

            style=TableStyle([ 

                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_AMBER), 

                ("BOX", (0, 0), (-1, -1), 0.5, AMBER), 

                ("TOPPADDING", (0, 0), (-1, -1), 5), 

                ("BOTTOMPADDING", (0, 0), (-1, -1), 5), 

                ("LEFTPADDING", (0, 0), (-1, -1), 10), 

            ]), 

        )) 

 

    # ── FOLLOW-UP ── 

    story += section_header("📅  FOLLOW-UP INSTRUCTIONS", styles) 

    story.append(Table( 

        [[Paragraph(summary.get("follow_up_instructions", "[MISSING]"), styles["field_value"])]], 

        colWidths=["100%"], 

        style=TableStyle([ 

            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY), 

            ("BOX", (0, 0), (-1, -1), 0.3, BORDER_GREY), 

            ("TOPPADDING", (0, 0), (-1, -1), 8), 

            ("BOTTOMPADDING", (0, 0), (-1, -1), 8), 

            ("LEFTPADDING", (0, 0), (-1, -1), 10), 

        ]), 

    )) 

 

    # ── ALL FLAGS ── 

    story += section_header("🚩  ALL CLINICIAN FLAGS", styles) 

    all_flags = summary.get("clinician_flags", []) 

    flag_data = [] 

    for flag in all_flags: 

        if "CRITICAL" in flag or "DISCHARGE AGAINST" in flag: 

            icon, style_key = "🔴", "flag_critical" 

        elif "CONFLICT" in flag or "DRUG INTERACTION" in flag: 

            icon, style_key = "🟠", "flag_warning" 

        elif "MISSING" in flag: 

            icon, style_key = "🟡", "flag_warning" 

        else: 

            icon, style_key = "🟢", "flag_info" 

        flag_data.append([Paragraph(f"{icon}  {flag}", styles[style_key])]) 

 

    if flag_data: 

        story.append(Table( 

            flag_data, 

            colWidths=["100%"], 

            style=TableStyle([ 

                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GREY, colors.white]), 

                ("GRID", (0, 0), (-1, -1), 0.3, BORDER_GREY), 

                ("TOPPADDING", (0, 0), (-1, -1), 5), 

                ("BOTTOMPADDING", (0, 0), (-1, -1), 5), 

                ("LEFTPADDING", (0, 0), (-1, -1), 10), 

            ]), 

        )) 

 

    # ── Footer ── 

    story.append(Spacer(1, 0.5 * cm)) 

    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER_GREY)) 

    story.append(Spacer(1, 0.2 * cm)) 

    story.append(Paragraph( 

        f"Generated by Clinical Discharge Summary Agent  •  {datetime.now().strftime('%d %B %Y %H:%M')}  •  DRAFT — NOT FOR CLINICAL USE WITHOUT REVIEW", 

        styles["footer"] 

    )) 

 

    doc.build(story) 

    return output_path 

 

 

if __name__ == "__main__": 

    summary_path = os.path.join("output", "summaries", "patient_001_summary.json") 

    output_path = os.path.join("output", "summaries", "patient_001_discharge_summary.pdf") 

 

    if not os.path.exists(summary_path): 

        print(f"ERROR: Summary JSON not found at {summary_path}") 

        print("Run main.py first to generate the summary.") 

        exit(1) 

 

    with open(summary_path, "r", encoding="utf-8") as f: 

        summary = json.load(f) 

 

    print("Generating PDF...") 

    path = generate_pdf(summary, output_path) 

    print(f"PDF saved to: {path}") 

 

 