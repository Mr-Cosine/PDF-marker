"""
interactive pdf rotation
"""

import tkinter
from PIL import ImageTk, Image
import numpy

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

        # create window
        self.window = tkinter.Toplevel(master)
        self.window.title(title)
        self.window.geometry("540x720")
        self.window.resizable(False, False)

        # handle window close event
        self.window.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.window.focus_set()

        # create widgets
        self.create_widgets()
        self.window.update()

        # show initial page
        self.update_display()

    def rotate_left(self):
        active_page = next((page for page in self._pages if page.get("page_num") == self._active_page_num), None)
        active_page["rotation"] += 90
        if active_page["rotation"] >= 360: active_page["rotation"] -= 360
        self.update_display()
    def rotate_right(self):
        active_page = next((page for page in self._pages if page.get("page_num") == self._active_page_num), None)
        active_page["rotation"] -= 90
        if active_page["rotation"] < 0: active_page["rotation"] += 360
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
        active_page = next((page for page in self._pages if page.get("page_num") == self._active_page_num), None)
        if active_page is None: raise ValueError("Missing page(s)")
        img = active_page["image"]
        angle = active_page["rotation"]

        rotated = img.rotate(angle, expand=True)

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 360
            canvas_height = 360

        img_width, img_height = rotated.size
        ratio = min(canvas_width / img_width, canvas_height / img_height)
        new_width = int(img_width * ratio)
        new_height = int(img_height * ratio)

        resized = rotated.resize((new_width, new_height), Image.Resampling.LANCZOS)

        self.tk_img = ImageTk.PhotoImage(resized)

        self.canvas.delete("all")
        self.canvas.create_image(
            canvas_width // 2, canvas_height // 2,
            anchor=tkinter.CENTER,
            image=self.tk_img
        )

        self.canvas.create_text(
            10, 10, anchor=tkinter.NW,
            text=f"Page {self._active_page_num + 1} / {len(self._pages)}",
            fill="red", font=("Arial", 10)
        )

    def create_widgets(self):
        # Main label – top, centered
        lbl1 = tkinter.Label(self.window, text="Adjust PDF Page Orientation", font=("Arial", 12))
        lbl1.pack(pady=(10, 5))

        # Container for the two control groups – will be centered
        controls_container = tkinter.Frame(self.window)
        controls_container.pack(pady=5)

        # Rotation controls
        rot_frame = tkinter.Frame(controls_container)
        tkinter.Label(rot_frame, text="Page Operations", font=("Arial", 10)).pack(pady=2)
        rot_btns = tkinter.Frame(rot_frame)
        rot_btns.pack()
        tkinter.Button(rot_btns, text="← To Left", command=self.rotate_left).pack(side=tkinter.LEFT, padx=3)
        tkinter.Button(rot_btns, text="→ To Right", command=self.rotate_right).pack(side=tkinter.LEFT, padx=3)
        rot_frame.pack(side=tkinter.LEFT, padx=10)   # side by side with page controls

        # Page navigation
        page_frame = tkinter.Frame(controls_container)
        tkinter.Label(page_frame, text="Select Page", font=("Arial", 10)).pack(pady=2)
        page_btns = tkinter.Frame(page_frame)
        page_btns.pack()
        tkinter.Button(page_btns, text="↑Previous Page", command=self.page_up).pack(side=tkinter.LEFT, padx=3)
        tkinter.Button(page_btns, text="↓Next Page", command=self.page_dn).pack(side=tkinter.LEFT, padx=3)
        page_frame.pack(side=tkinter.LEFT, padx=10)

        # Confirm button (below, centered)
        quit_frame = tkinter.Frame(self.window)
        quit_frame.pack(pady=10)
        tkinter.Button(quit_frame, text="Complete", command=self.quit_app).pack()

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

def show_window(pages): #pdf_page object
    root = tkinter.Tk()
    root.withdraw()
    pages_4_rotate = []
    for page in pages:
        pages_4_rotate.append({
            "image": NParray_to_PILimage(page.image), # Image is a numpy array
            "page_num":page.page_num, 
            "rotation": 0
            })
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