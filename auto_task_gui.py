# -*- coding: utf-8 -*-
"""
自动化任务生成器 GUI
基于 CustomTkinter 的可视化自动化任务配置工具
"""

import customtkinter as ctk
import json
import os
import uuid
import subprocess
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Callable
from tkinter import filedialog, messagebox

# ==================== 数据模型 ====================

# 步骤类型定义
STEP_TYPES = {
    'click_image': {'icon': '📌', 'name': '点击图片', 'params': ['image_path', 'confidence', 'timeout']},
    'wait_image': {'icon': '⏳', 'name': '等待图片', 'params': ['image_path', 'confidence', 'timeout']},
    'long_press': {'icon': '👆', 'name': '长按', 'params': ['duration', 'x', 'y']},
    'mouse_drag': {'icon': '🖱️', 'name': '鼠标拖动', 'params': ['start_x', 'start_y', 'end_x', 'end_y', 'duration']},
    'input_text': {'icon': '⌨️', 'name': '输入文本', 'params': ['text', 'clear_first']},
    'wait_time': {'icon': '⏱️', 'name': '等待时间', 'params': ['seconds']},
    'open_url': {'icon': '🌐', 'name': '打开URL', 'params': ['url']},
    'open_app': {'icon': '🚀', 'name': '打开程序', 'params': ['app_path']},
    'paste': {'icon': '📋', 'name': '粘贴', 'params': []},
    'clipboard_set': {'icon': '📋', 'name': '设置剪贴板', 'params': ['content']},
    'ocr_region': {'icon': '🔤', 'name': 'OCR识别', 'params': ['x1', 'y1', 'x2', 'y2', 'var_name']},
    'press_key': {'icon': '⌨️', 'name': '按键操作', 'params': ['key', 'modifiers']},
    'wx_push': {'icon': '📱', 'name': '微信推送', 'params': ['title', 'content', 'token']},
    'loop_start': {'icon': '🔁', 'name': '循环开始', 'params': ['loop_count']},
    'loop_end': {'icon': '🔚', 'name': '循环结束', 'params': []},
}

# 参数默认值
PARAM_DEFAULTS = {
    'image_path': '', 'confidence': 0.8, 'timeout': 30,
    'text': '', 'clear_first': True, 'seconds': 3,
    'url': 'https://', 'var_name': 'result', 'content': '',
    'x': 0, 'y': 0, 'width': 200, 'height': 100,
    'x1': 0, 'y1': 0, 'x2': 200, 'y2': 100,
    'start_x': 0, 'start_y': 0, 'end_x': 100, 'end_y': 100,
    'key': 'enter', 'modifiers': '',
    'title': '通知', 'token': '',
    'duration': 1.0,
    'app_path': '',
    'loop_count': 3,
}

# 参数中文名称
PARAM_LABELS = {
    'image_path': '图片路径',
    'confidence': '置信度',
    'timeout': '超时(秒)',
    'text': '文本内容',
    'clear_first': '先清空',
    'seconds': '秒数',
    'url': '网址',
    'app_path': '程序路径',
    'var_name': '变量名',
    'content': '内容',
    'x': 'X坐标',
    'y': 'Y坐标',
    'width': '宽度',
    'height': '高度',
    'x1': '起始X',
    'y1': '起始Y',
    'x2': '结束X',
    'y2': '结束Y',
    'start_x': '起点X',
    'start_y': '起点Y',
    'end_x': '终点X',
    'end_y': '终点Y',
    'key': '按键',
    'modifiers': '组合键',
    'title': '标题',
    'token': '令牌',
    'duration': '时长(秒)',
    'loop_count': '循环次数',
}


