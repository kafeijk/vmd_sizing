# -*- coding: utf-8 -*-
#
import os
import wx
import wx.lib.newevent

from form.parts.BaseFilePickerCtrl import BaseFilePickerCtrl
from form.parts.HistoryFilePickerCtrl import HistoryFilePickerCtrl
from module.MMath import MRect, MVector3D, MVector4D, MQuaternion, MMatrix4x4 # noqa
from mmd.PmxData import PmxModel
from utils import MServiceUtils, MFileUtils # noqa
from utils.MLogger import MLogger # noqa

logger = MLogger(__name__)


class SizingFileSet():

    def __init__(self, frame: wx.Frame, panel: wx.Panel, file_hitories: dict, set_no):
        self.file_hitories = file_hitories
        self.frame = frame
        self.panel = panel
        self.set_no = set_no
        self.STANCE_DETAIL_CHOICES = ["センターXZ補正", "上半身補正", "下半身補正", "足ＩＫ補正", "つま先補正", "つま先ＩＫ補正", "肩補正", "センターY補正"]
        self.selected_stance_details = [0, 1, 2, 4, 5, 6, 7]

        if self.set_no == 1:
            # 文件标签页的直接添加
            self.set_sizer = wx.BoxSizer(wx.VERTICAL)
        else:
            self.set_sizer = wx.StaticBoxSizer(wx.StaticBox(self.panel, wx.ID_ANY, "【No.{0}】".format(set_no)), orient=wx.VERTICAL)

        able_aster_toottip = "在文件名中使用通配符（*）可以一次性对多条数据进行适配。" if self.set_no == 1 else "不支持批量指定。"
        # VMD/VPD文件控件
        self.motion_vmd_file_ctrl = HistoryFilePickerCtrl(frame, panel, u"待适配动作VMD/VPD", u"打开待适配动作VMD/VPD文件", ("vmd", "vpd"), wx.FLP_DEFAULT_STYLE, \
                                                          u"请指定想要适配的动作VMD/VPD路径。\n可以通过拖放、打开按钮或历史记录进行指定。\n{0}".format(able_aster_toottip), \
                                                          file_model_spacer=46, title_parts_ctrl=None, title_parts2_ctrl=None, file_histories_key="vmd", is_change_output=True, \
                                                          is_aster=True, is_save=False, set_no=set_no)
        self.set_sizer.Add(self.motion_vmd_file_ctrl.sizer, 1, wx.EXPAND, 0)

        # 源模型的站姿细节还原标志
        detail_stance_flg_ctrl = wx.CheckBox(panel, wx.ID_ANY, u"站姿追加修正", wx.DefaultPosition, wx.DefaultSize, 0)
        detail_stance_flg_ctrl.SetToolTip(u"勾选后可以追加进行更细致的站姿修正。\n修正内容的详情请点击旁边的「＊」按钮查看。")
        detail_stance_flg_ctrl.Bind(wx.EVT_CHECKBOX, self.set_output_vmd_path)

        # 站姿修正
        detail_btn_ctrl = wx.Button(panel, wx.ID_ANY, u"＊", wx.DefaultPosition, (20, 20), 0)
        detail_btn_ctrl.SetToolTip("可查看站姿追加修正的具体项目，并进行取舍选择。")
        detail_btn_ctrl.Bind(wx.EVT_BUTTON, self.select_detail)

        # 源模型PMX文件控件
        self.org_model_file_ctrl = HistoryFilePickerCtrl(frame, panel, u"动作源模型PMX", u"打开动作源模型PMX文件", ("pmx"), wx.FLP_DEFAULT_STYLE, \
                                                         u"请指定制作该动作时所用模型的PMX路径。\n虽然精度会有所下降，但也可以使用尺寸与骨骼结构相近的模型替代。\n可以通过拖放、打开按钮或历史记录进行指定。", \
                                                         file_model_spacer=1, title_parts_ctrl=detail_stance_flg_ctrl, title_parts2_ctrl=detail_btn_ctrl, \
                                                         file_histories_key="org_pmx", is_change_output=False, is_aster=False, is_save=False, set_no=set_no)
        self.set_sizer.Add(self.org_model_file_ctrl.sizer, 1, wx.EXPAND, 0)

        # 扭转分散追加标志
        twist_flg_ctrl = wx.CheckBox(panel, wx.ID_ANY, u"启用扭转分散", wx.DefaultPosition, wx.DefaultSize, 0)
        twist_flg_ctrl.SetToolTip(u"勾选后可以追加对手臂扭转等的分散处理。\n会比较耗时。")
        twist_flg_ctrl.Bind(wx.EVT_CHECKBOX, self.set_output_vmd_path)

        # 目标模型PMX文件控件
        self.rep_model_file_ctrl = HistoryFilePickerCtrl(frame, panel, u"动作目标模型PMX", u"打开动作目标模型PMX文件", ("pmx"), wx.FLP_DEFAULT_STYLE, \
                                                         u"请指定实际要载入该动作的模型的PMX路径。\n可以通过拖放、打开按钮或历史记录进行指定。", \
                                                         file_model_spacer=18, title_parts_ctrl=twist_flg_ctrl, title_parts2_ctrl=None, file_histories_key="rep_pmx", \
                                                         is_change_output=True, is_aster=False, is_save=False, set_no=set_no)
        self.set_sizer.Add(self.rep_model_file_ctrl.sizer, 1, wx.EXPAND, 0)

        # 输出VMD文件控件
        self.output_vmd_file_ctrl = BaseFilePickerCtrl(frame, panel, u"输出VMD", u"打开输出VMD文件", ("vmd"), wx.FLP_OVERWRITE_PROMPT | wx.FLP_SAVE | wx.FLP_USE_TEXTCTRL, \
                                                       u"请指定适配结果VMD的输出路径。\n会基于VMD文件与目标模型PMX的文件名自动生成，也可以更改为任意路径。", \
                                                       is_aster=False, is_save=True, set_no=set_no)
        self.set_sizer.Add(self.output_vmd_file_ctrl.sizer, 1, wx.EXPAND, 0)

    def get_selected_stance_details(self):
        # 返回所选中INDEX对应的名称
        return [self.STANCE_DETAIL_CHOICES[n] for n in self.selected_stance_details]

    def select_detail(self, event: wx.Event):

        with wx.MultiChoiceDialog(self.panel, "站姿追加修正中，仅执行已勾选的修正项目", caption="站姿追加修正选择", \
                                  choices=self.STANCE_DETAIL_CHOICES, style=wx.CHOICEDLG_STYLE) as choiceDialog:

            choiceDialog.SetSelections(self.selected_stance_details)

            if choiceDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind
            
            self.selected_stance_details = choiceDialog.GetSelections()

            if len(self.selected_stance_details) == 0:
                self.org_model_file_ctrl.title_parts_ctrl.SetValue(0)
            else:
                self.org_model_file_ctrl.title_parts_ctrl.SetValue(1)

    def save(self):
        self.motion_vmd_file_ctrl.save()
        self.org_model_file_ctrl.save()
        self.rep_model_file_ctrl.save()

    # 表单禁用
    def disable(self):
        self.motion_vmd_file_ctrl.disable()
        self.org_model_file_ctrl.disable()
        self.rep_model_file_ctrl.disable()
        self.output_vmd_file_ctrl.disable()

    # 表单启用
    def enable(self):
        self.motion_vmd_file_ctrl.enable()
        self.org_model_file_ctrl.enable()
        self.rep_model_file_ctrl.enable()
        self.output_vmd_file_ctrl.enable()

    # 文件读取前的检查
    def is_valid(self):
        result = True
        if self.set_no == 1:
            # 第1组必定检查
            result = self.motion_vmd_file_ctrl.is_valid() and result
            result = self.org_model_file_ctrl.is_valid() and result
            result = self.rep_model_file_ctrl.is_valid() and result
            result = self.output_vmd_file_ctrl.is_valid() and result
        else:
            # 第2组以后，若文件已齐备则检查
            if self.motion_vmd_file_ctrl.is_set_path() or self.org_model_file_ctrl.is_set_path() or \
               self.rep_model_file_ctrl.is_set_path() or self.output_vmd_file_ctrl.is_set_path():
                result = self.motion_vmd_file_ctrl.is_valid() and result
                result = self.org_model_file_ctrl.is_valid() and result
                result = self.rep_model_file_ctrl.is_valid() and result
                result = self.output_vmd_file_ctrl.is_valid() and result

        return result

    # 输入后的可否录入检查
    def is_loaded_valid(self):
        if self.set_no == 0:
            # CSV之类的文件不输出编号
            display_set_no = ""
        else:
            display_set_no = "第{0}组".format(self.set_no)
        
        # 两个PMX都能读取且动作也已载入时，检查关键帧
        not_org_standard_bones = []
        not_org_other_bones = []
        not_org_morphs = []
        not_rep_standard_bones = []
        not_rep_other_bones = []
        not_rep_morphs = []
        mismatch_bones = []

        motion = self.motion_vmd_file_ctrl.data
        org_pmx = self.org_model_file_ctrl.data
        rep_pmx = self.rep_model_file_ctrl.data

        if not motion or not org_pmx or not rep_pmx:
            # 有任何一个未能读取则直接结束
            return True

        if motion.motion_cnt == 0:
            logger.warning("%s骨骼动作数据中未注册任何关键帧。", display_set_no, decoration=MLogger.DECORATION_BOX)
            return True

        result = True
        is_warning = False

        # 骨骼
        for k in motion.bones.keys():
            bone_fnos = motion.get_bone_fnos(k)
            for fno in bone_fnos:
                if motion.bones[k][fno].position != MVector3D() or motion.bones[k][fno].rotation != MQuaternion():
                    # 存在关键帧且其值不是初始值时，作为警告对象

                    if isinstance(org_pmx, Exception):
                        raise org_pmx

                    if k not in org_pmx.bones:
                        if k in PmxModel.PARENT_BORN_PAIR:
                            not_org_standard_bones.append(k)
                        else:
                            not_org_other_bones.append(k)

                    if isinstance(rep_pmx, Exception):
                        raise rep_pmx

                    if k not in rep_pmx.bones:
                        if k in PmxModel.PARENT_BORN_PAIR:
                            not_rep_standard_bones.append(k)
                        else:
                            not_rep_other_bones.append(k)
                    
                    if k in org_pmx.bones and k in rep_pmx.bones:
                        mismatch_types = []
                        # 两边都存在该骨骼时，检查标志是否一致
                        if org_pmx.bones[k].getRotatable() != rep_pmx.bones[k].getRotatable():
                            mismatch_types.append("性能:旋转")
                        if org_pmx.bones[k].getTranslatable() != rep_pmx.bones[k].getTranslatable():
                            mismatch_types.append("性能:移动")
                        if org_pmx.bones[k].getIkFlag() != rep_pmx.bones[k].getIkFlag():
                            mismatch_types.append("性能:IK")
                        if org_pmx.bones[k].getVisibleFlag() != rep_pmx.bones[k].getVisibleFlag():
                            mismatch_types.append("性能:显示")
                        if org_pmx.bones[k].getManipulatable() != rep_pmx.bones[k].getManipulatable():
                            mismatch_types.append("性能:操作")
                        if org_pmx.bones[k].display != rep_pmx.bones[k].display:
                            mismatch_types.append("显示框")

                        if len(mismatch_types) > 0:
                            mismatch_bones.append(f"{k} 　【差异】{', '.join(mismatch_types)}）")
                    
                    # 有1条即可
                    break

        for k in motion.morphs.keys():
            morph_fnos = motion.get_morph_fnos(k)
            for fno in morph_fnos:
                if motion.morphs[k][fno].ratio != 0:
                    # 存在关键帧且其值不是初始值时，作为警告对象

                    if k not in org_pmx.morphs:
                        not_org_morphs.append(k)

                    if k not in rep_pmx.morphs:
                        not_rep_morphs.append(k)
                    
                    # 有1条即可
                    break

        if len(not_org_standard_bones) > 0 or len(not_org_other_bones) > 0 or len(not_org_morphs) > 0:
            logger.warning("%s%s缺少动作中使用的骨骼・表情。\n模型: %s\n缺失骨骼（准标准以内）: %s\n缺失骨骼（其他）: %s\n缺失表情: %s", \
                           display_set_no, self.org_model_file_ctrl.title, org_pmx.name, ",".join(not_org_standard_bones), ",".join(not_org_other_bones), ",".join(not_org_morphs), decoration=MLogger.DECORATION_BOX)
            is_warning = True

        if len(not_rep_standard_bones) > 0 or len(not_rep_other_bones) > 0 or len(not_rep_morphs) > 0:
            logger.warning("%s%s缺少动作中使用的骨骼・表情。\n模型: %s\n缺失骨骼（准标准以内）: %s\n缺失骨骼（其他）: %s\n缺失表情: %s", \
                           display_set_no, self.rep_model_file_ctrl.title, rep_pmx.name, ",".join(not_rep_standard_bones), ",".join(not_rep_other_bones), ",".join(not_rep_morphs), decoration=MLogger.DECORATION_BOX)
            is_warning = True

        if len(mismatch_bones) > 0:
            logger.warning("%s%s中动作所使用的骨骼性能等存在差异。\n模型: %s\n差异骨骼:\n　%s", \
                           display_set_no, self.rep_model_file_ctrl.title, rep_pmx.name, "\n　".join(mismatch_bones), decoration=MLogger.DECORATION_BOX)
            is_warning = True

        if not is_warning:
            logger.info("动作中使用的骨骼・表情已齐备。", decoration=MLogger.DECORATION_BOX, title="OK")

        return result

    def is_loaded(self):
        result = True
        if self.is_valid():
            result = self.motion_vmd_file_ctrl.data and result
            result = self.org_model_file_ctrl.data and result
            result = self.rep_model_file_ctrl.data and result
        else:
            result = False
        
        return result

    def load(self):
        result = True
        try:
            is_check = not self.frame.arm_panel_ctrl.arm_check_skip_flg_ctrl.GetValue()
            result = self.motion_vmd_file_ctrl.load(is_check=is_check) and result
            result = self.org_model_file_ctrl.load(is_check=is_check) and result
            result = self.rep_model_file_ctrl.load(is_check=is_check) and result
        except Exception:
            result = False
        
        return result

    # 生成VMD输出文件路径
    def set_output_vmd_path(self, event, is_force=False):
        output_vmd_path = MFileUtils.get_output_vmd_path(
            self.motion_vmd_file_ctrl.file_ctrl.GetPath(),
            self.rep_model_file_ctrl.file_ctrl.GetPath(),
            self.org_model_file_ctrl.title_parts_ctrl.GetValue(),
            self.rep_model_file_ctrl.title_parts_ctrl.GetValue(),
            self.frame.arm_panel_ctrl.arm_process_flg_avoidance.GetValue(),
            self.frame.arm_panel_ctrl.arm_process_flg_alignment.GetValue(),
            (self.set_no in self.frame.morph_panel_ctrl.morph_set_dict and self.frame.morph_panel_ctrl.morph_set_dict[self.set_no].is_set_morph()) \
            or (self.set_no in self.frame.morph_panel_ctrl.bulk_morph_set_dict and len(self.frame.morph_panel_ctrl.bulk_morph_set_dict[self.set_no]) > 0),
            self.output_vmd_file_ctrl.file_ctrl.GetPath(), is_force)

        self.output_vmd_file_ctrl.file_ctrl.SetPath(output_vmd_path)

        if len(output_vmd_path) >= 255 and os.name == "nt":
            logger.error("将要生成的文件路径超出了Windows的限制。\n预计生成路径: {0}".format(output_vmd_path), decoration=MLogger.DECORATION_BOX)

    def calc_leg_ik_ratio(self):
        target_bones = ["左足", "左ひざ", "左足首", "センター"]

        if self.is_loaded() and set(target_bones).issubset(self.org_model_file_ctrl.data.bones) and set(target_bones).issubset(self.rep_model_file_ctrl.data.bones):
            # 头身
            _, _, org_heads_tall = MServiceUtils.calc_heads_tall(self.org_model_file_ctrl.data)
            _, _, rep_heads_tall = MServiceUtils.calc_heads_tall(self.rep_model_file_ctrl.data)

            # 头身比例
            heads_tall_ratio = org_heads_tall / rep_heads_tall

            # XZ比例(腿长)
            org_leg_length = ((self.org_model_file_ctrl.data.bones["左足首"].position - self.org_model_file_ctrl.data.bones["左ひざ"].position) \
                              + (self.org_model_file_ctrl.data.bones["左ひざ"].position - self.org_model_file_ctrl.data.bones["左足"].position)).length()
            rep_leg_length = ((self.rep_model_file_ctrl.data.bones["左足首"].position - self.rep_model_file_ctrl.data.bones["左ひざ"].position) \
                              + (self.rep_model_file_ctrl.data.bones["左ひざ"].position - self.rep_model_file_ctrl.data.bones["左足"].position)).length()
            logger.test("xz_ratio rep_leg_length: %s, org_leg_length: %s", rep_leg_length, org_leg_length)
            xz_ratio = 1 if org_leg_length == 0 else (rep_leg_length / org_leg_length)

            # Y比例(裆下Y方向差值)
            rep_leg_length = (self.rep_model_file_ctrl.data.bones["左足首"].position - self.rep_model_file_ctrl.data.bones["左足"].position).y()
            org_leg_length = (self.org_model_file_ctrl.data.bones["左足首"].position - self.org_model_file_ctrl.data.bones["左足"].position).y()
            logger.test("y_ratio rep_leg_length: %s, org_leg_length: %s", rep_leg_length, org_leg_length)
            y_ratio = 1 if org_leg_length == 0 else (rep_leg_length / org_leg_length)

            return xz_ratio, y_ratio, heads_tall_ratio
        
        return 1, 1, 1
