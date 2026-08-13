"""
text recognition and annotation marking
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import pymupdf
import pytesseract
import numpy
from PIL import Image
import IPC
import tesseractOCR_reader
import pdf_rotate
from page_elements import pdf_page
from pdf_rotate import revert_rotation_points

def get_model_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, "OCRmodels", "TesseractOCR", "tesseract.exe")

    if os.path.exists(path): return path
    else: raise FileNotFoundError(f"tesseract.exe not found at:{path}")

def load_model():
    tesseract_exe_path = get_model_path()
    pytesseract.pytesseract.tesseract_cmd = tesseract_exe_path
    tessdata_dir = os.path.join(os.path.dirname(tesseract_exe_path), "tessdata")

    if os.path.exists(tessdata_dir): 
        os.environ["TESSDATA_PREFIX"] = tessdata_dir
    else:
        raise ImportError("Failed loading OCR model.")

def process_one_page(upright_page, leniency):
    snippets_read = tesseractOCR_reader.read(upright_page.image)
    upright_page.content = tesseractOCR_reader.group_snippets_into_paragraphs(snippets_read, leniency=leniency)

def markPDF(settings, pdf_file):
    os.environ["OMP_THREAD_LIMIT"] = "2"
    os.environ["OMP_NUM_THREADS"] = "2"

    MAX_WORKERS = 3

    # 解析设置
    keyword = settings.get("keyword", None)
    capital = settings.get("capital", None)
    leniency = settings.get("leniency", None)
    output_dir = settings.get("output_dir", None)
    output_name = settings.get("output_name", None)
    DPI = settings.get("dpi", 150)

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

    IPC.log("Loading settings successful, start reading.")

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

    IPC.log("Using tesseractOCR as OCR model")
    IPC.log("Loading OCR models...")
    IPC.report("Loading OCR models... (The first time is slower to initialize the model)")
    
    # 初始化 OCR 模型（只加载一次）
    load_model()
    IPC.log("Loaded OCR model successfully, start processing")
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

    # 摆正图像
    pdf_rotate.show_window(pages_4_read)

    # 对每一页进行处理
    with ThreadPoolExecutor(max_workers=3) as executor:
        task_done = 0
        IPC.report(f"Processing... progress: [{task_done}/{len(all_tasks)}] pages")
        all_tasks = [executor.submit(process_one_page, page, leniency) for page in pages_4_read]

        for task in as_completed(all_tasks):
            task_done += 1

            try: task.result()
            except Exception as e: raise e

            IPC.report(f"Processing... progress: [{task_done}/{len(all_tasks)}] pages")

    for page_4_read in pages_4_read:
        page_file = page_4_read.page_file
        og_height = page_4_read.height
        og_width = page_4_read.width

        page_rect = page_file.rect
        scale_x = page_rect.width / og_width
        scale_y = page_rect.height / og_height
    
        for i, para in enumerate(page_4_read.content):
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