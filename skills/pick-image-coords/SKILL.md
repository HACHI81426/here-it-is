---
name: pick-image-coords
description: Identify elements in images or screenshots (buttons, input boxes, icons, text regions) and get precise original-image coordinates for automation scripts. Use when the user mentions OCR, 取坐标, 识别图片元素, 按钮位置, 截图分析, element positions, or wants coordinates of UI elements in an image.
---

# 图片元素识别与坐标选取

## 概览

识别图片/截图中的界面元素，并在需要时给出精确的原图坐标。坐标通过“选点/拉框”工具（tkinter GUI）由用户点选获得，适合人机协作与自动化脚本定位。工具随技能自带，也可以使用本机标准目录里的最新版。

## 流程

1. **看图片**：用 `view_image` 查看图片，识别并列出元素（名称、类型、大致位置）。
2. **判断是否需要精确坐标**：
   - 用户只要识别内容 → 直接文字描述元素，结束。
   - 用户要坐标或要写自动化脚本 → 进入第 3 步。
3. **启动选点工具**（脚本自动找工具，无需手动指定路径）：
   ```
   python <skill>/scripts/launch_pick_coords.py <图片路径>
   ```
   等待模式（用户关闭窗口后自动打印坐标）：
   ```
   python <skill>/scripts/launch_pick_coords.py <图片路径> --wait
   ```
   也可让用户手动启动：双击工具目录里的 `start.bat`，把图片拖进窗口。
4. **告知用户操作**：左键取点、`r` 拉矩形、右键撤销、滚轮缩放、中键平移、列表选中后填写区域说明、`q`/`ESC` 退出。
5. **拿到输出**（等待模式的 stdout，或用户粘贴）后整理成结构化结果，必须带上坐标零点。

## 坐标约定（必须遵守）

- 零点：右侧“全局坐标定位方式”5 个按钮（左上/右上/左下/右下/中心，默认左上）只决定零点位置。
- 轴方向固定：x 向右增大（越靠右越大），y 向上增大（越靠上越大）。
- 输出坐标是原图坐标，按所选零点换算；缩放和平移不改变数值。
- 默认左上零点时 y 为负；选“左下”时图片内坐标全为正。
- 回报结果时必须注明坐标零点，否则坐标无法被脚本正确使用。

输出示例：

```text
坐标零点: 左下
最终坐标: [(532, 481), (642, 379)]
最终矩形: [(120, 589, 360, 711)]
形状说明: {'点1': '起始点', '矩形1': '登录按钮区域'}
```

## 工具查找规则（launch_pick_coords.py）

按以下顺序找工具，取版本号最高的文件夹：

1. 命令行 `--tool-root` 指定目录
2. 本机标准目录 `E:\01.Codex\02.软件输出\选点工具`
3. 技能自带目录 `<skill>/assets/coords-tool`

Python 查找顺序：`--python` 指定 → 已知本机路径 → 当前解释器 → PATH 里的 `python`，要求带 Pillow 与 tkinter；找不到时脚本会打印安装提示。

## 工具信息与维护

- 工具功能：取点、拉矩形、画圆形（按 c）、一键复制全部坐标和备注到剪贴板、400x400 放大镜（±100px）、形状列表、区域说明、删除选中、选中高亮、滚轮缩放、中键平移。
- 依赖：Python 3.9+（带 Tk）和 Pillow；启动闪退时先 `pip install -r <工具目录>/requirements.txt`。
- 工具升级：本机标准目录按版本号递增保存（旧版本保留），脚本自动用最新版。
- 分享技能时，把最新工具版本同步复制到 `<skill>/assets/coords-tool/`，保证朋友解压即用。

## 常见用户请求示例

- “识别这张截图里的按钮和输入框” → 视觉识别并描述。
- “给我这个按钮的坐标” → 启动工具取点/拉框，回报坐标和零点。
- “OCR 定位元素” → 先识别文字/元素，再用工具取精确坐标。