@dataclass
class Step:
    """步骤数据类"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    step_type: str = ''
    params: Dict = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)


class StepManager:
    """步骤管理器"""
    def __init__(self):
        self.steps: List[Step] = []
        self._on_change: Optional[Callable] = None

    def set_on_change(self, callback):
        self._on_change = callback

    def _notify(self):
        if self._on_change:
            self._on_change()

    def add_step(self, step_type: str) -> Step:
        params = {p: PARAM_DEFAULTS.get(p, '') for p in STEP_TYPES[step_type]['params']}
        step = Step(step_type=step_type, params=params)
        self.steps.append(step)
        self._notify()
        return step

    def remove_step(self, step_id: str):
        self.steps = [s for s in self.steps if s.id != step_id]
        self._notify()

    def move_step(self, step_id: str, direction: int):
        for i, s in enumerate(self.steps):
            if s.id == step_id:
                new_idx = i + direction
                if 0 <= new_idx < len(self.steps):
                    self.steps[i], self.steps[new_idx] = self.steps[new_idx], self.steps[i]
                    self._notify()
                break

    def update_step(self, step_id: str, params: Dict):
        for s in self.steps:
            if s.id == step_id:
                s.params.update(params)
                self._notify()
                break

    def toggle_step(self, step_id: str):
        for s in self.steps:
            if s.id == step_id:
                s.enabled = not s.enabled
                self._notify()
                break

    def get_step(self, step_id: str) -> Optional[Step]:
        for s in self.steps:
            if s.id == step_id:
                return s
        return None

    def clear(self):
        self.steps = []
        self._notify()

    def to_list(self):
        return [s.to_dict() for s in self.steps]

    def from_list(self, data):
        self.steps = [Step.from_dict(d) for d in data]
        self._notify()


class TaskConfig:
    """任务配置"""
    def __init__(self):
        self.name = "未命名任务"
        self.description = ""
        self.settings = {'default_confidence': 0.8, 'default_timeout': 30}
        self.step_manager = StepManager()

    def save(self, filepath: str):
        data = {
            'name': self.name,
            'description': self.description,
            'settings': self.settings,
            'steps': self.step_manager.to_list()
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.name = data.get('name', '未命名任务')
        self.description = data.get('description', '')
        self.settings = data.get('settings', {})
        self.step_manager.from_list(data.get('steps', []))


# ==================== 代码生成器 ====================

class CodeGenerator:
    """代码生成器"""

    IMPORTS = '''# -*- coding: utf-8 -*-
"""自动生成的任务脚本"""
import time
import webbrowser
import pyautogui
import pyperclip
from auto_signin import ImageFinder, HumanMouse, WxPush, get_ocr_reader
from PIL import ImageGrab
import numpy as np
'''

    TEMPLATES = {
        'click_image': '''
def step_{idx}_click_image():
    """点击图片: {image_path}"""
    finder = ImageFinder()
    mouse = HumanMouse()
    pos = finder.wait_for_image("{image_path}", timeout={timeout}, confidence={confidence})
    if pos:
        mouse.click(pos[0], pos[1])
        return True
    return False
''',
        'wait_image': '''
def step_{idx}_wait_image():
    """等待图片: {image_path}"""
    finder = ImageFinder()
    pos = finder.wait_for_image("{image_path}", timeout={timeout}, confidence={confidence})
    return pos is not None
''',
        'input_text': '''
def step_{idx}_input_text():
    """输入文本"""
    {clear_code}
    text = "{text}"
    # 使用剪贴板方式输入，支持中文
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.2)
''',
        'wait_time': '''
def step_{idx}_wait_time():
    """等待 {seconds} 秒"""
    time.sleep({seconds})
''',
        'open_url': '''
def step_{idx}_open_url():
    """打开URL: {url}"""
    webbrowser.open("{url}")
    time.sleep(3)
''',
        'long_press': '''
def step_{idx}_long_press():
    """长按 {duration} 秒"""
    import pyautogui
    x, y = {x}, {y}
    if x == 0 and y == 0:
        x, y = pyautogui.position()
    pyautogui.mouseDown(x, y)
    time.sleep({duration})
    pyautogui.mouseUp()
''',
        'paste': '''
def step_{idx}_paste():
    """粘贴剪贴板内容"""
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.3)
''',
        'open_app': '''
def step_{idx}_open_app():
    """打开程序: {app_path}"""
    import subprocess
    import os
    app_path = r"{app_path}"
    if os.path.exists(app_path):
        subprocess.Popen(app_path, shell=True)
        print(f"  [√] 已启动: {{app_path}}")
        time.sleep(2)
    else:
        print(f"  [!] 程序不存在: {{app_path}}")
''',
        'clipboard_set': '''
def step_{idx}_clipboard_set():
    """设置剪贴板内容"""
    pyperclip.copy("{content}")
''',
        'ocr_region': '''
def step_{idx}_ocr_region():
    """OCR识别区域 ({x1},{y1}) - ({x2},{y2}) - 使用Umi-OCR"""
    global {var_name}
    import os
    import base64
    import io
    import requests
    
    screenshot = ImageGrab.grab(bbox=({x1}, {y1}, {x2}, {y2}))
    # 保存截图用于调试
    debug_path = "images/_ocr_debug_{idx}.png"
    os.makedirs("images", exist_ok=True)
    screenshot.save(debug_path)
    print(f"  [OCR] 截图区域: ({x1},{y1}) - ({x2},{y2})")
    
    # 转换为base64
    buffer = io.BytesIO()
    screenshot.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    # 调用Umi-OCR HTTP API
    try:
        resp = requests.post(
            "http://127.0.0.1:1224/api/ocr",
            json={{"base64": img_base64, "options": {{"data.format": "text"}}}},
            timeout=30
        )
        data = resp.json()
        if data.get("code") == 100:
            {var_name} = data.get("data", "")
            print(f"  [OCR] 识别结果: {{{var_name}}}")
        else:
            {var_name} = ""
            print(f"  [OCR] 识别失败: {{data.get('msg', '未知错误')}}")
    except Exception as e:
        {var_name} = ""
        print(f"  [OCR] 请求失败: {{e}}")
        print("  [OCR] 请确保Umi-OCR已启动并开启HTTP服务(端口1224)")
    return {var_name}
''',
        'press_key': '''
def step_{idx}_press_key():
    """按键: {key}"""
    {key_code}
''',
        'wx_push': '''
def step_{idx}_wx_push():
    """微信推送"""
    config = {{'enabled': True, 'url': 'https://xiaoxi.qxbl.de5.net/wxsend', 'token': '{token}'}}
    # 支持变量引用，如 {{result}} 会被替换为变量值
    title = "{title}"
    content = "{content}"
    # 尝试替换变量
    for var_name in ['result', 'redeem_code', 'ocr_result']:
        if var_name in globals():
            content = content.replace('{{' + var_name + '}}', str(globals()[var_name]))
            title = title.replace('{{' + var_name + '}}', str(globals()[var_name]))
    WxPush.send(title, content, config)
''',
        'mouse_drag': '''
def step_{idx}_mouse_drag():
    """鼠标拖动: ({start_x},{start_y}) -> ({end_x},{end_y})"""
    import pyautogui
    pyautogui.moveTo({start_x}, {start_y})
    time.sleep(0.1)
    pyautogui.drag({end_x} - {start_x}, {end_y} - {start_y}, duration={duration})
''',
        'loop_start': '''
def step_{idx}_loop_start():
    """循环开始: {loop_count} 次"""
    pass  # 循环逻辑在main中处理
''',
        'loop_end': '''
def step_{idx}_loop_end():
    """循环结束"""
    pass  # 循环逻辑在main中处理
''',
    }

    MAIN_TEMPLATE = '''

def main():
    """执行所有步骤"""
    print("=" * 50)
    print("开始执行自动化任务")
    print("=" * 50)
{step_calls}
    print("=" * 50)
    print("任务执行完成")
    print("=" * 50)

if __name__ == "__main__":
    main()
'''

    def generate(self, step_manager: StepManager) -> str:
        code = self.IMPORTS
        step_calls = []
        indent_level = 1  # 基础缩进级别
        loop_stack = []  # 循环栈，存储循环次数

        for idx, step in enumerate(step_manager.steps, 1):
            if not step.enabled:
                continue

            template = self.TEMPLATES.get(step.step_type, '')
            params = step.params.copy()
            params['idx'] = idx

            # 特殊处理
            if step.step_type == 'input_text':
                params['clear_code'] = 'pyautogui.hotkey("ctrl", "a")\n    ' if params.get('clear_first') else ''
            elif step.step_type == 'press_key':
                mods = params.get('modifiers', '').strip()
                key = params.get('key', 'enter')
                if mods:
                    # 支持逗号分隔的修饰键
                    mod_list = [m.strip() for m in mods.replace('+', ',').split(',') if m.strip()]
                    key_list = [k.strip() for k in key.split(',') if k.strip()]
                    all_keys = mod_list + key_list
                    keys_str = '", "'.join(all_keys)
                    params['key_code'] = f'pyautogui.hotkey("{keys_str}")'
                else:
                    params['key_code'] = f'pyautogui.press("{key}")'

            code += template.format(**params)

            # 处理循环逻辑
            base_indent = '    ' * indent_level
            if step.step_type == 'loop_start':
                loop_count = params.get('loop_count', 3)
                loop_stack.append(loop_count)
                step_calls.append(f'{base_indent}print("步骤{idx}: 循环开始 ({loop_count}次)")')
                step_calls.append(f'{base_indent}for _loop_i_{len(loop_stack)} in range({loop_count}):')
                step_calls.append(f'{base_indent}    print(f"  第 {{_loop_i_{len(loop_stack)} + 1}}/{loop_count} 次循环")')
                indent_level += 1
            elif step.step_type == 'loop_end':
                if loop_stack:
                    loop_stack.pop()
                    indent_level = max(1, indent_level - 1)
                    base_indent = '    ' * indent_level
                step_calls.append(f'{base_indent}print("步骤{idx}: 循环结束")')
            else:
                step_calls.append(f'{base_indent}print("步骤{idx}: {STEP_TYPES[step.step_type]["name"]}")')
                step_calls.append(f'{base_indent}step_{idx}_{step.step_type}()')

        code += self.MAIN_TEMPLATE.format(step_calls='\n'.join(step_calls))
        return code


# ==================== GUI 组件 ====================

class StepTypePanel(ctk.CTkScrollableFrame):
    """步骤类型面板（左侧）"""
    def __init__(self, master, on_add_step, **kwargs):
        super().__init__(master, **kwargs)
        self.on_add_step = on_add_step

        ctk.CTkLabel(self, text="步骤类型", font=("", 14, "bold")).pack(pady=(0, 10))

        for step_type, info in STEP_TYPES.items():
            btn = ctk.CTkButton(
                self, text=f"{info['icon']} {info['name']}",
                command=lambda t=step_type: self.on_add_step(t),
                width=140, height=32
            )
            btn.pack(pady=3, padx=5, fill="x")


class StepListPanel(ctk.CTkScrollableFrame):
    """步骤列表面板"""
    def __init__(self, master, step_manager: StepManager, on_select, **kwargs):
        super().__init__(master, **kwargs)
        self.step_manager = step_manager
        self.on_select = on_select
        self.selected_id = None
        self.step_frames = {}

        step_manager.set_on_change(self.refresh)

    def refresh(self):
        for w in self.winfo_children():
            w.destroy()
        self.step_frames = {}

        for idx, step in enumerate(self.step_manager.steps, 1):
            frame = ctk.CTkFrame(self, fg_color="gray25" if step.id == self.selected_id else "transparent")
            frame.pack(fill="x", pady=2, padx=2)

            info = STEP_TYPES.get(step.step_type, {})
            status = "☑" if step.enabled else "☐"
            text = f"{status} {idx}. [{info.get('name', '')}]"

            # 显示关键参数
            if step.step_type in ['open_url', 'click_image', 'wait_image']:
                key_param = step.params.get('url') or step.params.get('image_path', '')
                if key_param:
                    text += f" {key_param[:20]}..."
            elif step.step_type == 'wait_time':
                text += f" {step.params.get('seconds', 0)}秒"
            elif step.step_type == 'loop_start':
                text += f" {step.params.get('loop_count', 3)}次"
            elif step.step_type == 'mouse_drag':
                text += f" ({step.params.get('start_x', 0)},{step.params.get('start_y', 0)})->({step.params.get('end_x', 0)},{step.params.get('end_y', 0)})"

            btn = ctk.CTkButton(
                frame, text=text, anchor="w",
                fg_color="transparent", hover_color="gray30",
                command=lambda s=step: self._select(s)
            )
            btn.pack(side="left", fill="x", expand=True)

            self.step_frames[step.id] = frame

    def _select(self, step: Step):
        self.selected_id = step.id
        self.refresh()
        self.on_select(step)


class PropertyEditor(ctk.CTkFrame):
    """属性编辑器"""
    def __init__(self, master, step_manager: StepManager, on_change, **kwargs):
        super().__init__(master, **kwargs)
        self.step_manager = step_manager
        self.on_change = on_change
        self.current_step = None
        self.entries = {}

        self.title_label = ctk.CTkLabel(self, text="步骤属性", font=("", 14, "bold"))
        self.title_label.pack(pady=(10, 5))

        self.form_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.form_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 操作按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10, padx=10)

        ctk.CTkButton(btn_frame, text="↑", width=40, command=lambda: self._move(-1)).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="↓", width=40, command=lambda: self._move(1)).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="复制", width=50, command=self._copy).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="启用/禁用", width=80, command=self._toggle).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="删除", width=60, fg_color="red", command=self._delete).pack(side="right", padx=2)

    def show_step(self, step: Step):
        self.current_step = step
        for w in self.form_frame.winfo_children():
            w.destroy()
        self.entries = {}

        if not step:
            return

        info = STEP_TYPES.get(step.step_type, {})
        self.title_label.configure(text=f"{info.get('icon', '')} {info.get('name', '')} 属性")

        for param in info.get('params', []):
            row = ctk.CTkFrame(self.form_frame, fg_color="transparent")
            row.pack(fill="x", pady=3)

            label = PARAM_LABELS.get(param, param)
            ctk.CTkLabel(row, text=f"{label}:", width=80, anchor="e").pack(side="left")

            value = step.params.get(param, PARAM_DEFAULTS.get(param, ''))

            if param == 'image_path':
                entry = ctk.CTkEntry(row, width=150)
                entry.insert(0, str(value))
                entry.pack(side="left", padx=5)
                ctk.CTkButton(row, text="浏览", width=50,
                              command=lambda e=entry: self._browse_image(e)).pack(side="left")
            elif param == 'app_path':
                entry = ctk.CTkEntry(row, width=150)
                entry.insert(0, str(value))
                entry.pack(side="left", padx=5)
                ctk.CTkButton(row, text="浏览", width=50,
                              command=lambda e=entry: self._browse_app(e)).pack(side="left")
            elif param == 'clear_first':
                var = ctk.BooleanVar(value=bool(value))
                cb = ctk.CTkCheckBox(row, text="", variable=var)
                cb.pack(side="left", padx=5)
                self.entries[param] = var
                continue
            elif param == 'key' and step.step_type == 'press_key':
                entry = ctk.CTkEntry(row, width=120)
                entry.insert(0, str(value))
                entry.pack(side="left", padx=5)
                ctk.CTkButton(row, text="录制", width=50,
                              command=lambda e=entry: self._record_key(e)).pack(side="left")
            elif param == 'modifiers' and step.step_type == 'press_key':
                entry = ctk.CTkEntry(row, width=120)
                entry.insert(0, str(value))
                entry.pack(side="left", padx=5)
                ctk.CTkButton(row, text="录制组合键", width=80,
                              command=lambda: self._record_hotkey()).pack(side="left")
            else:
                entry = ctk.CTkEntry(row, width=200)
                entry.insert(0, str(value))
                entry.pack(side="left", padx=5)

            self.entries[param] = entry

        # 保存按钮
        ctk.CTkButton(self.form_frame, text="保存修改", command=self._save).pack(pady=10)

    def _browse_image(self, entry):
        path = filedialog.askopenfilename(
            initialdir="images",
            filetypes=[("PNG", "*.png"), ("All", "*.*")]
        )
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def _browse_app(self, entry):
        path = filedialog.askopenfilename(
            filetypes=[("可执行文件", "*.exe"), ("All", "*.*")]
        )
        if path:
            entry.delete(0, "end")
            entry.insert(0, path)

    def _record_key(self, entry):
        """录制单个按键"""
        import keyboard
        messagebox.showinfo("录制按键", "请按下要录制的按键...")
        
        def on_key(event):
            key_name = event.name
            entry.delete(0, "end")
            entry.insert(0, key_name)
            keyboard.unhook_all()
        
        keyboard.on_press(on_key)

    def _record_hotkey(self):
        """录制组合键"""
        import keyboard
        
        # 创建录制窗口
        record_win = ctk.CTkToplevel(self)
        record_win.title("录制组合键")
        record_win.geometry("300x150")
        record_win.transient(self)
        record_win.grab_set()
        
        ctk.CTkLabel(record_win, text="请按下组合键...", font=("", 14)).pack(pady=20)
        result_label = ctk.CTkLabel(record_win, text="", font=("", 12))
        result_label.pack(pady=10)
        
        recorded_keys = []
        
        def on_key(event):
            key = event.name
            if key not in recorded_keys:
                recorded_keys.append(key)
                result_label.configure(text=" + ".join(recorded_keys))
        
        def confirm():
            keyboard.unhook_all()
            if recorded_keys and self.current_step:
                # 分离修饰键和非修饰键
                modifiers = []
                main_keys = []
                for k in recorded_keys:
                    if k in ['ctrl', 'alt', 'shift', 'win', 'left ctrl', 'right ctrl', 'left alt', 'right alt', 'left shift', 'right shift']:
                        # 统一修饰键名称
                        mod = k.replace('left ', '').replace('right ', '')
                        if mod not in modifiers:
                            modifiers.append(mod)
                    else:
                        main_keys.append(k)
                
                if 'key' in self.entries:
                    self.entries['key'].delete(0, "end")
                    # 多个主键用逗号分隔
                    self.entries['key'].insert(0, ",".join(main_keys) if main_keys else "")
                if 'modifiers' in self.entries:
                    self.entries['modifiers'].delete(0, "end")
                    self.entries['modifiers'].insert(0, ",".join(modifiers))
            record_win.destroy()
        
        def cancel():
            keyboard.unhook_all()
            record_win.destroy()
        
        keyboard.on_press(on_key)
        
        btn_frame = ctk.CTkFrame(record_win, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="确定", command=confirm).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="取消", command=cancel).pack(side="left", padx=10)

    def _save(self):
        if not self.current_step:
            return
        params = {}
        for param, widget in self.entries.items():
            if isinstance(widget, ctk.BooleanVar):
                params[param] = widget.get()
            else:
                val = widget.get()
                # 尝试转换数字
                try:
                    if '.' in val:
                        params[param] = float(val)
                    else:
                        params[param] = int(val)
                except ValueError:
                    params[param] = val

        self.step_manager.update_step(self.current_step.id, params)
        self.on_change()

    def _move(self, direction):
        if self.current_step:
            self.step_manager.move_step(self.current_step.id, direction)

    def _toggle(self):
        if self.current_step:
            self.step_manager.toggle_step(self.current_step.id)

    def _copy(self):
        """复制当前步骤"""
        if self.current_step:
            new_step = Step(
                step_type=self.current_step.step_type,
                params=self.current_step.params.copy(),
                enabled=self.current_step.enabled
            )
            self.step_manager.steps.append(new_step)
            self.step_manager._notify()
            self.on_change()

    def _delete(self):
        if self.current_step:
            self.step_manager.remove_step(self.current_step.id)
            self.current_step = None
            self.show_step(None)


class CodePreview(ctk.CTkFrame):
    """代码预览区域"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        ctk.CTkLabel(self, text="代码预览", font=("", 14, "bold")).pack(pady=(5, 0))

        self.textbox = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.textbox.pack(fill="both", expand=True, padx=5, pady=5)

    def set_code(self, code: str):
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", code)


