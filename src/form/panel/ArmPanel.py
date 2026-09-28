# -*- coding: utf-8 -*-
#
import wx
import wx.lib.newevent
import numpy as np

from form.panel.BasePanel import BasePanel
from form.parts.FloatSliderCtrl import FloatSliderCtrl
from form.parts.SizingFileSet import SizingFileSet
from module.MMath import MRect, MVector3D, MVector4D, MQuaternion, MMatrix4x4 # noqa
from utils.MLogger import MLogger # noqa

logger = MLogger(__name__)


class ArmPanel(BasePanel):
    
    def __init__(self, frame: wx.Frame, parent: wx.Notebook, tab_idx: int):
        super().__init__(frame, parent, tab_idx)

        # 刚体列表
        self.avoidance_set_dict = {}
        # 刚体用对话框
        self.avoidance_dialog = AvoidanceDialog(self.frame)

        avoidance_tooltip = "将规避指定名称的骨骼跟随刚体与手腕、指尖之间的接触。\n请通过选择按钮，选择目标模型中希望规避的骨骼跟随刚体。\n" \
                            + "「頭接触回避」会自动计算以头部为中心的球体刚体。"
        alignment_tooltip = "调整手腕位置，使目标模型的手腕位置与源模型基本保持一致。"

        # 批量用接触规避数据
        self.bulk_avoidance_set_dict = {}

        self.description_txt = wx.StaticText(self, wx.ID_ANY, "可将手臂调整为贴合目标模型。\n「接触规避」与「位置对齐」可同时执行。（按接触规避→位置对齐的顺序执行）" + \
                                             "\n手臂的动作可能会与原始动作有所不同。两者都需要耗费一定的时间。", wx.DefaultPosition, wx.DefaultSize, 0)
        self.sizer.Add(self.description_txt, 0, wx.ALL, 5)

        self.static_line01 = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.sizer.Add(self.static_line01, 0, wx.EXPAND | wx.ALL, 5)

        # 刚体接触规避 ----------------
        self.avoidance_title_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 刚体接触规避标题
        self.avoidance_title_txt = wx.StaticText(self, wx.ID_ANY, u"接触规避", wx.DefaultPosition, wx.DefaultSize, 0)
        self.avoidance_title_txt.SetToolTip(avoidance_tooltip)
        self.avoidance_title_txt.Wrap(-1)
        self.avoidance_title_txt.SetFont(wx.Font(wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, wx.EmptyString))
        self.avoidance_title_txt.Bind(wx.EVT_LEFT_DOWN, self.on_check_arm_process_avoidance)

        self.arm_process_flg_avoidance = wx.CheckBox(self, wx.ID_ANY, u"", wx.DefaultPosition, wx.DefaultSize)
        self.arm_process_flg_avoidance.SetToolTip(avoidance_tooltip)
        self.arm_process_flg_avoidance.Bind(wx.EVT_CHECKBOX, self.set_output_vmd_path)
        self.avoidance_title_sizer.Add(self.arm_process_flg_avoidance, 0, wx.ALL, 5)
        self.avoidance_title_sizer.Add(self.avoidance_title_txt, 0, wx.ALL, 5)
        self.sizer.Add(self.avoidance_title_sizer, 0, wx.ALL, 5)

        # 刚体接触规避说明文字
        self.avoidance_description_txt = wx.StaticText(self, wx.ID_ANY, avoidance_tooltip, wx.DefaultPosition, wx.DefaultSize, 0)
        self.sizer.Add(self.avoidance_description_txt, 0, wx.ALL, 5)

        self.avoidance_target_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 刚体名称指定
        self.avoidance_target_txt_ctrl = wx.TextCtrl(self, wx.ID_ANY, "", wx.DefaultPosition, (450, 80), wx.HSCROLL | wx.VSCROLL | wx.TE_MULTILINE | wx.TE_READONLY)
        self.avoidance_target_txt_ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        self.avoidance_target_txt_ctrl.Bind(wx.EVT_TEXT, self.on_check_arm_process_avoidance)
        self.avoidance_target_sizer.Add(self.avoidance_target_txt_ctrl, 1, wx.EXPAND | wx.ALL, 5)

        self.avoidance_target_btn_ctrl = wx.Button(self, wx.ID_ANY, u"刚体选择", wx.DefaultPosition, wx.DefaultSize, 0)
        self.avoidance_target_btn_ctrl.SetToolTip(u"可选择目标模型中的骨骼跟随刚体")
        self.avoidance_target_btn_ctrl.Bind(wx.EVT_BUTTON, self.on_click_avoidance_target)
        self.avoidance_target_sizer.Add(self.avoidance_target_btn_ctrl, 0, wx.ALIGN_BOTTOM | wx.ALL, 5)

        self.sizer.Add(self.avoidance_target_sizer, 0, wx.ALL, 0)

        self.static_line03 = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.sizer.Add(self.static_line03, 0, wx.EXPAND | wx.ALL, 5)

        # 手腕位置对齐 --------------------
        self.alignment_title_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 手腕位置对齐标题
        self.alignment_title_txt = wx.StaticText(self, wx.ID_ANY, u"位置对齐", wx.DefaultPosition, wx.DefaultSize, 0)
        self.alignment_title_txt.SetToolTip("对于双手合十或以手撑地等动作，将调整为贴合目标模型的手腕位置。\n" + \
                                            "通过调整各项距离，可以调整位置对齐的适用范围。")
        self.alignment_title_txt.Wrap(-1)
        self.alignment_title_txt.SetFont(wx.Font(wx.NORMAL_FONT.GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, wx.EmptyString))
        self.alignment_title_txt.Bind(wx.EVT_LEFT_DOWN, self.on_check_arm_process_alignment)

        self.arm_process_flg_alignment = wx.CheckBox(self, wx.ID_ANY, u"", wx.DefaultPosition, wx.DefaultSize)
        self.arm_process_flg_alignment.SetToolTip(alignment_tooltip)
        self.arm_process_flg_alignment.Bind(wx.EVT_CHECKBOX, self.set_output_vmd_path)
        self.alignment_title_sizer.Add(self.arm_process_flg_alignment, 0, wx.ALL, 5)
        self.alignment_title_sizer.Add(self.alignment_title_txt, 0, wx.ALL, 5)
        self.sizer.Add(self.alignment_title_sizer, 0, wx.ALL, 5)

        # 手腕位置对齐说明文字
        self.alignment_description_txt = wx.StaticText(self, wx.ID_ANY, alignment_tooltip, wx.DefaultPosition, wx.DefaultSize, 0)
        self.sizer.Add(self.alignment_description_txt, 0, wx.ALL, 5)

        # 选项布局
        self.alignment_option_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 手指位置对齐
        self.arm_alignment_finger_flg_ctrl = wx.CheckBox(self, wx.ID_ANY, u"按手指位置进行位置对齐", wx.DefaultPosition, wx.DefaultSize, 0)
        self.arm_alignment_finger_flg_ctrl.SetToolTip(u"勾选后，可针对手指TUT等动作，以手指之间的距离为基准调整手腕位置。" \
                                                      + "多人动作时保持关闭状态效果更佳。")
        self.arm_alignment_finger_flg_ctrl.Bind(wx.EVT_CHECKBOX, self.on_check_arm_process_alignment)
        self.alignment_option_sizer.Add(self.arm_alignment_finger_flg_ctrl, 0, wx.ALL, 5)

        # 地面位置对齐
        self.arm_alignment_floor_flg_ctrl = wx.CheckBox(self, wx.ID_ANY, u"同时与地面进行位置对齐", wx.DefaultPosition, wx.DefaultSize, 0)
        self.arm_alignment_floor_flg_ctrl.SetToolTip(u"勾选后，当手腕陷入地面或浮空时，可按源模型调整手腕位置。\nセンター位置也会一并调整。")
        self.arm_alignment_floor_flg_ctrl.Bind(wx.EVT_CHECKBOX, self.on_check_arm_process_alignment)
        self.alignment_option_sizer.Add(self.arm_alignment_floor_flg_ctrl, 0, wx.ALL, 5)

        self.sizer.Add(self.alignment_option_sizer, 0, wx.ALL, 5)

        # 手腕位置滑块
        self.alignment_distance_wrist_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.alignment_distance_wrist_txt = wx.StaticText(self, wx.ID_ANY, u"手腕之间的距离　  ", wx.DefaultPosition, wx.DefaultSize, 0)
        self.alignment_distance_wrist_txt.SetToolTip(u"请指定手腕靠近到什么程度时执行手腕位置对齐。\n数值越小，仅在手腕靠近时才进行手腕位置对齐。\n距离的单位以源模型的手掌大小为基准。" \
                                                     + "\n执行适配时，手腕之间的距离会显示在消息栏中，可供参考。\n将滑块设为最大值则会始终执行手腕位置对齐。（对于双手持剑等动作很方便）")
        self.alignment_distance_wrist_txt.Wrap(-1)
        self.alignment_distance_wrist_sizer.Add(self.alignment_distance_wrist_txt, 0, wx.ALL, 5)

        self.alignment_distance_wrist_label = wx.StaticText(self, wx.ID_ANY, u"（1.7）", wx.DefaultPosition, wx.DefaultSize, 0)
        self.alignment_distance_wrist_label.SetToolTip(u"当前指定的手腕之间的距离。当源模型的双手腕位置处于该范围内时，将进行手腕之间的位置对齐。")
        self.alignment_distance_wrist_label.Wrap(-1)
        self.alignment_distance_wrist_sizer.Add(self.alignment_distance_wrist_label, 0, wx.ALL, 5)

        self.alignment_distance_wrist_slider = FloatSliderCtrl(self, wx.ID_ANY, 1.7, 0, 10, 0.1, self.alignment_distance_wrist_label, wx.DefaultPosition, wx.DefaultSize, wx.SL_HORIZONTAL)
        self.alignment_distance_wrist_slider.Bind(wx.EVT_SCROLL_CHANGED, self.on_check_arm_process_alignment)
        self.alignment_distance_wrist_sizer.Add(self.alignment_distance_wrist_slider, 1, wx.ALL | wx.EXPAND, 5)

        self.sizer.Add(self.alignment_distance_wrist_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # 手指位置滑块
        self.alignment_distance_finger_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.alignment_distance_finger_txt = wx.StaticText(self, wx.ID_ANY, u"手指之间的距离　", wx.DefaultPosition, wx.DefaultSize, 0)
        self.alignment_distance_finger_txt.SetToolTip(u"请指定手指靠近到什么程度时执行手指位置对齐。\n数值越小，仅在手指靠近时才进行手指位置对齐。\n距离的单位以源模型的手掌大小为基准。\n" \
                                                      + "\n执行适配时，手指之间的距离会显示在消息栏中，可供参考。\n将滑块设为最大值则会始终执行手指位置对齐。")
        self.alignment_distance_finger_txt.Wrap(-1)
        self.alignment_distance_finger_sizer.Add(self.alignment_distance_finger_txt, 0, wx.ALL, 5)

        self.alignment_distance_finger_label = wx.StaticText(self, wx.ID_ANY, u"（1.4）", wx.DefaultPosition, wx.DefaultSize, 0)
        self.alignment_distance_finger_label.SetToolTip(u"当前指定的手指之间的距离。当源模型的双手手指位置处于该范围内时，将进行手指之间的位置对齐。")
        self.alignment_distance_finger_label.Wrap(-1)
        self.alignment_distance_finger_sizer.Add(self.alignment_distance_finger_label, 0, wx.ALL, 5)

        self.alignment_distance_finger_slider = FloatSliderCtrl(self, wx.ID_ANY, 1.4, 0, 10, 0.1, self.alignment_distance_finger_label, wx.DefaultPosition, wx.DefaultSize, wx.SL_HORIZONTAL)
        self.alignment_distance_finger_slider.Bind(wx.EVT_SCROLL_CHANGED, self.on_check_arm_process_alignment)
        self.alignment_distance_finger_sizer.Add(self.alignment_distance_finger_slider, 1, wx.ALL | wx.EXPAND, 5)

        self.sizer.Add(self.alignment_distance_finger_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # 手腕与地面位置滑块
        self.alignment_distance_floor_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.alignment_distance_floor_txt = wx.StaticText(self, wx.ID_ANY, u"手腕与地面之间的距离", wx.DefaultPosition, wx.DefaultSize, 0)
        self.alignment_distance_floor_txt.SetToolTip(u"请指定手腕与地面靠近到什么程度时执行手腕与地面的位置对齐。\n数值越小，仅在手腕与地面靠近时才进行位置对齐。\n距离的单位以源模型的手掌大小为基准。" \
                                                     + "\n执行适配时，手腕与地面之间的距离会显示在消息栏中，可供参考。\n将滑块设为最大值则会始终执行手腕与地面的位置对齐。")
        self.alignment_distance_floor_txt.Wrap(-1)
        self.alignment_distance_floor_sizer.Add(self.alignment_distance_floor_txt, 0, wx.ALL, 5)

        self.alignment_distance_floor_label = wx.StaticText(self, wx.ID_ANY, u"（1.2）", wx.DefaultPosition, wx.DefaultSize, 0)
        self.alignment_distance_floor_label.SetToolTip(u"当前指定的手腕与地面之间的距离。当源模型的双手手腕与地面的距离处于该范围内时，将进行手腕与地面的位置对齐。")
        self.alignment_distance_floor_label.Wrap(-1)
        self.alignment_distance_floor_sizer.Add(self.alignment_distance_floor_label, 0, wx.ALL, 5)

        self.alignment_distance_floor_slider = FloatSliderCtrl(self, wx.ID_ANY, 1.2, 0, 10, 0.1, self.alignment_distance_floor_label, wx.DefaultPosition, wx.DefaultSize, wx.SL_HORIZONTAL)
        self.alignment_distance_floor_slider.Bind(wx.EVT_SCROLL_CHANGED, self.on_check_arm_process_alignment)
        self.alignment_distance_floor_sizer.Add(self.alignment_distance_floor_slider, 1, wx.ALL | wx.EXPAND, 5)

        self.sizer.Add(self.alignment_distance_floor_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.static_line04 = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.sizer.Add(self.static_line04, 0, wx.EXPAND | wx.ALL, 5)

        # 手臂检查跳过 --------------------
        self.arm_check_skip_sizer = wx.BoxSizer(wx.VERTICAL)

        self.arm_check_skip_flg_ctrl = wx.CheckBox(self, wx.ID_ANY, u"跳过手臂到手腕的适配可行性检查", wx.DefaultPosition, wx.DefaultSize, 0)
        self.arm_check_skip_flg_ctrl.SetToolTip(u"跳过适配可行性检查（存在手臂IK时判定为不可），使处理必定执行。")
        self.arm_check_skip_sizer.Add(self.arm_check_skip_flg_ctrl, 0, wx.ALL, 5)

        self.arm_check_skip_description = wx.StaticText(self, wx.ID_ANY, u"跳过手臂适配可行性检查（存在手臂IK时判定为不可），必定执行手臂相关处理。\n" \
                                                        + "※适配结果可能会变得异常，但该情况不在支持范围内。", \
                                                        wx.DefaultPosition, wx.DefaultSize, 0)
        self.arm_check_skip_description.Wrap(-1)
        self.arm_check_skip_sizer.Add(self.arm_check_skip_description, 0, wx.ALL, 5)
        self.sizer.Add(self.arm_check_skip_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.fit()
        
    def get_avoidance_target(self):
        if len(self.bulk_avoidance_set_dict.keys()) > 0:
            # 存在批量数据时，优先返回
            return self.bulk_avoidance_set_dict
        
        target = {}
        if self.arm_process_flg_avoidance.GetValue() == 0:
            return target
        
        # 将选中的刚体列表设置到输入框（仅哈希相同时）
        if 1 in self.avoidance_set_dict and self.avoidance_set_dict[1].rep_choices:
            if self.avoidance_set_dict[1].equal_hashdigest(self.frame.file_panel_ctrl.file_set):
                target[0] = [self.avoidance_set_dict[1].rep_avoidance_names[n] for n in self.avoidance_set_dict[1].rep_choices.GetSelections()]
            else:
                logger.warning("【No.%s】接触规避设置后文件集发生变更，因此清除接触规避设置", 1, decoration=MLogger.DECORATION_BOX)

        for set_no in list(self.avoidance_set_dict.keys())[1:]:
            if set_no in self.avoidance_set_dict and self.avoidance_set_dict[set_no].rep_choices:
                if len(self.frame.multi_panel_ctrl.file_set_list) >= set_no - 1 and self.avoidance_set_dict[set_no].equal_hashdigest(self.frame.multi_panel_ctrl.file_set_list[set_no - 2]):
                    target[set_no - 1] = [self.avoidance_set_dict[set_no].rep_avoidance_names[n] for n in self.avoidance_set_dict[set_no].rep_choices.GetSelections()]
                else:
                    logger.warning("【No.%s】接触规避设置后文件集发生变更，因此清除接触规避设置", set_no, decoration=MLogger.DECORATION_BOX)

        return target
    
    def on_click_avoidance_target(self, event: wx.Event):
        if self.avoidance_dialog.ShowModal() == wx.ID_CANCEL:
            return     # the user changed their mind

        # 先清空
        self.avoidance_target_txt_ctrl.SetValue("")

        # 将选中的刚体列表设置到输入框
        for set_no, set_data in self.avoidance_set_dict.items():
            # 每个选项的显示文字
            if set_data.rep_choices:
                selections = [set_data.rep_choices.GetString(n) for n in set_data.rep_choices.GetSelections()]
                self.avoidance_target_txt_ctrl.WriteText("【No.{0}】{1}\n".format(set_no, ', '.join(selections)))

        self.arm_process_flg_avoidance.SetValue(1)
        self.avoidance_dialog.Hide()

    def initialize(self, event: wx.Event):

        if 1 in self.avoidance_set_dict:
            # 存在文件标签页用接触规避的文件集时
            if self.frame.file_panel_ctrl.file_set.is_loaded():
                # 已存在时，进行哈希校验
                if self.avoidance_set_dict[1].equal_hashdigest(self.frame.file_panel_ctrl.file_set):
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
            if set_no in self.avoidance_set_dict:
                # 存在多标签页用接触规避的文件集时
                if multi_file_set.is_loaded():
                    # 已存在时，进行哈希校验
                    if self.avoidance_set_dict[set_no].equal_hashdigest(multi_file_set):
                        # 相同时则跳过
                        pass
                    else:
                        # 不同时则重新读取文件集
                        self.add_set(set_no, multi_file_set, replace=True)
                    
                        # 存在多项时，更改默认值
                        self.set_multi_initialize_value()
                else:
                    # 多标签页读取失败时，重新读取（清空）
                    self.add_set(set_no, multi_file_set, replace=True)

                    # 存在多项时，更改默认值
                    self.set_multi_initialize_value()
            else:
                # 从空白创建时，引用多标签页的文件集
                self.add_set(set_no, multi_file_set, replace=False)
            
                # 存在多项时，更改默认值
                self.set_multi_initialize_value()

        # 手臂不可用模型名称列表
        disable_arm_model_names = []

        if self.frame.file_panel_ctrl.file_set.is_loaded():
            if not self.frame.file_panel_ctrl.file_set.org_model_file_ctrl.data.can_arm_sizing:
                # 手臂不可用时，加入列表
                disable_arm_model_names.append("【No.1】源模型: {0}".format(self.frame.file_panel_ctrl.file_set.org_model_file_ctrl.data.name))

            if not self.frame.file_panel_ctrl.file_set.rep_model_file_ctrl.data.can_arm_sizing:
                # 手臂不可用时，加入列表
                disable_arm_model_names.append("【No.1】目标模型: {0}".format(self.frame.file_panel_ctrl.file_set.rep_model_file_ctrl.data.name))

        for multi_file_set_idx, multi_file_set in enumerate(self.frame.multi_panel_ctrl.file_set_list):
            set_no = multi_file_set_idx + 2
            if multi_file_set.is_loaded():
                if not multi_file_set.org_model_file_ctrl.data.can_arm_sizing:
                    # 手臂不可用时，加入列表
                    disable_arm_model_names.append("【No.{0}】源模型: {1}".format(set_no, multi_file_set.org_model_file_ctrl.data.name))

                if not multi_file_set.rep_model_file_ctrl.data.can_arm_sizing:
                    # 手臂不可用时，加入列表
                    disable_arm_model_names.append("【No.{0}】目标模型: {1}".format(set_no, multi_file_set.rep_model_file_ctrl.data.name))
            
        if len(disable_arm_model_names) > 0 and not self.arm_check_skip_flg_ctrl.GetValue():
            # 存在手臂不可用模型时，显示对话框
            with wx.MessageDialog(self, "由于下列模型中包含「腕IK」之类的字符串，相应文件集的手臂相关处理\n（手臂姿势修正・扭转分散・接触规避・位置对齐）将就这样被跳过。\n" \
                                  + "若将手臂检查跳过FLG设为ON，则会强制执行手臂相关处理。\n※但即使结果变得异常，也不在支持范围内。\n" \
                                  + "是否要将手臂检查跳过FLG设为ON？ \n\n{0}".format('\n'.join(disable_arm_model_names)), style=wx.YES_NO | wx.ICON_WARNING) as dialog:
                if dialog.ShowModal() == wx.ID_NO:
                    # 手臂检查跳过关闭
                    self.arm_check_skip_flg_ctrl.SetValue(0)
                else:
                    # 手臂检查跳过开启
                    self.arm_check_skip_flg_ctrl.SetValue(1)
                
        event.Skip()
    
    def set_multi_initialize_value(self):
        # 存在多项时，更改手腕之间距离的默认值
        self.alignment_distance_wrist_slider.SetValue(2.5)
        self.alignment_distance_wrist_label.SetLabel("（2.5）")

    def add_set(self, set_idx: int, file_set: SizingFileSet, replace: bool):
        new_avoidance_set = AvoidanceSet(self.frame, self, self.avoidance_dialog.scrolled_window, set_idx, file_set)
        if replace:
            # 替换
            self.avoidance_dialog.set_list_sizer.Hide(self.avoidance_set_dict[set_idx].set_sizer, recursive=True)
            self.avoidance_dialog.set_list_sizer.Replace(self.avoidance_set_dict[set_idx].set_sizer, new_avoidance_set.set_sizer, recursive=True)

            # 替换时清空刚体列表
            self.avoidance_target_txt_ctrl.SetValue("")
        else:
            # 新增
            self.avoidance_dialog.set_list_sizer.Add(new_avoidance_set.set_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.avoidance_set_dict[set_idx] = new_avoidance_set

        # 为显示滚动条而调整尺寸
        self.avoidance_dialog.set_list_sizer.Layout()
        self.avoidance_dialog.set_list_sizer.FitInside(self.avoidance_dialog.scrolled_window)

    # 生成VMD输出文件路径
    def set_output_vmd_path(self, event, is_force=False):
        # 保险起见自动生成输出文件路径（为空时设置）
        self.frame.file_panel_ctrl.file_set.set_output_vmd_path(event)

        # multi 也自动生成输出文件路径（为空时设置）
        for file_set in self.frame.multi_panel_ctrl.file_set_list:
            file_set.set_output_vmd_path(event)
    
    # 处理对象：接触规避开启
    def on_check_arm_process_avoidance(self, event: wx.Event):
        # 文本、复选框、实际值发生变化时进行切换
        if isinstance(event.GetEventObject(), wx.StaticText):
            if self.arm_process_flg_avoidance.GetValue() == 0:
                self.arm_process_flg_avoidance.SetValue(1)
            else:
                self.arm_process_flg_avoidance.SetValue(0)

        # 重新生成路径
        self.set_output_vmd_path(event)
        
        event.Skip()

    # 处理对象：手腕位置对齐开启
    def on_check_arm_process_alignment(self, event: wx.Event):
        # 文本、复选框、实际值发生变化时进行切换
        if isinstance(event.GetEventObject(), wx.StaticText):
            if self.arm_process_flg_alignment.GetValue() == 0:
                self.arm_process_flg_alignment.SetValue(1)
            else:
                self.arm_process_flg_alignment.SetValue(0)
        else:
            if self.arm_alignment_finger_flg_ctrl.GetValue() == 1 or self.arm_alignment_floor_flg_ctrl.GetValue() == 1:
                self.arm_process_flg_alignment.SetValue(1)

        if self.arm_alignment_finger_flg_ctrl.GetValue() and len(self.frame.multi_panel_ctrl.file_set_list) > 0:
            self.frame.on_popup_finger_warning(event)

        # 重新生成路径
        self.set_output_vmd_path(event)

        event.Skip()


class AvoidanceSet():

    def __init__(self, frame: wx.Frame, panel: wx.Panel, window: wx.Window, set_idx: int, file_set: SizingFileSet):
        self.frame = frame
        self.panel = panel
        self.window = window
        self.set_idx = set_idx
        self.file_set = file_set
        self.rep_model_digest = 0 if not file_set.rep_model_file_ctrl.data else file_set.rep_model_file_ctrl.data.digest
        self.rep_avoidances = ["頭接触回避 (頭)"]   # 选项显示文字
        self.rep_avoidance_names = ["頭接触回避"]   # 与选项显示文字对应的刚体名称
        self.rep_choices = None

        self.set_sizer = wx.StaticBoxSizer(wx.StaticBox(self.window, wx.ID_ANY, "【No.{0}】".format(set_idx)), orient=wx.VERTICAL)

        if file_set.is_loaded():
            self.model_name_txt = wx.StaticText(self.window, wx.ID_ANY, file_set.rep_model_file_ctrl.data.name[:15], wx.DefaultPosition, wx.DefaultSize, 0)
            self.model_name_txt.Wrap(-1)
            self.set_sizer.Add(self.model_name_txt, 0, wx.ALL, 5)

            for rigidbody_name, rigidbody in file_set.rep_model_file_ctrl.data.rigidbodies.items():
                # 处理对象刚体：有效的骨骼跟随刚体
                if rigidbody.isModeStatic() and rigidbody.bone_index in file_set.rep_model_file_ctrl.data.bone_indexes:
                    self.rep_avoidances.append("{0} ({1})".format(rigidbody.name, file_set.rep_model_file_ctrl.data.bone_indexes[rigidbody.bone_index]))
                    self.rep_avoidance_names.append(rigidbody.name)

            # 选择控件
            self.rep_choices = wx.ListBox(self.window, id=wx.ID_ANY, choices=self.rep_avoidances, style=wx.LB_MULTIPLE | wx.LB_NEEDED_SB, size=(-1, 220))
            # 頭接触回避默认选中
            self.rep_choices.SetSelection(0)
            self.set_sizer.Add(self.rep_choices, 0, wx.ALL, 5)

            # 批量用复制按钮
            self.copy_btn_ctrl = wx.Button(self.window, wx.ID_ANY, u"批量用复制", wx.DefaultPosition, wx.DefaultSize, 0)
            self.copy_btn_ctrl.SetToolTip(u"将接触规避数据按批量CSV的格式复制到剪贴板")
            self.copy_btn_ctrl.Bind(wx.EVT_BUTTON, self.on_copy)
            self.set_sizer.Add(self.copy_btn_ctrl, 0, wx.ALL, 5)
        else:
            self.no_data_txt = wx.StaticText(self.window, wx.ID_ANY, u"无数据", wx.DefaultPosition, wx.DefaultSize, 0)
            self.no_data_txt.Wrap(-1)
            self.set_sizer.Add(self.no_data_txt, 0, wx.ALL, 5)

    def on_copy(self, event: wx.Event):
        # 生成批量CSV用文本
        avoidance_txt_list = []
        for idx in self.rep_choices.GetSelections():
            avoidance_txt_list.append(f"{self.rep_avoidance_names[idx]}")
        # 末尾分号
        avoidance_txt_list.append("")

        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(";".join(avoidance_txt_list)))
            wx.TheClipboard.Close()

        with wx.TextEntryDialog(self.frame, u"将输出批量CSV用的接触规避数据。\n" \
                                + "显示该对话框时，下列接触规避数据已被复制到剪贴板。\n" \
                                + "若未能复制成功，请选中框内的字符串，粘贴到CSV中。", caption=u"批量CSV用接触规避数据",
                                value=";".join(avoidance_txt_list), style=wx.TextEntryDialogStyle, pos=wx.DefaultPosition) as dialog:
            dialog.ShowModal()

    # 检查是否与当前文件集的哈希一致
    def equal_hashdigest(self, now_file_set: SizingFileSet):
        return self.rep_model_digest == now_file_set.rep_model_file_ctrl.data.digest


class AvoidanceDialog(wx.Dialog):

    def __init__(self, parent):
        super().__init__(parent, id=wx.ID_ANY, title="接触规避刚体选择", pos=(-1, -1), size=(800, 500), style=wx.DEFAULT_DIALOG_STYLE, name="AvoidanceDialog")

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        # 说明文字
        self.description_txt = wx.StaticText(self, wx.ID_ANY, u"可从目标模型中选择希望让手部规避的骨骼跟随刚体。\n" \
                                             + u"「頭接触回避」是根据头部大小自动计算的刚体。若结果不理想，请取消选择。\n" \
                                             + u"只要是骨骼跟随刚体便没有限制，但若选择过多刚体，手部将无处可避，可能会导致意料之外的结果。", wx.DefaultPosition, wx.DefaultSize, 0)
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
                                                 wx.FULL_REPAINT_ON_RESIZE | wx.HSCROLL | wx.ALWAYS_SHOW_SB)
        self.scrolled_window.SetScrollRate(5, 5)

        # 接触规避刚体集用的基本布局器
        self.set_list_sizer = wx.BoxSizer(wx.HORIZONTAL)

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

