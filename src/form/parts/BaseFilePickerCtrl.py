# -*- coding: utf-8 -*-
#

import glob
import os
import re
import wx
import logging
from mmd.PmxReader import PmxReader
from mmd.VmdReader import VmdReader
from mmd.VpdReader import VpdReader
from utils import MFileUtils
from utils.MException import SizingException
from utils.MLogger import MLogger # noqa
from utils.MException import MKilledException


logger = MLogger(__name__)


class BaseFilePickerCtrl():
    
    # 按扩展名区分的通配符
    WILDCARD_DICT = {
        ("vmd", "vpd"): u"VMD/VPD文件 (*.vmd, *.vpd)|*.vmd;*.vpd|所有文件 (*.*)|*.*",
        ("pmx"): u"PMX文件 (*.pmx)|*.pmx|所有文件 (*.*)|*.*",
        ("vmd"): u"VMD文件 (*.vmd)|*.vmd|所有文件 (*.*)|*.*",
        ("csv"): u"CSV文件 (*.csv)|*.csv|所有文件 (*.*)|*.*",
    }

    def __init__(self, frame, parent, title, message, file_type, style, tooltip, file_model_spacer=0, \
                 title_parts_ctrl=None, file_parts_ctrl=None, title_parts2_ctrl=None, is_change_output=False, is_aster=False, is_save=False, set_no=0, required=True):
        super().__init__()

        self.frame = frame
        self.parent = parent
        self.title = title
        self.message = message
        self.file_type = file_type
        self.style = style
        self.title_parts_ctrl = None
        self.title_parts2_ctrl = None
        self.file_parts_ctrl = None
        self.file_model_ctrl = None
        self.is_change_output = is_change_output
        self.is_aster = is_aster
        self.is_save = is_save
        self.set_no = set_no
        self.required = required
        self.data = None
        self.astr_path = None
        self.target_paths = []

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        # ------------------------
        # 文件标题
        self.title_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.title_ctrl = wx.StaticText(parent, wx.ID_ANY, title, wx.DefaultPosition, wx.DefaultSize, 0)
        self.title_ctrl.Wrap(-1)

        self.title_sizer.Add(self.title_ctrl, 0, wx.ALL, 5)

        # 文件标题部件（复选框等）
        if title_parts_ctrl:
            self.title_parts_ctrl = title_parts_ctrl
            self.title_sizer.Add(self.title_parts_ctrl, 0, wx.ALL, 5)
        
        # 文件标题部件2
        if title_parts2_ctrl:
            self.title_parts2_ctrl = title_parts2_ctrl
            self.title_sizer.Add(self.title_parts2_ctrl, 0, wx.ALL, 5)

        # 文件模型
        if file_model_spacer > 0:
            self.file_model_ctrl = FileModelCtrl(parent, self, title, file_model_spacer, self.set_no)
            self.title_sizer.Add(self.file_model_ctrl.spacer_ctrl, 0, wx.ALL, 5)
            self.title_sizer.Add(self.file_model_ctrl.txt_ctrl, 0, wx.ALL, 5)

        self.sizer.Add(self.title_sizer, 1, wx.EXPAND, 0)

        # ------------------------
        # 文件控件
        self.file_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.file_ctrl = wx.FilePickerCtrl(parent, wx.ID_ANY, wx.EmptyString, message, BaseFilePickerCtrl.WILDCARD_DICT[self.file_type], wx.DefaultPosition, wx.DefaultSize, style)
        self.file_ctrl.GetPickerCtrl().SetLabel("打开")
        self.file_ctrl.SetToolTip(tooltip)

        self.file_sizer.Add(self.file_ctrl, 1, wx.ALL | wx.EXPAND, 5)

        # 文件控件部件（历史按钮等）
        if file_parts_ctrl:
            self.file_parts_ctrl = file_parts_ctrl
            self.file_sizer.Add(self.file_parts_ctrl, 0, wx.ALL, 5)

        self.sizer.Add(self.file_sizer, 0, wx.EXPAND, 5)

        # ------------------------
        # 按下「打开」按钮时的处理
        self.file_ctrl.GetPickerCtrl().Bind(wx.EVT_BUTTON, self.on_pick_file)

        # 拖放功能实现
        self.file_ctrl.SetDropTarget(MFileDropTarget(self, self.is_aster))

        # 文件路径变更时
        self.file_ctrl.Bind(wx.EVT_FILEPICKER_CHANGED, self.on_change_file)
    
    def on_pick_file(self, event):
        event.Skip()
    
    def on_change_file(self, event):
        # 清除对话框标志
        self.frame.popuped_finger_warning = False
        
        # 去除开头和结尾的换行符
        target_path = self.file_ctrl.GetPath().strip()
        logger.test("target_path strip: %s", target_path)

        # 去除开头和结尾的双引号
        target_path = re.sub(r'^\\+\"(\w)\\', r'\1:\\', target_path)
        target_path = target_path.strip("\"")
        logger.test("target_path strip: %s", target_path)

        # 重新设置
        self.file_ctrl.SetPath(target_path)

        logger.test("self.file_model_ctrl: %s", self.file_model_ctrl)

        # 存在文件模型时，输出
        if self.file_model_ctrl:
            self.file_model_ctrl.set_model(target_path)
        
        # 包含通配符（*）时，更新原始路径
        if "*" in self.file_ctrl.GetPath():
            self.astr_path = "{0}".format(self.file_ctrl.GetPath())
            self.target_paths = [p for p in glob.glob(self.astr_path) if os.path.isfile(p)]
        else:
            self.astr_path = None
            self.target_paths = []

        # 属于输出文件变更对象时，更新输出文件
        if self.is_change_output:
            self.parent.set_output_vmd_path(event, True)
        
    def disable(self):
        self.file_ctrl.GetPickerCtrl().Disable()
        self.file_ctrl.GetTextCtrl().Disable()
        
        if self.title_parts_ctrl:
            self.title_parts_ctrl.Disable()
        
        if self.title_parts2_ctrl:
            self.title_parts2_ctrl.Disable()
        
        if self.file_parts_ctrl:
            self.file_parts_ctrl.Disable()

    def enable(self):
        self.file_ctrl.GetPickerCtrl().Enable()
        self.file_ctrl.GetTextCtrl().Enable()
        
        if self.title_parts_ctrl:
            self.title_parts_ctrl.Enable()
        
        if self.title_parts2_ctrl:
            self.title_parts2_ctrl.Enable()
        
        if self.file_parts_ctrl:
            self.file_parts_ctrl.Enable()
    
    def is_set_path(self):
        return len(self.file_ctrl.GetPath()) > 0
    
    def is_valid(self):
        if self.set_no == 0:
            # CSV之类的文件不输出编号
            display_set_no = ""
        else:
            display_set_no = "第{0}个".format(self.set_no)

        if self.is_aster and self.set_no <= 1:
            base_file_path = self.file_ctrl.GetPath()

            if os.path.exists(base_file_path):
                file_path_list = [base_file_path]
            else:
                file_path_list = [p for p in glob.glob(base_file_path) if os.path.isfile(p)]

            if len(file_path_list) == 0:
                logger.error("{0}未找到符合{1}条件的文件。\n输入路径: {2}".format(
                    display_set_no, self.title, self.file_ctrl.GetPath()), decoration=MLogger.DECORATION_BOX)
                return False

            file_path = file_path_list[0]
        else:
            file_path = self.file_ctrl.GetPath()
        
        if not self.is_save and not os.path.exists(file_path):
            if self.required:
                logger.error("{0}未找到{1}。\n输入路径: {2}".format(
                    display_set_no, self.title, self.file_ctrl.GetPath()), decoration=MLogger.DECORATION_BOX)
                return False
            else:
                # 非必填时，若没有文件路径则跳过
                return True

        if not self.is_save and not os.path.isfile(file_path):
            logger.error("{0}{1}不是正常的文件。\n输入路径: {2}".format(
                display_set_no, self.title, self.file_ctrl.GetPath()), decoration=MLogger.DECORATION_BOX)
            return False

        # 扩展名
        _, ext = os.path.splitext(os.path.basename(file_path))

        if ext[1:].lower() not in self.file_type:
            logger.error("{0}{1}的扩展名不正确。\n输入路径: {2}\n可设置的扩展名: {3}".format(
                display_set_no, self.title, self.file_ctrl.GetPath(), self.file_type), decoration=MLogger.DECORATION_BOX)
            return False
        
        # 获取上级目录
        if self.is_save:
            # 写入时直接取上级目录
            dir_path = os.path.dirname(self.file_ctrl.GetPath())
        else:
            # 读取时进行解析
            dir_path = MFileUtils.get_dir_path(self.file_ctrl.GetPath())

        if not os.path.exists(dir_path):
            logger.error("未找到{0}{1}的上级文件夹。\n输入路径: {2}".format(
                display_set_no, self.title, dir_path), decoration=MLogger.DECORATION_BOX)
            return False

        if not os.path.isdir(dir_path):
            logger.error("{0}{1}的上级文件夹不是正常的文件夹。\n输入路径: {2}".format(
                display_set_no, self.title, dir_path), decoration=MLogger.DECORATION_BOX)
            return False

        if not os.access(dir_path, os.W_OK):
            logger.error("{0}没有{1}上级文件夹的写入权限。\n输入路径: {2}".format(
                display_set_no, self.title, dir_path), decoration=MLogger.DECORATION_BOX)
            return False

        # 输出类文件，检查覆盖自身文件所需的写入权限
        if self.is_save and os.path.isfile(self.file_ctrl.GetPath()) and not os.access(self.file_ctrl.GetPath(), os.W_OK):
            logger.error("{0}没有{1}的写入权限。\n输入路径: {2}".format(
                display_set_no, self.title, self.file_ctrl.GetPath()), decoration=MLogger.DECORATION_BOX)
            return False

        return True
    
    def path(self):
        return self.file_ctrl.GetPath()

    # 从文件集读取的处理
    def load_from_set(self, target, results):
        results[target] = self.load()

    # 文件读取处理
    def load(self, file_idx=0, is_check=True):
        if not self.is_set_path():
            # 未指定路径时，直接结束
            self.data = None
            return True

        if not self.is_valid():
            # 是否可读取
            self.data = None
            return False

        try:
            if self.set_no == 0:
                # CSV之类的文件不输出编号
                display_set_no = ""
            else:
                display_set_no = "【No.{0}】 ".format(self.set_no)

            if self.is_aster and self.set_no == 1:
                base_file_path = self.file_ctrl.GetPath()

                if os.path.exists(base_file_path):
                    file_path_list = [base_file_path]
                else:
                    file_path_list = [p for p in glob.glob(base_file_path) if os.path.isfile(p)]

                if len(file_path_list) == 0:
                    # 是否可读取
                    self.data = None
                    return False

                file_path = file_path_list[file_idx]
            else:
                file_path = self.file_ctrl.GetPath()

            file_name, input_ext = os.path.splitext(os.path.basename(file_path))

            # 按扩展名生成读取器
            if input_ext.lower() == ".vmd":
                reader = VmdReader(file_path)
            elif input_ext.lower() == ".vpd":
                reader = VpdReader(file_path)
            elif input_ext.lower() == ".pmx":
                reader = PmxReader(file_path, is_check=is_check)
            else:
                logger.error("%s%s 读取失败(扩展名不正确): %s", display_set_no, self.title, os.path.basename(file_path), decoration=MLogger.DECORATION_BOX)
                return False
            
            # 获取哈希值
            new_data_digest = reader.hexdigest()

            if isinstance(self.data, Exception):
                raise self.data

            # 存在新数据且哈希不同时，进行替换
            if new_data_digest and ((self.data and self.data.digest != new_data_digest) or not self.data):
                # 已获取到哈希，且无历史数据或哈希不一致时，执行读取
                self.data = reader.read_data()
                    
                logger.info("%s%s 读取成功: %s", display_set_no, self.title, os.path.basename(file_path))
                return True
            elif new_data_digest and self.data and self.data.digest == new_data_digest:
                # 哈希一致时，直接跳过
                logger.info("%s%s 读取成功: %s", display_set_no, self.title, os.path.basename(file_path))
                return True
        except MKilledException:
            logger.warning("中断读取处理。", decoration=MLogger.DECORATION_BOX)
        except SizingException as se:
            logger.error("适配处理因无法处理的数据而结束。\n\n%s", se.message, decoration=MLogger.DECORATION_BOX)
        except Exception as e:
            logger.critical("适配处理因意外错误而结束。", e, decoration=MLogger.DECORATION_BOX)
        finally:
            logging.shutdown()

        logger.error("%s%s 读取失败: %s", display_set_no, self.title, os.path.basename(file_path), decoration=MLogger.DECORATION_BOX)
        return False


