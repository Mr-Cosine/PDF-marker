"""
interactive pdf rotation
"""

import tkinter
from PIL import ImageTk, Image
import numpy
from page_elements import pdf_page

def NParray_to_PILimage(numpy_array):
    return Image.fromarray(numpy_array)

def PILimage_to_NParray(image):
    return numpy.array(image)

class rotate_image_window:
    _pages = []
    _active_page_num = 0

    def __init__(self, master, title, pages):
        self._pages = pages #PIL image object + orientation + page number
        self._active_page_num = 0

        # 创建顶层窗口
        self.window = tkinter.Toplevel(master)
        self.window.title(title)
        self.window.geometry("540x720")
        self.window.resizable(False, False)

        # 绑定键盘快捷键
        self.window.bind("<Left>", self.rotate_left)
        self.window.bind("<Right>", self.rotate_right)
        self.window.bind("<Up>", self.page_up)
        self.window.bind("<Down>", self.page_dn)
        self.window.bind("<Return>", self.page_dn)
        self.window.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.window.focus_set()  # 确保窗口捕获键盘事件

        # 创建界面组件
        self.create_widgets()
        self.window.update()
        self.update_display()

    def rotate_left(self):
        self._pages[self._active_page_num]["rotation"] += 90
        if self._pages[self._active_page_num]["rotation"] >= 360: self._pages[self._active_page_num]["rotation"] -= 360
        self.update_display()
    def rotate_right(self):
        self._pages[self._active_page_num]["rotation"] -= 90
        if self._pages[self._active_page_num]["rotation"] < 0: self._pages[self._active_page_num]["rotation"] += 360
        self.update_display()

    def page_up(self):
        self._active_page_num = max(self._active_page_num - 1, 0)
        self.update_display()
    def page_dn(self):
        self._active_page_num = min(self._active_page_num + 1, len(self._pages) - 1)
        self.update_display()

    def quit_app(self):
        self.window.destroy()
        self.window.master.quit() 

    def update_display(self):
        # 获取当前页数据和旋转角度
        active_page = next((page for page in self._pages if page.get("page_num") == self._active_page_num), None)
        if active_page is None: raise ValueError("Missing page(s)")
        img = active_page["image"]
        angle = active_page["rotation"]

        # 旋转图像（使用 PIL）
        rotated = img.rotate(angle, expand=True)

        # 获取 Canvas 当前尺寸
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        # 若 Canvas 尚未布局，使用默认窗口尺寸
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 360
            canvas_height = 360

        # 计算缩放比例，使图像完全放入 Canvas 并保持比例
        img_width, img_height = rotated.size
        ratio = min(canvas_width / img_width, canvas_height / img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)

        # 缩放图像
        resized = rotated.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # 转换为 tkinter PhotoImage
        self.tk_img = ImageTk.PhotoImage(resized)

        # 清空 Canvas 并绘制图像（居中）
        self.canvas.delete("all")
        self.canvas.create_image(
            canvas_width // 2, canvas_height // 2,
            anchor=tkinter.CENTER,
            image=self.tk_img
        )
        # 可选：在角上显示页码
        self.canvas.create_text(
            10, 10, anchor=tkinter.NW,
            text=f"第 {self._active_page_num + 1} / {len(self._pages)} 页",
            fill="red", font=("Arial", 10)
        )

    def create_widgets(self):
        # Main label – top, centered
        lbl1 = tkinter.Label(self.window, text="调整 PDF 页面朝向", font=("Arial", 12))
        lbl1.pack(pady=(10, 5))

        # Container for the two control groups – will be centered
        controls_container = tkinter.Frame(self.window)
        controls_container.pack(pady=5)

        # ---- Rotation controls ----
        rot_frame = tkinter.Frame(controls_container)
        tkinter.Label(rot_frame, text="页面操作", font=("Arial", 10)).pack(pady=2)
        rot_btns = tkinter.Frame(rot_frame)
        rot_btns.pack()
        tkinter.Button(rot_btns, text="←逆时针旋转", command=self.rotate_left).pack(side=tkinter.LEFT, padx=3)
        tkinter.Button(rot_btns, text="→顺时针旋转", command=self.rotate_right).pack(side=tkinter.LEFT, padx=3)
        rot_frame.pack(side=tkinter.LEFT, padx=10)   # side by side with page controls

        # ---- Page navigation ----
        page_frame = tkinter.Frame(controls_container)
        tkinter.Label(page_frame, text="选择页面", font=("Arial", 10)).pack(pady=2)
        page_btns = tkinter.Frame(page_frame)
        page_btns.pack()
        tkinter.Button(page_btns, text="↑上一页", command=self.page_up).pack(side=tkinter.LEFT, padx=3)
        tkinter.Button(page_btns, text="↓下一页", command=self.page_dn).pack(side=tkinter.LEFT, padx=3)
        page_frame.pack(side=tkinter.LEFT, padx=10)

        # ---- Confirm button (below, centered) ----
        quit_frame = tkinter.Frame(self.window)
        quit_frame.pack(pady=10)
        tkinter.Button(quit_frame, text="确认完成", command=self.quit_app).pack()

        # Canvas (occupies remaining space)
        self.canvas = tkinter.Canvas(
                                    self.window, 
                                    bg="gray",
                                    highlightthickness=0,
                                    borderwidth=0
                                    )
        self.canvas.pack(side=tkinter.BOTTOM, fill=tkinter.BOTH, expand=True, padx=0, pady=0)

    def get_rotated(self, pages):
        """Return list of rotated PIL images and their final rotation angles."""
        for item in self._pages:
            img = item["image"]
            page_num = item["page_num"]
            rotation = item["rotation"] % 360
            if rotation != 0: 
                page_2_update = next((page for page in pages if page.page_num == page_num), None)
                if page_2_update is not None:
                    page_2_update.image = PILimage_to_NParray(img.rotate(rotation, expand=True))
                    page_2_update.rotation = rotation
                else:
                    raise ValueError("Missing page(s)")
            else: continue

def show_window(pages): #image: numpy array
    root = tkinter.Tk()
    root.withdraw()
    pages_4_rotate = []
    for page in pages:
        pages_4_rotate.append({"image": NParray_to_PILimage(page.image), "page_num":page.page_num})
    app = rotate_image_window(root, "Adjust page orientation", pages_4_rotate)
    root.mainloop()
    app.get_rotated(pages)
    

def revert_rotation_points(points, angle, orig_shape):
    if angle == 0:
        return points

    h, w = orig_shape
    if angle == 90:
        return [(w - 1 - y, x) for x, y in points] 
    elif angle == 180:
        return [(w - 1 - x, h - 1 - y) for x, y in points]
    elif angle == 270:
        return [(y, h - 1 - x) for x, y in points]
    else:
        return points

if __name__ == "__main__":
    from PIL import ImageDraw
    test_images = []
    for i in range(3):
        img = Image.new('RGB', (300, 200), color=(100 + i*50, 150, 200))
        draw = ImageDraw.Draw(img)
        draw.text((50, 80), f"Page {i+1}", fill='black')
        test_images.append(numpy.array(img))
        
    result = show_window(test_images)
    print("over")
    print([page for page in result])