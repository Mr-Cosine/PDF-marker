"""
text recognition and annotation marking
"""

import json
import os
import sys 
import pymupdf
import traceback
import numpy
from PIL import Image
import paddleOCR_reader
from paddleocr import TextDetection, TextRecognition
import pdf_rotate
from pdf_rotate import revert_rotation_image, revert_rotation_points

def _print(message): print(message, file=sys.stderr, flush=True)

def _return(message): print(json.dumps(message), flush=True)

def get_model_path(name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, 'OCRmodels', name)
    if os.path.exists(path): return path
    else: raise FileNotFoundError(f"PaddleOCR model not found at:{path}")
    
def get_configs():
    raw = sys.stdin.buffer.read().decode('utf-8')
    if not raw:
        raise ValueError("stdin is empty")
    
    settings = json.loads(raw)

    keyword = settings.get('keyword', None)
    capital = settings.get('capital', None)
    leniency = settings.get('leniency', None)
    output_dir = settings.get('outputDir', None)
    output_name = settings.get('outputName', None)
    files = settings.get('files', None)

    if not all([capital is not None and isinstance(capital, bool), 
                leniency is not None and leniency > 0, 
                files is not None and len(files) > 0, 
                output_dir is not None and len(output_dir) > 0, 
                output_name is not None and len(output_name) > 0]):
        raise ValueError("Invalid input parameters: capital, output directory, and files are required.")

    return { 
        'keyword': keyword,
        'capital': capital,
        'leniency': leniency,
        'output_dir': output_dir,
        'output_name': output_name,
    }, files

def mergePDF(files):
    if len(files) == 0:
        raise ValueError("empty files list")

    try:
        files.sort(key=lambda x: x.get('index', 0))
    except Exception as e:
        raise Exception(f"error in sorting the files: {e}")
    
    merged_pdf = pymupdf.open()

    for pdf in files:
        pdf_path = pdf.get('path')
        if not pdf_path:
            continue
        pdf_path = os.path.normpath(pdf_path)
        if not os.path.exists(pdf_path):
            _print(f"File not exist: {pdf_path}")
            continue
        
        try:
            with open(pdf_path, 'rb') as f:
                data = f.read()
            doc = pymupdf.open(stream=data, filetype="pdf")
            merged_pdf.insert_pdf(doc)
            doc.close()
        except Exception as e:
            _print(f"Opening file failed - {pdf_path}: {e}")
            continue

    return merged_pdf

def markPDF(settings, pdf_file):
    # 解析设置
    keyword = settings.get('keyword', None)
    capital = settings.get('capital', None)
    leniency = settings.get('leniency', None)
    output_dir = settings.get('output_dir', None)
    output_name = settings.get('output_name', None)

    if not all([capital is not None and isinstance(capital, bool), 
                leniency is not None and leniency > 0,  
                output_dir is not None and len(output_dir) > 0, 
                output_name is not None and len(output_name) > 0]):
        raise ValueError("Invalid input parameters: capital, leniency, output directory, and output name are required.")

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{output_name}.pdf")

    # 如果没有关键词，直接保存 PDF
    if not keyword:
        pdf_file.save(output_path)
        return

    _print('have keyword, start reading.')

    keywords = keyword.split()

    def match(text):
        if not keywords: return False
        tokens = text.split()
        if not tokens: return False

        remaining = list(keywords)
        for token in tokens:
            while remaining:
                part = remaining[0]
                if capital:
                    if part in token: remaining.pop(0)
                    else: break 
                else:
                    if part.lower() in token.lower(): remaining.pop(0)
                    else: break
            if not remaining: return True
        return False

    _print('using tesseractOCR')
    _print("loading OCR models...")
    
    # 初始化 OCR 模型（只加载一次）
    try:
        model_det = TextDetection(
            model_name="PP-OCRv6_medium_det",
            model_dir=get_model_path("PP-OCRv6_medium_det_safetensors"),
            engine="transformers"
        )
        model_rec = TextRecognition(
            model_name="PP-OCRv6_small_rec",
            model_dir=get_model_path("PP-OCRv6_small_rec_safetensors"),
            engine="transformers"
        )
    except Exception:
        raise ImportError('Failed loading PaddleOCR models')

    _print("loaded OCR model successfully, start processing")

    page_images = []

    # 准备pdf每一页，变成图像，摆正
    for page_idx in range(len(pdf_file)):
        _print("================================")
        page = pdf_file[page_idx]

        zoom = 200 / 72
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, colorspace=pymupdf.csRGB)
        img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        page_img = numpy.array(img_pil)

        page_images.append(page_img)

    upright_pages = pdf_rotate.show_window(page_images)
    if upright_pages is None: upright_pages = page_images
    if len(upright_pages) != len(pdf_file): raise ValueError('invalid corrected pages.')

    # 对每一页进行处理
    for idx, upright_page in enumerate(upright_pages):
        _print("================================")
        page = pdf_file[idx]
        page_image = upright_page['image']
        page_rotation = upright_page['rotation']
        [height, width] = revert_rotation_image(page_image, page_rotation).shape[:2]

        # 提取文本行，分组为段落
        snippets_read = paddleOCR_reader.read(page_image, model_det, model_rec)
        paragraphs = paddleOCR_reader.group_snippets_into_paragraphs(snippets_read, leniency=leniency)

        # 4. 坐标映射准备
        # PDF 页面尺寸（旋转后视图）
        page_rect = page.rect
        scale_x = page_rect.width / height   # 像素 → 点 (宽度)
        scale_y = page_rect.height / width  # 像素 → 点 (高度)

        for i, para in enumerate(paragraphs):
            # ---- 先判断整个段落是否匹配关键词 ----
            has_kw = match(para.text())
            _print(f"paragraph{i}: has keyword is {has_kw}")
            _print(f"{para.text()}")
            if not has_kw: continue

            # ---- 匹配时，画红色矩形框（段落边框） ----
            left_c, top_c, right_c, bottom_c = para.left_bound(), para.top_bound(), para.right_bound(), para.bottom_bound()
            corners_c = [(left_c, top_c), (right_c, top_c), (right_c, bottom_c), (left_c, bottom_c)]
            corners_orig = revert_rotation_points(corners_c, page_rotation, (height, width))
            xs = [p[0] for p in corners_orig]
            ys = [p[1] for p in corners_orig]
            left_o, right_o = min(xs), max(xs)
            top_o, bottom_o = min(ys), max(ys)

            x1 = left_o * scale_x
            y1 = top_o * scale_y
            x2 = right_o * scale_x
            y2 = bottom_o * scale_y
            rect = pymupdf.Rect(x1, y1, x2, y2) * page.derotation_matrix
            annot = page.add_rect_annot(rect)
            annot.set_colors(stroke=(1, 0, 0))  # 红色
            annot.set_border(width=1.5)
            annot.update()

    # 保存修改后的 PDF
    pdf_file.save(output_path)
    return

if __name__ == "__main__":
    merged_pdf = None
    try:
        [settings, files] = get_configs()
        merged_pdf = mergePDF(files)
        markPDF(settings, merged_pdf)
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
        merged_pdf.close()