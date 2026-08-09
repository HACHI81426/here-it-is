# Author: 8!!
# GitHub: https://github.com/HACHI81426

"""选点/拉框工具：打开图片，鼠标取点或拉矩形，输出原图坐标，并可为每个形状添加说明。

用法: python pick_coords.py <图片路径>

操作:
- 左键点击: 取一个点（取点模式）
- r / p: 切换矩形模式 / 取点模式
- c: 切换圆形模式，左键从圆心拖到边缘画圆
- 矩形模式下左键拖拽: 拉矩形，松开后记录矩形坐标
- 右键点击: 撤销上一个形状
- 列表上方“删除选中”按钮或 Delete 键: 删除列表中选中的形状
- 面板顶部“复制全部（坐标+备注）”按钮: 把当前所有选区坐标和备注复制到剪贴板
- 滚轮: 以鼠标位置为中心缩放画面（按住中键拖动可平移）
- q 或 ESC: 退出

界面:
- 右侧列表显示所有已取的形状，选中后可在下方文本框填写该区域说明
- 放大镜窗口（400x400）实时显示光标周围 ±100px 的放大画面，中心有十字线辅助定位
- 右侧“全局坐标定位方式”5 个按钮（左上/右上/左下/右下/中心）只决定坐标轴零点，坐标轴方向固定：x 向右增大、y 向上增大
"""

__version__ = "1.12.0"

import math
import sys
from pathlib import Path

import tkinter as tk
from PIL import Image, ImageTk


