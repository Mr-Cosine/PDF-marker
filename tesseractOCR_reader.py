"""
OCR core logics
"""

import pytesseract
from page_elements import read_snippet, read_paragraph

def read(image, lang="eng+chi_sim", psm=3):
    """
    使用 Tesseract 进行文本检测和识别。
    返回: read_snippet 列表，每个 snippet 代表一个文本行。
    参数：
        image : numpy.ndarray   (RGB 图像，已被校正方向)
        lang  : str             语言代码，默认 "eng"
        psm   : int             Page Segmentation Mode，默认 6 (统一文本块)
    """
    # 获取详细的识别结果（包含单词位置）
    data = pytesseract.image_to_data(
        image,
        output_type=pytesseract.Output.DICT,
        lang=lang,
        config=f"--psm {psm}"
    )

    # 按 (block_num, par_num, line_num) 将单词聚合成文本行
    lines = {}
    n_boxes = len(data["level"])
    for i in range(n_boxes):
        text = data["text"][i].strip()
        if not text:
            continue
        line_key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]

        if line_key not in lines:
            lines[line_key] = {
                "texts": [text],
                "left": x, "top": y,
                "right": x + w, "bottom": y + h
            }
        else:
            lines[line_key]["texts"].append(text)
            lines[line_key]["left"]   = min(lines[line_key]["left"], x)
            lines[line_key]["top"]    = min(lines[line_key]["top"], y)
            lines[line_key]["right"]  = max(lines[line_key]["right"], x + w)
            lines[line_key]["bottom"] = max(lines[line_key]["bottom"], y + h)

    # 为每一行构建 read_snippet 对象
    all_snippets = []
    for line_key, line_data in lines.items():
        l = line_data["left"]
        t = line_data["top"]
        r = line_data["right"]
        b = line_data["bottom"]
        if r <= l or b <= t:
            continue

        # 创建四边形角点（这里是水平矩形）
        p1 = (l, t)
        p2 = (r, t)
        p3 = (r, b)
        p4 = (l, b)
        snippet = read_snippet(p1, p2, p3, p4)
        snippet.set_text(" ".join(line_data["texts"]))
        snippet.set_image(None)
        all_snippets.append(snippet)

    return all_snippets

def group_snippets_into_paragraphs(snippets, leniency=1):
    def avg(*args): return sum(args) / len(args) if args else 0
    def gap_hor(s1, s2):
        return max(s1.left_bound(), s2.left_bound()) - min(s1.right_bound(), s2.right_bound())
    def dist_ver(s1, s2):
        return abs(s1.center_point()[1] - s2.center_point()[1])

    def is_same_line(s1, s2):
        return dist_ver(s1, s2) < avg(s1.line_height(), s2.line_height()) * 0.7 * leniency
    def near_horizontal(s1, s2):
        return gap_hor(s1, s2) < avg(s1.line_height(), s2.line_height()) * 1.4 * leniency
    def near_vertical(s1, s2):
        return dist_ver(s1, s2) < avg(s1.line_height(), s2.line_height()) * 2.8 * leniency
    def overlap_hor(s1, s2):
        # 找出较窄的框（宽度较小）和较宽的框
        if (s1.right_bound() - s1.left_bound()) < (s2.right_bound() - s2.left_bound()):
            narrow_l, narrow_r = s1.left_bound(), s1.right_bound()
            wide_l, wide_r = s2.left_bound(), s2.right_bound()
        else:
            narrow_l, narrow_r = s2.left_bound(), s2.right_bound()
            wide_l, wide_r = s1.left_bound(), s1.right_bound()
        
        # 计算重叠区间
        overlap_l = max(narrow_l, wide_l)
        overlap_r = min(narrow_r, wide_r)
        if overlap_r <= overlap_l: return False
        else: return (overlap_r - overlap_l) >= 0.5 * (narrow_r - narrow_l)

    def should_merge(para, s_outside):
        def in_same_paragraph(s1, s2):
            h1 = s1.line_height()
            h2 = s2.line_height()
            
            if any([h1 == 0, h2 == 0]): return False
            if max(h1, h2) / min(h1, h2) > 2: return False
            
            if is_same_line(s1, s2) and near_horizontal(s1, s2): return True
            elif near_vertical(s1, s2) and overlap_hor(s1, s2): return True
            return False

        return any(in_same_paragraph(s_outside, snippet) for snippet in para.snippets())

    paragraphs = []

    unselected = sorted(snippets, key=lambda s: (s.top_bound(), s.left_bound()))

    while len(unselected) > 0:
        current = unselected.pop(0)
        para = read_paragraph()
        para.append(current)

        # 扩展段落，直到没有更多 snippet 可以加入
        added = True
        while added:
            added = False
            for s in unselected.copy():
                if should_merge(para, s):
                    para.append(s)
                    unselected.remove(s)
                    added = True

        paragraphs.append(para)

    return paragraphs