class FileModelCtrl():

    def __init__(self, parent, picker, title, spacer_cnt, set_no):
        super().__init__()

        self.parent = parent
        self.picker = picker
        self.title = title
        self.set_no = set_no
        self.spacer_ctrl = wx.StaticText(parent, wx.ID_ANY, "".join([" " for n in range(spacer_cnt)]))

        width = 300 if self.set_no == 1 else 220

        self.txt_ctrl = wx.TextCtrl(parent, wx.ID_ANY, "（未设置）", wx.DefaultPosition, (width, -1), wx.TE_READONLY | wx.BORDER_NONE | wx.WANTS_CHARS)
        self.txt_ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        self.txt_ctrl.SetToolTip(u"记录在{0}中的模型名。\n该字符串可选中并复制。".format(title))

    def set_model(self, target_path):
        self.txt_ctrl.SetValue("（{0}）".format(self.get_model_name()))

    # 获取VMD的模型名
    def get_model_name(self):
        try:
            if self.picker.is_aster:
                base_file_path = self.picker.file_ctrl.GetPath()

                if os.path.exists(base_file_path):
                    file_path_list = [base_file_path]
                else:
                    file_path_list = [p for p in glob.glob(base_file_path) if os.path.isfile(p)]

                if len(file_path_list) == 0:
                    return "获取失败"

                file_path = file_path_list[0]
            else:
                file_path = self.picker.file_ctrl.GetPath()

            file_name, input_ext = os.path.splitext(os.path.basename(file_path))

            model_name = "未设置"
            if input_ext.lower() == ".vmd":
                reader = VmdReader(file_path)
            elif input_ext.lower() == ".vpd":
                reader = VpdReader(file_path)
            elif input_ext.lower() == ".pmx":
                reader = PmxReader(file_path)
            else:
                return "不支持的扩展名"
            
            try:
                model_name = reader.read_model_name()
            except Exception:
                model_name = "获取失败"

            logger.test("model_name: %s, ", model_name)

            return model_name
        except Exception as e:
            logger.test("get_model_name 失败", e)

            return "获取失败"


