# -*- coding: utf-8 -*-
#
import wx
from wx.core import TreeItemId
import wx.lib.newevent
import sys

from form.panel.BasePanel import BasePanel
from form.parts.SizingFileSet import SizingFileSet
from form.parts.ConsoleCtrl import ConsoleCtrl
from form.parts.StatusCtrl import StatusCtrl
from module.MMath import MRect, MVector3D, MVector4D, MQuaternion, MMatrix4x4 # noqa
from utils import MFormUtils, MFileUtils # noqa
from utils.MLogger import MLogger # noqa

logger = MLogger(__name__)
TIMER_ID = wx.NewId()


class FilePanel(BasePanel):
    
    def __init__(self, frame: wx.Frame, parent: wx.Notebook, tab_idx: int, file_hitories: dict):
        super().__init__(frame, parent, tab_idx)
        self.file_hitories = file_hitories
        self.timer = None
        self.tree_process_dict = {}

        # 文件集
        self.file_set = SizingFileSet(frame, self, self.file_hitories, 1)
        self.sizer.Add(self.file_set.set_sizer, 0, wx.ALL, 0)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 转换前检查按钮
        self.check_btn_ctrl = wx.Button(self, wx.ID_ANY, u"转换前检查", wx.DefaultPosition, wx.Size(200, 50), 0)
        self.check_btn_ctrl.SetToolTip(u"检查依据已输入的文件信息是否可以执行处理。")
        self.check_btn_ctrl.Bind(wx.EVT_LEFT_DCLICK, self.on_doubleclick)
        self.check_btn_ctrl.Bind(wx.EVT_LEFT_DOWN, self.on_check_click)
        btn_sizer.Add(self.check_btn_ctrl, 0, wx.ALL, 5)

        # 执行按钮
        self.exec_btn_ctrl = wx.Button(self, wx.ID_ANY, u"执行VMD适配", wx.DefaultPosition, wx.Size(200, 50), 0)
        self.exec_btn_ctrl.SetToolTip(u"执行VMD适配处理。")
        self.exec_btn_ctrl.Bind(wx.EVT_LEFT_DCLICK, self.on_doubleclick)
        self.exec_btn_ctrl.Bind(wx.EVT_LEFT_DOWN, self.on_exec_click)
        btn_sizer.Add(self.exec_btn_ctrl, 0, wx.ALL, 5)

        self.sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.SHAPED, 5)

        # 控制台
        self.console_ctrl = ConsoleCtrl(self, self.frame.logging_level, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(-1, -1), \
                                        wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_NONE | wx.HSCROLL | wx.VSCROLL | wx.WANTS_CHARS)
        self.console_ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        self.console_ctrl.Bind(wx.EVT_CHAR, lambda event: MFormUtils.on_select_all(event, self.console_ctrl))
        self.sizer.Add(self.console_ctrl, 1, wx.ALL | wx.EXPAND, 5)

        status_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 进度对话框
        self.process_dialog = None

        # 进度状态
        self.before_bracket_ctrl = wx.TextCtrl(self, wx.ID_ANY, "(", wx.DefaultPosition, wx.Size(5, -1), wx.TE_READONLY | wx.BORDER_NONE | wx.WANTS_CHARS)
        self.before_bracket_ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        status_sizer.Add(self.before_bracket_ctrl, 0, wx.ALIGN_LEFT, 5)

        self.now_process_ctrl = StatusCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(20, -1), wx.TE_READONLY | wx.BORDER_NONE | wx.WANTS_CHARS)
        self.now_process_ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        self.now_process_ctrl.SetToolTip(u"当前已进行的大致处理数。点击后会以对话框显示具体的处理进度。")
        self.now_process_ctrl.Bind(wx.EVT_LEFT_DOWN, self.show_process_dialog)
        status_sizer.Add(self.now_process_ctrl, 0, wx.ALIGN_LEFT, 5)

        self.slash_ctrl = wx.TextCtrl(self, wx.ID_ANY, "/", wx.DefaultPosition, wx.Size(5, -1), wx.TE_READONLY | wx.BORDER_NONE | wx.WANTS_CHARS)
        self.slash_ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        status_sizer.Add(self.slash_ctrl, 0, wx.ALIGN_LEFT, 5)

        self.total_process_ctrl = StatusCtrl(self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(20, -1), wx.TE_READONLY | wx.BORDER_NONE | wx.WANTS_CHARS)
        self.total_process_ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        self.total_process_ctrl.SetToolTip(u"整体的大致处理数。点击后会以对话框显示具体的处理进度。")
        self.total_process_ctrl.Bind(wx.EVT_LEFT_DOWN, self.show_process_dialog)
        status_sizer.Add(self.total_process_ctrl, 0, wx.ALIGN_LEFT, 5)

        self.after_bracket_ctrl = wx.TextCtrl(self, wx.ID_ANY, ")", wx.DefaultPosition, wx.Size(5, -1), wx.TE_READONLY | wx.BORDER_NONE | wx.WANTS_CHARS)
        self.after_bracket_ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        status_sizer.Add(self.after_bracket_ctrl, 0, wx.ALIGN_LEFT, 5)

        # 进度条
        self.gauge_ctrl = wx.Gauge(self, wx.ID_ANY, 100, wx.DefaultPosition, wx.Size(550, -1), wx.GA_HORIZONTAL)
        self.gauge_ctrl.SetValue(0)
        status_sizer.Add(self.gauge_ctrl, 0, wx.ALL | wx.EXPAND, 5)

        self.sizer.Add(status_sizer, 0, wx.ALL, 0)

        self.fit()
    
    def show_process_dialog(self, event: wx.Event):
        if self.process_dialog:
            # 若已存在则先销毁
            self.process_dialog.Destroy()

        self.process_dialog = ProcessDialog(self.frame, self)
        self.process_dialog.Show()

        event.Skip()

    # 多进程用的 flush
    def print(self, txt):
        print(txt)
        wx.GetApp().Yield()

    # 禁用表单
    def disable(self):
        self.file_set.disable()
        self.check_btn_ctrl.Disable()
        self.exec_btn_ctrl.Disable()

    # 禁用表单
    def enable(self):
        self.file_set.enable()
        self.check_btn_ctrl.Enable()
        self.exec_btn_ctrl.Enable()
    
    def on_doubleclick(self, event: wx.Event):
        self.timer.Stop()
        logger.warning("检测到双击操作。", decoration=MLogger.DECORATION_BOX)
        event.Skip(False)
        return False
    
    def on_check_click(self, event: wx.Event):
        self.timer = wx.Timer(self, TIMER_ID)
        self.timer.Start(200)
        self.Bind(wx.EVT_TIMER, self.on_check, id=TIMER_ID)

    # 执行前检查
    def on_check(self, event: wx.Event):
        self.timer.Stop()
        self.Unbind(wx.EVT_TIMER, id=TIMER_ID)
        # 将输出目标改为文件面板的控制台
        sys.stdout = self.console_ctrl

        if self.check_btn_ctrl.GetLabel() == "停止读取处理" and self.frame.load_worker:
            # 禁用表单
            self.disable()
            # 处于停止状态时按下按钮则停止
            self.frame.load_worker.stop()

            # 允许切换标签页
            self.frame.release_tab()
            # 启用表单
            self.frame.enable()
            # 结束工作线程
            self.frame.load_worker = None
            # 隐藏进度条
            self.gauge_ctrl.SetValue(0)

            logger.warning("正在中断读取处理。", decoration=MLogger.DECORATION_BOX)
            
            event.Skip(False)
        elif not self.frame.load_worker:
            # 禁用表单
            self.disable()
            # 固定标签页
            self.fix_tab()
            # 清空控制台
            self.console_ctrl.Clear()

            # 保存历史记录
            self.save()

            # 先执行一次读取（随后直接进行检查）
            self.frame.load(event, target_idx=0)
            
            event.Skip()
        else:
            logger.error("处理仍在执行中，请结束后再重新执行。", decoration=MLogger.DECORATION_BOX)
            event.Skip(False)

    def on_exec_click(self, event: wx.Event):
        self.timer = wx.Timer(self, TIMER_ID)
        self.timer.Start(200)
        self.Bind(wx.EVT_TIMER, self.on_exec, id=TIMER_ID)

    # 执行适配
    def on_exec(self, event: wx.Event):
        if self.timer:
            self.timer.Stop()
            self.Unbind(wx.EVT_TIMER, id=TIMER_ID)
            
        # 将输出目标改为文件面板的控制台
        sys.stdout = self.console_ctrl

        if self.exec_btn_ctrl.GetLabel() == "停止VMD适配" and self.frame.worker:
            # 禁用表单
            self.disable()
            # 处于停止状态时按下按钮则停止
            self.frame.worker.stop()

            # 允许切换标签页
            self.frame.release_tab()
            # 启用表单
            self.frame.enable()
            # 结束工作线程
            self.frame.worker = None
            # 隐藏进度条
            self.gauge_ctrl.SetValue(0)

            logger.warning("正在中断VMD适配。", decoration=MLogger.DECORATION_BOX)
            
            event.Skip(False)
        elif not self.frame.worker:
            # 禁用表单
            self.disable()
            # 固定标签页
            self.fix_tab()
            # 清空控制台
            self.console_ctrl.Clear()

            # 保存历史记录
            self.save()

            # 检查是否可适配后再执行
            self.frame.load(event, is_exec=True, target_idx=0)
            
            event.Skip()
        else:
            logger.error("处理仍在执行中，请结束后再重新执行。", decoration=MLogger.DECORATION_BOX)
            event.Skip(False)

    def set_output_vmd_path(self, event, is_force=False):
        self.file_set.set_output_vmd_path(event, is_force)
        # 同时更改相机输出路径
        self.frame.camera_panel_ctrl.header_panel.set_output_vmd_path(event, is_force)

    def save(self):

        # 保存历史记录
        self.frame.file_panel_ctrl.file_set.save()

        # multi 的全部也一并保存
        for file_set in self.frame.multi_panel_ctrl.file_set_list:
            file_set.save()

        # 保存相机历史记录
        self.frame.camera_panel_ctrl.save()

        # 保存相机源模型
        for camera_set in self.frame.camera_panel_ctrl.camera_set_dict.values():
            camera_set.camera_model_file_ctrl.save()

        # JSON输出
        MFileUtils.save_history(self.frame.mydir_path, self.frame.file_hitories)


