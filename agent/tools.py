""" 

Tool definitions and implementations for the discharge summary agent. 

""" 

 

import os 

import re 

import json 

import requests 

from ingestion.pdf_reader import extract_pdf, extract_sections 

 

# ── Shared state ── 

_doc_cache = {} 

_flags = [] 

_summary_finalized = False 

 

# ── Indian brand name to generic mapping ── 

INDIAN_DRUG_MAP = { 

    "RACTIPER": {"generic": "Rabeprazole", "class": "Proton Pump Inhibitor"}, 

    "RACIPER": {"generic": "Rabeprazole", "class": "Proton Pump Inhibitor"}, 

    "RAZO": {"generic": "Rabeprazole", "class": "Proton Pump Inhibitor"}, 

    "EMESET": {"generic": "Ondansetron", "class": "Antiemetic"}, 

    "ZOFER": {"generic": "Ondansetron", "class": "Antiemetic"}, 

    "OFLOX TZ": {"generic": "Ofloxacin + Tinidazole", "class": "Antibiotic + Antiprotozoal"}, 

    "OFLOXTZ": {"generic": "Ofloxacin + Tinidazole", "class": "Antibiotic + Antiprotozoal"}, 

    "M STRONG": {"generic": "Methylcobalamin (Vitamin B12)", "class": "Vitamin B12 Supplement"}, 

    "MSTRONG": {"generic": "Methylcobalamin (Vitamin B12)", "class": "Vitamin B12 Supplement"}, 

    "ZEDOTT": {"generic": "Zinc + ORS", "class": "Electrolyte Supplement"}, 

    "ENTR": {"generic": "Racecadotril", "class": "Antidiarrheal"}, 

    "MEFTAL SPAS": {"generic": "Mefenamic Acid + Dicyclomine", "class": "Antispasmodic + NSAID"}, 

    "MEFTALSPAS": {"generic": "Mefenamic Acid + Dicyclomine", "class": "Antispasmodic + NSAID"}, 

    "LOPIRAMIDE": {"generic": "Loperamide", "class": "Antidiarrheal"}, 

    "LOPERAMIDE": {"generic": "Loperamide", "class": "Antidiarrheal"}, 

    "PANTOP": {"generic": "Pantoprazole", "class": "Proton Pump Inhibitor"}, 

    "PAN": {"generic": "Pantoprazole", "class": "Proton Pump Inhibitor"}, 

    "MEROPENEM": {"generic": "Meropenem", "class": "Carbapenem Antibiotic"}, 

    "LANTUS": {"generic": "Insulin Glargine", "class": "Long-acting Insulin"}, 

    "DOLO": {"generic": "Paracetamol", "class": "Analgesic / Antipyretic"}, 

    "CALPOL": {"generic": "Paracetamol", "class": "Analgesic / Antipyretic"}, 

    "AUGMENTIN": {"generic": "Amoxicillin + Clavulanate", "class": "Antibiotic"}, 

    "METFORMIN": {"generic": "Metformin", "class": "Antidiabetic (Biguanide)"}, 

    "GLYCOMET": {"generic": "Metformin", "class": "Antidiabetic (Biguanide)"}, 

} 

 

# ── ICD-10 local lookup for common diagnoses in this document ── 

# Used as fast local cache before hitting the API 

