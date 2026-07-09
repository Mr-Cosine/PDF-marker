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

        keyword = settings.get('keyword', 'NEW VAM')
        vague = settings.get('vague', True)
        files = settings.get('files', [])
        output_dir = settings.get('outputDir', '')
        output_name = settings.get('outputName', 'MarkedPDF')

        
        return {'keyword': keyword, 'vague': vague, 'files': files, 'output_dir': output_dir, 'output_name': output_name}

    except Exception as e:
        _throw(traceback.format_exc())

def mergePDF(settings):
    files = settings.get('files')
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

    output_path = os.path.join(settings.get('output_dir', ''), f"{settings.get('output_name', 'MarkedPDF')}.pdf")
    merged_pdf.save(output_path)

    return merged_pdf

def markPDF(settings, file):
    vague = settings.get('vague')

    keyword_str = settings.get('keyword', '').strip()
    if not keyword_str:
        return
    elif vague:
        keywords = [keyword_str]
    else:
        keywords = [kw.strip() for kw in keyword_str.split() if kw.strip()]

    output_dir = settings.get('output_dir')
    output_name = settings.get('output_name')

    if vague:
        def match(text):
            return keyword_str.lower() in text.lower()
    else:
        keywords = [kw.strip().lower() for kw in keyword_str.split() if kw.strip()]
        def match(text):
            text_lower = text.lower()
            return all(kw in text_lower for kw in keywords)
    
    for page_num in range(len(file)):
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
                'left': ocr_data['left'][i] * scale_x,
                'top': ocr_data['top'][i] * scale_y,
                'width': ocr_data['width'][i] * scale_x,
                'height': ocr_data['height'][i] * scale_y,
                'right': (ocr_data['left'][i] + ocr_data['width'][i]) * scale_x,
                'bottom': (ocr_data['top'][i] + ocr_data['height'][i]) * scale_y
            })

        if not words:
            continue
    words.sort(key=lambda w: (w['top'], w['left']))
    lines = []
    if words:
        current_line = [words[0]]
        for w in words[1:]:
            avg_top = sum(ww['top'] for ww in current_line) / len(current_line)
            avg_height = sum(ww['height'] for ww in current_line) / len(current_line)
            if abs(w['top'] - avg_top) < avg_height / 2:
                current_line.append(w)
            else:
                current_line.sort(key=lambda ww: ww['left'])
                lines.append(current_line)
                current_line = [w]
        if current_line:
            current_line.sort(key=lambda ww: ww['left'])
            lines.append(current_line)

    # ---- 将行合并为段落 ----
    paragraphs = []
    if lines:
        current_para = lines[0]
        for line in lines[1:]:
            # 计算间距
            last_line_bottom = max(w['bottom'] for w in current_para)
            next_line_top = min(w['top'] for w in line)
            gap = next_line_top - last_line_bottom
            avg_height = sum(w['height'] for w in current_para) / len(current_para)
            if gap < avg_height * 1.5:
                current_para.extend(line)
            else:
                paragraphs.append(current_para)
                current_para = line
        paragraphs.append(current_para)

    # ---- 匹配段落 ----
    for para_words in paragraphs:
        para_text = ' '.join(w['text'] for w in para_words)
        if match(para_text):
            left = min(w['left'] for w in para_words)
            top = min(w['top'] for w in para_words)
            right = max(w['right'] for w in para_words)
            bottom = max(w['bottom'] for w in para_words)
            rect = pymupdf.Rect(left, top, right, bottom)
            annot = page.add_rect_annot(rect)
            annot.set_border(width=2)
            annot.update()
            _print(f"已标记段落: {para_text[:30]}...")


if __name__ == "__main__":
    settings = getConfigs()

    merged_pdf = mergePDF(settings)

    markPDF(settings, merged_pdf)

    _return({"success": True, "message": "success", "details": []})