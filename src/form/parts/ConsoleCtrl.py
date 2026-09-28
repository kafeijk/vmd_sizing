# -*- coding: utf-8 -*-
#

import wx
from utils.MLogger import MLogger # noqa

logger = MLogger(__name__)


class ConsoleCtrl(wx.TextCtrl):

    def __init__(self, parent, logging_level, id=wx.ID_ANY, value="", pos=wx.DefaultPosition, size=wx.DefaultSize, style=0, validator=wx.DefaultValidator, name=wx.TextCtrlNameStr):
        super().__init__(parent, id, value, pos, size, style, validator, name)
        self.limit_cnt = 10

        if logging_level <= MLogger.DEBUG:
            # 调试版汇总输出
            self.limit_cnt = 5000

        self.texts = ""

    def write(self, text, stack=False):
        try:
            self.texts += text

            if len(self.texts) > self.limit_cnt and stack:
                # 仅当超过一定字符数时输出
                wx.CallAfter(self.AppendText, self.texts)
                self.texts = ""
            elif not stack:
                # 非stack时，直接输出
                wx.CallAfter(self.AppendText, self.texts)
                self.texts = ""

        except: # noqa
            pass

    # def monitor(self, queue):
    #     while True:
    #         # super().write(queue.get())
    #         wx.CallAfter(queue.get())
    #         # 等待0.1秒
    #         time.sleep(0.1)

