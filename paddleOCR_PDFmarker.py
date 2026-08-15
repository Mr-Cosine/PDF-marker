"""
text recognition and annotation marking
"""

import os
import pymupdf
import numpy
from PIL import Image
import IPC
import paddleOCR_reader as reader
from paddleocr import TextDetection, TextRecognition
import pdf_rotate
from page_elements import pdf_page
from pdf_rotate import revert_rotation_points

model_det = None
model_rec = None

def get_model_path(name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "OCRmodels", name)

    if os.path.exists(path): return path
    else: raise FileNotFoundError(f"PaddleOCR model not found at:{path}")

def load_model():
    global model_det, model_rec
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
        raise ImportError("Failed loading OCR model")



def markPDF(settings, pdf_file):
    # 解析设置
    keyword = settings.get("keyword", None)
    capital = settings.get("capital", None)
    leniency = settings.get("leniency", None)
    output_dir = settings.get("output_dir", None)
    output_name = settings.get("output_name", None)
    DPI = settings.get("dpi", None)

    if not all([output_dir is not None and len(output_dir) > 0, 
                output_name is not None and len(output_name) > 0,
                capital is not None and isinstance(capital, bool), 
                DPI is not None and DPI > 0,
                leniency is not None and leniency > 0, ]):
        raise ValueError("Invalid input settings occurred.")
    
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{output_name}.pdf")

    # 如果没有关键词，直接保存 PDF
    if not keyword:
        pdf_file.save(output_path)
        return

    IPC.log("Loading settings , start reading.")

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

    IPC.log("Using paddleOCR as OCR model")
    IPC.log("Loading OCR models...")
    IPC.report("Loading OCR models... (The first time is slower to initialize the model)")
    
    # 初始化 OCR 模型（只加载一次）
    load_model()
    IPC.log("loaded OCR model successfully, start processing")
    IPC.report("Loaded OCR model successfully, start processing.")

    # 准备pdf每一页，变成图像
    pages_4_read = []
    IPC.report("Check the pop up window for pdf preview, and fix any pages not oriented upright.")
    for page_num in range(len(pdf_file)):
        page_file = pdf_file[page_num]

        zoom = DPI / 72
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page_file.get_pixmap(matrix=mat, colorspace=pymupdf.csGRAY)
        page_image = numpy.array(Image.frombytes("L", [pix.width, pix.height], pix.samples))

        pages_4_read.append(pdf_page(
                                    page_file=page_file,
                                    page_num=page_num,
                                    image=page_image, 
                                    rotation=0, 
                                    height=page_image.shape[0], 
                                    width=page_image.shape[1]
                                    ))

    pdf_rotate.show_window(pages_4_read)

    # 对每一页进行处理
    IPC.report("Start reading...")
    for page_4_read in pages_4_read:
        IPC.report(f"Processing... progress: [{page_4_read.page_num + 1}/{len(pages_4_read)}] pages")

        page_file = page_4_read.page_file
        og_height = page_4_read.height
        og_width = page_4_read.width

        # 提取文本行，分组为段落
        snippets_read = reader.read(page_4_read.image, model_det, model_rec)
        paragraphs = reader.group_snippets_into_paragraphs(snippets_read, leniency=leniency)

        # 页面旋转&缩放矫正设置
        scale_x = page_file.rect.width / og_width
        scale_y = page_file.rect.height / og_height

        # 检测关键字并标注
        IPC.log("================================")
        for i, para in enumerate(paragraphs):
            # ---- 先判断整个段落是否匹配关键词 ----
            has_kw = match(para.text())
            IPC.log(f"paragraph{i}: has keyword is {has_kw}")
            IPC.log(f"{para.text()[:50]}" + ("..." if len(para.text()) > 50 else ""))
            if not has_kw: continue

            # ---- 匹配时，画红色矩形框（段落边框） ----
            left_c, top_c, right_c, bottom_c = para.left_bound(), para.top_bound(), para.right_bound(), para.bottom_bound()
            corners_c = [(left_c, top_c), (right_c, top_c), (right_c, bottom_c), (left_c, bottom_c)]
            corners_orig = revert_rotation_points(corners_c, page_4_read.rotation, (og_height, og_width))
            xs = [p[0] for p in corners_orig]
            ys = [p[1] for p in corners_orig]
            left_o, right_o = min(xs), max(xs)
            top_o, bottom_o = min(ys), max(ys)

            x1 = left_o * scale_x
            y1 = top_o * scale_y
            x2 = right_o * scale_x
            y2 = bottom_o * scale_y
            rect = pymupdf.Rect(x1, y1, x2, y2) * page_file.derotation_matrix
            annot = page_file.add_rect_annot(rect)
            annot.set_colors(stroke=(1, 0, 0))
            annot.set_border(width=1.5)
            annot.update()

    # 保存修改后的 PDF
    pdf_file.save(output_path)