# ==================== 主窗口 ====================

class AutoTaskGUI(ctk.CTk):
    """主窗口"""
    def __init__(self):
        super().__init__()

        self.title("自动化任务生成器")
        self.geometry("1100x750")
        self.minsize(900, 600)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.config = TaskConfig()
        self.generator = CodeGenerator()
        self.current_file = None

        self._create_toolbar()
        self._create_main_layout()

    def _create_toolbar(self):
        toolbar = ctk.CTkFrame(self, height=40)
        toolbar.pack(fill="x", padx=5, pady=5)

        buttons = [
            ("新建", self._new_task),
            ("打开", self._open_task),
            ("保存", self._save_task),
            ("运行", self._run_task),
            ("生成代码", self._export_code),
            ("定时任务", self._show_scheduler),
        ]
        for text, cmd in buttons:
            ctk.CTkButton(toolbar, text=text, width=80, command=cmd).pack(side="left", padx=3)

    def _create_main_layout(self):
        # 主容器
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=5, pady=5)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # 左侧：步骤类型面板
        self.step_type_panel = StepTypePanel(
            main, on_add_step=self._add_step, width=160
        )
        self.step_type_panel.grid(row=0, column=0, sticky="ns", padx=(0, 5))

        # 中间：步骤列表 + 属性编辑
        middle = ctk.CTkFrame(main)
        middle.grid(row=0, column=1, sticky="nsew")
        middle.grid_rowconfigure(0, weight=1)
        middle.grid_rowconfigure(1, weight=1)
        middle.grid_columnconfigure(0, weight=1)

        self.step_list = StepListPanel(
            middle, self.config.step_manager, on_select=self._on_step_select
        )
        self.step_list.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

        self.property_editor = PropertyEditor(
            middle, self.config.step_manager, on_change=self._update_preview
        )
        self.property_editor.grid(row=1, column=0, sticky="nsew")

        # 底部：代码预览
        self.code_preview = CodePreview(self, height=200)
        self.code_preview.pack(fill="x", padx=5, pady=5)

        self._update_preview()

    def _add_step(self, step_type: str):
        self.config.step_manager.add_step(step_type)
        self._update_preview()

    def _on_step_select(self, step: Step):
        self.property_editor.show_step(step)

    def _update_preview(self):
        code = self.generator.generate(self.config.step_manager)
        self.code_preview.set_code(code)

    def _new_task(self):
        self.config = TaskConfig()
        self.config.step_manager.set_on_change(self.step_list.refresh)
        self.step_list.step_manager = self.config.step_manager
        self.property_editor.step_manager = self.config.step_manager
        self.step_list.refresh()
        self.property_editor.show_step(None)
        self._update_preview()
        self.current_file = None

    def _open_task(self):
        path = filedialog.askopenfilename(
            initialdir="tasks",
            filetypes=[("JSON", "*.json")]
        )
        if path:
            self.config.load(path)
            self.config.step_manager.set_on_change(self.step_list.refresh)
            self.step_list.step_manager = self.config.step_manager
            self.property_editor.step_manager = self.config.step_manager
            self.step_list.refresh()
            self._update_preview()
            self.current_file = path

    def _save_task(self):
        path = self.current_file or filedialog.asksaveasfilename(
            initialdir="tasks",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")]
        )
        if path:
            self.config.save(path)
            self.current_file = path
            messagebox.showinfo("保存", "任务已保存")

    def _run_task(self):
        # 生成临时脚本并运行
        if not self.config.step_manager.steps:
            messagebox.showwarning("提示", "请先添加步骤")
            return
        
        import tempfile
        # 使用系统临时目录避免中文路径问题
        temp_dir = tempfile.gettempdir()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        code = self.generator.generate(self.config.step_manager)
        # 修改代码中的相对路径为绝对路径
        code = code.replace('from auto_signin import', f'import sys\nsys.path.insert(0, r"{script_dir}")\nfrom auto_signin import')
        # 将相对图片路径转换为绝对路径
        code = code.replace('"images/', f'r"{script_dir}/images/')
        code = code.replace("'images/", f"r'{script_dir}/images/")
        
        temp_file = os.path.join(temp_dir, "_auto_task_temp.py")
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        # 创建批处理文件
        bat_file = os.path.join(temp_dir, "_run_task.bat")
        with open(bat_file, 'w') as f:
            f.write(f'@echo off\nchcp 65001 >nul\ncd /d "{script_dir}"\npython "{temp_file}"\npause')
        
        os.startfile(bat_file)

    def _export_code(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python", "*.py")]
        )
        if path:
            code = self.generator.generate(self.config.step_manager)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(code)
            messagebox.showinfo("导出", f"代码已导出到 {path}")

    def _show_scheduler(self):
        """显示定时任务管理窗口"""
        SchedulerWindow(self)


