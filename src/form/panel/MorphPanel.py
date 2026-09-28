# -*- coding: utf-8 -*-
#
import os
import wx
import csv
import traceback

from form.panel.BasePanel import BasePanel
from form.parts.SizingFileSet import SizingFileSet
from utils import MFileUtils
from utils.MLogger import MLogger # noqa

logger = MLogger(__name__)


class MorphPanel(BasePanel):
        
    def __init__(self, frame: wx.Frame, parent: wx.Notebook, tab_idx: int):
        super().__init__(frame, parent, tab_idx)

        self.header_panel = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        self.header_sizer = wx.BoxSizer(wx.VERTICAL)

        self.description_txt = wx.StaticText(self.header_panel, wx.ID_ANY, "可以将动作中使用的表情，替换为目标模型上的任意表情。" \
                                             + "\n动作表情下拉框的前缀符号含义如下。" \
                                             + "\n○　…　动作、源模型、目标模型中都存在的表情" \
                                             + "\n●　…　动作、目标模型中存在，但源模型中没有的表情" \
                                             + "\n▲　…　动作、源模型中存在，但目标模型中没有的表情", wx.DefaultPosition, wx.DefaultSize, 0)
        self.header_sizer.Add(self.description_txt, 0, wx.ALL, 5)

        self.header_panel.SetSizer(self.header_sizer)
        self.header_panel.Layout()
        self.sizer.Add(self.header_panel, 0, wx.EXPAND | wx.ALL, 5)

        # 表情集合(key: 文件集编号, value: 表情集合)
        self.morph_set_dict = {}
        # 批量用表情集合(key: 文件集编号, value: 表情list)
        self.bulk_morph_set_dict = {}
        # 表情集合用基础Sizer
        self.set_list_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.scrolled_window = wx.ScrolledWindow(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, \
                                                 wx.FULL_REPAINT_ON_RESIZE | wx.VSCROLL | wx.ALWAYS_SHOW_SB)
        # self.scrolled_window.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        # self.scrolled_window.SetBackgroundColour("BLUE")
        self.scrolled_window.SetScrollRate(5, 5)

        # 为显示滚动条而调整尺寸
        self.scrolled_window.SetSizer(self.set_list_sizer)
        self.scrolled_window.Layout()
        self.sizer.Add(self.scrolled_window, 1, wx.ALL | wx.EXPAND | wx.FIXED_MINSIZE, 5)
        self.sizer.Layout()
        self.fit()
    
    # 由表情标签页生成表情替换列表
    def get_morph_list(self, set_no: int, vmd_digest: str, org_model_digest: str, rep_model_digest: str):
        if set_no in self.bulk_morph_set_dict:
            # 存在批量用数据时优先获取
            return self.bulk_morph_set_dict[set_no], (len(self.bulk_morph_set_dict[set_no]) > 0)
        elif set_no not in self.morph_set_dict:
            # 本身就没有注册则返回空
            return [], False
        else:
            morph_set = self.morph_set_dict[set_no]
            if morph_set.vmd_digest == vmd_digest and morph_set.org_model_digest == org_model_digest and morph_set.rep_model_digest == rep_model_digest:
                # 存在则返回该编号的表情替换列表
                return morph_set.get_morph_list(), True
            else:
                logger.warning("【No.%s】表情替换设置后，文件集发生了变更，因此清空表情替换设置", set_no, decoration=MLogger.DECORATION_BOX)
                # 哈希不一致时返回空（仅返回曾经设置过这一事实）
                return [], True

    # 表情标签页初始化处理
    def initialize(self, event: wx.Event):
        self.bulk_morph_set_dict = {}
        
        if 1 in self.morph_set_dict:
            # 存在文件标签页用表情的文件集时
            if self.frame.file_panel_ctrl.file_set.is_loaded():
                # 已存在时进行哈希校验
                if self.morph_set_dict[1].equal_hashdigest(self.frame.file_panel_ctrl.file_set):
                    # 相同则跳过
                    pass
                else:
                    # 不同则重新读取文件集
                    self.add_set(1, self.frame.file_panel_ctrl.file_set, replace=True)
            else:
                # 文件标签页读取失败时，重新读取（清空）
                self.add_set(1, self.frame.file_panel_ctrl.file_set, replace=True)
        else:
            # 从空状态创建时，引用文件标签页的文件集
            self.add_set(1, self.frame.file_panel_ctrl.file_set, replace=False)
        
        # multi 逐个检查
        for multi_file_set_idx, multi_file_set in enumerate(self.frame.multi_panel_ctrl.file_set_list):
            set_no = multi_file_set_idx + 2
            if set_no in self.morph_set_dict:
                # 存在多文件标签页用表情的文件集时
                if multi_file_set.is_loaded():
                    # 已存在时进行哈希校验
                    if self.morph_set_dict[set_no].equal_hashdigest(multi_file_set):
                        # 相同则跳过
                        pass
                    else:
                        # 不同则重新读取文件集
                        self.add_set(set_no, multi_file_set, replace=True)
                else:
                    # 多文件标签页读取失败时，重新读取（清空）
                    self.add_set(set_no, multi_file_set, replace=True)
            else:
                # 从空状态创建时，引用多文件标签页的文件集
                self.add_set(set_no, multi_file_set, replace=False)

    def add_set(self, set_idx: int, file_set: SizingFileSet, replace: bool, hide=False):
        new_morph_set = MorphSet(self.frame, self, self.scrolled_window, set_idx, file_set)
        if replace:
            # 替换
            self.set_list_sizer.Hide(self.morph_set_dict[set_idx].set_sizer, recursive=True)
            self.set_list_sizer.Replace(self.morph_set_dict[set_idx].set_sizer, new_morph_set.set_sizer, recursive=True)
        else:
            # 新增
            self.set_list_sizer.Add(new_morph_set.set_sizer, 0, wx.EXPAND | wx.ALL, 5)
        self.morph_set_dict[set_idx] = new_morph_set
        
        # 为显示滚动条而调整尺寸
        self.set_list_sizer.Layout()
        self.set_list_sizer.FitInside(self.scrolled_window)

    # 表单禁用
    def disable(self):
        self.file_set.disable()

    # 表单启用
    def enable(self):
        self.file_set.enable()


