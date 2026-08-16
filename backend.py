"""
Reader starter, communication with frontend
"""
import IPC

def get_configs():
    raw = sys.stdin.buffer.read().decode("utf-8")
    if not raw: raise ValueError("no settings passed through stdin")
    
    settings = json.loads(raw)

    keyword = settings.get("keyword", None)
    output_dir = settings.get("outputDir", None)
    output_name = settings.get("outputName", None)
    model = settings.get("model", None)
    capital = settings.get("capital", None)
    leniency = settings.get("leniency", None)
    DPI = settings.get("DPI", None)

    files = settings.get("files", None)

    if not all([files is not None and len(files) > 0, 
                output_dir is not None and len(output_dir) > 0, 
                output_name is not None and len(output_name) > 0,
                model is not None,
                capital is not None and isinstance(capital, bool), 
                DPI is not None and DPI > 0,
                leniency is not None and leniency > 0, ]):
        raise ValueError("Invalid input settings occurred.")

    return { 
        "keyword": keyword,
        "output_dir": output_dir,
        "output_name": output_name,
        "model": model,
        "capital": capital,
        "dpi": DPI,
        "leniency": leniency,
    }, files

def mergePDF(files):
    if len(files) == 0: raise ValueError("empty files list")

    try:
        files.sort(key=lambda x: x.get("index", 0))
    except Exception as e:
        raise Exception(f"Error in sorting the files: {e}")
    
    merged_pdf = pymupdf.open()

    for pdf_num, pdf in enumerate(files):
        IPC.report(f"Merging PDF, progress: [{pdf_num}/{len(pdf)}]")

        pdf_path = pdf.get("path")
        if not pdf_path:
            continue
        pdf_path = os.path.normpath(pdf_path)
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"File not exist: {pdf_path}")
        
        try:
            with open(pdf_path, "rb") as f:
                data = f.read()
            doc = pymupdf.open(stream=data, filetype="pdf")
            merged_pdf.insert_pdf(doc)
            doc.close()
        except Exception as e:
            raise ValueError(f"Opening file failed - {pdf_path}: {e}")

    return merged_pdf

if __name__ == "__main__":
    merged_pdf = None
    try:
        import json
        import os
        import sys 
        import pymupdf
        import traceback

        # the resolution when render pdf in dpi

        IPC.report("Loading configurations...")
        [settings, files] = get_configs()

        model = settings.get("model", None)
        if isinstance(model, str): model = model.strip()
        
        if model is not None and model == "tesseractOCR":   import tesseractOCR_PDFmarker as PDFmarker
        elif model is not None and model == "paddleOCR":    import paddleOCR_PDFmarker as PDFmarker
        else: raise ValueError(f"unknown model name: {model}")
        IPC.report("Configurations good.")

        IPC.report("Merging pdfs...")
        merged_pdf = mergePDF(files)
        IPC.report("Merge complete.")

        IPC.report("Read and marking pdfs...")
        PDFmarker.markPDF(settings, merged_pdf)
        IPC.report("Finished")

        merged_pdf.close()

        IPC.resolve({
            "success": True,
            "message": "",
            "details": []
            })

    except Exception as e:
        IPC.report("Process failed. Check pop up window for more informations.")

        if merged_pdf is not None: merged_pdf.close()

        IPC.resolve({
            "success": False,
            "message": f"Error: {str(e)}",
            "details": [traceback.format_exc()]
            })