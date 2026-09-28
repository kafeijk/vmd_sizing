# -*- coding: utf-8 -*-
#
import numpy as np
import multiprocessing
import traceback
import logging
import os

from module.MOptions import MSmoothOptions
from service.ConvertSmoothService import ConvertSmoothService
from utils.MException import SizingException

# 不使用指数计数法，有效小数位数6，超过30则省略，每行字符数200
np.set_printoptions(suppress=True, precision=6, threshold=30, linewidth=200)

# Windows 多进程对策
multiprocessing.freeze_support()


if __name__ == "__main__":
    if os.name == "nt":
        import winsound     # 仅 Windows 下导入

    # 有参数指定时，以命令行方式执行
    try:
        options = MSmoothOptions.parse("VmdSizing Smooth")

        ConvertSmoothService(options).execute()
    except SizingException as se:
        print("平滑处理因数据无法处理而结束。\n\n%s", se.message)
    except Exception:
        print("平滑处理因意外错误而结束。")
        print(traceback.format_exc())
    finally:
        logging.shutdown()

    # 播放结束提示音
    if os.name == "nt":
        # Windows
        try:
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
        except Exception:
            pass
