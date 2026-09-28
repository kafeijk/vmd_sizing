# -*- coding: utf-8 -*-
#

import os
import time
import wx
import re
import gc

from form.worker.BaseWorkerThread import BaseWorkerThread, task_takes_time
from module.MOptions import MOptions, MOptionsDataSet, MArmProcessOptions, MLegProcessOptions
from service.SizingService import SizingService
from utils import MFileUtils # noqa
from utils.MLogger import MLogger # noqa

logger = MLogger(__name__)


class SizingWorkerThread(BaseWorkerThread):

    def __init__(self, frame: wx.Frame, result_event: wx.Event, target_idx: int, is_exec_saving: bool, is_out_log: bool):
        self.elapsed_time = 0
        self.is_out_log = is_out_log
        self.is_exec_saving = is_exec_saving
        self.target_idx = target_idx
        self.gauge_ctrl = frame.file_panel_ctrl.gauge_ctrl
        self.options = None
        self.output_log_path = None

        super().__init__(frame, result_event, frame.file_panel_ctrl.console_ctrl)

    @task_takes_time
    def thread_event(self):
        try:
            start = time.time()
            # 数据集列表
            data_set_list = []
            total_process = 0
            self.frame.file_panel_ctrl.tree_process_dict = {}

            now_camera_output_vmd_path = None
            now_camera_data = None
            now_camera_path = self.frame.camera_panel_ctrl.camera_vmd_file_ctrl.file_ctrl.GetPath()
            if len(now_camera_path) > 0:
                now_camera_data = self.frame.camera_panel_ctrl.camera_vmd_file_ctrl.data.copy()
                now_camera_output_vmd_path = self.frame.camera_panel_ctrl.output_camera_vmd_file_ctrl.file_ctrl.GetPath()

            if self.frame.file_panel_ctrl.file_set.is_loaded():
                
                proccess_key = "【No.1】{0}({1})".format( \
                    os.path.basename(self.frame.file_panel_ctrl.file_set.motion_vmd_file_ctrl.data.path), \
                    self.frame.file_panel_ctrl.file_set.rep_model_file_ctrl.data.name)

                camera_offset_y = 0
                camera_org_model = None
                if len(now_camera_path) > 0:
                    camera_org_model = self.frame.file_panel_ctrl.file_set.org_model_file_ctrl.data
                    if 1 in self.frame.camera_panel_ctrl.camera_set_dict:
                        if self.frame.camera_panel_ctrl.camera_set_dict[1].camera_model_file_ctrl.is_set_path():
                            # 已指定相机源模型时，重新指定相机源模型
                            camera_org_model = self.frame.camera_panel_ctrl.camera_set_dict[1].camera_model_file_ctrl.data
                        camera_offset_y = self.frame.camera_panel_ctrl.camera_set_dict[1].camera_offset_y_ctrl.GetValue()
                
                morph_list, morph_seted = self.frame.morph_panel_ctrl.get_morph_list(1, self.frame.file_panel_ctrl.file_set.motion_vmd_file_ctrl.data.digest, \
                    self.frame.file_panel_ctrl.file_set.org_model_file_ctrl.data.digest, self.frame.file_panel_ctrl.file_set.rep_model_file_ctrl.data.digest)   # noqa

                if not self.frame.camera_panel_ctrl.camera_only_flg_ctrl.GetValue():
                    # 第1组动作与模型
                    self.frame.file_panel_ctrl.tree_process_dict[proccess_key] = {"移動縮尺補正": False}

                    total_process += 2                                                                                      # 基本修正・手臂姿势修正
                    if self.frame.file_panel_ctrl.file_set.org_model_file_ctrl.title_parts_ctrl.GetValue() > 0:
                        total_process += len(self.frame.file_panel_ctrl.file_set.get_selected_stance_details())             # 姿势追加修正
                        self.frame.file_panel_ctrl.tree_process_dict[proccess_key]["スタンス追加補正"] = {}

                        for v in self.frame.file_panel_ctrl.file_set.get_selected_stance_details():
                            self.frame.file_panel_ctrl.tree_process_dict[proccess_key]["スタンス追加補正"][v] = False

                    self.frame.file_panel_ctrl.tree_process_dict[proccess_key]["腕スタンス補正"] = False

                    total_process += self.frame.file_panel_ctrl.file_set.rep_model_file_ctrl.title_parts_ctrl.GetValue()    # 扭转分散
                    if self.frame.file_panel_ctrl.file_set.rep_model_file_ctrl.title_parts_ctrl.GetValue() == 1:
                        self.frame.file_panel_ctrl.tree_process_dict[proccess_key]["捩り分散"] = False
                    
                    if self.frame.arm_panel_ctrl.arm_process_flg_avoidance.GetValue() > 0:
                        self.frame.file_panel_ctrl.tree_process_dict[proccess_key]["接触回避"] = False

                    if morph_seted:
                        total_process += 1  # 表情替换
                        self.frame.file_panel_ctrl.tree_process_dict[proccess_key]["モーフ置換"] = False

                # 第1组必定读取
                first_data_set = MOptionsDataSet(
                    motion=self.frame.file_panel_ctrl.file_set.motion_vmd_file_ctrl.data.copy(), \
                    org_model=self.frame.file_panel_ctrl.file_set.org_model_file_ctrl.data, \
                    rep_model=self.frame.file_panel_ctrl.file_set.rep_model_file_ctrl.data, \
                    output_vmd_path=self.frame.file_panel_ctrl.file_set.output_vmd_file_ctrl.file_ctrl.GetPath(), \
                    detail_stance_flg=self.frame.file_panel_ctrl.file_set.org_model_file_ctrl.title_parts_ctrl.GetValue(), \
                    twist_flg=self.frame.file_panel_ctrl.file_set.rep_model_file_ctrl.title_parts_ctrl.GetValue(), \
                    morph_list=morph_list, \
                    camera_org_model=camera_org_model, \
                    camera_offset_y=camera_offset_y, \
                    selected_stance_details=self.frame.file_panel_ctrl.file_set.get_selected_stance_details()
                )
                data_set_list.append(first_data_set)

            # 第2组以后仅读取有效的数据
            for multi_idx, file_set in enumerate(self.frame.multi_panel_ctrl.file_set_list):
                if file_set.is_loaded():

                    proccess_key = "【No.{0}】{1}({2})".format( \
                        file_set.set_no, \
                        os.path.basename(file_set.motion_vmd_file_ctrl.data.path), \
                        file_set.rep_model_file_ctrl.data.name)

                    # 第2组以后的动作与模型
                    morph_list, morph_seted = self.frame.morph_panel_ctrl.get_morph_list(file_set.set_no, file_set.motion_vmd_file_ctrl.data.digest, \
                        file_set.org_model_file_ctrl.data.digest, file_set.rep_model_file_ctrl.data.digest)   # noqa

                    if not self.frame.camera_panel_ctrl.camera_only_flg_ctrl.GetValue():
                        self.frame.file_panel_ctrl.tree_process_dict[proccess_key] = {"移動縮尺補正": False}

                        total_process += 2                                                                          # 基本修正・手臂姿势修正
                        if file_set.org_model_file_ctrl.title_parts_ctrl.GetValue() > 0:
                            total_process += len(file_set.get_selected_stance_details())                            # 姿势追加修正
                            self.frame.file_panel_ctrl.tree_process_dict[proccess_key]["スタンス追加補正"] = {}

                            for v in file_set.get_selected_stance_details():
                                self.frame.file_panel_ctrl.tree_process_dict[proccess_key]["スタンス追加補正"][v] = False

                        total_process += file_set.rep_model_file_ctrl.title_parts_ctrl.GetValue()                   # 扭转分散
                        if file_set.rep_model_file_ctrl.title_parts_ctrl.GetValue() == 1:
                            self.frame.file_panel_ctrl.tree_process_dict[proccess_key]["捩り分散"] = False

                        self.frame.file_panel_ctrl.tree_process_dict[proccess_key]["腕スタンス補正"] = False

                        if self.frame.arm_panel_ctrl.arm_process_flg_avoidance.GetValue() > 0:
                            self.frame.file_panel_ctrl.tree_process_dict[proccess_key]["接触回避"] = False

                    if morph_seted:
                        total_process += 1  # 表情替换
                        self.frame.file_panel_ctrl.tree_process_dict[proccess_key]["モーフ置換"] = False

                    camera_offset_y = 0
                    camera_org_model = file_set.org_model_file_ctrl.data
                    if multi_idx + 2 in self.frame.camera_panel_ctrl.camera_set_dict:
                        if self.frame.camera_panel_ctrl.camera_set_dict[multi_idx + 2].camera_model_file_ctrl.is_set_path():
                            # 已指定相机源模型时，重新指定相机源模型
                            camera_org_model = self.frame.camera_panel_ctrl.camera_set_dict[multi_idx + 2].camera_model_file_ctrl.data
                        camera_offset_y = self.frame.camera_panel_ctrl.camera_set_dict[multi_idx + 2].camera_offset_y_ctrl.GetValue()

                    multi_data_set = MOptionsDataSet(
                        motion=file_set.motion_vmd_file_ctrl.data.copy(), \
                        org_model=file_set.org_model_file_ctrl.data, \
                        rep_model=file_set.rep_model_file_ctrl.data, \
                        output_vmd_path=file_set.output_vmd_file_ctrl.file_ctrl.GetPath(), \
                        detail_stance_flg=file_set.org_model_file_ctrl.title_parts_ctrl.GetValue(), \
                        twist_flg=file_set.rep_model_file_ctrl.title_parts_ctrl.GetValue(), \
                        morph_list=morph_list, \
                        camera_org_model=camera_org_model, \
                        camera_offset_y=camera_offset_y, \
                        selected_stance_details=file_set.get_selected_stance_details()
                    )
                    data_set_list.append(multi_data_set)
            
            total_process += self.frame.arm_panel_ctrl.arm_process_flg_avoidance.GetValue() * len(data_set_list)    # 接触规避
            total_process += self.frame.arm_panel_ctrl.arm_process_flg_alignment.GetValue()                         # 位置对齐
            if not self.frame.camera_panel_ctrl.camera_only_flg_ctrl.GetValue() and self.frame.arm_panel_ctrl.arm_process_flg_alignment.GetValue() > 0:
                self.frame.file_panel_ctrl.tree_process_dict["位置合わせ"] = False

            if len(now_camera_path) > 0:
                total_process += 1                                                                                  # 相机
                self.frame.file_panel_ctrl.tree_process_dict["カメラ補正"] = False

            self.options = MOptions(\
                version_name=self.frame.version_name, \
                logging_level=self.frame.logging_level, \
                data_set_list=data_set_list, \
                arm_options=MArmProcessOptions( \
                    self.frame.arm_panel_ctrl.arm_process_flg_avoidance.GetValue(), \
                    self.frame.arm_panel_ctrl.get_avoidance_target(), \
                    self.frame.arm_panel_ctrl.arm_process_flg_alignment.GetValue(), \
                    self.frame.arm_panel_ctrl.arm_alignment_finger_flg_ctrl.GetValue(), \
                    self.frame.arm_panel_ctrl.arm_alignment_floor_flg_ctrl.GetValue(), \
                    self.frame.arm_panel_ctrl.alignment_distance_wrist_slider.GetValue(), \
                    self.frame.arm_panel_ctrl.alignment_distance_finger_slider.GetValue(), \
                    self.frame.arm_panel_ctrl.alignment_distance_floor_slider.GetValue(), \
                    self.frame.arm_panel_ctrl.arm_check_skip_flg_ctrl.GetValue()
                ), \
                leg_options=MLegProcessOptions(
                    move_correction_ratio=self.frame.leg_panel_ctrl.move_correction_slider.GetValue(),
                    leg_offsets=self.frame.leg_panel_ctrl.get_leg_offsets()
                ), \
                camera_motion=now_camera_data, \
                camera_output_vmd_path=now_camera_output_vmd_path, \
                is_sizing_camera_only=self.frame.camera_panel_ctrl.camera_only_flg_ctrl.GetValue(), \
                camera_length=self.frame.camera_panel_ctrl.camera_length_slider.GetValue(), \
                monitor=self.frame.file_panel_ctrl.console_ctrl, \
                is_file=False, \
                outout_datetime=logger.outout_datetime, \
                max_workers=(1 if self.is_exec_saving else min(32, os.cpu_count() + 4)), \
                total_process=total_process, \
                now_process=0, \
                total_process_ctrl=self.frame.file_panel_ctrl.total_process_ctrl, \
                now_process_ctrl=self.frame.file_panel_ctrl.now_process_ctrl, \
                tree_process_dict=self.frame.file_panel_ctrl.tree_process_dict)
            
            self.result = SizingService(self.options).execute() and self.result

            self.elapsed_time = time.time() - start
        except Exception as e:
            logger.critical("VMD适配处理因意外错误而结束。", e, decoration=MLogger.DECORATION_BOX)
        finally:
            try:
                logger.debug("★★★result: %s, is_killed: %s", self.result, self.is_killed)
                if self.is_out_log or (not self.result and not self.is_killed):
                    # 生成日志路径
                    output_vmd_path = self.frame.file_panel_ctrl.file_set.output_vmd_file_ctrl.file_ctrl.GetPath()
                    self.output_log_path = re.sub(r'\.vmd$', '.log', output_vmd_path)

                    # 将已输出的消息全部写出
                    self.frame.file_panel_ctrl.console_ctrl.SaveFile(filename=self.output_log_path)

            except Exception:
                pass

    def thread_delete(self):
        del self.options
        gc.collect()

    def post_event(self):
        wx.PostEvent(self.frame, self.result_event(result=self.result and not self.is_killed, target_idx=self.target_idx, elapsed_time=self.elapsed_time, output_log_path=self.output_log_path))

