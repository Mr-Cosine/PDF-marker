"""
Reader starter, communication with frontend
"""

def _print(message): print(message, file=sys.stderr, flush=True)

def _return(message): print(json.dumps(message), flush=True)

def get_configs():
    raw = sys.stdin.buffer.read().decode("utf-8")
    if not raw: raise ValueError("no settings passed through stdin")
    
    settings = json.loads(raw)

    model = settings.get("model", None)
    keyword = settings.get("keyword", None)
    capital = settings.get("capital", None)
    leniency = settings.get("leniency", None)
    output_dir = settings.get("outputDir", None)
    output_name = settings.get("outputName", None)
    files = settings.get("files", None)

    if not all([model is not None,
                capital is not None, 
                leniency is not None and leniency > 0, 
                files is not None and len(files) > 0, 
                output_dir is not None and len(output_dir) > 0, 
                output_name is not None and len(output_name) > 0]):
        raise ValueError("Invalid input settings.")

    return { 
        "model": model,
        "keyword": keyword,
        "capital": capital,
        "leniency": leniency,
        "output_dir": output_dir,
        "output_name": output_name,
    }, files

def mergePDF(files):
    if len(files) == 0:
        raise ValueError("empty files list")

    try:
        files.sort(key=lambda x: x.get("index", 0))
    except Exception as e:
        raise Exception(f"error in sorting the files: {e}")
    
    merged_pdf = pymupdf.open()

    for pdf in files:
        pdf_path = pdf.get("path")
        if not pdf_path:
            continue
        pdf_path = os.path.normpath(pdf_path)
        if not os.path.exists(pdf_path):
            _print(f"File not exist: {pdf_path}")
            continue
        
        try:
            with open(pdf_path, "rb") as f:
                data = f.read()
            doc = pymupdf.open(stream=data, filetype="pdf")
            merged_pdf.insert_pdf(doc)
            doc.close()
        except Exception as e:
            _print(f"Opening file failed - {pdf_path}: {e}")
            continue

    return merged_pdf

if __name__ == "__main__":
    merged_pdf = None
    try:
        import json
        import os
        import sys 
        import pymupdf
        import traceback
    
        [settings, files] = get_configs()
        model = settings.get("model", None)
        if isinstance(model, str):
            model = model.strip()
        if model == "tesseractOCR":
            import tesseractOCR_PDFmarker as PDFmarker
        elif model == "paddleOCR":
            import paddleOCR_PDFmarker as PDFmarker
        else:
            raise ValueError(f"unknown model name: {model}")

        merged_pdf = mergePDF(files)
        PDFmarker.markPDF(settings, merged_pdf)
        
        _return({
            "success": True, 
            "message": "success", 
            "details": []
            }) 

    except Exception as e:
        _return({
            "success": False, 
            "message": f"Error: {str(e)}", 
            "details": [traceback.format_exc()]
            })

    finally:
        if merged_pdf is not None: merged_pdf.close()