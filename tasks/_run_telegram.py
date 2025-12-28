# -*- coding: utf-8 -*-
import sys
import json
sys.path.insert(0, r"C:\Users\Administrator\Desktop\新建文件夹")
from auto_task_gui import TaskConfig, CodeGenerator

config = TaskConfig()
config.load(r"C:/Users/Administrator/Desktop/新建文件夹/tasks/Telegram.json")
generator = CodeGenerator()
code = generator.generate(config.step_manager)
exec(code.split("if __name__")[0] + "main()")
