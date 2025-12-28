# 网站自动签到工具

## 安装依赖

```bash
pip install pyautogui pillow opencv-python
```

## 使用步骤

### 第一步：截取图片素材

1. 打开浏览器，访问 https://x666.me/
2. 运行截图工具：
   ```bash
   python capture_tool.py
   ```
3. 按照提示截取以下图片：
   - **cf_checkbox.png** - CloudFlare验证框（"验证您是人类"的勾选框）
   - **signin_button.png** - 签到按钮

### 第二步：运行签到脚本

```bash
python auto_signin.py
```

## 文件说明

```
新建文件夹/
├── auto_signin.py    # 主签到脚本
├── capture_tool.py   # 截图工具
├── images/           # 图片素材目录
│   ├── cf_checkbox.png
│   └── signin_button.png
└── README.md         # 本说明文件
```

## 配置说明

在 `auto_signin.py` 中修改 CONFIG：

```python
CONFIG = {
    'url': 'https://x666.me/',      # 目标网站
    'confidence': 0.8,               # 图片匹配度 (0.7-0.9)
    'wait_time': {
        'page_load': 5,              # 页面加载等待秒数
        'cf_verify': 8,              # CF验证等待秒数
    }
}
```

## 定时运行

### Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
3. 设置触发器（每天某个时间）
4. 操作：启动程序
   - 程序：`python`
   - 参数：`auto_signin.py`
   - 起始位置：脚本所在目录

## 注意事项

- 运行时不要移动鼠标
- 确保浏览器窗口可见（不要最小化）
- 如果匹配失败，尝试降低 confidence 值到 0.7
- 截图时确保只截取按钮本身，不要包含太多背景