class ProcessDialog(wx.Dialog):

    def __init__(self, frame: wx.Frame, panel: wx.Panel):
        super().__init__(frame, id=wx.ID_ANY, title="进度对话框", pos=(-1, -1), size=(700, 450), style=wx.DEFAULT_DIALOG_STYLE | wx.STAY_ON_TOP)

        self.frame = frame
        self.panel = panel

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        # 数据树
        self.tree_ctrl = wx.TreeCtrl(self, id=wx.ID_ANY, pos=(-1, -1), size=(650, 400), style=wx.TR_ROW_LINES)
        # 初始化
        self.initialize(self.panel.tree_process_dict)

        self.sizer.Add(self.tree_ctrl, 0, wx.ALL, 5)

        self.SetSizer(self.sizer)
        self.sizer.Layout()
        
        # 显示在屏幕中央
        self.CentreOnScreen()
        
        # 初始时先隐藏
        self.Hide()

    # 初始化
    def initialize(self, tree_dict: dict):
        # Root
        tr_root_ctrl = self.tree_ctrl.AddRoot(text="VMD适配")

        # 追加树节点
        self.append_tree(tree_dict, tr_root_ctrl)

    # 追加树节点
    def append_tree(self, item_dict: dict, parent_ctrl: TreeItemId):
        for tk, tv in item_dict.items():
            if isinstance(tv, bool) and tv:
                # 处理已结束时，追加图标
                display_ctrl = self.tree_ctrl.AppendItem(parent=parent_ctrl, text=("○ {0}".format(tk)))
                self.tree_ctrl.SetItemTextColour(display_ctrl, "BLUE")
            elif isinstance(tv, bool) and not tv:
                # 尚未结束的情况
                display_ctrl = self.tree_ctrl.AppendItem(parent=parent_ctrl, text=("－ {0}".format(tk)))
                self.tree_ctrl.SetItemTextColour(display_ctrl, "GREY")
            else:
                display_ctrl = self.tree_ctrl.AppendItem(parent=parent_ctrl, text=tk)

            if isinstance(tv, dict):
                # 下层为字典时，循环递归
                self.append_tree(tv, display_ctrl)
            
        self.tree_ctrl.ExpandAllChildren(parent_ctrl)

