import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from pathlib import Path

# --- WINDOWS OCR CONFIGURATION ---
# Point these to where you installed Tesseract and Poppler on your Windows machine!
pytesseract.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'
POPPLER_PATH = r'C:/poppler/Library/bin'

def parse_digital_pdf(pdf_path: str, output_md_path: str):
    """
    Hybrid Parser: 
    1. Attempts strict digital extraction.
    2. Falls back to Tesseract OCR if the page is a scanned image (text length < 50 chars).
    """
    extracted_markdown = f"# Document Parsing Report: {Path(pdf_path).name}/n/n"
    
    print(f"📄 Processing: {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        
        for page_num in range(total_pages):
            page = pdf.pages[page_num]
            text = page.extract_text()
            
            # --- DETECTION: Is it a scanned page? ---
            # If the page has no text, or very little text, it's likely a scanned image.
            if not text or len(text.strip()) < 50:
                print(f"   ⚠️ Page {page_num + 1} appears to be scanned. Triggering Tesseract OCR...")
                
                try:
                    # Convert just this specific page to an image
                    images = convert_from_path(
                        pdf_path, 
                        first_page=page_num + 1, 
                        last_page=page_num + 1, 
                        poppler_path=POPPLER_PATH
                    )
                    
                    if images:
                        # Run OCR on the image
                        ocr_text = pytesseract.image_to_string(images[0])
                        extracted_markdown += f"/n/n## --- Page {page_num + 1} (OCR Extracted) ---/n/n{ocr_text}"
                except Exception as e:
                    print(f"   ❌ OCR Failed on page {page_num + 1}: {str(e)}")
                    extracted_markdown += f"/n/n## --- Page {page_num + 1} ---/n/n[ERROR: OCR Extraction Failed]"
            
            else:
                # --- STANDARD EXTRACTION ---
                print(f"   ✅ Page {page_num + 1} parsed digitally.")
                
                # Extract any standard tables found on the page
                tables = page.extract_tables()
                table_md = ""
                if tables:
                    for table in tables:
                        table_md += "/n"
                        for row in table:
                            # Clean up empty cells (None types)
                            clean_row = [str(cell).replace("/n", " ") if cell else "" for cell in row]
                            table_md += "| " + " | ".join(clean_row) + " |/n"
                        table_md += "/n"

                extracted_markdown += f"/n/n## --- Page {page_num + 1} ---/n/n{text}/n{table_md}"
                
    # Save the synthesized markdown ready for ChromaDB vectorization
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(extracted_markdown)
        
    print(f"🎉 Parsing complete! Saved to {output_md_path}")