ICD10_LOCAL = { 

    "acute gastroenteritis": {"code": "A09", "description": "Infectious gastroenteritis and colitis, unspecified"}, 

    "gastroenteritis": {"code": "A09", "description": "Infectious gastroenteritis and colitis, unspecified"}, 

    "dehydration": {"code": "E86.0", "description": "Dehydration"}, 

    "urinary tract infection": {"code": "N39.0", "description": "Urinary tract infection, site not specified"}, 

    "uti": {"code": "N39.0", "description": "Urinary tract infection, site not specified"}, 

    "pyelonephritis": {"code": "N10", "description": "Acute pyelonephritis"}, 

    "acute pyelonephritis": {"code": "N10", "description": "Acute pyelonephritis"}, 

    "type 2 diabetes": {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications"}, 

    "diabetes mellitus": {"code": "E11.9", "description": "Type 2 diabetes mellitus without complications"}, 

    "uncontrolled diabetes": {"code": "E11.65", "description": "Type 2 diabetes mellitus with hyperglycemia"}, 

    "acute kidney injury": {"code": "N17.9", "description": "Acute kidney failure, unspecified"}, 

    "aki": {"code": "N17.9", "description": "Acute kidney failure, unspecified"}, 

    "hyponatremia": {"code": "E87.1", "description": "Hypo-osmolality and hyponatraemia"}, 

    "electrolyte imbalance": {"code": "E87.8", "description": "Other disorders of electrolyte and fluid balance"}, 

    "fatty liver": {"code": "K76.0", "description": "Fatty (change of) liver"}, 

    "cholelithiasis": {"code": "K80.20", "description": "Calculus of gallbladder without cholecystitis"}, 

    "thyroid disorder": {"code": "E07.9", "description": "Disorder of thyroid, unspecified"}, 

    "hypothyroidism": {"code": "E03.9", "description": "Hypothyroidism, unspecified"}, 

    "hypertensive emergency": {"code": "I16.1", "description": "Hypertensive emergency"}, 

    "hypertension": {"code": "I10", "description": "Essential hypertension"}, 

    "copd": {"code": "J44.1", "description": "Chronic obstructive pulmonary disease with acute exacerbation"}, 

    "pneumonia": {"code": "J18.9", "description": "Pneumonia, unspecified organism"}, 

    "dka": {"code": "E11.10", "description": "Type 2 diabetes mellitus with ketoacidosis without coma"}, 

    "diabetic ketoacidosis": {"code": "E11.10", "description": "Type 2 diabetes mellitus with ketoacidosis without coma"}, 

} 

 

 

# ── Tool Schemas ── 

TOOL_SCHEMAS = [ 

    { 

        "type": "function", 

        "function": { 

            "name": "read_document", 

            "description": "Reads and extracts all text from the patient PDF. Call this first before any other tool.", 

            "parameters": { 

                "type": "object", 

                "properties": { 

                    "pdf_path": { 

                        "type": "string", 

                        "description": "Path to the patient PDF file." 

                    } 

                }, 

                "required": ["pdf_path"] 

            } 

        } 

    }, 

    { 

        "type": "function", 

        "function": { 

            "name": "get_section", 

            "description": "Retrieves a specific clinical section from the extracted document.", 

            "parameters": { 

                "type": "object", 

                "properties": { 

                    "section_name": { 

                        "type": "string", 

                        "description": "Section to retrieve e.g. DIAGNOSIS, HISTORY, COURSE IN THE HOSPITAL, CONDITION AT DISCHARGE, FOLLOW-UP INSTRUCTIONS" 

                    } 

                }, 

                "required": ["section_name"] 

            } 

        } 

    }, 

    { 

        "type": "function", 

        "function": { 

            "name": "get_raw_pages", 

            "description": "Returns raw text from specific page numbers. Pages 1-2 have discharge summary, pages 27-28 have lab results, page 30 has USG report.", 

            "parameters": { 

                "type": "object", 

                "properties": { 

                    "page_numbers": { 

                        "type": "array", 

                        "items": {"type": "integer"}, 

                        "description": "List of page numbers to retrieve." 

                    } 

                }, 

                "required": ["page_numbers"] 

            } 

        } 

    }, 

    { 

        "type": "function", 

        "function": { 

            "name": "extract_structured_data", 

            "description": "Pre-extracts all key clinical fields using Python. Call after read_document. Use returned values directly in finalize_summary.", 

            "parameters": { 

                "type": "object", 

                "properties": {}, 

                "required": [] 

            } 

        } 

    }, 

    { 

        "type": "function", 

        "function": { 

            "name": "normalize_medication", 

            "description": "Looks up a medication name to find the correct generic name and drug class. Checks Indian brand name database first, then RxNorm.", 

            "parameters": { 

                "type": "object", 

                "properties": { 

                    "drug_name": { 

                        "type": "string", 

                        "description": "The drug name as it appears in the document." 

                    } 

                }, 

                "required": ["drug_name"] 

            } 

        } 

    }, 

    { 

        "type": "function", 

        "function": { 

            "name": "validate_diagnosis", 

            "description": "Validates a diagnosis against ICD-10 codes. Returns the standard ICD-10 code and description for a given diagnosis. Use this for every diagnosis found in the document.", 

            "parameters": { 

                "type": "object", 

                "properties": { 

                    "diagnosis": { 

                        "type": "string", 

                        "description": "The diagnosis as written in the document." 

                    } 

                }, 

                "required": ["diagnosis"] 

            } 

        } 

    }, 

    { 

        "type": "function", 

        "function": { 

            "name": "lookup_drug_interaction", 

            "description": "Checks for interactions between two medications using OpenFDA.", 

            "parameters": { 

                "type": "object", 

                "properties": { 

                    "drug_a": {"type": "string", "description": "First drug name."}, 

                    "drug_b": {"type": "string", "description": "Second drug name."} 

                }, 

                "required": ["drug_a", "drug_b"] 

            } 

        } 

    }, 

    { 

        "type": "function", 

        "function": { 

            "name": "flag_conflict", 

            "description": "Flags a genuine conflict between two pieces of information from different parts of the document.", 

            "parameters": { 

                "type": "object", 

                "properties": { 

                    "field": {"type": "string"}, 

                    "value_a": {"type": "string"}, 

                    "source_a": {"type": "string"}, 

                    "value_b": {"type": "string"}, 

                    "source_b": {"type": "string"} 

                }, 

                "required": ["field", "value_a", "source_a", "value_b", "source_b"] 

            } 

        } 

    }, 

    { 

        "type": "function", 

        "function": { 

            "name": "flag_missing", 

            "description": "Flags a required field not found anywhere in the document.", 

            "parameters": { 

                "type": "object", 

                "properties": { 

                    "field": {"type": "string"}, 

                    "reason": {"type": "string"} 

                }, 

                "required": ["field", "reason"] 

            } 

        } 

    }, 

    { 

        "type": "function", 

        "function": { 

            "name": "finalize_summary", 

            "description": "Produces the final structured discharge summary. Call ONCE ONLY with real values from the document.", 

            "parameters": { 

                "type": "object", 

                "properties": { 

                    "patient_demographics": {"type": "object"}, 

                    "admission_date": {"type": "string"}, 

                    "discharge_date": {"type": "string"}, 

                    "diagnoses": {"type": "object"}, 

                    "history": {"type": "string"}, 

                    "hospital_course": {"type": "string"}, 

                    "procedures": {"type": "array", "items": {"type": "string"}}, 

                    "key_investigations": {"type": "object"}, 

                    "allergies": {"type": "string"}, 

                    "discharge_medications": {"type": "array", "items": {"type": "string"}}, 

                    "condition_at_discharge": {"type": "string"}, 

                    "pending_results": {"type": "array", "items": {"type": "string"}}, 

                    "follow_up_instructions": {"type": "string"}, 

                    "discharge_circumstances": {"type": "string"}, 

                    "clinician_flags": {"type": "array", "items": {"type": "string"}} 

                }, 

                "required": [ 

                    "patient_demographics", "admission_date", "discharge_date", 

                    "diagnoses", "history", "hospital_course", "procedures", 

                    "key_investigations", "allergies", "discharge_medications", 

                    "condition_at_discharge", "pending_results", "follow_up_instructions", 

                    "discharge_circumstances", "clinician_flags" 

                ] 

            } 

        } 

    } 

] 

 

 

# ── Tool Implementations ── 

 

def read_document(pdf_path: str) -> str: 

    global _doc_cache, _flags, _summary_finalized 

    _doc_cache = {} 

    _flags = [] 

    _summary_finalized = False 

 

    result = extract_pdf(pdf_path) 

 

    for w in result["warnings"]: 

        _flags.append(f"EXTRACTION WARNING: {w}") 

 

    _doc_cache["full_text"] = result["full_text"] 

    _doc_cache["sections"] = extract_sections(result["full_text"]) 

    _doc_cache["total_pages"] = result["total_pages"] 

    _doc_cache["ocr_pages"] = result["ocr_pages"] 

    _doc_cache["pages_data"] = result.get("pages", []) 

 

    pages = result.get("pages", []) 

    key_pages_text = "" 

    for page in pages: 

        if page["page"] in [1, 2]: 

            key_pages_text += f"\n--- PAGE {page['page']} ---\n{page['text']}\n" 

 

    return ( 

        f"Document loaded. Total pages: {result['total_pages']}\n" 

        f"Sections detected: {list(_doc_cache['sections'].keys())}\n\n" 

        f"=== KEY CLINICAL PAGES (pages 1-2) ===\n" 

        f"{key_pages_text}\n" 

        f"=== END KEY PAGES ===\n\n" 

        f"NEXT STEP: Call extract_structured_data() to get pre-extracted values." 

    ) 

 

 

def get_section(section_name: str) -> str: 

    if not _doc_cache: 

        return "ERROR: Document not loaded. Call read_document first." 

 

    sections = _doc_cache.get("sections", {}) 

    section_upper = section_name.upper() 

 

    if section_upper in sections: 

        return f"[SECTION: {section_upper}]\n{sections[section_upper]}" 

 

    for key in sections: 

        if section_upper in key or key in section_upper: 

            return f"[SECTION: {key}]\n{sections[key]}" 

 

    full_text = _doc_cache.get("full_text", "") 

    lines = full_text.split("\n") 

    relevant = [l for l in lines if section_upper in l.upper()] 

    if relevant: 

        return f"No header found but found matches:\n" + "\n".join(relevant[:20]) 

 

    return f"Section '{section_name}' not found. Available: {list(sections.keys())}" 

 

 

def get_raw_pages(page_numbers: list) -> str: 

    if not _doc_cache: 

        return "ERROR: Document not loaded. Call read_document first." 

 

    full_text = _doc_cache.get("full_text", "") 

    lines = full_text.split("\n") 

    output = [] 

    capture = False 

    current_page = 0 

 

    for line in lines: 

        if "--- PAGE " in line: 

            try: 

                current_page = int(line.split("--- PAGE ")[1].split(" ")[0]) 

                capture = current_page in page_numbers 

            except Exception: 

                capture = False 

        if capture: 

            output.append(line) 

 

    return "\n".join(output) if output else "No content found for those pages." 

 

 

def extract_structured_data() -> str: 

    if not _doc_cache: 

        return "ERROR: Document not loaded. Call read_document first." 

 

    pages = _doc_cache.get("pages_data", []) 

    page_texts = {p["page"]: p["text"] for p in pages} 

 

    p1 = page_texts.get(1, "") 

    p2 = page_texts.get(2, "") 

    p27 = page_texts.get(27, "") 

    p28 = page_texts.get(28, "") 

    p30 = page_texts.get(30, "") 

    combined = p1 + "\n" + p2 

 

    def extract_between(text, start_kw, end_kws): 

        lines = text.split("\n") 

        capturing = False 

        out = [] 

        for line in lines: 

            if start_kw.upper() in line.upper(): 

                capturing = True 

                continue 

            if capturing: 

                if any(k.upper() in line.upper() for k in end_kws): 

                    break 

                out.append(line) 

        return "\n".join(out).strip() 

 

    diagnosis = extract_between(combined, "DIAGNOSIS:", ["HISTORY", "PAST HISTORY", "PHYSICAL"]) 

    history = extract_between(combined, "HISTORY:", ["PAST HISTORY", "PHYSICAL EXAMINATION"]) 

    past_history = extract_between(combined, "PAST HISTOR", ["PHYSICAL EXAMINATION", "INVESTIGATIONS"]) 

    course = extract_between(combined, "COURSE IN THE HOSPITAL", ["CONDITION AT DISCHARGE", "ADVICE", "FOLLOW"]) 

    condition = extract_between(combined, "CONDITION AT DISCHARGE", ["ADVICE ON DISCHARGE", "FOLLOW-UP", "TAB."]) 

    medications = extract_between(combined, "ADVICE", ["FOLLOW-UP", "REVIEW"]) 

    followup = extract_between(combined, "FOLLOW-UP", ["PAGE", "---", "ER OBSERVATION"]) 

 

    return f"""EXTRACTED CLINICAL DATA — USE THESE EXACT VALUES IN finalize_summary: 

 

DIAGNOSES (page 1): 

{diagnosis if diagnosis else '[NOT FOUND]'} 

 

HISTORY (page 1): 

{history if history else '[NOT FOUND]'} 

 

PAST HISTORY (page 1): 

{past_history if past_history else '[NOT FOUND]'} 

 

HOSPITAL COURSE (pages 1-2): 

{course if course else '[NOT FOUND]'} 

 

CONDITION AT DISCHARGE (page 2): 

{condition if condition else 'Hemodynamically stable'} 

 

DISCHARGE MEDICATIONS (page 2): 

{medications if medications else '[NOT FOUND]'} 

 

FOLLOW-UP INSTRUCTIONS (page 2): 

{followup if followup else '[NOT FOUND]'} 

 

LAB RESULTS (pages 27-28): 

{p27[:800] if p27 else '[NOT FOUND]'} 

{p28[:800] if p28 else '[NOT FOUND]'} 

 

USG REPORT (page 30): 

{p30[:600] if p30 else '[NOT FOUND]'} 

""" 

 

 

def normalize_medication(drug_name: str) -> str: 

    clean = drug_name.upper().strip() 

    for prefix in ["TAB.", "TAB ", "INJ.", "INJ ", "SYR.", "SYR ", "CAP.", "CAP "]: 

        clean = clean.replace(prefix, "").strip() 

    clean = re.sub(r"\d+\s*M?C?G?S?\b", "", clean).strip() 

    clean = clean.split("|")[0].strip() 

    clean = clean.split("-")[0].strip() 

 

    # Step 1: Indian brand name table 

    for brand, info in INDIAN_DRUG_MAP.items(): 

        if brand in clean or clean in brand: 

            return ( 

                f"Input: '{drug_name}'\n" 

                f"Brand name: {brand}\n" 

                f"Generic name: {info['generic']}\n" 

                f"Drug class: {info['class']}\n" 

                f"Source: Indian brand name database\n" 

            ) 

 

    # Step 2: RxNorm fallback 

    if not clean or len(clean) < 3: 

        return f"Could not normalize '{drug_name}' — name too short after cleaning." 

 

    try: 

        search_url = ( 

            f"https://rxnav.nlm.nih.gov/REST/approximateTerm.json" 

            f"?term={requests.utils.quote(clean)}&maxEntries=3" 

        ) 

        response = requests.get(search_url, timeout=10) 

 

        if response.status_code == 200: 

            data = response.json() 

            candidates = data.get("approximateGroup", {}).get("candidate", []) 

            if candidates: 

                best = candidates[0] 

                rxcui = best.get("rxcui", "") 

                name = best.get("name", "") 

                score = float(best.get("score", 0)) 

 

                class_url = ( 

                    f"https://rxnav.nlm.nih.gov/REST/rxclass/" 

                    f"class/byRxcui.json?rxcui={rxcui}&relaSource=ATC" 

                ) 

                class_response = requests.get(class_url, timeout=10) 

                drug_class = "" 

                if class_response.status_code == 200: 

                    class_data = class_response.json() 

                    concepts = ( 

                        class_data.get("rxclassDrugInfoList", {}) 

                                  .get("rxclassDrugInfo", []) 

                    ) 

                    if concepts: 

                        drug_class = concepts[0].get( 

                            "rxclassMinConceptItem", {} 

                        ).get("className", "") 

 

                result = ( 

                    f"Input: '{drug_name}'\n" 

                    f"Normalized name: {name}\n" 

                    f"RxCUI: {rxcui}\n" 

                    f"Match score: {score:.0f}/100\n" 

                    f"Source: RxNorm\n" 

                ) 

                if drug_class: 

                    result += f"Drug class: {drug_class}\n" 

                if score < 50: 

                    result += "WARNING: Low match score — verify manually.\n" 

                return result 

 

        return ( 

            f"'{drug_name}' not found in Indian brand database or RxNorm. " 

            f"Include as-is and flag for clinician verification." 

        ) 

 

    except requests.Timeout: 

        return f"RxNorm lookup timed out for '{drug_name}'." 

    except Exception as e: 

        return f"RxNorm lookup failed for '{drug_name}': {e}" 

 

 

def validate_diagnosis(diagnosis: str) -> str: 

    """ 

    Validates a diagnosis against ICD-10 codes. 

    Step 1: Check local ICD-10 cache for common diagnoses. 

    Step 2: Fall back to WHO ICD-10 API. 

    """ 

    clean = diagnosis.lower().strip() 

 

    # Step 1: Local cache lookup 

    for key, value in ICD10_LOCAL.items(): 

        if key in clean or clean in key: 

            return ( 

                f"Diagnosis: '{diagnosis}'\n" 

                f"ICD-10 Code: {value['code']}\n" 

                f"Standard Description: {value['description']}\n" 

                f"Source: ICD-10 local database\n" 

            ) 

 

    # Step 2: WHO ICD-10 API (free, no key needed) 

    try: 

        url = ( 

            f"https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search" 

            f"?sf=code,name&terms={requests.utils.quote(diagnosis)}&maxList=3" 

        ) 

        response = requests.get(url, timeout=10) 

 

        if response.status_code == 200: 

            data = response.json() 

            # Response format: [total, codes_list, extra, display_list] 

            if data and len(data) >= 4 and data[0] > 0: 

                codes = data[1] 

                displays = data[3] 

                if codes and displays: 

                    results = [] 

                    for i, (code, display) in enumerate(zip(codes[:3], displays[:3])): 

                        results.append(f"  {code[0]} — {display[1]}") 

                    return ( 

                        f"Diagnosis: '{diagnosis}'\n" 

                        f"ICD-10 matches found:\n" 

                        + "\n".join(results) 

                        + "\nSource: NLM ICD-10 API\n" 

                    ) 

 

        return ( 

            f"Diagnosis: '{diagnosis}'\n" 

            f"ICD-10 Code: NOT FOUND — flag for clinician to assign code\n" 

        ) 

 

    except requests.Timeout: 

        return f"ICD-10 lookup timed out for '{diagnosis}'." 

    except Exception as e: 

        return f"ICD-10 lookup failed for '{diagnosis}': {e}" 

 

 

def lookup_drug_interaction(drug_a: str, drug_b: str) -> str: 

    try: 

        query = f"{drug_a} {drug_b}" 

        url = ( 

            f"https://api.fda.gov/drug/label.json" 

            f"?search=drug_interactions:{requests.utils.quote(query)}&limit=2" 

        ) 

        response = requests.get(url, timeout=10) 

 

        if response.status_code == 200: 

            data = response.json() 

            results = data.get("results", []) 

            if results: 

                text = results[0].get("drug_interactions", [""])[0] 

                if text: 

                    return f"INTERACTION INFO for {drug_a} + {drug_b}:\n{text[:400]}" 

            return f"No documented interaction found between {drug_a} and {drug_b}." 

        elif response.status_code == 404: 

            return f"No records found for {drug_a} + {drug_b} in OpenFDA." 

        else: 

            return f"OpenFDA returned status {response.status_code}." 

 

    except requests.Timeout: 

        return f"Drug lookup timed out for {drug_a} + {drug_b}. Flag for manual review." 

    except Exception as e: 

        return f"Drug lookup failed: {e}. Flag for manual review." 

 

 

def flag_conflict( 

    field: str, value_a: str, source_a: str, value_b: str, source_b: str 

) -> str: 

    flag = ( 

        f"CONFLICT [{field}]: '{value_a}' (from {source_a}) " 

        f"vs '{value_b}' (from {source_b})" 

    ) 

    _flags.append(flag) 

    return f"Conflict recorded: {flag}" 

 

 

def flag_missing(field: str, reason: str) -> str: 

    flag = f"MISSING [{field}]: {reason}" 

    _flags.append(flag) 

    return f"Missing field recorded: {flag}" 

 

 

def finalize_summary( 

    patient_demographics, admission_date, discharge_date, diagnoses, 

    history, hospital_course, procedures, key_investigations, allergies, 

    discharge_medications, condition_at_discharge, pending_results, 

    follow_up_instructions, discharge_circumstances, clinician_flags 

) -> str: 

    global _summary_finalized 

    if _summary_finalized: 

        return "Summary already finalized. Do not call finalize_summary again." 

    _summary_finalized = True 

 

    placeholder_phrases = [ 

        "history", "hospital course", "condition at discharge", 

        "follow-up instructions", "lab results", "usg report", 

        "primary diagnosis", "secondary diagnosis", "discharge circumstances", 

        "follow up instructions" 

    ] 

    for phrase in placeholder_phrases: 

        if isinstance(history, str) and history.lower().strip() == phrase: 

            _summary_finalized = False 

            return ( 

                "ERROR: finalize_summary called with placeholder values. " 

                "Call extract_structured_data() first and use the returned " 

                "values to populate each field with real document content." 

            ) 

 

    def to_list(val): 

        if isinstance(val, list): 

            return val 

        if isinstance(val, str): 

            return [val] if val else [] 

        return [] 

 

    def to_dict(val): 

        if isinstance(val, dict): 

            return val 

        if isinstance(val, str): 

            return {"note": val} 

        return {} 

 

    procedures = to_list(procedures) 

    discharge_medications = to_list(discharge_medications) 

    pending_results = to_list(pending_results) 

    clinician_flags = to_list(clinician_flags) 

    patient_demographics = to_dict(patient_demographics) 

    key_investigations = to_dict(key_investigations) 

 

    all_flags = list(set(_flags + clinician_flags)) 

 

    summary = { 

        "note": "AI-GENERATED DRAFT — REQUIRES CLINICIAN REVIEW BEFORE ANY CLINICAL USE", 

        "patient_demographics": patient_demographics, 

        "admission_date": admission_date, 

        "discharge_date": discharge_date, 

        "diagnoses": diagnoses, 

        "history": history, 

        "hospital_course": hospital_course, 

        "procedures": procedures, 

        "key_investigations": key_investigations, 

        "allergies": allergies, 

        "discharge_medications": discharge_medications, 

        "condition_at_discharge": condition_at_discharge, 

        "pending_results": pending_results, 

        "follow_up_instructions": follow_up_instructions, 

        "discharge_circumstances": discharge_circumstances, 

        "clinician_flags": all_flags, 

        "total_flags": len(all_flags), 

    } 

 

    out_path = os.path.join("output", "summaries", "patient_001_summary.json") 

    os.makedirs(os.path.dirname(out_path), exist_ok=True) 

    with open(out_path, "w", encoding="utf-8") as f: 

        json.dump(summary, f, indent=2, ensure_ascii=False) 

 

    return ( 

        f"Summary saved to {out_path}\n" 

        f"Total flags: {len(all_flags)}\n" 

        f"Flags:\n{json.dumps(all_flags, indent=2)}" 

    ) 

 

 

# ── Dispatcher ── 

 

TOOL_MAP = { 

    "read_document": lambda args: read_document(**args), 

    "get_section": lambda args: get_section(**args), 

    "get_raw_pages": lambda args: get_raw_pages(**args), 

    "extract_structured_data": lambda args: extract_structured_data(), 

    "normalize_medication": lambda args: normalize_medication(**args), 

    "validate_diagnosis": lambda args: validate_diagnosis(**args), 

    "lookup_drug_interaction": lambda args: lookup_drug_interaction(**args), 

    "flag_conflict": lambda args: flag_conflict(**args), 

    "flag_missing": lambda args: flag_missing(**args), 

    "finalize_summary": lambda args: finalize_summary(**args), 

} 

 

 

def execute_tool(tool_name: str, tool_args: dict) -> str: 

    if tool_name not in TOOL_MAP: 

        return f"ERROR: Unknown tool '{tool_name}'. Available: {list(TOOL_MAP.keys())}" 

    try: 

        return TOOL_MAP[tool_name](tool_args) 

    except Exception as e: 

        return f"ERROR: Tool '{tool_name}' failed: {e}" 

 

 