# -*- coding: utf-8 -*-
"""
截图工具 - 用于截取签到所需的图片素材
支持多步骤签到流程的所有图片截取
"""

import pyautogui
import time
import os
from PIL import ImageGrab

# 创建images目录
os.makedirs('images', exist_ok=True)

# 需要截取的图片列表
IMAGES_TO_CAPTURE = [
    # (文件名, 描述, 是否必须)
    # 主站 x666.me
    ('cf_checkbox', 'CF验证框（勾选框）- 主站', True),
    ('announcement_close', '公告关闭按钮 - 主站', True),
    ('signin_entry', '签到入口按钮 - 主站', True),

    # 签到页 qd.x666.me
    ('spin_button', '开始转动按钮 - 签到页', True),
    ('wheel_confirm', '转盘结果确定按钮 - 签到页', True),

    # 充值页 x666.me/console/topup
    ('redeem_input', '兑换码输入框 - 充值页', True),
    ('redeem_button', '兑换按钮 - 充值页', True),
    ('confirm_button', '确定按钮 - 兑换确认弹窗', True),
    ('success_message', '兑换成功提示（可选）', False),
]


def countdown(seconds):
    """倒计时"""
    for i in range(seconds, 0, -1):
        print(f"  {i}秒后截图...", end='\r')
        time.sleep(1)
    print(" " * 20, end='\r')


def capture_region(name, size=100):
    """截取鼠标周围区域"""
    # 获取鼠标位置
    x, y = pyautogui.position()

    # 截取周围区域
    half = size // 2
    left = max(0, x - half)
    top = max(0, y - half)
    right = x + half
    bottom = y + half

    # 截图
    screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))

    # 保存
    filepath = f'images/{name}.png'
    screenshot.save(filepath)

    print(f"  [√] 已保存: {filepath}")
    print(f"      位置: ({x}, {y}), 大小: {size}x{size}")

    return filepath


def capture_custom_region(name):
    """截取自定义区域（两点定位）"""
    print("  步骤1: 将鼠标移动到目标区域的【左上角】")
    countdown(4)
    x1, y1 = pyautogui.position()
    print(f"  左上角: ({x1}, {y1})")

    print("  步骤2: 将鼠标移动到目标区域的【右下角】")
    countdown(4)
    x2, y2 = pyautogui.position()
    print(f"  右下角: ({x2}, {y2})")

    # 截图
    screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))

    # 保存
    filepath = f'images/{name}.png'
    screenshot.save(filepath)

    print(f"  [√] 已保存: {filepath}")

    return filepath


def capture_by_coordinates(name):
    """通过手动输入坐标截图"""
    print(f"\n  手动输入坐标截图: {name}")
    print("  格式说明:")
    print("    - 输入中心点坐标和大小: x,y,size (如: 500,300,100)")
    print("    - 输入左上角和右下角: x1,y1,x2,y2 (如: 450,250,550,350)")
    print("    - 输入 m 获取当前鼠标位置")

    while True:
        coords = input("\n  请输入坐标: ").strip().lower()

        if coords == 'm':
            x, y = pyautogui.position()
            print(f"  当前鼠标位置: ({x}, {y})")
            continue

        parts = [p.strip() for p in coords.replace(' ', ',').split(',') if p.strip()]

        try:
            if len(parts) == 3:
                # 中心点 + 大小
                cx, cy, size = int(parts[0]), int(parts[1]), int(parts[2])
                half = size // 2
                x1, y1 = cx - half, cy - half
                x2, y2 = cx + half, cy + half
                print(f"  中心: ({cx}, {cy}), 大小: {size}x{size}")

            elif len(parts) == 4:
                # 左上角 + 右下角
                x1, y1, x2, y2 = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
                print(f"  区域: ({x1}, {y1}) - ({x2}, {y2})")

            elif len(parts) == 2:
                # 只输入中心点，默认大小100
                cx, cy = int(parts[0]), int(parts[1])
                size = 100
                half = size // 2
                x1, y1 = cx - half, cy - half
                x2, y2 = cx + half, cy + half
                print(f"  中心: ({cx}, {cy}), 默认大小: {size}x{size}")

            else:
                print("  [!] 格式错误，请重新输入")
                continue

            # 确保坐标有效
            x1, y1 = max(0, x1), max(0, y1)
            if x2 <= x1 or y2 <= y1:
                print("  [!] 坐标无效，右下角必须大于左上角")
                continue

            # 截图
            screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))

            # 保存
            filepath = f'images/{name}.png'
            screenshot.save(filepath)

            print(f"  [√] 已保存: {filepath}")
            print(f"      区域: ({x1}, {y1}) - ({x2}, {y2})")
            print(f"      大小: {x2-x1}x{y2-y1}")

            return filepath

        except ValueError:
            print("  [!] 请输入有效的数字坐标")
            continue


def show_current_images():
    """显示已截取的图片"""
    print("\n已截取的图片:")
    print("-" * 40)

    if not os.path.exists('images'):
        print("  (无)")
        return

    files = [f for f in os.listdir('images') if f.endswith('.png')]
    if not files:
        print("  (无)")
        return

    for f in sorted(files):
        filepath = os.path.join('images', f)
        size = os.path.getsize(filepath)
        print(f"  [√] {f} ({size} bytes)")


def show_missing_images():
    """显示缺失的必要图片"""
    print("\n缺失的必要图片:")
    print("-" * 40)

    missing = []
    for name, desc, required in IMAGES_TO_CAPTURE:
        filepath = f'images/{name}.png'
        if required and not os.path.exists(filepath):
            missing.append((name, desc))
            print(f"  [!] {name}.png - {desc}")

    if not missing:
        print("  (无，所有必要图片已就绪)")

    return missing


