# -*- coding: utf-8 -*-
#
import wx
import wx.xrc
from abc import ABCMeta, abstractmethod
from threading import Thread
from functools import wraps
import time
import threading

from utils import MFormUtils # noqa
from utils.MLogger import MLogger # noqa

logger = MLogger(__name__)


# https://wiki.wxpython.org/LongRunningTasks
# https://teratail.com/questions/158458
# http://nobunaga.hatenablog.jp/entry/2016/06/03/204450
class BaseWorkerThread(metaclass=ABCMeta):

    """Worker Thread Class."""
    def __init__(self, frame, result_event, console):
        """Init Worker Thread Class."""
        # Thread.__init__(self)
        self.frame = frame
        # self._want_abort = 0
        self.event_id = wx.NewId()
        self.result_event = result_event
        self.result = True
        self.monitor = None
        self.is_killed = False

    def start(self):
        self.run()

    def stop(self):
        self.is_killed = True

    def run(self):
        # 线程执行
        self.thread_event()

        # 执行后处理
        self.post_event()
    
    def post_event(self):
        wx.PostEvent(self.frame, self.result_event(result=self.result))
    
    @abstractmethod
    def thread_event(self):
        pass

    @abstractmethod
    def thread_delete(self):
        pass


# https://doloopwhile.hatenablog.com/entry/20090627/1275175850
class SimpleThread(Thread):
    """ 仅执行可调用对象（函数等）的线程 """
    def __init__(self, base_thread, acallable):
        self.base_thread = base_thread
        self.acallable = acallable
        self._result = None
        super(SimpleThread, self).__init__(name="simple_thread", kwargs={"is_killed": False})
    
    def run(self):
        self._result = self.acallable(self.base_thread)
    
    def result(self):
        return self._result


def task_takes_time(acallable):
    """
    函数装饰器
    在另一个线程中执行acallable原本的处理，
    同时持续调用用于更新窗口的wx.YieldIfNeeded
    """
    @wraps(acallable)
    def f(base_thread):
        t = SimpleThread(base_thread, acallable)
        t.daemon = True
        t.start()
        while t.is_alive():
            base_thread.gauge_ctrl.Pulse()
            wx.YieldIfNeeded()
            time.sleep(0.01)

            if base_thread.is_killed:
                # 调用方发出停止指令时，向除自身以外的所有线程发出结束指令
                for th in threading.enumerate():
                    if th.ident != threading.current_thread().ident:
                        th._kwargs["is_killed"] = True
                break
        
        return t.result()
    return f


# 将字符串输出到控制台
def monitering(console, queue):
    while True:
        try:
            console.write(queue.get(timeout=3))
            wx.Yield()
        except Exception:
            pass

