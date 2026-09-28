# -*- coding: utf-8 -*-
#
import os
import copy

from mmd.VmdData import VmdMorphFrame
from module.MMath import MRect, MVector3D, MVector4D, MQuaternion, MMatrix4x4 # noqa
from module.MOptions import MOptions, MOptionsDataSet
from utils import MServiceUtils, MBezierUtils # noqa
from utils.MLogger import MLogger # noqa
from utils.MException import SizingException, MKilledException


logger = MLogger(__name__)


class MorphService():
    def __init__(self, options: MOptions):
        self.options = options

    def execute(self):
        for data_set_idx, data_set in enumerate(self.options.data_set_list):
            if data_set.motion.morph_cnt <= 0 or len(data_set.morph_list) == 0:
                # 无表情数据或无替换数据时，跳过处理
                continue

            logger.info("表情替换　【No.%s】", (data_set_idx + 1), decoration=MLogger.DECORATION_LINE)

            self.replace_morph(data_set_idx, data_set)

            if self.options.now_process_ctrl:
                self.options.now_process += 1
                self.options.now_process_ctrl.write(str(self.options.now_process))

                proccess_key = "【No.{0}】{1}({2})".format(data_set_idx + 1, os.path.basename(data_set.motion.path), data_set.rep_model.name)
                self.options.tree_process_dict[proccess_key]["モーフ置換"] = True

        return True

    # 执行表情替换
    def replace_morph(self, data_set_idx: int, data_set: MOptionsDataSet):
        try:
            # 替换前的表情列表
            original_morphs = {}
            # 替换后的表情列表
            replaced_morphs = {}

            for (org_morph_name, rep_morph_name, morph_ratio) in data_set.morph_list:
                if org_morph_name in data_set.motion.morphs:
                    # 存在替换源表情时，保留
                    original_morphs[org_morph_name] = copy.deepcopy(data_set.motion.morphs[org_morph_name])

                if rep_morph_name in data_set.motion.morphs and org_morph_name != rep_morph_name:
                    # 存在替换目标表情时，保留（源与目标相同时跳过）
                    replaced_morphs[rep_morph_name] = copy.deepcopy(data_set.motion.morphs[rep_morph_name])
            
            # 已保留，故删除表情
            for (org_morph_name, rep_morph_name, morph_ratio) in data_set.morph_list:
                if org_morph_name in data_set.motion.morphs:
                    del data_set.motion.morphs[org_morph_name]
                
                if rep_morph_name in data_set.motion.morphs:
                    del data_set.motion.morphs[rep_morph_name]

            for (org_morph_name, rep_morph_name, morph_ratio) in data_set.morph_list:
                if org_morph_name in original_morphs and rep_morph_name not in replaced_morphs:
                    # 源有而目标没有时，以目标名称注册替换源
                    for fno, org_morph_data in original_morphs[org_morph_name].items():
                        morph_data = VmdMorphFrame(fno)
                        # 替换名称
                        morph_data.set_name(rep_morph_name)

                        # 大小乘以比例
                        morph_data.ratio = org_morph_data.ratio * morph_ratio

                        if rep_morph_name not in replaced_morphs:
                            replaced_morphs[rep_morph_name] = {}

                        # 设置替换后的表情数据
                        replaced_morphs[rep_morph_name][fno] = morph_data
            
                elif org_morph_name in original_morphs and rep_morph_name in replaced_morphs:
                    # 源有且目标也有时
                    for fno, org_morph_data in original_morphs[org_morph_name].items():
                        morph_data = VmdMorphFrame(fno)

                        # 替换名称
                        morph_data.set_name(rep_morph_name)

                        # 大小乘以比例
                        morph_data.ratio = org_morph_data.ratio * morph_ratio

                        if fno in replaced_morphs[rep_morph_name]:
                            # 若目标fno已注册，则累加后注册
                            morph_data.ratio += replaced_morphs[rep_morph_name][fno].ratio

                        # 追加替换后的表情数据
                        replaced_morphs[rep_morph_name][fno] = morph_data

                logger.info("表情替换 %s → %s (%s)【No.%s】", org_morph_name, rep_morph_name, morph_ratio, (data_set_idx + 1))
            
            # 全部替换完成后，重新注册
            for new_rep_morph_name, new_rep_morph_data in replaced_morphs.items():
                data_set.motion.morphs[new_rep_morph_name] = new_rep_morph_data
        except MKilledException as ke:
            raise ke
        except SizingException as se:
            logger.error("适配处理因无法处理的数据而结束。\n\n%s", se.message)
            return se
        except Exception as e:
            import traceback
            logger.error("适配处理因意外错误而结束。\n\n%s", traceback.format_exc())
            raise e


