# -*- coding: utf-8 -*-
#

import os
import wx
import sys
import logging
import argparse
import numpy as np
import traceback
import multiprocessing

from form.MainFrame import MainFrame
from module.MOptions import MOptions
from utils.MLogger import MLogger
from utils import MFileUtils
from service.SizingService import SizingService
from utils.MException import SizingException

VERSION_NAME = "ver5.01.08_CN_1.0.0"

# 不使用指数计数法，有效小数位数6，超过30则省略，每行字符数200
np.set_printoptions(suppress=True, precision=6, threshold=30, linewidth=200)

# Windows 多进程对策
multiprocessing.freeze_support()

if __name__ == '__main__':
    mydir_path = MFileUtils.get_mydir_path(sys.argv[0])

    if len(sys.argv) > 3 and "--motion_path" in sys.argv:
        if os.name == "nt":
            import winsound     # 仅 Windows 下导入

        # 有参数指定时，以命令行方式执行
        try:
            SizingService(MOptions.parse(VERSION_NAME)).execute()
        except SizingException as se:
            print("适配处理因数据无法处理而结束。\n\n%s", se.message)
        except Exception:
            print("适配处理因意外错误而结束。")
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
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument("--verbose", default=20, type=int)
        parser.add_argument("--out_log", default=0, type=int)
        parser.add_argument("--is_saving", default=1, type=int)
        args = parser.parse_args()
        
        # 日志级别
        is_out_log = True if args.out_log == 1 else False
        # 省电模式
        is_saving = True if args.is_saving == 1 else False

        MLogger.initialize(level=args.verbose, is_file=False)

        log_level_name = ""
        if args.verbose == MLogger.FULL:
            # 完整数据的情况
            log_level_name = "（全量输出版）"
        elif args.verbose == MLogger.DEBUG_FULL:
            # 完整数据的情况
            log_level_name = "（全量输出调试版）"
        elif args.verbose == MLogger.DEBUG:
            # 测试（调试版）的情况
            log_level_name = "（调试版）"
        elif args.verbose == MLogger.TIMER:
            # 计时测试的情况
            log_level_name = "（计时版）"
        elif not is_saving:
            # 省电模式关闭的情况
            log_level_name = "（高性能版）"
        elif is_out_log:
            # 带日志的情况
            log_level_name = "（带日志版）"

        now_version_name = "{0}{1}".format(VERSION_NAME, log_level_name)

        # 无参数指定时，正常启动
        app = wx.App(False)
        icon = wx.Icon(MFileUtils.resource_path('src/vmdsizing.ico'), wx.BITMAP_TYPE_ICO)
        frame = MainFrame(None, mydir_path, now_version_name, args.verbose, is_saving, is_out_log)
        frame.SetIcon(icon)
        frame.Show(True)
        app.MainLoop()