class MorphSet():

    def __init__(self, frame: wx.Frame, panel: wx.Panel, window: wx.Window, set_idx: int, file_set: SizingFileSet):
        self.frame = frame
        self.panel = panel
        self.window = window
        self.set_idx = set_idx
        self.file_set = file_set
        self.vmd_digest = 0 if not file_set.motion_vmd_file_ctrl.data else file_set.motion_vmd_file_ctrl.data.digest
        self.org_model_digest = 0 if not file_set.org_model_file_ctrl.data else file_set.org_model_file_ctrl.data.digest
        self.rep_model_digest = 0 if not file_set.rep_model_file_ctrl.data else file_set.rep_model_file_ctrl.data.digest
        self.org_morphs = [""]  # 选项显示文本
        self.rep_morphs = [""]
        self.org_choices = []   # 选项控件
        self.rep_choices = []
        self.org_morph_names = {}   # 与选项显示文本对应的表情名
        self.rep_morph_names = {}
        self.org_buttons = []   # 相关按钮控件
        self.rep_buttons = []
        self.ratios = []

        self.set_sizer = wx.StaticBoxSizer(wx.StaticBox(self.window, wx.ID_ANY, "【No.{0}】".format(set_idx)), orient=wx.VERTICAL)

        if file_set.is_loaded():
            for mk in file_set.motion_vmd_file_ctrl.data.morphs.keys():
                morph_fnos = file_set.motion_vmd_file_ctrl.data.get_morph_fnos(mk)
                for fno in morph_fnos:
                    if file_set.motion_vmd_file_ctrl.data.morphs[mk][fno].ratio != 0:
                        # 键存在且不是初始值的情况下，作为替换对象

                        if mk in file_set.rep_model_file_ctrl.data.morphs and file_set.rep_model_file_ctrl.data.morphs[mk].display:
                            if mk in file_set.org_model_file_ctrl.data.morphs and file_set.org_model_file_ctrl.data.morphs[mk].display:
                                # 源模型和目标模型中都存在的情况
                                txt = file_set.org_model_file_ctrl.data.morphs[mk].get_panel_name() + "○:" + mk[:10]
                                self.org_morphs.append(txt)
                                self.org_morph_names[txt] = mk
                            else:
                                # 源模型中没有、目标模型中有的情况
                                txt = "？●:" + mk[:10]
                                self.org_morphs.append(txt)
                                self.org_morph_names[txt] = mk
                        else:
                            if mk in file_set.org_model_file_ctrl.data.morphs and file_set.org_model_file_ctrl.data.morphs[mk].display:
                                # 源模型中有、目标模型中没有的情况
                                txt = file_set.org_model_file_ctrl.data.morphs[mk].get_panel_name() + "▲:" + mk[:10]
                                self.org_morphs.append(txt)
                                self.org_morph_names[txt] = mk
                            else:
                                # 源模型和目标模型中都没有的情况
                                txt = "？▲:" + mk[:10]
                                self.org_morphs.append(txt)
                                self.org_morph_names[txt] = mk
                        
                        # 只要有1条即可
                        break

            # 目标模型仅以显示出来的表情为对象
            for rmk, rmv in file_set.rep_model_file_ctrl.data.morphs.items():
                if rmv.display:
                    txt = rmv.get_panel_name() + ":" + rmk[:10]
                    self.rep_morphs.append(txt)
                    self.rep_morph_names[txt] = rmk

            self.btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

            # 批量用复制按钮
            self.copy_btn_ctrl = wx.Button(self.window, wx.ID_ANY, u"批量用复制", wx.DefaultPosition, wx.DefaultSize, 0)
            self.copy_btn_ctrl.SetToolTip(u"将表情替换数据按批量CSV的格式复制到剪贴板")
            self.copy_btn_ctrl.Bind(wx.EVT_BUTTON, self.on_copy)
            self.btn_sizer.Add(self.copy_btn_ctrl, 0, wx.ALL, 5)

            # 导入按钮
            self.import_btn_ctrl = wx.Button(self.window, wx.ID_ANY, u"导入 ...", wx.DefaultPosition, wx.DefaultSize, 0)
            self.import_btn_ctrl.SetToolTip(u"从CSV文件读取表情替换数据。\n会打开文件选择对话框。")
            self.import_btn_ctrl.Bind(wx.EVT_BUTTON, self.on_import)
            self.btn_sizer.Add(self.import_btn_ctrl, 0, wx.ALL, 5)

            # 导出按钮
            self.export_btn_ctrl = wx.Button(self.window, wx.ID_ANY, u"导出 ...", wx.DefaultPosition, wx.DefaultSize, 0)
            self.export_btn_ctrl.SetToolTip(u"将表情替换数据输出到CSV文件。\n输出到与待适配VMD相同的文件夹中。")
            self.export_btn_ctrl.Bind(wx.EVT_BUTTON, self.on_export)
            self.btn_sizer.Add(self.export_btn_ctrl, 0, wx.ALL, 5)

            # 添加行按钮
            self.add_line_btn_ctrl = wx.Button(self.window, wx.ID_ANY, u"添加行", wx.DefaultPosition, wx.DefaultSize, 0)
            self.add_line_btn_ctrl.SetToolTip(u"添加表情替换的组合行。\n没有数量上限。")
            self.add_line_btn_ctrl.Bind(wx.EVT_BUTTON, self.on_add_line)
            self.btn_sizer.Add(self.add_line_btn_ctrl, 0, wx.ALL, 5)

            self.set_sizer.Add(self.btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

            # 标题部分
            self.grid_sizer = wx.FlexGridSizer(0, 4, 0, 0)
            self.grid_sizer.SetFlexibleDirection(wx.BOTH)
            self.grid_sizer.SetNonFlexibleGrowMode(wx.FLEX_GROWMODE_SPECIFIED)

            # 模型名 ----------
            self.org_model_name_txt = wx.StaticText(self.window, wx.ID_ANY, file_set.org_model_file_ctrl.data.name[:15], wx.DefaultPosition, wx.DefaultSize, 0)
            self.org_model_name_txt.Wrap(-1)
            self.grid_sizer.Add(self.org_model_name_txt, 0, wx.ALL, 5)

            self.name_arrow_txt = wx.StaticText(self.window, wx.ID_ANY, u"　", wx.DefaultPosition, wx.DefaultSize, 0)
            self.name_arrow_txt.Wrap(-1)
            self.grid_sizer.Add(self.name_arrow_txt, 0, wx.CENTER | wx.ALL, 5)

            self.rep_model_name_txt = wx.StaticText(self.window, wx.ID_ANY, file_set.rep_model_file_ctrl.data.name[:15], wx.DefaultPosition, wx.DefaultSize, 0)
            self.rep_model_name_txt.Wrap(-1)
            self.grid_sizer.Add(self.rep_model_name_txt, 0, wx.ALL, 5)

            self.name_ratio_txt = wx.StaticText(self.window, wx.ID_ANY, u"　", wx.DefaultPosition, wx.DefaultSize, 0)
            self.name_ratio_txt.Wrap(-1)
            self.grid_sizer.Add(self.name_ratio_txt, 0, wx.CENTER | wx.ALL, 5)

            # ------------
            self.org_morph_txt = wx.StaticText(self.window, wx.ID_ANY, u"动作表情", wx.DefaultPosition, wx.DefaultSize, 0)
            self.org_morph_txt.SetToolTip(u"注册在待适配VMD/VPD中的表情。")
            self.org_morph_txt.Wrap(-1)
            self.grid_sizer.Add(self.org_morph_txt, 0, wx.ALL, 5)

            self.arrow_txt = wx.StaticText(self.window, wx.ID_ANY, u"　→　", wx.DefaultPosition, wx.DefaultSize, 0)
            self.arrow_txt.Wrap(-1)
            self.grid_sizer.Add(self.arrow_txt, 0, wx.CENTER | wx.ALL, 5)

            self.rep_morph_txt = wx.StaticText(self.window, wx.ID_ANY, u"替换后表情", wx.DefaultPosition, wx.DefaultSize, 0)
            self.rep_morph_txt.SetToolTip(u"在动作转换目标模型中定义的表情。")
            self.rep_morph_txt.Wrap(-1)
            self.grid_sizer.Add(self.rep_morph_txt, 0, wx.ALL, 5)

            self.ratio_title_txt = wx.StaticText(self.window, wx.ID_ANY, u"大小修正", wx.DefaultPosition, wx.DefaultSize, 0)
            self.ratio_title_txt.SetToolTip(u"修正替换后表情的大小。")
            self.ratio_title_txt.Wrap(-1)
            self.grid_sizer.Add(self.ratio_title_txt, 0, wx.ALL, 5)

            # 添加一行
            self.add_line()

            self.set_sizer.Add(self.grid_sizer, 0, wx.ALL, 5)
        else:
            self.no_data_txt = wx.StaticText(self.window, wx.ID_ANY, u"无数据", wx.DefaultPosition, wx.DefaultSize, 0)
            self.no_data_txt.Wrap(-1)
            self.set_sizer.Add(self.no_data_txt, 0, wx.ALL, 5)

    def get_morph_list(self):
        morph_list = []

        for midx, (oc, rc, ratio) in enumerate(zip(self.org_choices, self.rep_choices, self.ratios)):
            if oc.GetSelection() > 0 and rc.GetSelection() > 0:
                # 有任何设置就作为对象

                # 去除前缀
                om = self.org_morph_names[oc.GetString(oc.GetSelection())]
                rm = self.rep_morph_names[rc.GetString(rc.GetSelection())]
                r = ratio.GetValue()

                if (om, rm, r) not in morph_list:
                    # 表情对尚未注册则进行注册
                    morph_list.append((om, rm, r))

        # 都没有设置则返回False
        return morph_list

    def add_line(self):
        # 替换前表情
        self.org_choices.append(wx.Choice(self.window, id=wx.ID_ANY, choices=self.org_morphs))
        self.org_choices[-1].Bind(wx.EVT_CHOICE, lambda event: self.on_change_choice(event, len(self.org_choices) - 1))
        self.grid_sizer.Add(self.org_choices[-1], 0, wx.ALL, 5)

        # 箭头
        self.arrow_txt = wx.StaticText(self.window, wx.ID_ANY, u"　→　", wx.DefaultPosition, wx.DefaultSize, 0)
        self.arrow_txt.Wrap(-1)
        self.grid_sizer.Add(self.arrow_txt, 0, wx.CENTER | wx.ALL, 5)

        # 替换后表情
        self.rep_choices.append(wx.Choice(self.window, id=wx.ID_ANY, choices=self.rep_morphs))
        self.rep_choices[-1].Bind(wx.EVT_CHOICE, lambda event: self.on_change_choice(event, len(self.rep_choices) - 1))
        self.grid_sizer.Add(self.rep_choices[-1], 0, wx.ALL, 5)

        # 大小比例
        self.ratios.append(wx.SpinCtrlDouble(self.window, id=wx.ID_ANY, size=wx.Size(80, -1), value="1.0", min=-10, max=10, initial=1.0, inc=0.01))
        self.ratios[-1].Bind(wx.EVT_MOUSEWHEEL, lambda event: self.frame.on_wheel_spin_ctrl(event, 0.05))
        self.grid_sizer.Add(self.ratios[-1], 0, wx.ALL, 5)

        # 为显示滚动条而调整尺寸
        self.panel.set_list_sizer.Layout()
        self.panel.set_list_sizer.FitInside(self.panel.scrolled_window)

    # 是否设置了表情
    def is_set_morph(self):
        for midx, (oc, rc) in enumerate(zip(self.org_choices, self.rep_choices)):
            if oc.GetSelection() > 0 and rc.GetSelection() > 0:
                # 有任何设置则通过
                return True

        # 都没有设置则返回False
        return False

    def on_change_choice(self, event: wx.Event, midx: int):
        # 更改选项时，先变更路径
        self.file_set.set_output_vmd_path(event)

        # 若是最后一行则添加行
        if midx == len(self.org_choices) - 1 and self.org_choices[midx].GetSelection() > 0 and self.rep_choices[midx].GetSelection() > 0:
            self.add_line()

    # 检查是否与当前文件集的哈希一致
    def equal_hashdigest(self, now_file_set: SizingFileSet):
        return self.vmd_digest == now_file_set.motion_vmd_file_ctrl.data.digest \
            and self.org_model_digest == now_file_set.org_model_file_ctrl.data.digest \
            and self.rep_model_digest == now_file_set.rep_model_file_ctrl.data.digest
    
    def on_copy(self, event: wx.Event):
        # 生成批量CSV用表情文本
        morph_txt_list = []
        morph_list = self.get_morph_list()
        for (om, rm, r) in morph_list:
            morph_txt_list.append(f"{om}:{rm}:{r}")
        # 文末分号
        morph_txt_list.append("")

        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(";".join(morph_txt_list)))
            wx.TheClipboard.Close()

        with wx.TextEntryDialog(self.frame, u"输出批量CSV用表情数据。\n" \
                                + "显示对话框的同时，下记表情数据已复制到剪贴板。\n" \
                                + "若未能复制成功，请选中输入框中的字符串，粘贴到CSV中。", caption=u"批量CSV用表情数据",
                                value=";".join(morph_txt_list), style=wx.TextEntryDialogStyle, pos=wx.DefaultPosition) as dialog:
            dialog.ShowModal()

    def on_import(self, event: wx.Event):
        input_morph_path = MFileUtils.get_output_morph_path(
            self.file_set.motion_vmd_file_ctrl.file_ctrl.GetPath(),
            self.file_set.org_model_file_ctrl.file_ctrl.GetPath(),
            self.file_set.rep_model_file_ctrl.file_ctrl.GetPath()
        )

        with wx.FileDialog(self.frame, "读取表情组合CSV", wildcard=u"CSV文件 (*.csv)|*.csv|所有文件 (*.*)|*.*",
                           defaultDir=os.path.dirname(input_morph_path),
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # Proceed loading the file chosen by the user
            target_morph_path = fileDialog.GetPath()
            try:
                with open(target_morph_path, 'r', encoding=MFileUtils.get_text_encoding(target_morph_path)) as f:
                    cr = csv.reader(f, delimiter=",", quotechar='"')
                    morph_lines = [row for row in cr]

                    if len(morph_lines) == 0:
                        return

                    org_choice_values = morph_lines[0]
                    rep_choice_values = morph_lines[1]
                    rep_rate_values = morph_lines[2]
                    
                    logger.debug("org_choice_values: %s", org_choice_values)
                    logger.debug("rep_choice_values: %s", rep_choice_values)
                    logger.debug("rep_rate_values: %s", rep_rate_values)

                    if len(org_choice_values) == 0 or len(rep_choice_values) == 0 or len(rep_rate_values) == 0:
                        return

                    for vcv, rcv, rrv in zip(org_choice_values, rep_choice_values, rep_rate_values):
                        vc = self.org_choices[-1]
                        rc = self.rep_choices[-1]
                        rr = self.ratios[-1]
                        # 遍历全部
                        for v, c in [(vcv, vc), (rcv, rc)]:
                            logger.debug("v: %s, c: %s", v, c)
                            is_seted = False
                            for n in range(c.GetCount()):
                                for p in ["目", "眉", "口", "他", "？"]:
                                    for s in ["", "○", "●", "▲"]:
                                        # 包含面板信息
                                        txt = "{0}{1}:{2}".format(p, s, v[:10])
                                        # if v == vcv:
                                        # 	logger.debug("txt: %s, c.GetString(n): %s", txt, c.GetString(n))
                                        if c.GetString(n).strip() == txt:
                                            logger.debug("[HIT] txt: %s, c.GetString(n): %s, n: %s", txt, c.GetString(n), n)
                                            # 面板与表情名一致时采用
                                            c.SetSelection(n)
                                            is_seted = True
                                            break
                                    if is_seted:
                                        break
                        # 设置大小修正
                        try:
                            rr.SetValue(float(rrv))
                        except Exception:
                            pass

                        # 添加行
                        self.add_line()

                # 路径变更
                self.file_set.set_output_vmd_path(event)

            except Exception:
                dialog = wx.MessageDialog(self.frame, "无法读取CSV文件 '%s'\n\n%s." % (target_morph_path, traceback.format_exc()), style=wx.OK)
                dialog.ShowModal()
                dialog.Destroy()

    def on_export(self, event: wx.Event):
        org_morph_list = []
        rep_morph_list = []
        ratio_list = []
        for m in self.get_morph_list():
            org_morph_list.append(m[0])
            rep_morph_list.append(m[1])
            ratio_list.append(m[2])

        output_morph_path = MFileUtils.get_output_morph_path(
            self.file_set.motion_vmd_file_ctrl.file_ctrl.GetPath(),
            self.file_set.org_model_file_ctrl.file_ctrl.GetPath(),
            self.file_set.rep_model_file_ctrl.file_ctrl.GetPath()
        )

        try:
            with open(output_morph_path, encoding=MFileUtils.get_output_encoding(org_morph_list + rep_morph_list), mode='w', newline='') as f:
                cw = csv.writer(f, delimiter=",", quotechar='"', quoting=csv.QUOTE_ALL)

                # 原表情行
                cw.writerow(org_morph_list)
                # 替换后表情行
                cw.writerow(rep_morph_list)
                # 大小
                cw.writerow(ratio_list)

            logger.info("输出成功: %s" % output_morph_path)

            dialog = wx.MessageDialog(self.frame, "表情数据导出成功 \n'%s'" % (output_morph_path), style=wx.OK)
            dialog.ShowModal()
            dialog.Destroy()

        except Exception:
            dialog = wx.MessageDialog(self.frame, "表情数据导出失败 \n'%s'\n\n%s." % (output_morph_path, traceback.format_exc()), style=wx.OK)
            dialog.ShowModal()
            dialog.Destroy()

    def on_add_line(self, event: wx.Event):
        # 添加行
        self.add_line()

