# -*- coding: utf-8 -*-
#
import os
import wx

from form.panel.BasePanel import BasePanel
from form.parts.SizingFileSet import SizingFileSet
from form.parts.BaseFilePickerCtrl import BaseFilePickerCtrl
from form.parts.HistoryFilePickerCtrl import HistoryFilePickerCtrl
from form.parts.FloatSliderCtrl import FloatSliderCtrl
from utils import MFileUtils
from utils.MLogger import MLogger # noqa

logger = MLogger(__name__)


class CameraPanel(BasePanel):
        
    def __init__(self, frame: wx.Frame, parent: wx.Notebook, tab_idx: int):
        super().__init__(frame, parent, tab_idx)

        self.header_panel = CameraHeaderPanel(self.frame, self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.header_sizer = wx.BoxSizer(wx.VERTICAL)

        self.description_txt = wx.StaticText(self.header_panel, wx.ID_ANY, u"可以与骨骼动作的适配同时进行所指定相机动作的适配。\n" \
                                             + "身高Y偏移可指定偏移量，用于调整映入相机的目标模型的身高。", wx.DefaultPosition, wx.DefaultSize, 0)
        self.header_sizer.Add(self.description_txt, 0, wx.ALL, 5)

        self.static_line01 = wx.StaticLine(self.header_panel, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.header_sizer.Add(self.static_line01, 0, wx.EXPAND | wx.ALL, 5)

        camera_only_flg_spacer_ctrl = wx.StaticText(self.header_panel, wx.ID_ANY, u"　　　　　　　　　　　　　　　　　　　　　", wx.DefaultPosition, wx.DefaultSize, 0)

        # 仅执行相机适配
        self.camera_only_flg_ctrl = wx.CheckBox(self.header_panel, wx.ID_ANY, u"仅执行相机适配", wx.DefaultPosition, wx.DefaultSize, 0)
        self.camera_only_flg_ctrl.SetToolTip(u"将已适配骨骼的文件指定为输出文件并勾选后，\n会以该适配完成的VMD为基础执行相机适配。")
        self.camera_only_flg_ctrl.Bind(wx.EVT_CHECKBOX, self.set_output_vmd_path)

        # 相机VMD文件控件
        self.camera_vmd_file_ctrl = HistoryFilePickerCtrl(self.frame, self.header_panel, u"相机动作VMD", u"打开相机动作VMD文件", ("vmd"), wx.FLP_DEFAULT_STYLE, \
                                                          u"请指定想要适配的相机动作的VMD路径。\n可通过拖放、打开按钮或历史记录进行指定。", \
                                                          file_model_spacer=0, title_parts_ctrl=camera_only_flg_spacer_ctrl, title_parts2_ctrl=self.camera_only_flg_ctrl, file_histories_key="camera_vmd", \
                                                          is_change_output=True, is_aster=False, is_save=False, set_no=1)
        self.header_sizer.Add(self.camera_vmd_file_ctrl.sizer, 1, wx.EXPAND, 0)

        # 输出目标VMD文件控件
        self.output_camera_vmd_file_ctrl = BaseFilePickerCtrl(frame, self.header_panel, u"输出相机VMD", u"打开输出相机VMD文件", ("vmd"), wx.FLP_OVERWRITE_PROMPT | wx.FLP_SAVE | wx.FLP_USE_TEXTCTRL, \
                                                              u"请指定适配结果的相机VMD输出路径。\n会根据相机VMD文件名自动生成，也可更改为任意路径。", \
                                                              is_aster=False, is_save=True, set_no=1)
        self.header_sizer.Add(self.output_camera_vmd_file_ctrl.sizer, 1, wx.EXPAND, 0)

        # 相机距离调整滑块
        self.camera_length_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.camera_length_txt = wx.StaticText(self.header_panel, wx.ID_ANY, u"距离可动范围", wx.DefaultPosition, wx.DefaultSize, 0)
        self.camera_length_txt.SetToolTip(u"由于舞台大小等原因，需要限定相机距离的调整范围时，\n" \
                                          + "可以对相机距离的可动范围加以限制。\n" \
                                          + "可动范围也可以手动调整。")
        self.camera_length_txt.Wrap(-1)
        self.camera_length_sizer.Add(self.camera_length_txt, 0, wx.ALL, 5)

        self.camera_length_type_ctrl = wx.Choice(self.header_panel, id=wx.ID_ANY, choices=["距离限制强", "距离限制弱", "无距离限制"])
        self.camera_length_type_ctrl.SetSelection(2)
        self.camera_length_type_ctrl.Bind(wx.EVT_CHOICE, self.on_camera_length_type)
        self.camera_length_type_ctrl.SetToolTip(u"「距离限制强」　…　适用于较小的舞台。较严格地限制距离可动范围。\n" \
                                                + "「距离限制弱」　…　适用于中等大小的舞台。适度限制距离可动范围。\n" \
                                                + "「无距离限制」　…　距离可动范围不受限制，将最大程度调整至与原模型相同的取景效果。")
        self.camera_length_sizer.Add(self.camera_length_type_ctrl, 0, wx.ALL, 5)

        self.camera_length_label = wx.StaticText(self.header_panel, wx.ID_ANY, u"（5）", wx.DefaultPosition, wx.DefaultSize, 0)
        self.camera_length_label.SetToolTip(u"当前指定的相机距离可动范围。")
        self.camera_length_label.Wrap(-1)
        self.camera_length_sizer.Add(self.camera_length_label, 0, wx.ALL, 5)

        self.camera_length_slider = FloatSliderCtrl(self.header_panel, wx.ID_ANY, 5, 1, 5, 0.01, self.camera_length_label, wx.DefaultPosition, wx.DefaultSize, wx.SL_HORIZONTAL)
        self.camera_length_slider.Bind(wx.EVT_SCROLL_CHANGED, self.set_output_vmd_path)
        self.camera_length_sizer.Add(self.camera_length_slider, 1, wx.ALL | wx.EXPAND, 5)

        self.header_sizer.Add(self.camera_length_sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.header_panel.SetSizer(self.header_sizer)
        self.header_panel.Layout()
        self.sizer.Add(self.header_panel, 0, wx.EXPAND | wx.ALL, 5)

        # 相机集合(key: 文件集编号, value: 相机集合)
        self.camera_set_dict = {}
        # 批量用相机集合
        self.bulk_camera_set_dict = {}
        # 相机集合用基础Sizer
        self.set_list_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.scrolled_window = CameraScrolledWindow(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, \
                                                    wx.FULL_REPAINT_ON_RESIZE | wx.VSCROLL | wx.ALWAYS_SHOW_SB)
        self.scrolled_window.SetScrollRate(5, 5)

        # 为显示滚动条而调整尺寸
        self.scrolled_window.SetSizer(self.set_list_sizer)
        self.scrolled_window.Layout()
        self.sizer.Add(self.scrolled_window, 1, wx.ALL | wx.EXPAND | wx.FIXED_MINSIZE, 5)
        self.sizer.Layout()
        self.fit()

    def on_camera_length_type(self, event):
        if self.camera_length_type_ctrl.GetSelection() == 0:
            self.camera_length_slider.SetValue(1.05)
        elif self.camera_length_type_ctrl.GetSelection() == 1:
            self.camera_length_slider.SetValue(1.3)
        else:
            self.camera_length_slider.SetValue(5)
        
        self.set_output_vmd_path(event)

    def set_output_vmd_path(self, event, is_force=False):
        # 强制更改相机输出路径
        self.header_panel.set_output_vmd_path(event, True)
    
    # 相机标签页初始化处理
    def initialize(self, event: wx.Event):
        self.bulk_camera_set_dict = {}
        
        if 1 not in self.camera_set_dict:
            # 从空状态创建时，引用文件标签页的文件集
            self.add_set(1, self.frame.file_panel_ctrl.file_set)
        else:
            # 存在时仅替换模型名
            self.camera_set_dict[1].model_name_txt.SetLabel("{0} → {1}".format(\
                                                            self.frame.file_panel_ctrl.file_set.org_model_file_ctrl.file_model_ctrl.txt_ctrl.GetValue()[1:-1], \
                                                            self.frame.file_panel_ctrl.file_set.rep_model_file_ctrl.file_model_ctrl.txt_ctrl.GetValue()[1:-1]))
        
        # multi 逐个检查
        for multi_file_set_idx, multi_file_set in enumerate(self.frame.multi_panel_ctrl.file_set_list):
            set_no = multi_file_set_idx + 2
            if set_no not in self.camera_set_dict:
                # 从空状态创建时，引用多文件标签页的文件集
                self.add_set(set_no, multi_file_set)
            else:
                # 存在时仅替换模型名
                self.camera_set_dict[set_no].model_name_txt.SetLabel("{0} → {1}".format(\
                                                                     multi_file_set.org_model_file_ctrl.file_model_ctrl.txt_ctrl.GetValue()[1:-1], \
                                                                     multi_file_set.rep_model_file_ctrl.file_model_ctrl.txt_ctrl.GetValue()[1:-1]))

    def add_set(self, set_idx: int, file_set: SizingFileSet):
        new_camera_set = CameraSet(self.frame, self, self.scrolled_window, set_idx, file_set)
        self.set_list_sizer.Add(new_camera_set.set_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.camera_set_dict[set_idx] = new_camera_set
        
        # 为显示滚动条而调整尺寸
        self.set_list_sizer.Layout()
        self.set_list_sizer.FitInside(self.scrolled_window)

    # 表单禁用
    def disable(self):
        self.file_set.disable()

    # 表单启用
    def enable(self):
        self.file_set.enable()

    def save(self):
        self.camera_vmd_file_ctrl.save()


class CameraScrolledWindow(wx.ScrolledWindow):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

    # 多动作用相机时输出路径不变，故跳过
    def set_output_vmd_path(self, event: wx.Event, is_force=False):
        pass


class CameraHeaderPanel(wx.Panel):

    def __init__(self, frame, parent, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.TAB_TRAVERSAL, name=wx.PanelNameStr):
        super().__init__(parent, id=id, pos=pos, size=size, style=style, name=name)

        self.parent = parent
        self.frame = frame

    # 文件变更时的处理
    def on_change_file(self, event: wx.Event):
        self.set_output_vmd_path(event)
    
    def set_output_vmd_path(self, event, is_force=False):
        output_camera_vmd_path = MFileUtils.get_output_camera_vmd_path(
            self.parent.camera_vmd_file_ctrl.file_ctrl.GetPath(),
            self.frame.file_panel_ctrl.file_set.rep_model_file_ctrl.file_ctrl.GetPath(),
            self.parent.output_camera_vmd_file_ctrl.file_ctrl.GetPath(),
            self.parent.camera_length_slider.GetValue(), is_force)

        self.parent.output_camera_vmd_file_ctrl.file_ctrl.SetPath(output_camera_vmd_path)

        if len(output_camera_vmd_path) >= 255 and os.name == "nt":
            logger.error("预计生成的文件路径已超出Windows的限制。\n预计生成路径: {0}".format(output_camera_vmd_path), decoration=MLogger.DECORATION_BOX)
        

class CameraSet():

    def __init__(self, frame: wx.Frame, panel: wx.Panel, window: wx.Window, set_idx: int, file_set: SizingFileSet):
        self.frame = frame
        self.panel = panel
        self.window = window
        self.set_idx = set_idx
        self.file_set = file_set

        self.set_sizer = wx.StaticBoxSizer(wx.StaticBox(self.window, wx.ID_ANY, "【No.{0}】".format(set_idx)), orient=wx.VERTICAL)

        self.model_name_txt = wx.StaticText(self.window, wx.ID_ANY, \
                                            "{0} → {1}".format(file_set.org_model_file_ctrl.file_model_ctrl.txt_ctrl.GetValue()[1:-1], \
                                                               file_set.rep_model_file_ctrl.file_model_ctrl.txt_ctrl.GetValue()[1:-1]), wx.DefaultPosition, wx.DefaultSize, 0)
        self.model_name_txt.Wrap(-1)
        self.set_sizer.Add(self.model_name_txt, 0, wx.ALL, 5)

        # 相机PMX文件控件
        self.camera_model_file_ctrl = HistoryFilePickerCtrl(frame, window, u"相机源模型PMX", u"打开相机源模型PMX文件", ("pmx"), wx.FLP_DEFAULT_STYLE, \
                                                            u"请指定用于制作相机的模型的PMX路径。\n未指定时将使用动作源模型PMX。" \
                                                            + "\n虽然精度会下降，但也可以使用尺寸和骨骼结构相近的模型代替。\n可通过拖放、打开按钮或历史记录进行指定。", \
                                                            file_model_spacer=20, title_parts_ctrl=None, title_parts2_ctrl=None, file_histories_key="camera_pmx", \
                                                            is_change_output=True, is_aster=False, is_save=False, set_no=set_idx)
        self.set_sizer.Add(self.camera_model_file_ctrl.sizer, 1, wx.EXPAND, 0)

        self.offset_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.camera_offset_y_txt = wx.StaticText(self.window, wx.ID_ANY, u"身高Y偏移", wx.DefaultPosition, wx.DefaultSize, 0)
        self.camera_offset_y_txt.Wrap(-1)
        self.offset_sizer.Add(self.camera_offset_y_txt, 0, wx.ALL, 5)

        # 偏移Y控件
        self.camera_offset_y_ctrl = wx.SpinCtrlDouble(self.window, id=wx.ID_ANY, size=wx.Size(100, -1), value="0.0", min=-1000, max=1000, initial=0.0, inc=0.1)
        self.camera_offset_y_ctrl.SetToolTip(u"可指定偏移量，用于调整映入相机的目标模型的身高。\n" \
                                             + "发饰等“想排除头顶以上物体”的情况，请指定负值。\n" \
                                             + "呆毛等“想包含头顶以上物体”的情况，请指定正值。")
        self.camera_offset_y_ctrl.Bind(wx.EVT_MOUSEWHEEL, lambda event: self.frame.on_wheel_spin_ctrl(event, 0.2))
        self.offset_sizer.Add(self.camera_offset_y_ctrl, 0, wx.ALL, 5)

        self.set_sizer.Add(self.offset_sizer, 0, wx.ALL, 0)


