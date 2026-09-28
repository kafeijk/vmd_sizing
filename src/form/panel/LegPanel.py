# -*- coding: utf-8 -*-
#
import wx
import wx.lib.newevent
import numpy as np

from form.panel.BasePanel import BasePanel
from form.parts.FloatSliderCtrl import FloatSliderCtrl
from form.parts.SizingFileSet import SizingFileSet
from utils.MLogger import MLogger # noqa

logger = MLogger(__name__)


class LegPanel(BasePanel):
    
    def __init__(self, frame: wx.Frame, parent: wx.Notebook, tab_idx: int):
        super().__init__(frame, parent, tab_idx)

        # 整体移动量修正 --------------------

        move_correction_tooltip = "可对センター・足ＩＫ等位移类骨骼的整体移动量进行修正。\n适用于希望整体拉宽多人动作的队形，或想让动作更具张力等情况"
        self.move_correction_title_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 整体移动量修正标题
        self.move_correction_title_txt = wx.StaticText(self, wx.ID_ANY, u"整体移动量修正", wx.DefaultPosition, wx.DefaultSize, 0)
        self.move_correction_title_txt.SetToolTip(move_correction_tooltip)
        self.move_correction_title_txt.Wrap(-1)
        self.move_correction_title_txt.SetFont(wx.Font(wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, wx.EmptyString))
        self.move_correction_title_sizer.Add(self.move_correction_title_txt, 0, wx.ALL, 5)
        self.sizer.Add(self.move_correction_title_sizer, 0, wx.ALL, 5)

        # 整体移动量修正说明文字
        self.move_correction_description_txt = wx.StaticText(self, wx.ID_ANY, move_correction_tooltip, wx.DefaultPosition, wx.DefaultSize, 0)
        self.sizer.Add(self.move_correction_description_txt, 0, wx.ALL, 5)

        # 整体移动量修正滑块
        self.move_correction_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.move_correction_txt = wx.StaticText(self, wx.ID_ANY, u"整体移动量修正值", wx.DefaultPosition, wx.DefaultSize, 0)
        self.move_correction_txt.SetToolTip(u"这是对身高比例施加的修正值。默认为单人时设为1，多人时设为头身比例。")
        self.move_correction_txt.Wrap(-1)
        self.move_correction_sizer.Add(self.move_correction_txt, 0, wx.ALL, 5)

        self.move_correction_label = wx.StaticText(self, wx.ID_ANY, u"（1）", wx.DefaultPosition, wx.DefaultSize, 0)
        self.move_correction_label.SetToolTip(u"当前指定的整体移动量修正值。")
        self.move_correction_label.Wrap(-1)
        self.move_correction_sizer.Add(self.move_correction_label, 0, wx.ALL, 5)

        self.move_correction_slider = FloatSliderCtrl(self, wx.ID_ANY, 1, 0.5, 1.5, 0.05, self.move_correction_label, wx.DefaultPosition, wx.DefaultSize, wx.SL_HORIZONTAL)
        self.move_correction_slider.Bind(wx.EVT_SCROLL_CHANGED, self.on_check_move_correction)
        self.move_correction_sizer.Add(self.move_correction_slider, 1, wx.ALL | wx.EXPAND, 5)

        self.sizer.Add(self.move_correction_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.static_line01 = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.sizer.Add(self.static_line01, 0, wx.EXPAND | wx.ALL, 5)

        # 偏移值
        self.leg_offset_set_dict = {}
        # 偏移用对话框
        self.leg_offset_dialog = LegOffsetDialog(self.frame)

        # 足ＩＫ偏移 --------------------

        # 批量用足ＩＫ偏移数据
        self.bulk_leg_offset_set_dict = {}

        leg_offset_tooltip = "可设置足ＩＫ的移动量偏移。\n适用于双腿并拢时发生重叠，或不想改变整体移动量、只想单独调整个别足ＩＫ移动量等情况"

        # 足ＩＫ偏移 ----------------
        self.leg_offset_title_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 足ＩＫ偏移标题
        self.leg_offset_title_txt = wx.StaticText(self, wx.ID_ANY, u"足ＩＫ偏移", wx.DefaultPosition, wx.DefaultSize, 0)
        self.leg_offset_title_txt.SetToolTip(leg_offset_tooltip)
        self.leg_offset_title_txt.Wrap(-1)
        self.leg_offset_title_txt.SetFont(wx.Font(wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, wx.EmptyString))
        self.leg_offset_title_sizer.Add(self.leg_offset_title_txt, 0, wx.ALL, 5)
        self.sizer.Add(self.leg_offset_title_sizer, 0, wx.ALL, 5)

        # 足ＩＫ偏移说明文字
        self.leg_offset_description_txt = wx.StaticText(self, wx.ID_ANY, leg_offset_tooltip, wx.DefaultPosition, wx.DefaultSize, 0)
        self.sizer.Add(self.leg_offset_description_txt, 0, wx.ALL, 5)

        self.leg_offset_target_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 偏移值指定
        self.leg_offset_target_txt_ctrl = wx.TextCtrl(self, wx.ID_ANY, "", wx.DefaultPosition, (450, 80), wx.HSCROLL | wx.VSCROLL | wx.TE_MULTILINE | wx.TE_READONLY)
        self.leg_offset_target_txt_ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        self.leg_offset_target_sizer.Add(self.leg_offset_target_txt_ctrl, 1, wx.EXPAND | wx.ALL, 5)

        self.leg_offset_target_btn_ctrl = wx.Button(self, wx.ID_ANY, u"偏移指定", wx.DefaultPosition, wx.DefaultSize, 0)
        self.leg_offset_target_btn_ctrl.SetToolTip(u"可指定目标模型的足ＩＫ偏移值")
        self.leg_offset_target_btn_ctrl.Bind(wx.EVT_BUTTON, self.on_click_leg_offset_target)
        self.leg_offset_target_sizer.Add(self.leg_offset_target_btn_ctrl, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)

        self.sizer.Add(self.leg_offset_target_sizer, 0, wx.ALL, 0)

        self.static_line03 = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.sizer.Add(self.static_line03, 0, wx.EXPAND | wx.ALL, 5)

        self.fit()
        
    def get_leg_offsets(self):
        if len(self.bulk_leg_offset_set_dict.keys()) > 0:
            # 存在批量数据时，优先返回
            return self.bulk_leg_offset_set_dict

        target = {}
        
        # 将指定的偏移值设置到输入框（仅哈希相同时）
        if 1 in self.leg_offset_set_dict and self.leg_offset_set_dict[1].leg_offset_slider:
            if self.leg_offset_set_dict[1].equal_hashdigest(self.frame.file_panel_ctrl.file_set):
                target[0] = self.leg_offset_set_dict[1].leg_offset_slider.GetValue()
            else:
                logger.warning("【No.%s】足ＩＫ偏移设置后文件集发生变更，因此清除足ＩＫ偏移", 1, decoration=MLogger.DECORATION_BOX)

        for set_no in list(self.leg_offset_set_dict.keys())[1:]:
            if set_no in self.leg_offset_set_dict and self.leg_offset_set_dict[set_no].leg_offset_slider:
                if len(self.frame.multi_panel_ctrl.file_set_list) >= set_no - 1 and self.leg_offset_set_dict[set_no].equal_hashdigest(self.frame.multi_panel_ctrl.file_set_list[set_no - 2]):
                    target[set_no - 1] = self.leg_offset_set_dict[set_no].leg_offset_slider.GetValue()
                else:
                    logger.warning("【No.%s】足ＩＫ偏移设置后文件集发生变更，因此清除足ＩＫ偏移", set_no, decoration=MLogger.DECORATION_BOX)

        return target
    
    def on_click_leg_offset_target(self, event: wx.Event):
        if self.leg_offset_dialog.ShowModal() == wx.ID_CANCEL:
            return     # the user changed their mind

        self.show_leg_offset()

        self.leg_offset_dialog.Hide()
    
    def show_leg_offset(self):
        # 先清空
        self.leg_offset_target_txt_ctrl.SetValue("")

        # 将指定的偏移值设置到输入框
        texts = []
        for set_no, set_data in self.leg_offset_set_dict.items():
            # 每个选项的显示文字
            texts.append("【No.{0}】　{1}".format(set_no, set_data.leg_offset_slider.GetValue()))

        self.leg_offset_target_txt_ctrl.WriteText(" / ".join(texts))

    def initialize(self, event: wx.Event):

        if 1 in self.leg_offset_set_dict:
            # 存在文件标签页用足ＩＫ偏移的文件集时
            if self.frame.file_panel_ctrl.file_set.is_loaded():
                # 已存在时，进行哈希校验
                if self.leg_offset_set_dict[1].equal_hashdigest(self.frame.file_panel_ctrl.file_set):
                    # 相同时则跳过
                    pass
                else:
                    # 不同时则重新读取文件集
                    self.add_set(1, self.frame.file_panel_ctrl.file_set, replace=True)
            else:
                # 文件标签页读取失败时，重新读取（清空）
                self.add_set(1, self.frame.file_panel_ctrl.file_set, replace=True)
        else:
            # 从空白创建时，引用文件标签页的文件集
            self.add_set(1, self.frame.file_panel_ctrl.file_set, replace=False)
        
        # multi 有多少就检查多少
        for multi_file_set_idx, multi_file_set in enumerate(self.frame.multi_panel_ctrl.file_set_list):
            set_no = multi_file_set_idx + 2
            if set_no in self.leg_offset_set_dict:
                # 存在多标签页用足ＩＫ偏移的文件集时
                if multi_file_set.is_loaded():
                    # 已存在时，进行哈希校验
                    if self.leg_offset_set_dict[set_no].equal_hashdigest(multi_file_set):
                        # 相同时则跳过
                        pass
                    else:
                        # 不同时则重新读取文件集
                        self.add_set(set_no, multi_file_set, replace=True)
                else:
                    # 多标签页读取失败时，重新读取（清空）
                    self.add_set(set_no, multi_file_set, replace=True)
            else:
                # 从空白创建时，引用多标签页的文件集
                self.add_set(set_no, multi_file_set, replace=False)

        self.show_leg_offset()

        event.Skip()

    # 生成VMD输出文件路径
    def set_output_vmd_path(self, event, is_force=False):
        # 保险起见自动生成输出文件路径（为空时设置）
        self.frame.file_panel_ctrl.file_set.set_output_vmd_path(event)

        # multi 也自动生成输出文件路径（为空时设置）
        for file_set in self.frame.multi_panel_ctrl.file_set_list:
            file_set.set_output_vmd_path(event)
    
    def on_check_move_correction(self, event: wx.Event):
        # 重新生成路径
        self.set_output_vmd_path(event)

        event.Skip()

    def add_set(self, set_idx: int, file_set: SizingFileSet, replace: bool):
        new_leg_offset_set = LegOffsetSet(self.frame, self, self.leg_offset_dialog.scrolled_window, set_idx, file_set)
        if replace:
            # 替换
            self.leg_offset_dialog.set_list_sizer.Hide(self.leg_offset_set_dict[set_idx].set_sizer, recursive=True)
            self.leg_offset_dialog.set_list_sizer.Replace(self.leg_offset_set_dict[set_idx].set_sizer, new_leg_offset_set.set_sizer, recursive=True)

            # 替换时清空偏移值
            self.leg_offset_target_txt_ctrl.SetValue("")
        else:
            # 新增
            self.leg_offset_dialog.set_list_sizer.Add(new_leg_offset_set.set_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.leg_offset_set_dict[set_idx] = new_leg_offset_set

        # 为显示滚动条而调整尺寸
        self.leg_offset_dialog.set_list_sizer.Layout()
        self.leg_offset_dialog.set_list_sizer.FitInside(self.leg_offset_dialog.scrolled_window)


class LegOffsetSet():

    def __init__(self, frame: wx.Frame, panel: wx.Panel, window: wx.Window, set_idx: int, file_set: SizingFileSet):
        self.frame = frame
        self.panel = panel
        self.window = window
        self.set_idx = set_idx
        self.file_set = file_set
        self.rep_model_digest = 0 if not file_set.rep_model_file_ctrl.data else file_set.rep_model_file_ctrl.data.digest

        self.set_sizer = wx.StaticBoxSizer(wx.StaticBox(self.window, wx.ID_ANY, "【No.{0}】 {1}".format(set_idx, file_set.rep_model_file_ctrl.data.name[:20])), orient=wx.VERTICAL)
        
        # 足ＩＫ偏移值
        self.leg_offset_label = wx.StaticText(self.window, wx.ID_ANY, "（0）", wx.DefaultPosition, wx.DefaultSize, 0)
        self.leg_offset_label.SetToolTip(u"当前指定的足ＩＫ偏移值。该值将实际（考虑朝向后）加算到足ＩＫ上。")
        self.leg_offset_label.Wrap(-1)
        self.set_sizer.Add(self.leg_offset_label, 0, wx.ALL, 5)

        self.leg_offset_slider = FloatSliderCtrl(self.window, wx.ID_ANY, 0, -2, 2, 0.05, self.leg_offset_label, wx.DefaultPosition, wx.DefaultSize, wx.SL_HORIZONTAL)
        self.set_sizer.Add(self.leg_offset_slider, 1, wx.ALL | wx.EXPAND, 5)

    # 检查是否与当前文件集的哈希一致
    def equal_hashdigest(self, now_file_set: SizingFileSet):
        return self.rep_model_digest == now_file_set.rep_model_file_ctrl.data.digest


class LegOffsetDialog(wx.Dialog):

    def __init__(self, parent):
        super().__init__(parent, id=wx.ID_ANY, title="足ＩＫ偏移指定", pos=(-1, -1), size=(800, 500), style=wx.DEFAULT_DIALOG_STYLE, name="LegOffsetDialog")

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        # 说明文字
        self.description_txt = wx.StaticText(self, wx.ID_ANY, u"可设置足ＩＫ的移动量偏移。该值将实际（考虑朝向后）加算到足ＩＫ上。\n" \
                                             + u"多人动作时，若指定的偏移过大，可能会导致队形错乱。\n" , wx.DefaultPosition, wx.DefaultSize, 0)
        self.sizer.Add(self.description_txt, 0, wx.ALL, 5)

        # 按钮
        self.btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ok_btn = wx.Button(self, wx.ID_OK, "OK")
        self.btn_sizer.Add(self.ok_btn, 0, wx.ALL, 5)

        self.calcel_btn = wx.Button(self, wx.ID_CANCEL, "取消")
        self.btn_sizer.Add(self.calcel_btn, 0, wx.ALL, 5)
        self.sizer.Add(self.btn_sizer, 0, wx.ALL, 5)

        self.static_line01 = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.sizer.Add(self.static_line01, 0, wx.EXPAND | wx.ALL, 5)

        self.scrolled_window = wx.ScrolledWindow(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, \
                                                 wx.FULL_REPAINT_ON_RESIZE | wx.VSCROLL | wx.ALWAYS_SHOW_SB)
        self.scrolled_window.SetScrollRate(5, 5)

        # 足ＩＫ偏移集用的基本布局器
        self.set_list_sizer = wx.BoxSizer(wx.VERTICAL)

        # 为显示滚动条而调整尺寸
        self.scrolled_window.SetSizer(self.set_list_sizer)
        self.scrolled_window.Layout()
        self.sizer.Add(self.scrolled_window, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(self.sizer)
        self.sizer.Layout()
        
        # 显示在屏幕中央
        self.CentreOnScreen()
        
        # 初始状态隐藏
        self.Hide()
