# -*- coding: utf-8 -*-
#
import wx
import wx.lib.newevent
import sys
import csv
import re
import os
from datetime import datetime

from form.panel.BasePanel import BasePanel
from form.parts.HistoryFilePickerCtrl import HistoryFilePickerCtrl
from form.parts.ConsoleCtrl import ConsoleCtrl
from form.parts.SizingFileSet import SizingFileSet
from form.worker.SizingWorkerThread import SizingWorkerThread
from form.worker.LoadWorkerThread import LoadWorkerThread
from utils import MFormUtils, MFileUtils # noqa
from utils.MLogger import MLogger # noqa

logger = MLogger(__name__)
TIMER_ID = wx.NewId()

# 事件
(BulkSizingThreadEvent, EVT_BULK_SIZING_THREAD) = wx.lib.newevent.NewEvent()
(BulkLoadThreadEvent, EVT_BULK_LOAD_THREAD) = wx.lib.newevent.NewEvent()


class BulkPanel(BasePanel):
    
    def __init__(self, frame: wx.Frame, parent: wx.Notebook, tab_idx: int):
        super().__init__(frame, parent, tab_idx)

        self.description_txt = wx.StaticText(self, wx.ID_ANY, "可以批量指定设置，并连续执行处理。", wx.DefaultPosition, wx.DefaultSize, 0)
        self.sizer.Add(self.description_txt, 0, wx.ALL, 5)

        self.static_line = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        self.sizer.Add(self.static_line, 0, wx.EXPAND | wx.ALL, 5)

        # 批量BULK文件控件
        self.bulk_csv_file_ctrl = HistoryFilePickerCtrl(frame, self, u"批量处理用CSV", u"打开批量处理用CSV文件", ("csv"), wx.FLP_DEFAULT_STYLE, \
                                                        u"请指定批量处理用CSV。\n可通过DL按钮获取文件格式。\n可以通过拖拽（D&D）指定、通过打开按钮指定，也可以从历史记录中选择。", \
                                                        file_model_spacer=0, title_parts_ctrl=None, title_parts2_ctrl=None, \
                                                        file_histories_key="bulk_csv", is_change_output=False, is_aster=False, is_save=False, set_no=0)
        self.sizer.Add(self.bulk_csv_file_ctrl.sizer, 0, wx.EXPAND | wx.ALL, 0)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 批量适配保存按钮
        self.save_btn_ctrl = wx.Button(self, wx.ID_ANY, u"批量适配保存", wx.DefaultPosition, wx.Size(150, 50), 0)
        self.save_btn_ctrl.SetToolTip(u"将当前的适配设置保存到CSV")
        self.save_btn_ctrl.Bind(wx.EVT_LEFT_DCLICK, self.on_doubleclick)
        self.save_btn_ctrl.Bind(wx.EVT_LEFT_DOWN, self.on_save_click)
        btn_sizer.Add(self.save_btn_ctrl, 0, wx.ALL, 5)

        # 批量适配确认按钮
        self.check_btn_ctrl = wx.Button(self, wx.ID_ANY, u"批量适配确认", wx.DefaultPosition, wx.Size(150, 50), 0)
        self.check_btn_ctrl.SetToolTip(u"确认指定CSV数据中的设置。")
        self.check_btn_ctrl.Bind(wx.EVT_LEFT_DCLICK, self.on_doubleclick)
        self.check_btn_ctrl.Bind(wx.EVT_LEFT_DOWN, self.on_check_click)
        btn_sizer.Add(self.check_btn_ctrl, 0, wx.ALL, 5)

        # 批量适配执行按钮
        self.bulk_btn_ctrl = wx.Button(self, wx.ID_ANY, u"批量适配执行", wx.DefaultPosition, wx.Size(150, 50), 0)
        self.bulk_btn_ctrl.SetToolTip(u"批量执行适配")
        self.bulk_btn_ctrl.Bind(wx.EVT_LEFT_DCLICK, self.on_doubleclick)
        self.bulk_btn_ctrl.Bind(wx.EVT_LEFT_DOWN, self.on_bulk_click)
        btn_sizer.Add(self.bulk_btn_ctrl, 0, wx.ALL, 5)

        self.sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.SHAPED, 5)

        # 控制台
        self.console_ctrl = ConsoleCtrl(self, self.frame.logging_level, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(-1, 420), \
                                        wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_NONE | wx.HSCROLL | wx.VSCROLL | wx.WANTS_CHARS)
        self.console_ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT))
        self.console_ctrl.Bind(wx.EVT_CHAR, lambda event: MFormUtils.on_select_all(event, self.console_ctrl))
        self.sizer.Add(self.console_ctrl, 1, wx.ALL | wx.EXPAND, 5)

        # 进度条
        self.gauge_ctrl = wx.Gauge(self, wx.ID_ANY, 100, wx.DefaultPosition, wx.DefaultSize, wx.GA_HORIZONTAL)
        self.gauge_ctrl.SetValue(0)
        self.sizer.Add(self.gauge_ctrl, 0, wx.ALL | wx.EXPAND, 5)

        self.fit()

        # 转换完成处理绑定
        self.frame.Bind(EVT_BULK_LOAD_THREAD, self.on_load_result)
        self.frame.Bind(EVT_BULK_SIZING_THREAD, self.on_exec_result)

    # 表单禁用
    def disable(self):
        self.bulk_csv_file_ctrl.disable()
        self.bulk_btn_ctrl.Disable()
        self.check_btn_ctrl.Disable()

    # 表单启用
    def enable(self):
        self.bulk_csv_file_ctrl.enable()
        self.bulk_btn_ctrl.Enable()
        self.check_btn_ctrl.Enable()
    
    def on_doubleclick(self, event: wx.Event):
        self.timer.Stop()
        logger.warning("检测到双击操作。", decoration=MLogger.DECORATION_BOX)
        event.Skip(False)
        return False
    
    def on_bulk_click(self, event: wx.Event):
        self.timer = wx.Timer(self, TIMER_ID)
        self.timer.Start(200)
        self.Bind(wx.EVT_TIMER, self.on_bulk, id=TIMER_ID)

    # 批量执行适配
    def on_bulk(self, event: wx.Event):
        if self.timer:
            self.timer.Stop()
            self.Unbind(wx.EVT_TIMER, id=TIMER_ID)
            
        # 将输出目标切换到文件面板的控制台
        sys.stdout = self.console_ctrl

        if self.bulk_btn_ctrl.GetLabel() == "批量适配停止" and self.frame.worker:
            # 表单禁用
            self.disable()
            # 处于停止状态时按下按钮，则执行停止
            self.frame.worker.stop()

            # 允许切换标签页
            self.release_tab()
            # 表单启用
            self.enable()
            # 结束工作线程
            self.frame.worker = None
            # 隐藏进度条
            self.gauge_ctrl.SetValue(0)

            logger.warning("将中断VMD适配批量处理。", decoration=MLogger.DECORATION_BOX)
            
            event.Skip(False)
        elif not self.frame.worker:
            # 表单禁用
            self.disable()
            # 固定标签页
            self.fix_tab()
            # 清空控制台
            self.console_ctrl.Clear()

            # 保存历史记录
            self.save()

            # 在适配可行性检查之后执行
            self.check(event, True)
            
            event.Skip()
        else:
            logger.error("仍有处理正在执行。请等待其结束后再次执行。", decoration=MLogger.DECORATION_BOX)
            event.Skip(False)
    
    def on_save_click(self, event: wx.Event):
        self.timer = wx.Timer(self, TIMER_ID)
        self.timer.Start(200)
        self.Bind(wx.EVT_TIMER, self.on_save, id=TIMER_ID)

    # 批量适配数据保存
    def on_save(self, event: wx.Event):
        if self.timer:
            self.timer.Stop()
            self.Unbind(wx.EVT_TIMER, id=TIMER_ID)
        
        # 批量标签页的控制台
        sys.stdout = self.console_ctrl

        if not self.frame.file_panel_ctrl.file_set.motion_vmd_file_ctrl.path():
            logger.warning("文件标签页的「待适配动作VMD/VPD」为空，因此中断处理。", decoration=MLogger.DECORATION_BOX)
            return

        save_key = ["グループNo(複数人モーションは同じNo)", "調整対象モーションVMD/VPD(フルパス)", "モーション作成元モデルPMX(フルパス)", "モーション変換先モデルPMX(フルパス)", \
                    "センターXZ補正(0:無効、1:有効)", "上半身補正(0:無効、1:有効)", "下半身補正(0:無効、1:有効)", "足ＩＫ補正(0:無効、1:有効)", "つま先補正(0:無効、1:有効)", \
                    "つま先ＩＫ補正(0:無効、1:有効)", "肩補正(0:無効、1:有効)", "センターY補正(0:無効、1:有効)", "捩り分散(0:なし、1:あり)", "モーフ置換(元:先:大きさ;)", "接触回避(0:なし、1:あり)", \
                    "接触回避剛体(剛体名;)", "位置合わせ(0:なし、1:あり)", "指位置合わせ(0:なし、1:あり)", "床位置合わせ(0:なし、1:あり)", "手首の距離", "指の距離", "床との距離", \
                    "腕チェックスキップ(0:なし、1:あり)", "全移動量補正値", "足ＩＫオフセット", "カメラモーションVMD(フルパス、グループ1件目のみ)", "距離可動範囲", "カメラ作成元モデルPMX(フルパス)", "全長Yオフセット"]
        
        output_path = os.path.join(os.path.dirname(self.frame.file_panel_ctrl.file_set.motion_vmd_file_ctrl.path()), f'一括サイジング用データ_{datetime.now():%Y%m%d_%H%M%S}.csv')

        with open(output_path, 'w', encoding='cp932', newline='') as f:
            writer = csv.DictWriter(f, save_key)
            writer.writeheader()
            writer.writerow(self.create_save_data(self.frame.file_panel_ctrl.file_set, 0, save_key))
        
            for multi_idx, file_set in enumerate(self.frame.multi_panel_ctrl.file_set_list):
                writer.writerow(self.create_save_data(file_set, multi_idx + 1, save_key))

        self.frame.sound_finish()
        event.Skip()

        logger.info("批量适配用数据保存成功\n\n%s", output_path, decoration=MLogger.DECORATION_BOX)
        return

    def create_save_data(self, file_set: SizingFileSet, file_idx: int, save_key: list):

        save_data = {}
        for skey in save_key:
            save_data[skey] = ""
        
        save_data[save_key[0]] = "1"
        save_data[save_key[1]] = file_set.motion_vmd_file_ctrl.path()
        save_data[save_key[2]] = file_set.org_model_file_ctrl.path()
        save_data[save_key[3]] = file_set.rep_model_file_ctrl.path()
        save_data[save_key[4]] = "1" if 0 in file_set.selected_stance_details and file_set.org_model_file_ctrl.title_parts_ctrl.GetValue() else "0"
        save_data[save_key[5]] = "1" if 1 in file_set.selected_stance_details and file_set.org_model_file_ctrl.title_parts_ctrl.GetValue() else "0"
        save_data[save_key[6]] = "1" if 2 in file_set.selected_stance_details and file_set.org_model_file_ctrl.title_parts_ctrl.GetValue() else "0"
        save_data[save_key[7]] = "1" if 3 in file_set.selected_stance_details and file_set.org_model_file_ctrl.title_parts_ctrl.GetValue() else "0"
        save_data[save_key[8]] = "1" if 4 in file_set.selected_stance_details and file_set.org_model_file_ctrl.title_parts_ctrl.GetValue() else "0"
        save_data[save_key[9]] = "1" if 5 in file_set.selected_stance_details and file_set.org_model_file_ctrl.title_parts_ctrl.GetValue() else "0"
        save_data[save_key[10]] = "1" if 6 in file_set.selected_stance_details and file_set.org_model_file_ctrl.title_parts_ctrl.GetValue() else "0"
        save_data[save_key[11]] = "1" if 7 in file_set.selected_stance_details and file_set.org_model_file_ctrl.title_parts_ctrl.GetValue() else "0"
        save_data[save_key[12]] = "1" if file_set.rep_model_file_ctrl.title_parts_ctrl.GetValue() else "0"
        save_data[save_key[13]] = ";".join([f"{om}:{rm}:{r}" for (om, rm, r) in self.frame.morph_panel_ctrl.morph_set_dict[file_idx].get_morph_list()]) + ";" \
            if file_idx in self.frame.morph_panel_ctrl.morph_set_dict else ""
        save_data[save_key[14]] = "1" if self.frame.arm_panel_ctrl.arm_process_flg_avoidance.GetValue() else "0"
        save_data[save_key[15]] = ";".join(list(self.frame.arm_panel_ctrl.get_avoidance_target()[file_idx])) + ";" if file_idx in self.frame.arm_panel_ctrl.get_avoidance_target() else ""
        save_data[save_key[16]] = "1" if self.frame.arm_panel_ctrl.arm_process_flg_alignment.GetValue() else "0"
        save_data[save_key[17]] = "1" if self.frame.arm_panel_ctrl.arm_alignment_finger_flg_ctrl.GetValue() else "0"
        save_data[save_key[18]] = "1" if self.frame.arm_panel_ctrl.arm_alignment_floor_flg_ctrl.GetValue() else "0"
        save_data[save_key[19]] = self.frame.arm_panel_ctrl.alignment_distance_wrist_slider.GetValue()
        save_data[save_key[20]] = self.frame.arm_panel_ctrl.alignment_distance_finger_slider.GetValue()
        save_data[save_key[21]] = self.frame.arm_panel_ctrl.alignment_distance_floor_slider.GetValue()
        save_data[save_key[22]] = "1" if self.frame.arm_panel_ctrl.arm_check_skip_flg_ctrl.GetValue() else "0"
        save_data[save_key[23]] = self.frame.leg_panel_ctrl.move_correction_slider.GetValue()
        save_data[save_key[24]] = self.frame.leg_panel_ctrl.get_leg_offsets()[file_idx] if file_idx in self.frame.leg_panel_ctrl.get_leg_offsets() else "0"
        save_data[save_key[25]] = self.frame.camera_panel_ctrl.camera_vmd_file_ctrl.file_ctrl.GetPath()
        save_data[save_key[26]] = self.frame.camera_panel_ctrl.camera_length_slider.GetValue()
        save_data[save_key[27]] = self.frame.camera_panel_ctrl.camera_set_dict[file_idx + 1].camera_model_file_ctrl.path() if file_idx + 1 in self.frame.camera_panel_ctrl.camera_set_dict else ""
        save_data[save_key[28]] = self.frame.camera_panel_ctrl.camera_set_dict[file_idx + 1].camera_offset_y_ctrl.GetValue() if file_idx + 1 in self.frame.camera_panel_ctrl.camera_set_dict else ""
        
        return save_data

    def on_check_click(self, event: wx.Event):
        self.timer = wx.Timer(self, TIMER_ID)
        self.timer.Start(200)
        self.Bind(wx.EVT_TIMER, self.on_check, id=TIMER_ID)

    # 批量适配确认
    def on_check(self, event: wx.Event):
        if self.timer:
            self.timer.Stop()
            self.Unbind(wx.EVT_TIMER, id=TIMER_ID)
            
        # 将输出目标切换到文件面板的控制台
        sys.stdout = self.console_ctrl

        # 仅进行适配可行性检查
        self.check(event, False)
        return

    def save(self):
        # 保存历史记录
        self.bulk_csv_file_ctrl.save()

        # JSON输出
        MFileUtils.save_history(self.frame.mydir_path, self.frame.file_hitories)
        
    # 数据检查
    def check(self, event: wx.Event, is_exec: bool):
        # 表单禁用
        self.disable()
        # 固定标签页
        self.fix_tab()

        if not self.bulk_csv_file_ctrl.is_valid():
            # CSV路径无效时结束
            self.enable()
            self.release_tab()
            return

        result = True
        with open(self.bulk_csv_file_ctrl.path(), encoding='cp932', mode='r') as f:
            reader = csv.reader(f)
            next(reader)  # 跳过表头
            
            prev_group_no = -1
            now_model_no = -1
            service_data_txt = ""
            for ridx, rows in enumerate(reader):
                row_no = ridx
                group_no_result, group_no = self.read_csv_row(rows, row_no, 0, "グループNo", True, int, r"\d+", "仅数值", None)
                org_motion_result, org_motion_path = self.read_csv_row(rows, row_no, 1, "調整対象モーションVMD/VPD", True, str, None, None, (".vmd", ".vpd"))
                org_model_result, org_model_path = self.read_csv_row(rows, row_no, 2, "モーション作成元モデルPMX", True, str, None, None, (".pmx"))
                rep_model_result, rep_model_path = self.read_csv_row(rows, row_no, 3, "モーション変換先モデルPMX", True, str, None, None, (".pmx"))
                stance_center_xz_result, stance_center_xz_datas = self.read_csv_row(rows, row_no, 4, "センターXZ補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_upper_result, stance_upper_datas = self.read_csv_row(rows, row_no, 5, "上半身補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_lower_result, stance_lower_datas = self.read_csv_row(rows, row_no, 6, "下半身補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_leg_ik_result, stance_leg_ik_datas = self.read_csv_row(rows, row_no, 7, "足ＩＫ補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_toe_result, stance_toe_datas = self.read_csv_row(rows, row_no, 8, "つま先補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_toe_ik_result, stance_toe_ik_datas = self.read_csv_row(rows, row_no, 9, "つま先ＩＫ補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_shoulder_result, stance_shoulder_datas = self.read_csv_row(rows, row_no, 10, "肩補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_center_y_result, stance_center_y_datas = self.read_csv_row(rows, row_no, 11, "センターY補正", True, int, r"^(0|1)$", "0 或 1", None)
                separate_twist_result, separate_twist_datas = self.read_csv_row(rows, row_no, 12, "捩り分散", True, int, r"^(0|1)$", "0 或 1", None)
                morph_result, morph_datas = self.read_csv_row(rows, row_no, 13, "モーフ置換", False, str, r"[^\:]+\:[^\:]+\:\d+\.?\d*\;", "源:目标:大小;", None)
                arm_avoidance_result, arm_avoidance_datas = self.read_csv_row(rows, row_no, 14, "接触回避", True, int, r"^(0|1)$", "0 或 1", None)
                avoidance_name_result, avoidance_name_datas = self.read_csv_row(rows, row_no, 15, "接触回避剛体", False, str, r"[^\;]+\;", "刚体名;", None)
                arm_alignment_result, arm_alignment_datas = self.read_csv_row(rows, row_no, 16, "位置合わせ", True, int, r"^(0|1)$", "0 或 1", None)
                finger_alignment_result, finger_alignment_datas = self.read_csv_row(rows, row_no, 17, "指位置合わせ", False, int, r"^(0|1)$", "0 或 1", None)
                floor_alignment_result, floor_alignment_datas = self.read_csv_row(rows, row_no, 18, "床位置合わせ", False, int, r"^(0|1)$", "0 或 1", None)
                arm_alignment_length_result, arm_alignment_length_datas = self.read_csv_row(rows, row_no, 19, "手首の距離", False, float, None, None, None)
                finger_alignment_length_result, finger_alignment_length_datas = self.read_csv_row(rows, row_no, 20, "指の距離", False, float, None, None, None)
                floor_alignment_length_result, floor_alignment_length_datas = self.read_csv_row(rows, row_no, 21, "床との距離", False, float, None, None, None)
                arm_check_skip_result, arm_check_skip_datas = self.read_csv_row(rows, row_no, 22, "腕チェックスキップ", True, int, r"^(0|1)$", "0 或 1", None)
                move_correction_result, move_correction_data = self.read_csv_row(rows, row_no, 23, "全体移動量補正", False, float, None, None, None)
                leg_offset_result, leg_offset_data = self.read_csv_row(rows, row_no, 24, "足ＩＫオフセット値", False, float, None, None, None)
                org_camera_motion_result, org_camera_motion_path = self.read_csv_row(rows, row_no, 25, "カメラモーションVMD", False, str, None, None, (".vmd"))
                camera_length_result, camera_length_datas = self.read_csv_row(rows, row_no, 26, "距離稼働範囲", False, float, r"^[1-9]\d*\.?\d*", "1以上", None)
                org_camera_model_result, org_camera_model_path = self.read_csv_row(rows, row_no, 27, "カメラ作成元モデルPMX", False, str, None, None, (".pmx"))
                camera_y_offset_result, camera_y_offset_datas = self.read_csv_row(rows, row_no, 28, "全長Yオフセット", False, float, None, None, None)
                
                result = result & group_no_result & org_motion_result & org_model_result & rep_model_result & stance_center_xz_result \
                    & stance_upper_result & stance_lower_result & stance_leg_ik_result & stance_toe_result & stance_toe_ik_result & stance_shoulder_result \
                    & stance_center_y_result & separate_twist_result & arm_check_skip_result & morph_result & arm_avoidance_result & avoidance_name_result \
                    & arm_alignment_result & finger_alignment_result & floor_alignment_result & arm_alignment_length_result & finger_alignment_length_result \
                    & floor_alignment_length_result & org_camera_motion_result & camera_length_result & org_camera_model_result \
                    & camera_y_offset_result & move_correction_result & leg_offset_result
                
                if result:
                    if prev_group_no != group_no[0]:
                        now_model_no = 1

                        if len(service_data_txt) > 0:
                            # 存在已有数据时输出
                            logger.info(service_data_txt, decoration=MLogger.DECORATION_BOX)

                        # 首个动作的情况
                        service_data_txt = f"\n【分组No.{group_no[0]}】 \n"

                        arm_avoidance_txt = "有" if arm_avoidance_datas[0] == 1 else "无"
                        service_data_txt = f"{service_data_txt}　刚体接触规避: {arm_avoidance_txt}\n"
                        arm_alignment_txt = "有" if arm_alignment_datas[0] == 1 else "无"
                        service_data_txt = f"{service_data_txt}　手腕位置对齐: {arm_alignment_txt} ({arm_alignment_length_datas})\n"
                        finger_alignment_txt = "有" if finger_alignment_datas[0] == 1 else "无"
                        service_data_txt = f"{service_data_txt}　手指位置对齐: {finger_alignment_txt} ({finger_alignment_length_datas})\n"
                        floor_alignment_txt = "有" if floor_alignment_datas[0] == 1 else "无"
                        service_data_txt = f"{service_data_txt}　地面位置对齐: {floor_alignment_txt} ({floor_alignment_length_datas})\n"
                        arm_check_skip_txt = "有" if arm_check_skip_datas[0] == 1 else "无"
                        service_data_txt = f"{service_data_txt}　跳过手臂检查: {arm_check_skip_txt}\n"
                        service_data_txt = f"{service_data_txt}　整体移动量修正值: {move_correction_data}\n"

                        service_data_txt = f"{service_data_txt}　相机: {org_camera_motion_path}\n"
                        service_data_txt = f"{service_data_txt}　距离限制: {camera_length_datas}\n"
                    else:
                        # 多人动作的情况，编号累加
                        now_model_no += 1

                    service_data_txt = f"{service_data_txt}\n　【人物No.{now_model_no}】 --------- \n"

                    service_data_txt = f"{service_data_txt}　　动作: {org_motion_path}\n"
                    service_data_txt = f"{service_data_txt}　　源模型: {org_model_path}\n"
                    service_data_txt = f"{service_data_txt}　　目标模型: {rep_model_path}\n"
                    service_data_txt = f"{service_data_txt}　　足ＩＫ修正值: {leg_offset_data}\n"
                    service_data_txt = f"{service_data_txt}　　相机源模型: {org_camera_model_path}\n"
                    service_data_txt = f"{service_data_txt}　　Y偏移: {camera_y_offset_datas}\n"
                    
                    detail_stance_list = []
                    if stance_center_xz_datas[0] == 1:
                        detail_stance_list.append("センターXZ補正")
                    if stance_upper_datas[0] == 1:
                        detail_stance_list.append("上半身補正")
                    if stance_lower_datas[0] == 1:
                        detail_stance_list.append("下半身補正")
                    if stance_leg_ik_datas[0] == 1:
                        detail_stance_list.append("足ＩＫ補正")
                    if stance_toe_datas[0] == 1:
                        detail_stance_list.append("つま先補正")
                    if stance_toe_ik_datas[0] == 1:
                        detail_stance_list.append("つま先ＩＫ補正")
                    if stance_shoulder_datas[0] == 1:
                        detail_stance_list.append("肩補正")
                    if stance_center_y_datas[0] == 1:
                        detail_stance_list.append("センターY補正")
                    detail_stance_txt = ", ".join(detail_stance_list)

                    service_data_txt = f"{service_data_txt}　　站姿追加修正有无: {detail_stance_txt}\n"

                    twist_txt = "有" if separate_twist_datas[0] == 1 else "无"
                    service_data_txt = f"{service_data_txt}　　扭转分散有无: {twist_txt}\n"

                    # 表情数据
                    morph_list = []
                    for morph_data in morph_datas:
                        m = re.findall(r"([^\:]+)\:([^\:]+)\:(\d+\.?\d*)\;", morph_data)
                        morph_list.append(f"{m[0][0]} → {m[0][1]} ({float(m[0][2])})")
                    morph_txt = ", ".join(morph_list)
                    service_data_txt = f"{service_data_txt}　　表情替换: {morph_txt}\n"

                    # 接触规避数据
                    arm_avoidance_name_list = []
                    for avoidance_data in avoidance_name_datas:
                        m = re.findall(r"([^\:]+)\;", avoidance_data)
                        arm_avoidance_name_list.append(m[0])
                    arm_avoidance_name_txt = ", ".join(arm_avoidance_name_list)
                    service_data_txt = f"{service_data_txt}　　目标刚体名: {arm_avoidance_name_txt}\n"

                prev_group_no = group_no[0]

        if result:
            if is_exec:
                # 全部OK则开始处理
                self.load(event, 0)
            else:

                if len(service_data_txt) > 0:
                    # 存在已有数据时，最后输出
                    logger.info(service_data_txt, decoration=MLogger.DECORATION_BOX)

                # 检查通过且仅确认的情况下，输出后结束
                logger.info("CSV数据确认成功。", decoration=MLogger.DECORATION_BOX, title="OK")

                self.enable()
                self.release_tab()
                return
        else:
            logger.error("CSV数据存在不一致，因此中断处理", decoration=MLogger.DECORATION_BOX)

            self.enable()
            self.release_tab()

            return

    def read_csv_row(self, rows: list, row_no: int, row_idx: int, row_name: str, row_required: bool, row_type: type, row_regex: str, row_regex_str: str, path_exts: tuple):
        try:
            if row_required and (len(rows) < row_idx or not rows[row_idx]):
                logger.warning("第%s行的%s（第%s列）未设置", row_no + 1, row_name, row_idx + 1)
                return False, None
            
            try:
                if rows[row_idx] and not row_type(rows[row_idx]):
                    pass
            except Exception:
                row_type_str = "半角整数" if row_type == int else "半角数字"
                logger.warning("第%s行的%s（第%s列）的类型（%s）不正确", row_no + 1, row_name, row_idx + 1, row_type_str)
                return False, None
            
            if rows[row_idx] and row_regex and not re.findall(row_regex, rows[row_idx]):
                logger.warning("第%s行的%s（第%s列）的格式（%s）不正确", row_no + 1, row_name, row_idx + 1, row_regex_str)
                return False, None

            if rows[row_idx] and path_exts:
                if not rows[row_idx] or (not os.path.exists(rows[row_idx]) or not os.path.isfile(rows[row_idx])):
                    logger.warning("第%s行的%s（第%s列）的文件不存在", row_no + 1, row_name, row_idx + 1)
                    return False, None

                # 文件名与扩展名
                file_name, ext = os.path.splitext(os.path.basename(rows[row_idx]))
                if (ext not in path_exts):
                    logger.warning("第%s行的%s（第%s列）的文件扩展名（%s）不正确", row_no + 1, row_name, row_idx + 1, \
                                   ','.join(map(str, path_exts)) if len(path_exts) > 1 else path_exts)
                    return False, None

            # 执行读取
            if rows[row_idx] and row_regex:
                # 使用正则表达式时，转换为列表后返回
                if row_type:
                    # 指定了类型时进行转换后返回
                    return True, [row_type(v) for v in re.findall(row_regex, rows[row_idx])]
                else:
                    return True, re.findall(row_regex, rows[row_idx])

            if (row_type == float or row_type == int) and not rows[row_idx]:
                # 数值型且可为空时设为零
                return True, 0
            elif row_type:
                return True, row_type(rows[row_idx])
            
            return True, rows[row_idx]
        except Exception as e:
            logger.warning("第%s行的%s（第%s列）读取失败\n%s", row_no + 1, row_name, row_idx + 1, e)
            return False, None

    # 读取
    def load(self, event, line_idx):
        # 按分组进行设置
        now_group_no = -1
        now_motion_idx = -1
        row_no = 0
        is_buld = False
        with open(self.bulk_csv_file_ctrl.path(), encoding='cp932', mode='r') as f:
            reader = csv.reader(f)
            next(reader)  # 跳过表头
            
            for ridx, rows in enumerate(reader):
                row_no = ridx

                if row_no < line_idx:
                    # 位于指定行之前的行则跳过
                    continue

                group_no_result, group_no = self.read_csv_row(rows, row_no, 0, "グループNo", True, int, r"\d+", "仅数值", None)

                if len(group_no) == 0:
                    # 无法取得分组NO，结束
                    return

                if len(group_no) > 0 and row_no == line_idx:
                    # 到达指定INDEX后进行设置并开始读取
                    now_motion_idx = 0
                    now_group_no = group_no[0]
                else:
                    now_motion_idx += 1

                if len(group_no) > 0 and group_no[0] != now_group_no:
                    # 分组NO发生变化则直接结束
                    continue
                
                # 批量处理对象
                is_buld = True
                
                group_no_result, group_no = self.read_csv_row(rows, row_no, 0, "グループNo", True, int, r"\d+", "仅数值", None)
                org_motion_result, org_motion_path = self.read_csv_row(rows, row_no, 1, "調整対象モーションVMD/VPD", True, str, None, None, (".vmd", ".vpd"))
                org_model_result, org_model_path = self.read_csv_row(rows, row_no, 2, "モーション作成元モデルPMX", True, str, None, None, (".pmx"))
                rep_model_result, rep_model_path = self.read_csv_row(rows, row_no, 3, "モーション変換先モデルPMX", True, str, None, None, (".pmx"))
                stance_center_xz_result, stance_center_xz_datas = self.read_csv_row(rows, row_no, 4, "センターXZ補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_upper_result, stance_upper_datas = self.read_csv_row(rows, row_no, 5, "上半身補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_lower_result, stance_lower_datas = self.read_csv_row(rows, row_no, 6, "下半身補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_leg_ik_result, stance_leg_ik_datas = self.read_csv_row(rows, row_no, 7, "足ＩＫ補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_toe_result, stance_toe_datas = self.read_csv_row(rows, row_no, 8, "つま先補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_toe_ik_result, stance_toe_ik_datas = self.read_csv_row(rows, row_no, 9, "つま先ＩＫ補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_shoulder_result, stance_shoulder_datas = self.read_csv_row(rows, row_no, 10, "肩補正", True, int, r"^(0|1)$", "0 或 1", None)
                stance_center_y_result, stance_center_y_datas = self.read_csv_row(rows, row_no, 11, "センターY補正", True, int, r"^(0|1)$", "0 或 1", None)
                separate_twist_result, separate_twist_datas = self.read_csv_row(rows, row_no, 12, "捩り分散", True, int, r"^(0|1)$", "0 或 1", None)
                morph_result, morph_datas = self.read_csv_row(rows, row_no, 13, "モーフ置換", False, str, r"[^\:]+\:[^\:]+\:\d+\.?\d*\;", "源:目标:大小;", None)
                arm_avoidance_result, arm_avoidance_datas = self.read_csv_row(rows, row_no, 14, "接触回避", True, int, r"^(0|1)$", "0 或 1", None)
                avoidance_name_result, avoidance_name_datas = self.read_csv_row(rows, row_no, 15, "接触回避剛体", False, str, r"[^\;]+\;", "刚体名;", None)
                arm_alignment_result, arm_alignment_datas = self.read_csv_row(rows, row_no, 16, "位置合わせ", True, int, r"^(0|1)$", "0 或 1", None)
                finger_alignment_result, finger_alignment_datas = self.read_csv_row(rows, row_no, 17, "指位置合わせ", False, int, r"^(0|1)$", "0 或 1", None)
                floor_alignment_result, floor_alignment_datas = self.read_csv_row(rows, row_no, 18, "床位置合わせ", False, int, r"^(0|1)$", "0 或 1", None)
                arm_alignment_length_result, arm_alignment_length_datas = self.read_csv_row(rows, row_no, 19, "手首の距離", False, float, None, None, None)
                finger_alignment_length_result, finger_alignment_length_datas = self.read_csv_row(rows, row_no, 20, "指の距離", False, float, None, None, None)
                floor_alignment_length_result, floor_alignment_length_datas = self.read_csv_row(rows, row_no, 21, "床との距離", False, float, None, None, None)
                arm_check_skip_result, arm_check_skip_datas = self.read_csv_row(rows, row_no, 22, "腕チェックスキップ", True, int, r"^(0|1)$", "0 或 1", None)
                move_correction_result, move_correction_data = self.read_csv_row(rows, row_no, 23, "全体移動量補正", False, float, None, None, None)
                leg_offset_result, leg_offset_data = self.read_csv_row(rows, row_no, 24, "足ＩＫオフセット値", False, float, None, None, None)
                org_camera_motion_result, org_camera_motion_path = self.read_csv_row(rows, row_no, 25, "カメラモーションVMD", False, str, None, None, (".vmd"))
                camera_length_result, camera_length_datas = self.read_csv_row(rows, row_no, 26, "距離稼働範囲", False, float, None, None, None)
                org_camera_model_result, org_camera_model_path = self.read_csv_row(rows, row_no, 27, "カメラ作成元モデルPMX", False, str, None, None, (".pmx"))
                camera_y_offset_result, camera_y_offset_datas = self.read_csv_row(rows, row_no, 28, "全長Yオフセット", False, float, None, None, None)
                
                if now_motion_idx == 0:
                    # 清空多人面板
                    self.frame.multi_panel_ctrl.on_clear_set(event)

                    # 文件面板设置
                    self.frame.file_panel_ctrl.file_set.motion_vmd_file_ctrl.file_ctrl.SetPath(org_motion_path)
                    self.frame.file_panel_ctrl.file_set.org_model_file_ctrl.file_ctrl.SetPath(org_model_path)
                    self.frame.file_panel_ctrl.file_set.rep_model_file_ctrl.file_ctrl.SetPath(rep_model_path)
                    self.frame.file_panel_ctrl.file_set.output_vmd_file_ctrl.file_ctrl.SetPath("")

                    self.frame.file_panel_ctrl.file_set.org_model_file_ctrl.title_parts_ctrl.SetValue(
                        stance_center_xz_datas[0] | stance_upper_datas[0] | stance_lower_datas[0] | stance_leg_ik_datas[0] | \
                        stance_toe_datas[0] | stance_toe_ik_datas[0] | stance_shoulder_datas[0] | stance_center_y_datas[0]
                    )

                    # 站姿追加修正
                    self.frame.file_panel_ctrl.file_set.selected_stance_details = []
                    if stance_center_xz_datas[0] == 1:
                        self.frame.file_panel_ctrl.file_set.selected_stance_details.append(0)
                    if stance_upper_datas[0] == 1:
                        self.frame.file_panel_ctrl.file_set.selected_stance_details.append(1)
                    if stance_lower_datas[0] == 1:
                        self.frame.file_panel_ctrl.file_set.selected_stance_details.append(2)
                    if stance_leg_ik_datas[0] == 1:
                        self.frame.file_panel_ctrl.file_set.selected_stance_details.append(3)
                    if stance_toe_datas[0] == 1:
                        self.frame.file_panel_ctrl.file_set.selected_stance_details.append(4)
                    if stance_toe_ik_datas[0] == 1:
                        self.frame.file_panel_ctrl.file_set.selected_stance_details.append(5)
                    if stance_shoulder_datas[0] == 1:
                        self.frame.file_panel_ctrl.file_set.selected_stance_details.append(6)
                    if stance_center_y_datas[0] == 1:
                        self.frame.file_panel_ctrl.file_set.selected_stance_details.append(7)

                    # 扭转分散
                    self.frame.file_panel_ctrl.file_set.rep_model_file_ctrl.title_parts_ctrl.SetValue(separate_twist_datas[0])

                    # 跳过手臂检查
                    self.frame.arm_panel_ctrl.arm_check_skip_flg_ctrl.SetValue(arm_check_skip_datas[0])
                    
                    # 表情数据
                    self.frame.morph_panel_ctrl.bulk_morph_set_dict[1] = []
                    for morph_data in morph_datas:
                        m = re.findall(r"([^\:]+)\:([^\:]+)\:(\d+\.?\d*)\;", morph_data)
                        self.frame.morph_panel_ctrl.bulk_morph_set_dict[1].append((m[0][0], m[0][1], float(m[0][2])))

                    # 接触规避
                    self.frame.arm_panel_ctrl.arm_process_flg_avoidance.SetValue(arm_avoidance_datas[0])

                    # 接触规避数据
                    self.frame.arm_panel_ctrl.bulk_avoidance_set_dict[0] = []
                    for avoidance_data in avoidance_name_datas:
                        m = re.findall(r"([^\:]+)\;", avoidance_data)
                        self.frame.arm_panel_ctrl.bulk_avoidance_set_dict[0].append(m[0][0])

                    # 位置对齐
                    self.frame.arm_panel_ctrl.arm_process_flg_alignment.SetValue(arm_alignment_datas[0])
                    self.frame.arm_panel_ctrl.arm_alignment_finger_flg_ctrl.SetValue(finger_alignment_datas[0])
                    self.frame.arm_panel_ctrl.arm_alignment_floor_flg_ctrl.SetValue(floor_alignment_datas[0])

                    # 位置对齐距离
                    self.frame.arm_panel_ctrl.alignment_distance_wrist_slider.SetValue(arm_alignment_length_datas)
                    self.frame.arm_panel_ctrl.alignment_distance_finger_slider.SetValue(finger_alignment_length_datas)
                    self.frame.arm_panel_ctrl.alignment_distance_floor_slider.SetValue(floor_alignment_length_datas)

                    # 移动量修正值
                    self.frame.leg_panel_ctrl.move_correction_slider.SetValue(move_correction_data)
                    
                    # 足ＩＫ偏移
                    self.frame.leg_panel_ctrl.bulk_leg_offset_set_dict[0] = leg_offset_data

                    # 相机
                    self.frame.camera_panel_ctrl.camera_vmd_file_ctrl.file_ctrl.SetPath(org_camera_motion_path)
                    self.frame.camera_panel_ctrl.output_camera_vmd_file_ctrl.file_ctrl.SetPath("")
                    self.frame.camera_panel_ctrl.camera_length_slider.SetValue(camera_length_datas)

                    # 相机源信息
                    self.frame.camera_panel_ctrl.initialize(event)
                    self.frame.camera_panel_ctrl.camera_set_dict[1].camera_model_file_ctrl.file_ctrl.SetPath(org_camera_model_path)
                    self.frame.camera_panel_ctrl.camera_set_dict[1].camera_offset_y_ctrl.SetValue(camera_y_offset_datas)
                    
                    # 更改输出路径
                    self.frame.file_panel_ctrl.file_set.set_output_vmd_path(event)
                    self.frame.camera_panel_ctrl.set_output_vmd_path(event)
                else:
                    # 添加多人面板组
                    self.frame.multi_panel_ctrl.on_add_set(event)

                    # 文件面板设置
                    self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].motion_vmd_file_ctrl.file_ctrl.SetPath(org_motion_path)
                    self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].org_model_file_ctrl.file_ctrl.SetPath(org_model_path)
                    self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].rep_model_file_ctrl.file_ctrl.SetPath(rep_model_path)
                    self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].output_vmd_file_ctrl.file_ctrl.SetPath("")

                    self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].org_model_file_ctrl.title_parts_ctrl.SetValue(
                        stance_center_xz_datas[0] | stance_upper_datas[0] | stance_lower_datas[0] | stance_leg_ik_datas[0] | \
                        stance_toe_datas[0] | stance_toe_ik_datas[0] | stance_shoulder_datas[0] | stance_center_y_datas[0]
                    )

                    # 站姿追加修正
                    self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].selected_stance_details = []
                    if stance_center_xz_datas[0] == 1:
                        self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].selected_stance_details.append(0)
                    if stance_upper_datas[0] == 1:
                        self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].selected_stance_details.append(1)
                    if stance_lower_datas[0] == 1:
                        self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].selected_stance_details.append(2)
                    if stance_leg_ik_datas[0] == 1:
                        self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].selected_stance_details.append(3)
                    if stance_toe_datas[0] == 1:
                        self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].selected_stance_details.append(4)
                    if stance_toe_ik_datas[0] == 1:
                        self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].selected_stance_details.append(5)
                    if stance_shoulder_datas[0] == 1:
                        self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].selected_stance_details.append(6)
                    if stance_center_y_datas[0] == 1:
                        self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].selected_stance_details.append(7)

                    # 扭转分散
                    self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].rep_model_file_ctrl.title_parts_ctrl.SetValue(separate_twist_datas[0])

                    # 表情数据
                    self.frame.morph_panel_ctrl.bulk_morph_set_dict[now_motion_idx + 1] = []
                    for morph_data in morph_datas:
                        m = re.findall(r"([^\:]+)\:([^\:]+)\:(\d+\.?\d*)\;", morph_data)
                        self.frame.morph_panel_ctrl.bulk_morph_set_dict[now_motion_idx + 1].append((m[0][0], m[0][1], float(m[0][2])))

                    # 接触规避数据
                    self.frame.arm_panel_ctrl.bulk_avoidance_set_dict[now_motion_idx - 1] = []
                    for avoidance_data in avoidance_name_datas:
                        m = re.findall(r"([^\:]+)\;", avoidance_data)
                        self.frame.arm_panel_ctrl.bulk_avoidance_set_dict[now_motion_idx - 1].append(m[0][0])
                    
                    # 足ＩＫ偏移
                    self.frame.leg_panel_ctrl.bulk_leg_offset_set_dict[now_motion_idx - 1] = leg_offset_data

                    # 手指位置对齐始终为0（防止弹出对话框）
                    self.frame.arm_panel_ctrl.arm_alignment_finger_flg_ctrl.SetValue(0)

                    # 相机源信息
                    self.frame.camera_panel_ctrl.initialize(event)
                    self.frame.camera_panel_ctrl.camera_set_dict[now_motion_idx + 1].camera_model_file_ctrl.file_ctrl.SetPath(org_camera_model_path)
                    self.frame.camera_panel_ctrl.camera_set_dict[now_motion_idx + 1].camera_offset_y_ctrl.SetValue(camera_y_offset_datas)
                    
                    # 更改输出路径
                    self.frame.multi_panel_ctrl.file_set_list[now_motion_idx - 1].set_output_vmd_path(event)
        
        if not is_buld:
            # 批量处理结束
            self.finish_buld()

            return

        # 暂时解除固定
        self.frame.release_tab()
        # 切换到文件标签页
        self.frame.note_ctrl.ChangeSelection(self.frame.file_panel_ctrl.tab_idx)
        # 表单禁用
        self.frame.file_panel_ctrl.disable()
        # 固定标签页
        self.frame.file_panel_ctrl.fix_tab()

        # 文件标签页的控制台
        sys.stdout = self.frame.file_panel_ctrl.console_ctrl

        self.frame.elapsed_time = 0
        result = True
        result = self.frame.is_valid() and result

        if not result:
            # 允许切换标签页
            self.frame.release_tab()
            # 表单启用
            self.frame.enable()

            return result

        # 开始读取
        if self.frame.load_worker:
            logger.error("仍有处理正在执行。请等待其结束后再次执行。", decoration=MLogger.DECORATION_BOX)
        else:
            # 切换为停止按钮
            self.frame.file_panel_ctrl.check_btn_ctrl.SetLabel("停止读取处理")
            self.frame.file_panel_ctrl.check_btn_ctrl.Enable()

            # 在另一线程执行（没有下一行时，以-1作为结束标志）
            self.frame.load_worker = LoadWorkerThread(self.frame, BulkLoadThreadEvent, row_no if row_no > line_idx else -1, True, False, False, False)
            self.frame.load_worker.start()

        return result
    
    # 读取完成处理
    def on_load_result(self, event: wx.Event):
        self.frame.elapsed_time = event.elapsed_time
        
        # 允许切换标签页
        self.frame.release_tab()
        # 表单启用
        self.frame.enable()
        # 结束工作线程
        self.frame.load_worker = None
        # 隐藏进度条
        self.frame.file_panel_ctrl.gauge_ctrl.SetValue(0)

        if not event.result:
            # 播放结束提示音
            self.frame.sound_finish()
            
            event.Skip()
            return False

        result = self.frame.is_loaded_valid()

        if not result:
            # 允许切换标签页
            self.frame.release_tab()
            # 表单启用
            self.frame.enable()

            event.Skip()
            return False
        
        logger.info("文件数据读取已完成", decoration=MLogger.DECORATION_BOX, title="OK")

        # 表单禁用
        self.frame.file_panel_ctrl.disable()
        # 固定标签页
        self.frame.file_panel_ctrl.fix_tab()

        if self.frame.worker:
            logger.error("仍有处理正在执行。请等待其结束后再次执行。", decoration=MLogger.DECORATION_BOX)
        else:
            # 切换为停止按钮
            self.frame.file_panel_ctrl.exec_btn_ctrl.SetLabel("停止VMD适配")
            self.frame.file_panel_ctrl.exec_btn_ctrl.Enable()

            # 在另一线程执行
            self.frame.worker = SizingWorkerThread(self.frame, BulkSizingThreadEvent, event.target_idx, self.frame.is_saving, self.frame.is_out_log)
            self.frame.worker.start()

    # 线程执行结果
    def on_exec_result(self, event: wx.Event):
        # 切换为执行按钮
        self.frame.file_panel_ctrl.exec_btn_ctrl.SetLabel("执行VMD适配")
        self.frame.file_panel_ctrl.exec_btn_ctrl.Enable()

        if not event.result:
            # 播放结束提示音
            self.frame.sound_finish()

            event.Skip()
            return False
        
        self.frame.elapsed_time += event.elapsed_time
        worked_time = "\n处理时间: {0}".format(self.frame.show_worked_time())
        logger.info(worked_time)

        if self.frame.is_out_log and event.output_log_path and os.path.exists(event.output_log_path):
            # 需要输出日志时，追加写入
            with open(event.output_log_path, mode='a', encoding='utf-8') as f:
                f.write(worked_time)

        # 结束工作线程
        self.frame.worker = None
        
        if event.target_idx >= 0:
            # 存在下一个目标时，处理下一个
            logger.info("\n----------------------------------")

            return self.load(event, event.target_idx + 1)

        # 批量处理结束
        self.finish_buld()

    def finish_buld(self):
        # 文件标签页的控制台
        sys.stdout = self.frame.file_panel_ctrl.console_ctrl

        # 播放结束提示音
        self.frame.sound_finish()

        # 文件标签页的控制台
        if sys.stdout != self.frame.file_panel_ctrl.console_ctrl:
            sys.stdout = self.frame.file_panel_ctrl.console_ctrl

        # 清除批量处理用数据
        self.frame.morph_panel_ctrl.bulk_morph_set_dict = {}
        self.frame.arm_panel_ctrl.bulk_avoidance_set_dict = {}
        self.frame.camera_panel_ctrl.bulk_camera_set_dict = {}

        # 允许切换标签页
        self.frame.release_tab()
        # 表单启用
        self.frame.enable()
        # 隐藏进度条
        self.frame.file_panel_ctrl.gauge_ctrl.SetValue(0)

        logger.info("所有适配处理已全部完成", decoration=MLogger.DECORATION_BOX, title="批量处理")
        