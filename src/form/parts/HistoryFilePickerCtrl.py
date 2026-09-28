# -*- coding: utf-8 -*-
#
import wx
import copy
from form.parts.BaseFilePickerCtrl import BaseFilePickerCtrl
from utils import MFileUtils
from utils.MLogger import MLogger

logger = MLogger(__name__)


class HistoryFilePickerCtrl(BaseFilePickerCtrl):
    
    def __init__(self, frame, parent, title, message, wildcard, style, tooltip, \
                 file_model_spacer, title_parts_ctrl, title_parts2_ctrl, file_histories_key, is_change_output, is_aster, is_save, set_no):
        
        self.parent = parent
        self.file_histories_key = file_histories_key

        # logger.test(self.frame.file_hitories)

        self.histroy_btn_ctrl = wx.Button(parent, wx.ID_ANY, u"历史记录", wx.DefaultPosition, wx.DefaultSize, 0)
        self.histroy_btn_ctrl.SetToolTip(u"可重新指定此前指定过的{0}。".format(title))

        super().__init__(frame, parent, title, message, wildcard, style, tooltip, file_model_spacer=file_model_spacer, title_parts_ctrl=title_parts_ctrl, \
                         title_parts2_ctrl=title_parts2_ctrl, file_parts_ctrl=self.histroy_btn_ctrl, is_change_output=is_change_output, is_aster=is_aster, \
                         is_save=is_save, set_no=set_no)

        # 按下「历史记录」按钮时的处理
        self.histroy_btn_ctrl.Bind(wx.EVT_BUTTON, self.on_show_history)
    
    def save(self):
        if len(self.file_ctrl.GetPath()) > 0 and self.frame.file_hitories and self.file_ctrl.GetPath() in self.frame.file_hitories[self.file_histories_key]:
            # 已注册的情况下，先暂时删除
            self.frame.file_hitories[self.file_histories_key].remove(self.file_ctrl.GetPath())
        
        if not self.frame.file_hitories:
            self.frame.file_hitories[self.file_histories_key] = []

        # 重新注册到首位
        if len(self.file_ctrl.GetPath()) > 0:
            self.frame.file_hitories[self.file_histories_key].insert(0, self.file_ctrl.GetPath())
        
        # 上限50条
        self.frame.file_hitories[self.file_histories_key] = self.frame.file_hitories[self.file_histories_key][:50]

    # 带有历史记录按钮的文件控件会打开最近使用的路径
    def on_pick_file(self, event):

        if len(self.file_ctrl.GetPath()) == 0 and self.frame.file_hitories and self.file_histories_key in self.frame.file_hitories and len(self.frame.file_hitories[self.file_histories_key]) > 0:
            # 未指定路径时，设置并打开最近使用的路径
            self.file_ctrl.SetInitialDirectory(MFileUtils.get_dir_path(self.frame.file_hitories[self.file_histories_key][0]))

        event.Skip()
    
    # 打开历史记录按钮
    def on_show_history(self, event):

        # 增加输入行数
        hs = copy.deepcopy(self.frame.file_hitories[self.file_histories_key])
        hs.extend(["" for x in range(self.frame.file_hitories["max"] + 1)])

        with wx.SingleChoiceDialog(self.parent, "请选择文件后双击，或点击OK按钮。", caption="文件历史记录选择",
                                   choices=hs[:(self.frame.file_hitories["max"] + 1)],
                                   style=wx.CAPTION | wx.CLOSE_BOX | wx.SYSTEM_MENU | wx.OK | wx.CANCEL | wx.CENTRE) as choiceDialog:

            if choiceDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # 将选中的路径设置到文件选择器
            self.file_ctrl.SetPath(choiceDialog.GetStringSelection())
            self.file_ctrl.UpdatePickerFromTextCtrl()
            self.file_ctrl.SetInitialDirectory(MFileUtils.get_dir_path(choiceDialog.GetStringSelection()))

            # 文件变更处理
            self.on_change_file(wx.FileDirPickerEvent())