def quick_capture_mode():
    """快速截图模式"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                   快速截图模式                            ║
╠══════════════════════════════════════════════════════════╣
║  将鼠标移动到目标元素中心，等待自动截图                    ║
║  截图区域: 鼠标周围 100x100 像素                          ║
╚══════════════════════════════════════════════════════════╝
    """)

    for name, desc, required in IMAGES_TO_CAPTURE:
        filepath = f'images/{name}.png'

        # 检查是否已存在
        if os.path.exists(filepath):
            choice = input(f"\n{desc} 已存在，是否重新截取？(y/n): ").strip().lower()
            if choice != 'y':
                continue

        print(f"\n{'='*50}")
        print(f"准备截取: {desc}")
        if required:
            print("(必须)")
        else:
            print("(可选)")
        print(f"{'='*50}")

        action = input("按回车开始，输入 s 跳过，输入 c 自定义区域: ").strip().lower()

        if action == 's':
            print(f"  [跳过] {desc}")
            continue
        elif action == 'c':
            capture_custom_region(name)
        else:
            print("请将鼠标移动到目标元素的中心位置...")
            countdown(5)
            capture_region(name)


def single_capture_mode():
    """单张截图模式"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                   单张截图模式                            ║
╠══════════════════════════════════════════════════════════╣
║  选择要截取的图片                                         ║
╚══════════════════════════════════════════════════════════╝
    """)

    while True:
        print("\n可截取的图片:")
        for i, (name, desc, required) in enumerate(IMAGES_TO_CAPTURE):
            filepath = f'images/{name}.png'
            status = "[√]" if os.path.exists(filepath) else "[  ]"
            req = "(必须)" if required else "(可选)"
            print(f"  {i+1:2}. {status} {name} - {desc} {req}")

        print(f"  {len(IMAGES_TO_CAPTURE)+1}. 自定义截图")
        print("   0. 返回")

        choice = input("\n请选择 (数字): ").strip()

        if choice == '0':
            break

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(IMAGES_TO_CAPTURE):
                name, desc, _ = IMAGES_TO_CAPTURE[idx]

                print(f"\n截取: {desc}")
                print("  1. 快速截图 (鼠标位置, 100x100)")
                print("  2. 鼠标选区 (移动鼠标选择左上角和右下角)")
                print("  3. 手动坐标 (输入xy坐标)")
                mode = input("请选择: ").strip()

                if mode == '2':
                    capture_custom_region(name)
                elif mode == '3':
                    capture_by_coordinates(name)
                else:
                    print("请将鼠标移动到目标元素的中心位置...")
                    countdown(5)
                    capture_region(name)

            elif idx == len(IMAGES_TO_CAPTURE):
                # 自定义截图
                name = input("输入图片名称（不含扩展名）: ").strip()
                if name:
                    print("  1. 快速截图  2. 鼠标选区  3. 手动坐标")
                    mode = input("请选择: ").strip()
                    if mode == '2':
                        capture_custom_region(name)
                    elif mode == '3':
                        capture_by_coordinates(name)
                    else:
                        print("请将鼠标移动到目标元素的中心位置...")
                        countdown(5)
                        capture_region(name)

        except ValueError:
            print("无效输入")


def test_image_match():
    """测试图片匹配"""
    import cv2
    import numpy as np

    print("""
╔══════════════════════════════════════════════════════════╗
║                   测试图片匹配                            ║
╠══════════════════════════════════════════════════════════╣
║  测试已截取的图片是否能在当前屏幕上找到                    ║
╚══════════════════════════════════════════════════════════╝
    """)

    # 截取当前屏幕
    screenshot = ImageGrab.grab()
    screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

    print("测试结果:")
    print("-" * 50)

    for name, desc, required in IMAGES_TO_CAPTURE:
        filepath = f'images/{name}.png'

        if not os.path.exists(filepath):
            print(f"  [跳过] {name} - 图片不存在")
            continue

        template = cv2.imread(filepath)
        if template is None:
            print(f"  [错误] {name} - 无法读取图片")
            continue

        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= 0.8:
            print(f"  [√] {name} - 匹配度: {max_val:.1%} 位置: {max_loc}")
        elif max_val >= 0.6:
            print(f"  [?] {name} - 匹配度: {max_val:.1%} (可能匹配)")
        else:
            print(f"  [x] {name} - 匹配度: {max_val:.1%} (未找到)")


def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║              签到图片截取工具 v2.0                        ║
╠══════════════════════════════════════════════════════════╣
║  请先打开浏览器，访问目标网站                              ║
║  然后按照提示截取所需图片                                 ║
╚══════════════════════════════════════════════════════════╝
    """)

    while True:
        show_current_images()
        missing = show_missing_images()

        print("\n" + "=" * 50)
        print("操作菜单:")
        print("  1. 快速截图模式（按顺序截取所有图片）")
        print("  2. 单张截图模式（选择性截取）")
        print("  3. 测试图片匹配")
        print("  4. 查看截图状态")
        print("  0. 退出")

        choice = input("\n请选择: ").strip()

        if choice == '0':
            break
        elif choice == '1':
            quick_capture_mode()
        elif choice == '2':
            single_capture_mode()
        elif choice == '3':
            test_image_match()
        elif choice == '4':
            continue  # 会自动显示状态

    print("""
╔══════════════════════════════════════════════════════════╗
║                    截图完成！                             ║
╠══════════════════════════════════════════════════════════╣
║  现在可以运行 auto_signin.py 进行签到                     ║
║  命令: python auto_signin.py                             ║
╚══════════════════════════════════════════════════════════╝
    """)


if __name__ == "__main__":
    main()
