"""
OCR core logics
"""

from page_elements import read_snippet, read_paragraph

def read(image, model_det, model_rec):
    """
    output to excel sheet

    :param image:           numpy.array                the image

    :return:                status, content     
                            if success: status = 'success', content = None
                            if error:   status = 'error',   content = 'error message'
    """

    output = model_det.predict(image)

    all_snippets = []
    for res in output:
        dt_polys = res['dt_polys']
        for _, poly in enumerate(dt_polys):
            new_snippet = read_snippet(poly[0], poly[1], poly[2], poly[3])
            if (new_snippet._top < new_snippet._bottom and 
                new_snippet._left < new_snippet._right):
                cropped = image[int(new_snippet._top):int(new_snippet._bottom),
                                int(new_snippet._left):int(new_snippet._right)]
                new_snippet.set_image(cropped)
                all_snippets.append(new_snippet)

    for snippet in all_snippets:
        snippet.set_text(model_rec.predict(snippet.image())[0].get('rec_text', '') or '')

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