class PickCoords:
    MAG_RADIUS = 100      # 放大镜显示光标周围 ±100px（原图坐标）
    MAG_SIZE = 400        # 放大镜窗口边长 400px
    MODE_POINT = "point"
    MODE_RECT = "rect"
    MODE_CIRCLE = "circle"

    def __init__(self, image_path: str):
        self.image_path = image_path
        self.img = Image.open(image_path).convert("RGB")
        self.w, self.h = self.img.size

        self.root = tk.Tk()
        self.root.title(f"在这里 Here it is v{__version__} - {Path(image_path).name} ({self.w}x{self.h})")

        # 按屏幕适配缩放显示
        max_w, max_h = 1000, 750
        scale = min(max_w / self.w, max_h / self.h, 1.0)
        self.scale = scale
        self.min_scale = max(scale * 0.5, 0.05)
        self.max_scale = min(40.0, 6000.0 / self.w, 6000.0 / self.h)
        self.pan_x = 0.0
        self.pan_y = 0.0
        self._pan_last = None
        disp_w, disp_h = int(self.w * scale), int(self.h * scale)
        self.display = self.img.resize((disp_w, disp_h), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(self.display)

        # ---- 主体布局：左侧图片，右侧面板 ----
        main = tk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(main, bg="black")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left.pack_propagate(False)
        left.config(width=disp_w, height=disp_h)

        self.canvas = tk.Canvas(left, width=disp_w, height=disp_h, bg="black")
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)

        right = tk.Frame(main, width=280)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        self.copy_btn = tk.Button(right, text="复制全部（坐标+备注）", font=("Microsoft YaHei", 10),
                                  command=self.copy_all_to_clipboard)
        self.copy_btn.pack(fill=tk.X, padx=6, pady=(6, 0))

        tk.Label(right, text="全局坐标定位方式", font=("Microsoft YaHei", 10)).pack(anchor="w", padx=6, pady=(6, 2))
        origin_row = tk.Frame(right)
        origin_row.pack(fill=tk.X, padx=6, pady=(0, 4))
        self.origin_btns: dict[str, tk.Button] = {}
        for mode in ("左上", "右上", "左下", "右下", "中心"):
            b = tk.Button(origin_row, text=mode, font=("Microsoft YaHei", 9),
                          command=lambda m=mode: self.set_origin(m))
            b.pack(side=tk.LEFT, padx=1, expand=True, fill=tk.X)
            self.origin_btns[mode] = b

        tk.Label(right, text="形状列表", font=("Microsoft YaHei", 10)).pack(anchor="w", padx=6, pady=(6, 2))
        btn_row = tk.Frame(right)
        btn_row.pack(fill=tk.X, padx=6, pady=(0, 4))
        self.delete_btn = tk.Button(btn_row, text="删除选中", font=("Microsoft YaHei", 10),
                                    command=self.on_delete)
        self.delete_btn.pack(side=tk.RIGHT)
        self.listbox = tk.Listbox(right, width=36, font=("Consolas", 10))
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=6)
        self.listbox.bind("<<ListboxSelect>>", self.on_select)
        self.listbox.bind("<Delete>", lambda e: self.on_delete())

        tk.Label(right, text="该区域说明：", font=("Microsoft YaHei", 10)).pack(anchor="w", padx=6, pady=(6, 2))
        self.desc_var = tk.StringVar()
        self.desc_entry = tk.Entry(right, textvariable=self.desc_var, font=("Microsoft YaHei", 10))
        self.desc_entry.pack(fill=tk.X, padx=6, pady=(0, 6))
        self.desc_var.trace_add("write", self.on_desc_change)

        # ---- 底部信息栏 ----
        self.info = tk.Label(self.root, text="", font=("Microsoft YaHei", 10))
        self.info.pack(fill=tk.X)
        self.coords_label = tk.Label(self.root, text="", font=("Consolas", 11), anchor="w")
        self.coords_label.pack(fill=tk.X)

        # ---- 状态 ----
        self.shapes: list[dict] = []          # {"kind": "point"/"rect", "coords": tuple, "desc": str}
        self.selected = None                  # 当前选中形状的下标
        self.origin = "左上"                  # 坐标零点（整张原图的角或中心）
        self.mode = self.MODE_POINT
        self._loading_desc = False
        self.drag_start = None                # 矩形拖拽起点（显示坐标）
        self.drag_item = None                 # 预览矩形 canvas item id
        self.mag_photo = None

        # ---- 事件 ----
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<Button-2>", self.on_pan_start)
        self.canvas.bind("<B2-Motion>", self.on_pan_move)
        self.canvas.bind("<ButtonRelease-2>", self.on_pan_end)
        self.root.bind("<p>", lambda e: self.switch_mode(self.MODE_POINT))
        self.root.bind("<P>", lambda e: self.switch_mode(self.MODE_POINT))
        self.root.bind("<r>", lambda e: self.switch_mode(self.MODE_RECT))
        self.root.bind("<R>", lambda e: self.switch_mode(self.MODE_RECT))
        self.root.bind("<c>", lambda e: self.switch_mode(self.MODE_CIRCLE))
        self.root.bind("<C>", lambda e: self.switch_mode(self.MODE_CIRCLE))
        self.root.bind("<q>", lambda e: self.quit_app())
        self.root.bind("<Escape>", lambda e: self.quit_app())
        self.root.bind("<Delete>", self.on_delete_key)

        self.set_mode(self.MODE_POINT)
        self.update_origin_buttons()
        self.update_label()
        self.setup_magnifier()

    # ---------- 坐标零点 ----------
    def set_origin(self, mode: str) -> None:
        self.origin = mode
        self.update_origin_buttons()
        self.redraw_all()
        self.update_label()

    def update_origin_buttons(self) -> None:
        for mode, btn in self.origin_btns.items():
            btn.config(relief=tk.SUNKEN if mode == self.origin else tk.RAISED)

    def convert(self, x: int, y: int) -> tuple[int, int]:
        """把左上为原点的原始坐标换算成当前零点下的坐标。

        坐标轴方向固定：x 向右增大、y 向上增大（越靠右越大、越靠上越大）。
        零点位置由 self.origin 决定。
        """
        if self.origin in ("左上", "左下"):
            ox = 0
        elif self.origin in ("右上", "右下"):
            ox = self.w - 1
        else:
            ox = self.w // 2
        if self.origin in ("左上", "右上"):
            oy = 0
        elif self.origin in ("左下", "右下"):
            oy = self.h - 1
        else:
            oy = self.h // 2
        return x - ox, oy - y

    def convert_rect(self, rect: tuple) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = rect
        ax1, ay1 = self.convert(x1, y1)
        ax2, ay2 = self.convert(x2, y2)
        return min(ax1, ax2), min(ay1, ay2), max(ax1, ax2), max(ay1, ay2)

    # ---------- 模式 ----------
    def set_mode(self, mode: str) -> None:
        self.mode = mode
        if mode == self.MODE_POINT:
            self.info.config(text="模式：取点 | 左键取点 | 右键撤销 | 滚轮缩放 | 中键平移 | r=矩形 | c=圆形 | p=取点 | q/ESC 退出")
        elif mode == self.MODE_RECT:
            self.info.config(text="模式：矩形 | 左键拖拽拉矩形 | 右键撤销 | 滚轮缩放 | 中键平移 | r=矩形 | p=取点 | q/ESC 退出")
        else:
            self.info.config(text="模式：圆形 | 左键从圆心拖到边缘 | 右键撤销 | 滚轮缩放 | 中键平移 | r=矩形 | c=圆形 | p=取点 | q/ESC 退出")

    def switch_mode(self, mode: str) -> None:
        # 正在文本框输入说明时，按键留给输入框
        if self.root.focus_get() is self.desc_entry:
            return
        self.set_mode(mode)

    def quit_app(self) -> None:
        if self.root.focus_get() is self.desc_entry:
            return
        self.root.destroy()

    def on_delete_key(self, event=None) -> None:
        # 正在文本框输入说明时，Delete 键留给输入框
        if self.root.focus_get() is self.desc_entry:
            return
        self.on_delete()

    # ---------- 坐标换算 ----------
    def to_orig(self, dx: int, dy: int) -> tuple[int, int]:
        ox, oy = int(dx / self.scale), int(dy / self.scale)
        return min(max(ox, 0), self.w - 1), min(max(oy, 0), self.h - 1)

    # ---------- 视图缩放/平移 ----------
    def update_placement(self) -> None:
        self.canvas.place(relx=0.5, rely=0.5, x=self.pan_x, y=self.pan_y, anchor="center")

    def set_scale(self, s: float) -> None:
        self.scale = s
        disp_w = max(1, int(self.w * s))
        disp_h = max(1, int(self.h * s))
        self.canvas.config(width=disp_w, height=disp_h)
        self.display = self.img.resize((disp_w, disp_h), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(self.display)

    def on_wheel(self, event) -> None:
        factor = 1.2 ** (event.delta / 120)
        self.zoom_at(event.x, event.y, factor)

    def zoom_at(self, cx: float, cy: float, factor: float) -> None:
        s = self.scale
        new_scale = min(max(s * factor, self.min_scale), self.max_scale)
        if abs(new_scale - s) < 1e-9:
            return
        ox = cx / s
        oy = cy / s
        cw = max(1, int(self.w * s))
        ch = max(1, int(self.h * s))
        self.set_scale(new_scale)
        cw2 = max(1, int(self.w * new_scale))
        ch2 = max(1, int(self.h * new_scale))
        # 保持鼠标下的原图点不动
        self.pan_x = self.pan_x + cx - cw / 2 - ox * new_scale + cw2 / 2
        self.pan_y = self.pan_y + cy - ch / 2 - oy * new_scale + ch2 / 2
        self.update_placement()
        self.redraw_all()

    def on_pan_start(self, event) -> None:
        self._pan_last = (event.x, event.y)
        self.canvas.config(cursor="fleur")

    def on_pan_move(self, event) -> None:
        if self._pan_last is None:
            return
        dx = event.x - self._pan_last[0]
        dy = event.y - self._pan_last[1]
        self._pan_last = (event.x, event.y)
        self.pan_x += dx
        self.pan_y += dy
        self.update_placement()
        self.redraw_all()

    def on_pan_end(self, event) -> None:
        self._pan_last = None
        self.canvas.config(cursor="")

    # ---------- 鼠标事件 ----------
    def on_press(self, event) -> None:
        self.canvas.focus_set()
        ox, oy = self.to_orig(event.x, event.y)
        self.update_magnifier(ox, oy)
        if self.mode == self.MODE_POINT:
            self.add_shape("point", (ox, oy))
        else:
            self.drag_start = (event.x, event.y)
            if self.mode == self.MODE_RECT:
                self.drag_item = self.canvas.create_rectangle(
                    event.x, event.y, event.x, event.y,
                    outline="#1e90ff", width=2, dash=(4, 2),
                )
            else:
                self.drag_item = self.canvas.create_oval(
                    event.x, event.y, event.x, event.y,
                    outline="#1e90ff", width=2, dash=(4, 2),
                )

    def on_drag(self, event) -> None:
        ox, oy = self.to_orig(event.x, event.y)
        self.update_magnifier(ox, oy)
        if self.mode == self.MODE_RECT and self.drag_start is not None:
            x0, y0 = self.drag_start
            self.canvas.coords(self.drag_item, x0, y0, event.x, event.y)
        elif self.mode == self.MODE_CIRCLE and self.drag_start is not None:
            x0, y0 = self.drag_start
            r = math.hypot(event.x - x0, event.y - y0)
            self.canvas.coords(self.drag_item, x0 - r, y0 - r, x0 + r, y0 + r)

    def on_release(self, event) -> None:
        ox, oy = self.to_orig(event.x, event.y)
        self.update_magnifier(ox, oy)
        if self.mode not in (self.MODE_RECT, self.MODE_CIRCLE) or self.drag_start is None:
            return
        if self.drag_item is not None:
            self.canvas.delete(self.drag_item)
            self.drag_item = None
        x1, y1 = self.to_orig(self.drag_start[0], self.drag_start[1])
        x2, y2 = ox, oy
        sx, sy = self.drag_start
        self.drag_start = None
        if self.mode == self.MODE_RECT:
            # 几乎没有拖动时视为误触，忽略
            if abs(x2 - x1) < 2 and abs(y2 - y1) < 2:
                return
            self.add_shape("rect", (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
        else:
            r = math.hypot(event.x - sx, event.y - sy) / self.scale
            if r < 2:
                return
            self.add_shape("circle", (x1, y1, round(r)))

    def on_motion(self, event) -> None:
        self.update_magnifier(*self.to_orig(event.x, event.y))

    def on_right_click(self, event) -> None:
        self.canvas.focus_set()
        if not self.shapes:
            return
        self.shapes.pop()
        self.selected = None
        self.refresh_list()
        self.load_desc()
        self.redraw_all()
        self.update_label()

    def on_delete(self) -> None:
        if self.selected is None or not (0 <= self.selected < len(self.shapes)):
            return
        self.shapes.pop(self.selected)
        self.selected = None
        self.refresh_list()
        self.load_desc()
        self.redraw_all()
        self.update_label()

    # ---------- 形状管理 ----------
    def add_shape(self, kind: str, coords: tuple) -> None:
        self.shapes.append({"kind": kind, "coords": coords, "desc": ""})
        self.refresh_list()
        idx = len(self.shapes) - 1
        self.listbox.selection_clear(0, tk.END)
        self.listbox.selection_set(idx)
        self.listbox.see(idx)
        self.selected = idx
        self.load_desc()
        self.redraw_all()
        self.update_label()

    def refresh_list(self) -> None:
        self.listbox.delete(0, tk.END)
        p = r = c = 0
        for s in self.shapes:
            if s["kind"] == "point":
                p += 1
                label = f"点{p}"
            elif s["kind"] == "rect":
                r += 1
                label = f"矩形{r}"
            else:
                c += 1
                label = f"圆形{c}"
            if s["desc"]:
                label += f" ｜ {s['desc']}"
            self.listbox.insert(tk.END, label)
        if self.selected is not None and 0 <= self.selected < len(self.shapes):
            self.listbox.selection_set(self.selected)

    def on_select(self, event=None) -> None:
        sel = self.listbox.curselection()
        self.selected = sel[0] if sel else None
        self.load_desc()
        self.redraw_all()

    def load_desc(self) -> None:
        self._loading_desc = True
        if self.selected is not None and 0 <= self.selected < len(self.shapes):
            self.desc_var.set(self.shapes[self.selected]["desc"])
        else:
            self.desc_var.set("")
        self._loading_desc = False

    def on_desc_change(self, *_args) -> None:
        if self._loading_desc or self.selected is None:
            return
        if 0 <= self.selected < len(self.shapes):
            self.shapes[self.selected]["desc"] = self.desc_var.get()
            self.refresh_list()
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(self.selected)

    # ---------- 绘制 ----------
    def redraw_all(self) -> None:
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        for idx, s in enumerate(self.shapes):
            is_selected = idx == self.selected
            if s["kind"] == "point":
                x, y = s["coords"]
                dx, dy = int(x * self.scale), int(y * self.scale)
                if is_selected:
                    self.canvas.create_oval(dx - 4, dy - 4, dx + 4, dy + 4, fill="#ff00ff", outline="white", width=2)
                else:
                    self.canvas.create_oval(dx - 3, dy - 3, dx + 3, dy + 3, fill="#1e90ff", outline="yellow", width=2)
                cx, cy = self.convert(x, y)
                self.canvas.create_text(
                    dx + 6, dy - 6, text=f"({cx},{cy})",
                    fill="white" if is_selected else "yellow",
                    font=("Consolas", 9), anchor="w",
                )
            else:
                if s["kind"] == "rect":
                    x1, y1, x2, y2 = s["coords"]
                    dx1, dy1 = int(x1 * self.scale), int(y1 * self.scale)
                    dx2, dy2 = int(x2 * self.scale), int(y2 * self.scale)
                    if is_selected:
                        self.canvas.create_rectangle(dx1, dy1, dx2, dy2, outline="#ff00ff", width=3)
                    else:
                        self.canvas.create_rectangle(dx1, dy1, dx2, dy2, outline="#1e90ff", width=2)
                    c1, c2, c3, c4 = self.convert_rect(s["coords"])
                    self.canvas.create_text(
                        dx1 + 4, dy1 - 4, text=f"({c1},{c2})-({c3},{c4})",
                        fill="white" if is_selected else "cyan",
                        font=("Consolas", 9), anchor="w",
                    )
                else:
                    cx, cy, r = s["coords"]
                    dcx, dcy = int(cx * self.scale), int(cy * self.scale)
                    dr = int(r * self.scale)
                    if is_selected:
                        self.canvas.create_oval(dcx - dr, dcy - dr, dcx + dr, dcy + dr,
                                                outline="#ff00ff", width=3)
                    else:
                        self.canvas.create_oval(dcx - dr, dcy - dr, dcx + dr, dcy + dr,
                                                outline="#1e90ff", width=2)
                    tx, ty = self.convert(cx, cy)
                    self.canvas.create_text(
                        dcx + 4, dcy - 4, text=f"({tx},{ty}) r={r}",
                        fill="white" if is_selected else "cyan",
                        font=("Consolas", 9), anchor="w",
                    )

    def update_label(self) -> None:
        parts = []
        points = [s["coords"] for s in self.shapes if s["kind"] == "point"]
        rects = [s["coords"] for s in self.shapes if s["kind"] == "rect"]
        circles = [s["coords"] for s in self.shapes if s["kind"] == "circle"]
        if points:
            parts.append("点: " + "  ".join(f"({cx},{cy})" for cx, cy in (self.convert(*p) for p in points)))
        if rects:
            parts.append("矩形: " + "  ".join(
                f"({c1},{c2})-({c3},{c4})" for c1, c2, c3, c4 in (self.convert_rect(r) for r in rects)))
        if circles:
            labels = []
            for cx, cy, r in circles:
                tx, ty = self.convert(cx, cy)
                labels.append(f"({tx},{ty}) r={r}")
            parts.append("圆形: " + "  ".join(labels))
        self.coords_label.config(text="    ".join(parts))

    def copy_all_to_clipboard(self) -> None:
        origin, points, rects, circles, descs = self.build_output()
        lines = [f"坐标零点: {origin}"]
        lines.append(f"最终坐标: {points}")
        lines.append(f"最终矩形: {rects}")
        lines.append(f"最终圆形: {circles}")
        if descs:
            lines.append(f"形状说明: {descs}")
        text = "\n".join(lines)
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.copy_btn.config(text="已复制 ✓")
        self.root.after(1500, lambda: self.copy_btn.config(text="复制全部（坐标+备注）"))

    # ---------- 放大镜 ----------
    def setup_magnifier(self) -> None:
        self.mag = tk.Toplevel(self.root)
        self.mag.title("放大镜")
        self.mag.resizable(False, False)
        self.mag_canvas = tk.Canvas(
            self.mag, width=self.MAG_SIZE, height=self.MAG_SIZE,
            bg="black", highlightthickness=0,
        )
        self.mag_canvas.pack()
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + self.root.winfo_width() + 8
        y = self.root.winfo_rooty()
        self.mag.geometry(f"+{x}+{y}")
        self.update_magnifier(self.w // 2, self.h // 2)

    def update_magnifier(self, ox: int, oy: int) -> None:
        try:
            if not self.mag.winfo_exists():
                return
        except tk.TclError:
            return
        r = self.MAG_RADIUS
        cx, cy = min(max(ox, 0), self.w - 1), min(max(oy, 0), self.h - 1)
        x0, y0 = cx - r, cy - r
        x1, y1 = cx + r, cy + r
        region = Image.new("RGB", (r * 2, r * 2), (0, 0, 0))
        region.paste(
            self.img.crop((max(0, x0), max(0, y0), min(self.w, x1), min(self.h, y1))),
            (max(0, -x0), max(0, -y0)),
        )
        zoom = region.resize((self.MAG_SIZE, self.MAG_SIZE), Image.NEAREST)
        self.mag_photo = ImageTk.PhotoImage(zoom)
        self.mag_canvas.delete("all")
        self.mag_canvas.create_image(0, 0, anchor="nw", image=self.mag_photo)
        mid = self.MAG_SIZE // 2
        self.mag_canvas.create_line(mid, 0, mid, self.MAG_SIZE, fill="#ff3b30")
        self.mag_canvas.create_line(0, mid, self.MAG_SIZE, mid, fill="#ff3b30")
        self.mag_canvas.create_rectangle(0, 0, self.MAG_SIZE, self.MAG_SIZE, outline="#888888")

    # ---------- 输出 ----------
    def build_output(self) -> tuple:
        points = [self.convert(*s["coords"]) for s in self.shapes if s["kind"] == "point"]
        rects = [self.convert_rect(s["coords"]) for s in self.shapes if s["kind"] == "rect"]
        circles = []
        descs = {}
        p = r = c = 0
        for s in self.shapes:
            if s["kind"] == "point":
                p += 1
                key = f"点{p}"
            elif s["kind"] == "rect":
                r += 1
                key = f"矩形{r}"
            else:
                c += 1
                key = f"圆形{c}"
                cx, cy, rad = s["coords"]
                tx, ty = self.convert(cx, cy)
                circles.append((tx, ty, rad))
            if s["desc"]:
                descs[key] = s["desc"]
        return self.origin, points, rects, circles, descs

    def run(self) -> None:
        self.root.mainloop()
        origin, points, rects, circles, descs = self.build_output()
        print("坐标零点:", origin)
        print("最终坐标:", points)
        print("最终矩形:", rects)
        print("最终圆形:", circles)
        if descs:
            print("形状说明:", descs)


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "screen.png"
    PickCoords(path).run()


if __name__ == "__main__":
    main()
