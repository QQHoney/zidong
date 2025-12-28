# -*- coding: utf-8 -*-
"""
网站自动签到脚本
流程：
1. 打开网站 https://x666.me/
2. 关闭公告
3. 点击签到入口 -> 自动跳转到 https://qd.x666.me/
4. 点击开始转动
5. 等待转动完毕（约8秒），兑换码自动复制到剪贴板
6. 返回 https://x666.me/console/topup
7. 在兑换码输入框粘贴
8. 点击兑换
9. 点击确定
10. 获取兑换成功信息，推送到微信
"""

import time
import random
import os
import cv2
import numpy as np
import pyautogui
import pyperclip
import requests
import urllib.parse
from PIL import ImageGrab

# OCR相关
OCR_READER = None

def get_ocr_reader():
    """懒加载OCR读取器"""
    global OCR_READER
    if OCR_READER is None:
        try:
            import easyocr
            print("  [OCR] 正在加载OCR模型（首次加载较慢）...")
            OCR_READER = easyocr.Reader(['ch_sim', 'en'], gpu=False)
            print("  [OCR] 模型加载完成")
        except Exception as e:
            print(f"  [OCR] 加载失败: {e}")
            return None
    return OCR_READER

# ==================== 配置区域 ====================
CONFIG = {
    # 网站地址
    'main_url': 'https://x666.me/',
    'signin_url': 'https://qd.x666.me/',
    'topup_url': 'https://x666.me/console/topup',

    # 微信推送配置
    'wx_push': {
        'enabled': True,
        'url': 'https://xiaoxi.qxbl.de5.net/wxsend',
        'token': 'bing521',
    },

    # 所有需要识别的图片
    'images': {
        # 主站相关
        'cf_checkbox': 'images/cf_checkbox.png',           # CF验证框
        'announcement_close': 'images/announcement_close.png',  # 公告关闭按钮
        'signin_entry': 'images/signin_entry.png',         # 签到入口按钮

        # 签到页面 (qd.x666.me)
        'spin_button': 'images/spin_button.png',           # 开始转动按钮
        'wheel_confirm': 'images/wheel_confirm.png',       # 转盘结果确定按钮

        # 充值页面 (console/topup)
        'redeem_input': 'images/redeem_input.png',         # 兑换码输入框
        'redeem_button': 'images/redeem_button.png',       # 兑换按钮
        'confirm_button': 'images/confirm_button.png',     # 确定按钮
        'success_message': 'images/success_message.png',   # 兑换成功提示
    },

    'confidence': 0.8,
    'wait_time': {
        'page_load': 5,
        'cf_verify': 8,
        'after_click': 2,
        'wheel_spin': 10,      # 转盘转动等待（8秒+缓冲）
        'clipboard_wait': 2,   # 等待剪贴板
    },

    # 弹窗区域配置（用于OCR识别）
    # 根据截图，弹窗大约在屏幕中央，可以根据实际情况调整
    'dialog_region': {
        'x': 600,      # 弹窗左上角X
        'y': 300,      # 弹窗左上角Y
        'width': 350,  # 弹窗宽度
        'height': 150, # 弹窗高度
    },
}
# ================================================