class MFileDropTarget(wx.FileDropTarget):
    def __init__(self, parent, is_aster):
        self.parent = parent
        self.is_aster = is_aster

        wx.FileDropTarget.__init__(self)
    
    def OnDropFiles(self, x, y, files):
        # 将文件路径显示到文本框
        file_name, input_ext = os.path.splitext(os.path.basename(files[0]))

        logger.test("file_name: %s, input_ext: %s", file_name, input_ext)
        logger.test("input_ext[1:].lower(): %s", input_ext[1:].lower())
        logger.test("self.parent.file_type: %s", self.parent.file_type)
        logger.test("test: %s", input_ext[1:].lower() in self.parent.file_type)

        if input_ext[1:].lower() in self.parent.file_type:
            # 输入扩展名属于允许的扩展名时，进行设置

            # 扩展名被允许则OK
            self.parent.file_ctrl.SetPath(files[0])

            # 文件变更处理
            self.parent.on_change_file(wx.FileDirPickerEvent())

            return True
        
        # 允许通配符（*）时，允许拖入文件夹
        if os.path.isdir(files[0]) and self.is_aster:
            # 拖入文件夹时，若文件夹内存在vmd或vpd文件则接受
            child_file_name_exts = [os.path.splitext(filename) for filename in os.listdir(files[0]) if os.path.isfile(os.path.join(files[0], filename))]

            for ft in self.parent.file_type:
                # 父级允许的文件路径
                for (child_file_name, child_file_ext) in child_file_name_exts:
                    if child_file_ext[1:].lower() == ft:
                        # 子文件的扩展名属于允许的扩展名时，加上通配符并允许
                        astr_path = "{0}\\*.{1}".format(files[0], ft)
                        self.parent.file_ctrl.SetPath(astr_path)

                        # 文件变更处理
                        self.parent.on_change_file(wx.FileDirPickerEvent())

                        return True
        
        display_file_type = self.parent.file_type
        if type(self.parent.file_type) == tuple:
            display_file_type = ",".join(self.parent.file_type)

        logger.error("{0}的扩展名不正确。\n输入文件扩展名: {1}\n可设置的扩展名: {2}".format(self.parent.title, input_ext, display_file_type), decoration=MLogger.DECORATION_BOX)

        # 不属于允许的扩展名时，不允许
        return False
