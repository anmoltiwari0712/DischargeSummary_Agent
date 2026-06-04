""" 
PDF ingestion layer for the discharge summary agent. 
Handles both typed/digital text and handwritten content via OCR fallback. 
""" 
 
import os 
import fitz 
import pdfplumber 
import pytesseract 
from pdf2image import convert_from_path 
 
MIN_TEXT_THRESHOLD = 50 
 
 
def extract_pdf(pdf_path: str) -> dict: 
   output = { 
       "source": pdf_path, 
       "total_pages": 0, 
       "pages": [], 
       "full_text": "", 
       "warnings": [], 
       "ocr_pages": [], 
   } 
 
   if not os.path.exists(pdf_path): 
       output["warnings"].append(f"File not found: {pdf_path}") 
       return output 
 
   try: 
       fitz_doc = fitz.open(pdf_path) 
       output["total_pages"] = len(fitz_doc) 
   except Exception as e: 
       output["warnings"].append(f"Failed to open PDF: {e}") 
       return output 
 
   pages_needing_ocr = [] 
   page_results = {} 
 
   try: 
       with pdfplumber.open(pdf_path) as plumber_doc: 
           for i, (fitz_page, plumber_page) in enumerate( 
               zip(fitz_doc.pages(), plumber_doc.pages) 
           ): 
               text = fitz_page.get_text("text").strip() 
               table_data = [] 
 
               try: 
                   tables = plumber_page.extract_tables() 
                   if tables: 
                       for table in tables: 
                           for row in table: 
                               cleaned = [c.strip() if c else "" for c in row] 
                               table_data.append(" | ".join(cleaned)) 
               except Exception: 
                   pass 
 
               method = "digital" if len(text) >= MIN_TEXT_THRESHOLD else "ocr" 
               if method == "ocr": 
                   pages_needing_ocr.append(i + 1) 
 
               page_results[i + 1] = { 
                   "page": i + 1, 
                   "text": text, 
                   "method": method, 
                   "table_data": table_data, 
               } 
 
   except Exception as e: 
       output["warnings"].append(f"Extraction error: {e}") 
       fitz_doc.close() 
       return output 
 
   if pages_needing_ocr: 
       output["ocr_pages"] = pages_needing_ocr 
       output["warnings"].append(f"Pages requiring OCR: {pages_needing_ocr}") 
       try: 
           images = convert_from_path(pdf_path, dpi=200) 
           for page_num in pages_needing_ocr: 
               img = images[page_num - 1] 
               ocr_text = pytesseract.image_to_string(img, lang="eng").strip() 
               page_results[page_num]["text"] = ocr_text if ocr_text else "[OCR RETURNED EMPTY]" 
       except Exception as e: 
           output["warnings"].append(f"OCR failed: {e}") 
           for page_num in pages_needing_ocr: 
               page_results[page_num]["text"] = "[OCR FAILED — CONTENT UNREADABLE]" 
 
   all_text_parts = [] 
   for page_num in sorted(page_results.keys()): 
       page = page_results[page_num] 
       output["pages"].append(page) 
       all_text_parts.append(f"\n--- PAGE {page_num} ({page['method'].upper()}) ---\n") 
       if page["table_data"]: 
           all_text_parts.append("[TABLE]\n" + "\n".join(page["table_data"])) 
       all_text_parts.append(page["text"] or "[NO CONTENT]") 
 
   output["full_text"] = "\n".join(all_text_parts) 
   fitz_doc.close() 
   return output 
 
 
def extract_sections(full_text: str) -> dict: 
   section_keywords = [ 
       "DIAGNOSIS", 
       "HISTORY", 
       "PAST HISTORY", 
       "PHYSICAL EXAMINATION", 
       "INVESTIGATIONS", 
       "COURSE IN THE HOSPITAL", 
       "CONDITION AT DISCHARGE", 
       "ADVICE ON DISCHARGE", 
       "FOLLOW-UP INSTRUCTIONS", 
       "VITAL PARAMETERS", 
       "MEDICATIONS", 
       "ALLERGIES", 
       "PROCEDURES", 
   ] 
 
   sections = {} 
   lines = full_text.split("\n") 
   current_section = "HEADER" 
   current_content = [] 
 
   for line in lines: 
       matched = False 
       stripped = line.strip().upper() 
       for keyword in section_keywords: 
           if stripped.startswith(keyword) or stripped == keyword + ":": 
               if current_content: 
                   sections[current_section] = "\n".join(current_content).strip() 
               current_section = keyword 
               current_content = [] 
               matched = True 
               break 
       if not matched: 
           current_content.append(line) 
 
   if current_content: 
       sections[current_section] = "\n".join(current_content).strip() 
 
   return sections 
 


 