class ImageFinder:
    """图像识别类"""

    @staticmethod
    def find_on_screen(template_path, confidence=0.8):
        """在屏幕上查找图片"""
        if not os.path.exists(template_path):
            print(f"  [!] 图片文件不存在: {template_path}")
            return None

        screenshot = ImageGrab.grab()
        screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

        # 使用 numpy 读取图片以支持中文路径
        template = cv2.imdecode(np.fromfile(template_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if template is None:
            print(f"  [!] 无法读取图片: {template_path}")
            return None

        h, w = template.shape[:2]
        result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= confidence:
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            print(f"  [√] 找到 {os.path.basename(template_path)} (匹配度: {max_val:.1%})")
            return (center_x, center_y)
        else:
            print(f"  [x] 未找到 {os.path.basename(template_path)} (最高: {max_val:.1%})")
            return None

    @staticmethod
    def wait_for_image(template_path, timeout=30, confidence=0.8, interval=0.5, silent=False):
        """等待图片出现"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not os.path.exists(template_path):
                if not silent:
                    print(f"  [!] 图片不存在: {template_path}")
                return None

            screenshot = ImageGrab.grab()
            screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

            # 使用 numpy 读取图片以支持中文路径
            template = cv2.imdecode(np.fromfile(template_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if template is None:
                if not silent:
                    print(f"  [!] 无法读取图片: {template_path}")
                return None

            h, w = template.shape[:2]
            result = cv2.matchTemplate(screenshot, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            if max_val >= confidence:
                center_x = max_loc[0] + w // 2
                center_y = max_loc[1] + h // 2
                if not silent:
                    print(f"  [√] 找到 {os.path.basename(template_path)} (匹配度: {max_val:.1%})")
                return (center_x, center_y)

            time.sleep(interval)

        if not silent:
            print(f"  [x] 等待超时: {os.path.basename(template_path)}")
        return None


class HumanMouse:
    """模拟人类鼠标行为"""

    @staticmethod
    def move_to(x, y):
        """人性化移动鼠标"""
        current_x, current_y = pyautogui.position()

        x += random.randint(-3, 3)
        y += random.randint(-3, 3)

        distance = ((x - current_x) ** 2 + (y - current_y) ** 2) ** 0.5
        duration = min(0.3 + distance / 1000, 1.0)

        ctrl_x = (current_x + x) // 2 + random.randint(-30, 30)
        ctrl_y = (current_y + y) // 2 + random.randint(-30, 30)

        steps = random.randint(15, 25)
        for i in range(steps + 1):
            t = i / steps
            t = t * t * (3 - 2 * t)

            bx = (1-t)**2 * current_x + 2*(1-t)*t * ctrl_x + t**2 * x
            by = (1-t)**2 * current_y + 2*(1-t)*t * ctrl_y + t**2 * y

            pyautogui.moveTo(int(bx), int(by), duration=0)
            time.sleep(duration / steps)

    @staticmethod
    def click(x=None, y=None):
        """人性化点击"""
        if x is not None and y is not None:
            HumanMouse.move_to(x, y)

        time.sleep(random.uniform(0.1, 0.3))
        pyautogui.mouseDown()
        time.sleep(random.uniform(0.05, 0.12))
        pyautogui.mouseUp()


class WxPush:
    """微信推送"""

    @staticmethod
    def send(title, content, config):
        """发送微信推送"""
        if not config.get('enabled'):
            print("  [跳过] 微信推送未启用")
            return False

        try:
            url = config['url']
            params = {
                'token': config['token'],
                'title': title,
                'content': content
            }

            full_url = f"{url}?{urllib.parse.urlencode(params)}"
            print(f"  [推送] 发送微信通知...")

            response = requests.get(full_url, timeout=30)

            print(f"  [推送] 状态码: {response.status_code}")
            print(f"  [推送] 返回: {response.text[:100] if response.text else '空'}")

            return response.status_code == 200

        except Exception as e:
            print(f"  [推送] 失败: {e}")
            return False


class AutoSignIn:
    """自动签到主类"""

    def __init__(self, config):
        self.config = config
        self.finder = ImageFinder()
        self.mouse = HumanMouse()
        self.redeem_code = None
        self.result_message = None

    def log(self, step, message):
        """格式化日志输出"""
        print(f"\n[步骤{step}] {message}")
        print("-" * 40)

    def find_and_click(self, image_key, description="", wait=True, timeout=10):
        """查找并点击图片"""
        image_path = self.config['images'].get(image_key)
        if not image_path:
            print(f"  [跳过] 未配置: {image_key}")
            return False

        if not os.path.exists(image_path):
            print(f"  [跳过] 图片不存在: {image_path}")
            return False

        print(f"  查找: {description or image_key}")

        if wait:
            pos = self.finder.wait_for_image(image_path, timeout=timeout,
                                             confidence=self.config['confidence'])
        else:
            pos = self.finder.find_on_screen(image_path, self.config['confidence'])

        if pos:
            self.mouse.click(pos[0], pos[1])
            time.sleep(self.config['wait_time']['after_click'])
            return True
        return False

    def open_url(self, url):
        """打开URL"""
        import webbrowser
        print(f"  打开: {url}")
        webbrowser.open(url)
        time.sleep(self.config['wait_time']['page_load'])

    def step1_open_main_site(self):
        """步骤1: 打开主站"""
        self.log(1, "打开主站")
        self.open_url(self.config['main_url'])

    def step2_handle_cloudflare(self):
        """步骤2: 处理CF验证"""
        self.log(2, "检测CloudFlare验证")

        cf_image = self.config['images'].get('cf_checkbox')
        if not cf_image or not os.path.exists(cf_image):
            print("  [跳过] 未配置CF验证图片")
            return True

        pos = self.finder.wait_for_image(cf_image, timeout=10,
                                         confidence=self.config['confidence'],
                                         silent=True)
        if pos:
            print("  [!] 检测到CF验证框")
            self.mouse.click(pos[0], pos[1])
            print("  等待验证完成...")
            time.sleep(self.config['wait_time']['cf_verify'])
        else:
            print("  [√] 未检测到CF验证，已自动通过")

        return True

    def step3_close_announcement(self):
        """步骤3: 关闭公告"""
        self.log(3, "关闭公告弹窗")

        # 等待公告出现
        time.sleep(2)

        if self.find_and_click('announcement_close', '公告关闭按钮', wait=False):
            print("  [√] 公告已关闭")
            time.sleep(1)
            return True

        # 尝试按ESC
        print("  尝试按ESC关闭...")
        pyautogui.press('escape')
        time.sleep(1)

        print("  [√] 公告处理完成")
        return True

    def step4_click_signin_entry(self):
        """步骤4: 点击签到入口"""
        self.log(4, "点击签到入口")

        if self.find_and_click('signin_entry', '签到入口按钮', wait=True, timeout=15):
            print("  [√] 已点击签到入口，等待跳转到签到页面...")
            time.sleep(self.config['wait_time']['page_load'])
            return True

        print("  [!] 未找到签到入口")
        return False

    def step5_spin_wheel(self):
        """步骤5: 点击转盘开始转动"""
        self.log(5, "开始转动转盘")

        # 等待签到页面加载
        time.sleep(3)

        if self.find_and_click('spin_button', '开始转动按钮', wait=True, timeout=15):
            print("  [√] 已点击开始转动")
            return True

        print("  [!] 未找到转动按钮")
        return False

    def step6_click_wheel_confirm(self):
        """步骤6: 点击转盘结果确定按钮"""
        self.log(6, "等待转盘结果，点击确定")

        spin_time = self.config['wait_time']['wheel_spin']
        print(f"  等待转盘转动 ({spin_time}秒)...")

        # 等待转动
        for i in range(spin_time):
            print(f"  {spin_time - i}秒...", end='\r')
            time.sleep(1)
        print(" " * 20, end='\r')

        # 点击转盘结果确定按钮
        if self.find_and_click('wheel_confirm', '转盘确定按钮', wait=True, timeout=10):
            print("  [√] 已点击确定")
            time.sleep(2)
            return True

        # 尝试按回车
        print("  尝试按回车确认...")
        pyautogui.press('enter')
        time.sleep(2)

        return True

    def step7_wait_and_get_code(self):
        """步骤7: 获取兑换码"""
        self.log(7, "获取兑换码")

        # 等待剪贴板
        print("  等待兑换码复制到剪贴板...")
        time.sleep(self.config['wait_time']['clipboard_wait'])

        # 获取剪贴板内容
        try:
            self.redeem_code = pyperclip.paste()
            if self.redeem_code and len(self.redeem_code) > 0:
                print(f"  [√] 获取到兑换码: {self.redeem_code}")
                return True
            else:
                print("  [!] 剪贴板为空")
        except Exception as e:
            print(f"  [!] 获取剪贴板失败: {e}")

        # 手动输入
        self.redeem_code = input("  请手动输入兑换码: ").strip()
        return bool(self.redeem_code)

    def step8_goto_topup_page(self):
        """步骤8: 前往充值页面"""
        self.log(8, "前往充值页面")
        self.open_url(self.config['topup_url'])

        # 可能需要再次处理CF
        time.sleep(2)
        cf_image = self.config['images'].get('cf_checkbox')
        if cf_image and os.path.exists(cf_image):
            pos = self.finder.wait_for_image(cf_image, timeout=5,
                                             confidence=self.config['confidence'],
                                             silent=True)
            if pos:
                print("  [!] 检测到CF验证框")
                self.mouse.click(pos[0], pos[1])
                time.sleep(self.config['wait_time']['cf_verify'])

        return True

    def step9_paste_redeem_code(self):
        """步骤9: 粘贴兑换码"""
        self.log(9, "粘贴兑换码")

        if not self.redeem_code:
            print("  [!] 没有兑换码")
            return False

        # 确保兑换码在剪贴板
        pyperclip.copy(self.redeem_code)

        # 找到输入框并点击
        if self.find_and_click('redeem_input', '兑换码输入框', wait=True, timeout=15):
            time.sleep(0.5)

            # 清空并粘贴
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)

            print(f"  [√] 已粘贴兑换码: {self.redeem_code}")
            return True

        print("  [!] 未找到兑换码输入框")
        return False

    def step10_click_redeem(self):
        """步骤10: 点击兑换按钮"""
        self.log(10, "点击兑换按钮")

        if self.find_and_click('redeem_button', '兑换按钮', wait=True, timeout=10):
            print("  [√] 已点击兑换")
            time.sleep(2)
            return True

        print("  [!] 未找到兑换按钮")
        return False

    def step11_get_result_and_confirm(self):
        """步骤11: 获取兑换结果并点击确定"""
        self.log(11, "获取兑换结果并点击确定")

        # 等待弹窗出现
        time.sleep(1)

        # 方法1: 使用OCR识别弹窗内容
        print("  使用OCR识别弹窗内容...")
        ocr_result = self.ocr_dialog_region()
        if ocr_result:
            self.result_message = ocr_result
            print(f"  [√] OCR识别结果: {self.result_message}")
        else:
            # 方法2: 尝试识别成功消息图片
            success_img = self.config['images'].get('success_message')
            if success_img and os.path.exists(success_img):
                pos = self.finder.find_on_screen(success_img, 0.7)
                if pos:
                    self.result_message = "兑换成功"
                    print("  [√] 检测到兑换成功提示")

        # 如果还没获取到结果，设置默认消息
        if not self.result_message:
            self.result_message = "兑换操作已完成"
            print("  [?] 未能获取详细结果，使用默认消息")

        # 点击确定按钮
        print("  点击确定按钮...")
        if self.find_and_click('confirm_button', '确定按钮', wait=True, timeout=10):
            print("  [√] 已点击确定")
            time.sleep(1)
            return True

        # 尝试按回车确认
        print("  尝试按回车确认...")
        pyautogui.press('enter')
        time.sleep(1)

        return True

    def ocr_dialog_region(self):
        """OCR识别弹窗区域"""
        try:
            # 获取弹窗区域配置
            region = self.config.get('dialog_region', {})
            x = region.get('x', 600)
            y = region.get('y', 300)
            width = region.get('width', 350)
            height = region.get('height', 150)

            # 截取弹窗区域
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))

            # 保存截图用于调试
            debug_path = 'images/dialog_debug.png'
            screenshot.save(debug_path)
            print(f"  [OCR] 弹窗截图已保存: {debug_path}")

            # 转换为numpy数组
            img_array = np.array(screenshot)

            # 获取OCR读取器
            reader = get_ocr_reader()
            if reader is None:
                print("  [OCR] OCR读取器未加载")
                return None

            # 执行OCR
            results = reader.readtext(img_array)

            # 提取文本
            texts = []
            for (bbox, text, prob) in results:
                if prob > 0.5:  # 置信度阈值
                    texts.append(text)
                    print(f"  [OCR] 识别: {text} (置信度: {prob:.2%})")

            # 合并文本
            if texts:
                full_text = ' '.join(texts)
                # 提取关键信息
                if '兑换' in full_text or '$' in full_text:
                    return full_text
                return full_text

            return None

        except Exception as e:
            print(f"  [OCR] 识别失败: {e}")
            return None

    def ocr_screen_region(self, x, y, width, height):
        """OCR识别指定屏幕区域"""
        try:
            screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
            img_array = np.array(screenshot)

            reader = get_ocr_reader()
            if reader is None:
                return None

            results = reader.readtext(img_array)
            texts = [text for (_, text, prob) in results if prob > 0.5]
            return ' '.join(texts) if texts else None

        except Exception as e:
            print(f"  [OCR] 错误: {e}")
            return None

    def step12_push_result(self):
        """步骤12: 推送结果到微信"""
        self.log(12, "推送结果到微信")

        # 构建推送内容
        title = "签到结果通知"
        content = f"兑换码: {self.redeem_code}\n结果: {self.result_message}\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"

        print(f"  推送内容:")
        print(f"    标题: {title}")
        print(f"    内容: {content}")

        # 推送到微信
        WxPush.send(title, content, self.config['wx_push'])

        return True

    def run(self):
        """执行完整签到流程"""
        print("=" * 60)
        print("           自动签到脚本启动")
        print("=" * 60)
        print(f"主站: {self.config['main_url']}")
        print(f"签到: {self.config['signin_url']}")
        print(f"充值: {self.config['topup_url']}")
        print("=" * 60)

        try:
            # 步骤1: 打开主站
            self.step1_open_main_site()

            # 步骤2: 处理CF验证
            self.step2_handle_cloudflare()

            # 步骤3: 关闭公告
            self.step3_close_announcement()

            # 步骤4: 点击签到入口
            if not self.step4_click_signin_entry():
                print("\n[失败] 无法进入签到页面")
                return False

            # 步骤5: 点击转盘
            if not self.step5_spin_wheel():
                print("\n[失败] 无法开始转盘")
                return False

            # 步骤6: 等待转盘结果，点击确定
            self.step6_click_wheel_confirm()

            # 步骤7: 获取兑换码
            if not self.step7_wait_and_get_code():
                print("\n[失败] 无法获取兑换码")
                return False

            # 步骤8: 前往充值页面
            self.step8_goto_topup_page()

            # 步骤9: 粘贴兑换码
            if not self.step9_paste_redeem_code():
                print("\n[失败] 无法粘贴兑换码")
                return False

            # 步骤10: 点击兑换
            if not self.step10_click_redeem():
                print("\n[失败] 无法点击兑换")
                return False

            # 步骤11: 获取兑换结果并点击确定
            self.step11_get_result_and_confirm()

            # 步骤12: 推送结果到微信
            self.step12_push_result()

            print("\n" + "=" * 60)
            print("           签到流程完成！")
            print("=" * 60)
            return True

        except KeyboardInterrupt:
            print("\n[中断] 用户取消操作")
        except Exception as e:
            print(f"\n[错误] {e}")
            import traceback
            traceback.print_exc()

            # 推送错误信息
            WxPush.send("签到失败", f"错误: {str(e)}", self.config['wx_push'])

        return False


def interactive_mode():
    """交互模式 - 单步执行"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                    交互模式                               ║
╠══════════════════════════════════════════════════════════╣
║  输入数字执行对应步骤，输入 q 退出                         ║
╚══════════════════════════════════════════════════════════╝
    """)

    auto = AutoSignIn(CONFIG)

    steps = {
        '1': ('打开主站', auto.step1_open_main_site),
        '2': ('处理CF验证', auto.step2_handle_cloudflare),
        '3': ('关闭公告', auto.step3_close_announcement),
        '4': ('点击签到入口', auto.step4_click_signin_entry),
        '5': ('转动转盘', auto.step5_spin_wheel),
        '6': ('点击转盘确定', auto.step6_click_wheel_confirm),
        '7': ('获取兑换码', auto.step7_wait_and_get_code),
        '8': ('前往充值页面', auto.step8_goto_topup_page),
        '9': ('粘贴兑换码', auto.step9_paste_redeem_code),
        '10': ('点击兑换', auto.step10_click_redeem),
        '11': ('获取结果并确定', auto.step11_get_result_and_confirm),
        '12': ('推送微信', auto.step12_push_result),
        'a': ('执行全部', auto.run),
    }

    while True:
        print("\n可用步骤:")
        for key, (name, _) in steps.items():
            print(f"  {key:3}: {name}")
        print("  q  : 退出")

        choice = input("\n请选择: ").strip().lower()

        if choice == 'q':
            break
        elif choice in steps:
            name, func = steps[choice]
            print(f"\n执行: {name}")
            print("-" * 40)
            func()
        else:
            print("无效选择")


def test_wx_push():
    """测试微信推送"""
    print("测试微信推送...")
    result = WxPush.send(
        "测试推送",
        f"这是一条测试消息\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        CONFIG['wx_push']
    )
    if result:
        print("[√] 推送成功")
    else:
        print("[x] 推送失败")


def calibrate_dialog_region():
    """校准弹窗区域（用于OCR识别）"""
    print("""
╔══════════════════════════════════════════════════════════╗
║                 校准弹窗区域                              ║
╠══════════════════════════════════════════════════════════╣
║  请先打开网站，触发兑换成功弹窗                            ║
║  然后按照提示确定弹窗区域坐标                              ║
╚══════════════════════════════════════════════════════════╝
    """)

    input("弹窗显示后按回车继续...")

    print("\n步骤1: 将鼠标移动到弹窗【左上角】")
    print("5秒后记录位置...")
    for i in range(5, 0, -1):
        print(f"  {i}...", end='\r')
        time.sleep(1)
    x1, y1 = pyautogui.position()
    print(f"\n左上角: ({x1}, {y1})")

    print("\n步骤2: 将鼠标移动到弹窗【右下角】")
    print("5秒后记录位置...")
    for i in range(5, 0, -1):
        print(f"  {i}...", end='\r')
        time.sleep(1)
    x2, y2 = pyautogui.position()
    print(f"\n右下角: ({x2}, {y2})")

    width = x2 - x1
    height = y2 - y1

    print(f"""
╔══════════════════════════════════════════════════════════╗
║                 校准结果                                  ║
╠══════════════════════════════════════════════════════════╣
║  请将以下配置复制到 auto_signin.py 的 CONFIG 中：         ║
╚══════════════════════════════════════════════════════════╝

    'dialog_region': {{
        'x': {x1},
        'y': {y1},
        'width': {width},
        'height': {height},
    }},
    """)

    # 测试截图
    print("\n测试截图...")
    screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
    test_path = 'images/dialog_calibrate_test.png'
    screenshot.save(test_path)
    print(f"测试截图已保存: {test_path}")

    # 测试OCR
    test_ocr = input("\n是否测试OCR识别？(y/n): ").strip().lower()
    if test_ocr == 'y':
        print("正在进行OCR识别...")
        img_array = np.array(screenshot)
        reader = get_ocr_reader()
        if reader:
            results = reader.readtext(img_array)
            print("\nOCR识别结果:")
            for (bbox, text, prob) in results:
                print(f"  - {text} (置信度: {prob:.2%})")
        else:
            print("OCR加载失败")


def test_ocr_current_screen():
    """测试当前屏幕的OCR识别"""
    print("测试OCR识别当前弹窗区域...")

    region = CONFIG.get('dialog_region', {})
    x = region.get('x', 600)
    y = region.get('y', 300)
    width = region.get('width', 350)
    height = region.get('height', 150)

    print(f"识别区域: ({x}, {y}) - ({x+width}, {y+height})")

    # 截图
    screenshot = ImageGrab.grab(bbox=(x, y, x + width, y + height))
    test_path = 'images/ocr_test.png'
    screenshot.save(test_path)
    print(f"截图已保存: {test_path}")

    # OCR
    img_array = np.array(screenshot)
    reader = get_ocr_reader()
    if reader:
        results = reader.readtext(img_array)
        print("\nOCR识别结果:")
        if results:
            for (bbox, text, prob) in results:
                print(f"  - {text} (置信度: {prob:.2%})")
        else:
            print("  (未识别到文字)")
    else:
        print("OCR加载失败")


if __name__ == "__main__":
    os.makedirs('images', exist_ok=True)

    print("""
╔══════════════════════════════════════════════════════════╗
║              网站自动签到工具 v3.0                        ║
╠══════════════════════════════════════════════════════════╣
║  1. 自动执行全部流程                                      ║
║  2. 交互模式（单步执行）                                  ║
║  3. 测试微信推送                                          ║
║  4. 校准弹窗区域（OCR用）                                 ║
║  5. 测试OCR识别                                           ║
║  0. 退出                                                  ║
╚══════════════════════════════════════════════════════════╝
    """)

    choice = input("请选择模式: ").strip()

    if choice == '1':
        auto = AutoSignIn(CONFIG)
        auto.run()
    elif choice == '2':
        interactive_mode()
    elif choice == '3':
        test_wx_push()
    elif choice == '4':
        calibrate_dialog_region()
    elif choice == '5':
        test_ocr_current_screen()
    else:
        print("退出")
