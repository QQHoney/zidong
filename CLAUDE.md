# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a website auto sign-in automation tool (网站自动签到工具) that automates a multi-step sign-in and redemption process for x666.me using image recognition and GUI automation.

## Commands

```bash
# Install dependencies
pip install pyautogui pillow opencv-python pyperclip requests easyocr

# Run the capture tool to create image templates
python capture_tool.py

# Run the main sign-in script
python auto_signin.py
```

## Architecture

### Core Components

- **auto_signin.py** - Main automation script with 12-step sign-in flow:
  1. Opens main site → 2. Handles CloudFlare → 3. Closes announcements → 4. Clicks sign-in entry → 5. Spins wheel → 6. Confirms wheel result → 7. Gets redemption code → 8. Goes to top-up page → 9. Pastes code → 10. Clicks redeem → 11. Gets result via OCR → 12. Pushes to WeChat

- **capture_tool.py** - Utility for capturing UI element screenshots used as templates for image matching

- **images/** - Directory containing PNG templates for image recognition (buttons, input fields, dialogs)

### Key Classes

- `ImageFinder` - OpenCV-based template matching for locating UI elements on screen
- `HumanMouse` - Simulates human-like mouse movements using Bezier curves
- `AutoSignIn` - Main orchestrator class with step-by-step execution methods
- `WxPush` - WeChat notification integration

### Configuration

All settings are in the `CONFIG` dict at the top of auto_signin.py:
- URLs for main site, sign-in page, and top-up page
- WeChat push notification settings
- Image template paths
- Timing parameters (page load, verification wait, wheel spin duration)
- Dialog region coordinates for OCR

### Image Recognition Flow

1. Templates are captured using capture_tool.py (100x100px around mouse cursor or custom region)
2. At runtime, screenshots are taken and matched against templates using `cv2.matchTemplate`
3. Confidence threshold (default 0.8) determines match success
4. OCR (EasyOCR) is used for reading dialog text when image matching isn't sufficient
