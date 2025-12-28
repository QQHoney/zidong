# -*- coding: utf-8 -*-
"""
基础代码模板
用于生成自动化任务脚本
"""

# 导入模板
IMPORTS_TEMPLATE = '''# -*- coding: utf-8 -*-
"""
自动生成的任务脚本
任务名称: {task_name}
生成时间: {timestamp}
"""
import time
import webbrowser
import pyautogui
import pyperclip
from auto_signin import ImageFinder, HumanMouse, WxPush, get_ocr_reader
from PIL import ImageGrab
import numpy as np

# 初始化
finder = ImageFinder()
mouse = HumanMouse()
'''

# 主函数模板
MAIN_TEMPLATE = '''

def main():
    """执行所有步骤"""
    print("=" * 50)
    print("开始执行: {task_name}")
    print("=" * 50)
    
    try:
{step_calls}
        print("\\n" + "=" * 50)
        print("任务执行完成!")
        print("=" * 50)
        return True
    except Exception as e:
        print(f"\\n[错误] {{e}}")
        return False

if __name__ == "__main__":
    main()
'''

# 步骤模板
STEP_TEMPLATES = {
    'click_image': '''
def step_{idx}_click_image():
    """点击图片: {image_path}"""
    pos = finder.wait_for_image("{image_path}", timeout={timeout}, confidence={confidence})
    if pos:
        mouse.click(pos[0], pos[1])
        time.sleep(1)
        return True
    print("  [!] 未找到图片")
    return False
''',

    'wait_image': '''
def step_{idx}_wait_image():
    """等待图片出现: {image_path}"""
    pos = finder.wait_for_image("{image_path}", timeout={timeout}, confidence={confidence})
    if pos:
        print(f"  [√] 图片已出现")
        return True
    print("  [!] 等待超时")
    return False
''',

    'input_text': '''
def step_{idx}_input_text():
    """输入文本: {text}"""
    {clear_code}
    pyautogui.write("{text}", interval=0.05)
    return True
''',

    'wait_time': '''
def step_{idx}_wait_time():
    """等待 {seconds} 秒"""
    print(f"  等待 {seconds} 秒...")
    time.sleep({seconds})
    return True
''',

    'open_url': '''
def step_{idx}_open_url():
    """打开URL: {url}"""
    webbrowser.open("{url}")
    time.sleep(3)
    return True
''',

    'clipboard_get': '''
def step_{idx}_clipboard_get():
    """获取剪贴板内容到变量: {var_name}"""
    global {var_name}
    {var_name} = pyperclip.paste()
    print(f"  剪贴板内容: {{{var_name}}}")
    return {var_name}
''',

    'clipboard_set': '''
def step_{idx}_clipboard_set():
    """设置剪贴板内容"""
    pyperclip.copy("{content}")
    return True
''',

    'ocr_region': '''
def step_{idx}_ocr_region():
    """OCR识别区域 ({x},{y},{width}x{height}) -> {var_name}"""
    global {var_name}
    screenshot = ImageGrab.grab(bbox=({x}, {y}, {x}+{width}, {y}+{height}))
    reader = get_ocr_reader()
    if reader:
        results = reader.readtext(np.array(screenshot))
        {var_name} = ' '.join([t for _, t, p in results if p > 0.5])
        print(f"  OCR结果: {{{var_name}}}")
        return {var_name}
    return None
''',

    'press_key': '''
def step_{idx}_press_key():
    """按键: {key}"""
    {key_code}
    return True
''',

    'wx_push': '''
def step_{idx}_wx_push():
    """微信推送: {title}"""
    config = {{
        'enabled': True,
        'url': 'https://xiaoxi.qxbl.de5.net/wxsend',
        'token': '{token}'
    }}
    WxPush.send("{title}", "{content}", config)
    return True
''',
}
