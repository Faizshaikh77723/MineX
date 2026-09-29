import os
from pathlib import Path
import pypdfium2 as pdfium
from paddleocr import PPStructureV3

# CRITICAL WINDOWS FIXES:
os.environ["FLAGS_use_gpu"] = "0"         # Force CPU mode
os.environ["FLAGS_use_mkldnn"] = "0"      # Disable the buggy oneDNN math backend on Windows
os.environ["FLAGS_enable_pir_api"] = "0"  # Disable the experimental executor causing the C++ crash

def parse_scanned_pdf(file_path: str, output_md_path: str = None) -> str:
    """
    Renders pages to images using PyPDFium2, then OCRs them with PaddleOCR.
    If output_md_path is provided, writes the content to disk.
    """
    pipeline = PPStructureV3(
        device="cpu", 
        use_formula_recognition=False,  
        use_chart_recognition=False     
    )
    
    full_markdown = []
    
    try:
        pdf = pdfium.PdfDocument(file_path)
        for page_num in range(len(pdf)):
            full_markdown.append(f"\n## --- Source Page {page_num + 1} ---")
            
            # 1. Render the PDF page as a high-res image
            page = pdf[page_num]
            bitmap = page.render(scale=2.0)
            pil_image = bitmap.to_pil()
            
            # 2. Save temporarily
            temp_img_path = f"temp_ocr_page_{page_num}.png"
            pil_image.save(temp_img_path)
            
            print(f"Processing Page {page_num + 1} with PaddleOCR...")
            
            # 3. OCR the image
            output = pipeline.predict(temp_img_path)
            for res in output:
                md_data = res.get('markdown') if isinstance(res, dict) else getattr(res, 'markdown', '')
                md_text = "\n".join([str(val) for val in md_data.values()]) if isinstance(md_data, dict) else str(md_data)
                
                if md_text.strip():
                    full_markdown.append(md_text)
                    
            # 4. Clean up temporary image
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)
                
        pdf.close()
        
        result_md = "\n\n".join(full_markdown)

        # 5. Write to disk if a destination path is specified
        if output_md_path:
            out_file = Path(output_md_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(result_md)
            print(f"✅ OCR Markdown saved successfully to: {output_md_path}")

        return result_md
        
    except Exception as e:
        error_msg = f"Error processing document: {e}"
        print(error_msg)
        
        # Ensure temporary image is deleted even if it crashes
        if 'temp_img_path' in locals() and os.path.exists(temp_img_path):
            os.remove(temp_img_path)
            
        return error_msg

if __name__ == "__main__":
    print("OCR Parser (PyPDFium2 + PaddleOCR) ready.")
    
    # Make sure this points to your actual PDF!
    input_pdf = "data/uploads/test.pdf"
    output_md = "data/extracted/test.md"
    
    parse_scanned_pdf(input_pdf, output_md)