class SchedulerWindow(ctk.CTkToplevel):
    """定时任务管理窗口"""
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("定时任务管理")
        self.geometry("500x450")
        self.minsize(500, 450)
        self.transient(parent)
        
        # 导入调度器
        import task_scheduler as scheduler
        self.scheduler = scheduler
        
        # 任务列表
        ctk.CTkLabel(self, text="定时任务列表", font=("", 14, "bold")).pack(pady=10)
        
        self.task_list = ctk.CTkTextbox(self, height=150)
        self.task_list.pack(fill="x", padx=20, pady=5)
        
        # 添加任务区域
        add_frame = ctk.CTkFrame(self)
        add_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(add_frame, text="添加定时任务", font=("", 12, "bold")).pack(anchor="w")
        
        row1 = ctk.CTkFrame(add_frame, fg_color="transparent")
        row1.pack(fill="x", pady=5)
        ctk.CTkLabel(row1, text="任务文件:").pack(side="left")
        self.file_entry = ctk.CTkEntry(row1, width=250)
        self.file_entry.pack(side="left", padx=5)
        ctk.CTkButton(row1, text="浏览", width=60, command=self._browse_task).pack(side="left")
        
        row2 = ctk.CTkFrame(add_frame, fg_color="transparent")
        row2.pack(fill="x", pady=5)
        ctk.CTkLabel(row2, text="运行时间:").pack(side="left")
        self.time_entry = ctk.CTkEntry(row2, width=100, placeholder_text="08:00")
        self.time_entry.pack(side="left", padx=5)
        ctk.CTkLabel(row2, text="(每天)").pack(side="left")
        
        row3 = ctk.CTkFrame(add_frame, fg_color="transparent")
        row3.pack(fill="x", pady=5)
        ctk.CTkLabel(row3, text="任务名称:").pack(side="left")
        self.name_entry = ctk.CTkEntry(row3, width=150, placeholder_text="可选")
        self.name_entry.pack(side="left", padx=5)
        
        # 按钮
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(btn_frame, text="添加定时任务", command=self._add_task).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="删除选中", command=self._delete_task, fg_color="red").pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="刷新列表", command=self._refresh_list).pack(side="right", padx=5)
        
        self._refresh_list()
    
    def _browse_task(self):
        path = filedialog.askopenfilename(initialdir="tasks", filetypes=[("JSON", "*.json")])
        if path:
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, path)
    
    def _refresh_list(self):
        self.task_list.delete("1.0", "end")
        tasks = self.scheduler.list_scheduled_tasks()
        if not tasks:
            self.task_list.insert("1.0", "暂无定时任务")
        else:
            for i, t in enumerate(tasks, 1):
                self.task_list.insert("end", f"{i}. {t['name']} - 每天 {t['time']} 运行\n   文件: {t['file']}\n\n")
    
    def _add_task(self):
        task_file = self.file_entry.get().strip()
        run_time = self.time_entry.get().strip()
        task_name = self.name_entry.get().strip() or None
        
        if not task_file or not run_time:
            messagebox.showwarning("提示", "请填写任务文件和运行时间")
            return
        
        success, msg = self.scheduler.add_scheduled_task(task_file, run_time, task_name)
        if success:
            messagebox.showinfo("成功", msg)
            self._refresh_list()
        else:
            messagebox.showerror("失败", msg)
    
    def _delete_task(self):
        tasks = self.scheduler.list_scheduled_tasks()
        if not tasks:
            return
        
        # 简单实现：删除第一个任务，实际应该让用户选择
        from tkinter import simpledialog
        idx = simpledialog.askinteger("删除任务", f"输入要删除的任务序号 (1-{len(tasks)}):", parent=self)
        if idx and 1 <= idx <= len(tasks):
            task = tasks[idx - 1]
            if self.scheduler.remove_scheduled_task(task["name"]):
                messagebox.showinfo("成功", f"已删除: {task['name']}")
                self._refresh_list()
            else:
                messagebox.showerror("失败", "删除失败")


if __name__ == "__main__":
    app = AutoTaskGUI()
    app.mainloop()
