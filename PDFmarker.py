"""
OCR and annotation marking
"""

import json
import os
import sys 
import pymupdf
import pytesseract
import sys
import json
import traceback
from PIL import Image
pytesseract.pytesseract.tesseract_cmd = 'TesseractOCR/tesseract.exe'

def _print(message): print(message, file=sys.stderr)

def _return(message): print(json.dumps(message))

def _throw(error): 
    print(error, file=sys.stderr)
    sys.exit(1)

def getConfigs():

    try:
        raw = sys.stdin.buffer.read().decode('utf-8')
        if not raw:
            raise ValueError("stdin is empty")
        
        settings = json.loads(raw)

        keyword = settings.get('keyword', None)
        vague = settings.get('vague', None)
        capital = settings.get('capital', None)
        output_dir = settings.get('outputDir', None)
        output_name = settings.get('outputName', None)
        files = settings.get('files', None)

        if not all([vague is not None, capital is not None, output_dir, output_name, files]): _throw("Invalid input parameters.")

        return [{'keyword': keyword, 'vague': vague, 'capital': capital, 'output_dir': output_dir, 'output_name': output_name}, files]

    except Exception as e:
        _throw(traceback.format_exc())

def mergePDF(files):
    if len(files) == 0: _throw("empty files list")

    try: files.sort(key=lambda x: x['index'])
    except: _throw("error in sorting the files")
    
    merged_pdf = pymupdf.open()

    for pdf in files:
        pdf_path = pdf.get('path')
        if not pdf_path: continue
        pdf_path = os.path.normpath(pdf_path)
        if not os.path.exists(pdf_path):
            _print(f"File not exist: {pdf_path}")
            continue
        
        try:
            with open(pdf_path, 'rb') as f: data = f.read()
            doc = pymupdf.open(stream=data, filetype="pdf")
            merged_pdf.insert_pdf(doc)
            doc.close()
        except Exception as e:
            _print(f"Opening file failed - {pdf_path}: {e}")
            continue

    return merged_pdf

def markPDF(settings, file):
    #read configs
    output_dir = settings.get('output_dir', '')
    output_name = settings.get('output_name', '')
    OUTPUT_PATH = os.path.join(output_dir, f"{output_name}.pdf")
    
    keyword_str = settings.get('keyword', '').strip()
    if not keyword_str:
        file.save(OUTPUT_PATH)
        return

    vague = settings.get('vague')
    match_capital = settings.get('capital')
    keywords = [kw.strip() if match_capital else kw.strip().lower() for kw in keyword_str.split()]

    #criteria for marking
    def has_keyword(text):
        text_comparing = text if match_capital else text.lower()
        if vague: return any(kw in text_comparing for kw in keywords)
        else: return all(kw in text_comparing for kw in keywords)
    
    #go through pages
    for page_num in range(len(file)):
        #read and get words on page
        page = file[page_num]
        words = []

        pix = page.get_pixmap(dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        scale_x = page.rect.width / pix.width
        scale_y = page.rect.height / pix.height
        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            if not text:
                continue
            words.append({
                'text': text,
                'block_num': ocr_data['block_num'][i],
                'left': ocr_data['left'][i] * scale_x,
                'top': ocr_data['top'][i] * scale_y,
                'width': ocr_data['width'][i] * scale_x,
                'height': ocr_data['height'][i] * scale_y,
                'right': (ocr_data['left'][i] + ocr_data['width'][i]) * scale_x,
                'bottom': (ocr_data['top'][i] + ocr_data['height'][i]) * scale_y
            })

        if not words: continue

        #group into text blocks
        text_blocks = {}
        for word in words:
            if word['block_num'] not in text_blocks: text_blocks[word['block_num']] = []
            text_blocks[word['block_num']].append(word)
        
        RED = (1, 0, 0)
        STR_WIDTH = 2
        #get combinations of text in block
        for block_num in text_blocks:
            words = text_blocks[block_num]
            words.sort(key=lambda w: (w['top'], w['left']))
            text = ' '.join(word['text'] for word in words)

            #mark if contains keyword
            if has_keyword(text):
                left = min(word['left'] for word in words) - STR_WIDTH * 2
                top = min(word['top'] for word in words) - STR_WIDTH * 2
                right = max(word['right'] for word in words) + STR_WIDTH * 2
                bottom = max(word['bottom'] for word in words) + STR_WIDTH * 2

                annot = page.add_rect_annot(pymupdf.Rect(left, top, right, bottom))
                annot.set_border(width=STR_WIDTH)
                annot.set_colors(stroke=RED)
                annot.update()

                _print(f"Marked: {text[:]}")

    file.save(OUTPUT_PATH)
    file.close()

if __name__ == "__main__":
    [settings, files] = getConfigs()

    merged_pdf = mergePDF(files)

    markPDF(settings, merged_pdf)

    _return({"success": True, "message": "success", "details": []}) 