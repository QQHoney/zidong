# -*- coding: utf-8 -*-
"""
定时任务管理器
支持添加、删除、查看定时任务
"""

import os
import sys
import json
import subprocess
from datetime import datetime

SCHEDULER_CONFIG = "tasks/scheduler_config.json"

def load_config():
    """加载定时任务配置"""
    if os.path.exists(SCHEDULER_CONFIG):
        with open(SCHEDULER_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"tasks": []}

def save_config(config):
    """保存定时任务配置"""
    os.makedirs("tasks", exist_ok=True)
    with open(SCHEDULER_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def create_windows_task(task_name, task_file, run_time, script_dir):
    """创建 Windows 计划任务"""
    python_exe = sys.executable
    
    # 创建运行脚本
    runner_script = os.path.join(script_dir, "tasks", f"_run_{task_name}.py")
    with open(runner_script, 'w', encoding='utf-8') as f:
        f.write(f'''# -*- coding: utf-8 -*-
import sys
import json
sys.path.insert(0, r"{script_dir}")
from auto_task_gui import TaskConfig, CodeGenerator

config = TaskConfig()
config.load(r"{task_file}")
generator = CodeGenerator()
code = generator.generate(config.step_manager)
exec(code.split("if __name__")[0] + "main()")
''')
    
    # 使用 schtasks 创建计划任务
    hour, minute = run_time.split(":")
    cmd = f'schtasks /create /tn "AutoTask_{task_name}" /tr "\\"{python_exe}\\" \\"{runner_script}\\"" /sc daily /st {run_time} /f'
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stderr or result.stdout

def delete_windows_task(task_name):
    """删除 Windows 计划任务"""
    cmd = f'schtasks /delete /tn "AutoTask_{task_name}" /f'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0

def list_windows_tasks():
    """列出所有 AutoTask 计划任务"""
    cmd = 'schtasks /query /fo csv | findstr "AutoTask_"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout

def add_scheduled_task(task_file, run_time, task_name=None):
    """添加定时任务"""
    if not os.path.exists(task_file):
        return False, f"任务文件不存在: {task_file}"
    
    if not task_name:
        task_name = os.path.splitext(os.path.basename(task_file))[0]
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    success, msg = create_windows_task(task_name, task_file, run_time, script_dir)
    
    if success:
        config = load_config()
        config["tasks"].append({
            "name": task_name,
            "file": task_file,
            "time": run_time,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_config(config)
        return True, f"定时任务已创建: {task_name} 每天 {run_time} 运行"
    return False, msg

def remove_scheduled_task(task_name):
    """删除定时任务"""
    success = delete_windows_task(task_name)
    if success:
        config = load_config()
        config["tasks"] = [t for t in config["tasks"] if t["name"] != task_name]
        save_config(config)
    return success

def list_scheduled_tasks():
    """列出所有定时任务"""
    config = load_config()
    return config.get("tasks", [])

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║                   定时任务管理器                          ║
╠══════════════════════════════════════════════════════════╣
║  1. 添加定时任务                                          ║
║  2. 删除定时任务                                          ║
║  3. 查看所有定时任务                                      ║
║  0. 退出                                                  ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    while True:
        choice = input("\n请选择: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            task_file = input("任务文件路径 (如 tasks/example.json): ").strip()
            run_time = input("运行时间 (如 08:00): ").strip()
            task_name = input("任务名称 (可选，回车使用文件名): ").strip() or None
            success, msg = add_scheduled_task(task_file, run_time, task_name)
            print(f"{'[√]' if success else '[x]'} {msg}")
        elif choice == "2":
            tasks = list_scheduled_tasks()
            if not tasks:
                print("没有定时任务")
                continue
            print("\n当前定时任务:")
            for i, t in enumerate(tasks, 1):
                print(f"  {i}. {t['name']} - {t['time']} - {t['file']}")
            idx = input("输入要删除的序号: ").strip()
            try:
                task = tasks[int(idx) - 1]
                if remove_scheduled_task(task["name"]):
                    print(f"[√] 已删除: {task['name']}")
                else:
                    print("[x] 删除失败")
            except (ValueError, IndexError):
                print("无效输入")
        elif choice == "3":
            tasks = list_scheduled_tasks()
            if not tasks:
                print("没有定时任务")
            else:
                print("\n定时任务列表:")
                for t in tasks:
                    print(f"  - {t['name']}: 每天 {t['time']} 运行 ({t['file']})")
