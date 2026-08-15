import numpy
import cv2

class pdf_page:
    def __init__(self, page_file, page_num, image, width, height, rotation=0, content=[]):
        self.page_file = page_file
        self.image = image
        self.rotation = rotation
        self.content = content
        self.width = width
        self.height = height
        self.content = content
        self.page_num = page_num

class read_snippet:
    def __init__(self, p1, p2, p3, p4, image=None):
        self._pts = numpy.array([p1, p2, p3, p4], dtype=numpy.float32)

        # 几何中心点
        self._center = [sum(p[0] for p in self._pts) / len(self._pts), sum(p[1] for p in self._pts) / len(self._pts)]

        # 计算最小外接矩形
        rect = cv2.minAreaRect(self._pts)
        center, size, angle = rect

        # 获取四个顶点（浮点数坐标）
        box = cv2.boxPoints(rect)   # shape (4, 2)

        # 按 x 坐标排序，分成左列和右列
        sorted_by_x = box[numpy.argsort(box[:, 0])]
        left_pts = sorted_by_x[:2]   # x 较小的两个
        right_pts = sorted_by_x[2:]  # x 较大的两个

        # 每列按 y 坐标排序，上为 top，下为 bottom
        left_pts_sorted = left_pts[numpy.argsort(left_pts[:, 1])]
        right_pts_sorted = right_pts[numpy.argsort(right_pts[:, 1])]

        # 赋值角点
        self._topleft_point = left_pts_sorted[0].tolist()
        self._bottomleft_point = left_pts_sorted[1].tolist()
        self._topright_point = right_pts_sorted[0].tolist()
        self._bottomright_point = right_pts_sorted[1].tolist()

        self._image = image
        self._text = None
        self._left = numpy.min( self._pts[:, 0])
        self._right = numpy.max( self._pts[:, 0])
        self._bottom = numpy.max(self._pts[:, 1])
        self._top = numpy.min(self._pts[:, 1])
        self._line_height = max(1.0, ((self._bottomright_point[1] + self._bottomleft_point[1] - 
                                       self._topleft_point[1] - self._topright_point[1])) / 4.0)
        
    def image(self):            return self._image
    def text(self):             return self._text
    def points(self):           return self._pts
    def top_bound(self):        return self._top
    def bottom_bound(self):     return self._bottom
    def left_bound(self):       return self._left
    def right_bound(self):      return self._right
    def topleft_point(self):    return self._topleft_point
    def topright_point(self):   return self._topright_point
    def bottomleft_point(self): return self._bottomleft_point
    def bottomright_point(self):return self._bottomright_point
    def center_point(self):     return self._center
    def line_height(self):      return self._line_height

    def set_image(self, image): 
        self._image = image
    def set_text(self, text): 
        self._text = text

class read_paragraph:
    """ 
    表示一个段落，由多个 read_snippet 组成。
    自动维护聚合属性：边界框、中心点、平均行高、合并文本等。
    文本以列表形式存储，便于单独插入或修改。
    """
    def __init__(self):
        self._snippets = []          # 存储 snippet 对象
        self._top = None
        self._bottom = None
        self._left = None
        self._right = None
        self._center = None
        self._line_height = None
        self._text = None            # 合并后的字符串（兼容旧代码）
        self._texts = []             # 每个 snippet 的文本列表（按阅读顺序）
        self._topleft_point = None
        self._topright_point = None
        self._bottomleft_point = None
        self._bottomright_point = None

    def append(self, snippet):
        self._snippets.append(snippet)
        self._recalc()

    def extend(self, snippets):
        self._snippets.extend(snippets)
        self._recalc()

    def _recalc(self):
        """重新计算所有聚合属性"""
        if not self._snippets:
            self._top = self._bottom = self._left = self._right = None
            self._center = None
            self._line_height = None
            self._text = None
            self._texts = []
            self._topleft_point = self._topright_point = self._bottomleft_point = self._bottomright_point = None
            return

        # 1. 边界框 (包围所有 snippet)
        tops = [s.top_bound() for s in self._snippets]
        bottoms = [s.bottom_bound() for s in self._snippets]
        lefts = [s.left_bound() for s in self._snippets]
        rights = [s.right_bound() for s in self._snippets]
        self._top = min(tops)
        self._bottom = max(bottoms)
        self._left = min(lefts)
        self._right = max(rights)

        # 2. 四个角点 (基于外接矩形)
        self._topleft_point = (self._left, self._top)
        self._topright_point = (self._right, self._top)
        self._bottomleft_point = (self._left, self._bottom)
        self._bottomright_point = (self._right, self._bottom)

        # 3. 中心点 (外接矩形中心)
        self._center = ((self._left + self._right) / 2, (self._top + self._bottom) / 2)

        # 4. 平均行高 (使用中位数更鲁棒)
        heights = [s.line_height() for s in self._snippets]
        heights.sort()
        n = len(heights)
        if n % 2 == 1:
            self._line_height = heights[n // 2]
        else:
            self._line_height = (heights[n // 2 - 1] + heights[n // 2]) / 2

        # 5. 合并文本 (按阅读顺序: 先上后下, 同 top 则左到右)
        sorted_snippets = sorted(self._snippets, key=lambda s: (s.top_bound(), s.left_bound()))
        self._texts = [s.text() or "" for s in sorted_snippets]
        self._text = " ".join(self._texts).strip()

    # ----- 属性访问器 (与 read_snippet 兼容) -----
    def image(self): return self._snippets[0].image() if self._snippets else None

    def text(self):
        """返回合并后的完整文本"""
        return self._text

    def texts(self):
        """返回每个 snippet 的文本列表（可修改）"""
        return self._texts

    def points(self):
        """返回四个角点 (用于绘图)"""
        return numpy.array([
            self._topleft_point,
            self._topright_point,
            self._bottomright_point,
            self._bottomleft_point
        ], dtype=numpy.float32)

    def top_bound(self): return self._top
    def bottom_bound(self): return self._bottom
    def left_bound(self): return self._left
    def right_bound(self): return self._right
    def topleft_point(self): return self._topleft_point
    def topright_point(self): return self._topright_point
    def bottomleft_point(self): return self._bottomleft_point
    def bottomright_point(self): return self._bottomright_point
    def center_point(self): return self._center
    def line_height(self): return self._line_height

    # ----- 其他辅助方法 -----
    def __len__(self): return len(self._snippets)
    def __iter__(self): return iter(self._snippets)
    def __getitem__(self, idx): return self._snippets[idx]
    def snippets(self): return self._snippets