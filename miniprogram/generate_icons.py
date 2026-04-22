#!/usr/bin/env python3
"""
生成微信小程序 TabBar 图标
使用 PIL/Pillow 绘制简单的几何图标 (81x81px, RGBA)
"""

import os
import math
from PIL import Image, ImageDraw

# 配置
ICON_SIZE = 81
NORMAL_COLOR = (0x88, 0x99, 0xAA, 255)   # 灰色 #8899aa
ACTIVE_COLOR = (0x18, 0xFF, 0xFF, 255)   # 青色 #18ffff
LINE_WIDTH = 3
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")


def create_icon():
    """创建透明背景的 RGBA 图像"""
    return Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))


def draw_market(draw, color):
    """绘制折线图图标 - 3个点连成的上升趋势线"""
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2
    # 坐标轴
    axis_left = 14
    axis_right = 67
    axis_top = 14
    axis_bottom = 67

    # 绘制坐标轴
    draw.line([(axis_left, axis_bottom), (axis_left, axis_top)], fill=color, width=2)
    draw.line([(axis_left, axis_bottom), (axis_right, axis_bottom)], fill=color, width=2)

    # 折线图的三个点（上升趋势）
    points = [
        (axis_left + 10, axis_bottom - 12),
        (cx, axis_top + 20),
        (axis_right - 5, axis_top + 5),
    ]
    draw.line(points, fill=color, width=LINE_WIDTH)

    # 绘制数据点圆点
    r = 3
    for px, py in points:
        draw.ellipse(
            [(px - r, py - r), (px + r, py + r)],
            fill=color, outline=color
        )


def draw_watch(draw, color):
    """绘制眼睛图标 - 椭圆外框 + 内部圆形"""
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2

    # 外部眼睛形状（用多边形近似杏仁形）
    eye_left = 12
    eye_right = 69
    eye_top = 24
    eye_bottom = 57
    mid_y = cy

    # 上眼睑曲线（用多边形近似）
    top_points = []
    bottom_points = []
    steps = 20
    for i in range(steps + 1):
        t = i / steps
        x = eye_left + t * (eye_right - eye_left)
        # 上弧
        dy_top = -math.sin(t * math.pi) * (mid_y - eye_top)
        top_points.append((x, mid_y + dy_top))
        # 下弧
        dy_bottom = math.sin(t * math.pi) * (eye_bottom - mid_y)
        bottom_points.append((x, mid_y + dy_bottom))

    # 合并上下弧形成闭合眼睛轮廓
    eye_outline = top_points + list(reversed(bottom_points))
    draw.polygon(eye_outline, outline=color)

    # 内部圆形（瞳孔）
    pupil_r = 10
    draw.ellipse(
        [(cx - pupil_r, cy - pupil_r), (cx + pupil_r, cy + pupil_r)],
        outline=color, width=LINE_WIDTH
    )
    # 瞳孔中心点
    dot_r = 4
    draw.ellipse(
        [(cx - dot_r, cy - dot_r), (cx + dot_r, cy + dot_r)],
        fill=color
    )


def draw_star(draw, color):
    """绘制五角星图标"""
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2
    outer_r = 28
    inner_r = 12

    points = []
    for i in range(10):
        angle = math.pi / 2 + i * math.pi / 5  # 从顶部开始
        r = outer_r if i % 2 == 0 else inner_r
        x = cx + r * math.cos(angle)
        y = cy - r * math.sin(angle)
        points.append((x, y))

    draw.polygon(points, outline=color, fill=None)


def draw_strategy(draw, color):
    """绘制棋盘/网格图标 - 4个方格"""
    cx, cy = ICON_SIZE // 2, ICON_SIZE // 2
    grid_size = 18
    gap = 4
    total = grid_size * 2 + gap

    start_x = cx - total // 2
    start_y = cy - total // 2

    # 绘制4个方格（2x2网格）
    for row in range(2):
        for col in range(2):
            x = start_x + col * (grid_size + gap)
            y = start_y + row * (grid_size + gap)
            rect = [(x, y), (x + grid_size, y + grid_size)]
            draw.rectangle(rect, outline=color, width=LINE_WIDTH)

    # 在对角方格中添加填充效果（棋盘格样式）
    # 左上和右下填充半透明色
    fill_color = color[:3] + (80,)  # 半透明
    draw.rectangle(
        [(start_x, start_y), (start_x + grid_size, start_y + grid_size)],
        fill=fill_color, outline=color, width=LINE_WIDTH
    )
    x2 = start_x + grid_size + gap
    y2 = start_y + grid_size + gap
    draw.rectangle(
        [(x2, y2), (x2 + grid_size, y2 + grid_size)],
        fill=fill_color, outline=color, width=LINE_WIDTH
    )


# 图标绘制函数映射
ICON_DRAWERS = {
    "market": draw_market,
    "watch": draw_watch,
    "star": draw_star,
    "strategy": draw_strategy,
}


def generate_icon(name, draw_func, color, suffix):
    """生成单个图标文件"""
    img = create_icon()
    draw = ImageDraw.Draw(img)
    draw_func(draw, color)
    filename = f"{name}{suffix}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)
    img.save(filepath, "PNG")
    print(f"  已生成: {filepath}")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"图标输出目录: {OUTPUT_DIR}")
    print(f"图标尺寸: {ICON_SIZE}x{ICON_SIZE}px")
    print()

    for name, draw_func in ICON_DRAWERS.items():
        print(f"[{name}]")
        generate_icon(name, draw_func, NORMAL_COLOR, "")
        generate_icon(name, draw_func, ACTIVE_COLOR, "-active")

    print()
    print("全部图标生成完成！")


if __name__ == "__main__":
    main()
