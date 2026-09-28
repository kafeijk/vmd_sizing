# -*- coding: utf-8 -*-
#
import os
import logging # noqa
import numpy as np
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from module.MMath import MRect, MVector3D, MVector4D, MQuaternion, MMatrix4x4 # noqa
from module.MOptions import MOptions, MOptionsDataSet
from utils import MServiceUtils, MBezierUtils # noqa
from utils.MLogger import MLogger # noqa
from utils.MException import SizingException, MKilledException


logger = MLogger(__name__, level=logging.DEBUG)


class MoveService():
    def __init__(self, options: MOptions):
        self.options = options

    def execute(self):
        futures = []

        with ThreadPoolExecutor(thread_name_prefix="move", max_workers=min(5, self.options.max_workers)) as executor:
            for data_set_idx, data_set in enumerate(self.options.data_set_list):
                if data_set.motion.motion_cnt <= 0:
                    # 没有动作数据时，跳过处理
                    continue

                logger.info("移动修正　【No.%s】", (data_set_idx + 1), decoration=MLogger.DECORATION_LINE)

                # 计算中心的Y轴偏移
                self.set_center_y_offset(data_set_idx, data_set)

                # 计算中心的Z轴偏移
                self.set_center_z_offset(data_set_idx, data_set)

                # 计算腿IK的偏移
                self.set_leg_ik_offset(data_set_idx, data_set)

                for bone_name in ["全ての親", "センター", "グルーブ", "右足IK親", "左足IK親", "右足ＩＫ", "左足ＩＫ", "右つま先ＩＫ", "左つま先ＩＫ"]:
                    if bone_name in data_set.motion.bones and bone_name in data_set.rep_model.bones and len(data_set.motion.bones[bone_name].keys()) > 0:
                        futures.append(executor.submit(self.adjust_move, data_set_idx, bone_name))

                if self.options.now_process_ctrl:
                    self.options.now_process += 1
                    self.options.now_process_ctrl.write(str(self.options.now_process))

                    proccess_key = "【No.{0}】{1}({2})".format(data_set_idx + 1, os.path.basename(data_set.motion.path), data_set.rep_model.name)
                    self.options.tree_process_dict[proccess_key]["移動縮尺補正"] = True
                
        concurrent.futures.wait(futures, timeout=None, return_when=concurrent.futures.FIRST_EXCEPTION)

        for f in futures:
            if not f.result():
                return False

        return True
    
    def adjust_move(self, data_set_idx: int, bone_name: str):
        try:
            logger.copy(self.options)
            data_set = self.options.data_set_list[data_set_idx]
            fnos = data_set.motion.get_bone_fnos(bone_name)
            bone_link = data_set.rep_model.create_link_2_top_one(bone_name)

            for fno in fnos:
                bf = data_set.motion.bones[bone_name][fno]

                # 先按原样乘以IK比例
                bf.position.setX(bf.position.x() * data_set.xz_ratio)
                bf.position.setY(bf.position.y() * data_set.y_ratio)
                bf.position.setZ(bf.position.z() * data_set.xz_ratio)

                _, rep_global_mats = MServiceUtils.calc_global_pos(data_set.rep_model, bone_link, data_set.motion, fno, return_matrix=True)
                # 该骨骼的局部位置
                local_pos = rep_global_mats[bone_name].inverted() * bf.position
                # 对局部位置进行偏移调整
                local_pos += data_set.rep_model.bones[bone_name].local_offset
                # 恢复原状
                bf.position = rep_global_mats[bone_name] * local_pos

            if len(fnos) > 0:
                logger.info("移动修正:完成【No.%s - %s】", data_set_idx + 1, bone_name)
            
            return True
        except MKilledException as ke:
            raise ke
        except SizingException as se:
            logger.error("适配处理因无法处理的数据而结束。\n\n%s", se.message)
            return se
        except Exception as e:
            import traceback
            logger.error("适配处理因意外错误而结束。\n\n%s", traceback.format_exc())
            raise e

    def set_leg_ik_offset(self, data_set_idx: int, data_set: MOptionsDataSet):
        target_bones = ["左足", "左足ＩＫ", "右足ＩＫ"]

        if set(target_bones).issubset(data_set.org_model.bones) and set(target_bones).issubset(data_set.rep_model.bones):
            # 腿骨骼的差值（以org为基准，因此比例反转）
            leg_ratio = 1 / data_set.original_xz_ratio

            # 腿IK的偏移上限
            leg_ik_offset = {"左": MVector3D(), "右": MVector3D()}
            for direction in ["左", "右"]:
                org_leg_ik_pos = data_set.org_model.bones["{0}足ＩＫ".format(direction)].position
                rep_leg_ik_global_pos = data_set.rep_model.bones["{0}足ＩＫ".format(direction)].position
                org_leg_pos = data_set.org_model.bones["{0}足".format(direction)].position
                rep_leg_pos = data_set.rep_model.bones["{0}足".format(direction)].position
                # IKオフセット
                leg_ik_offset[direction] = ((org_leg_ik_pos - org_leg_pos) * leg_ratio) - (rep_leg_ik_global_pos - rep_leg_pos)
                leg_ik_offset[direction].effective()
                leg_ik_offset[direction].setY(0)
                leg_ik_offset[direction].setZ(0)
                logger.debug("leg_ik_offset(%s): %s", direction, leg_ik_offset[direction])

                if abs(leg_ik_offset[direction].x() * data_set.original_xz_ratio) > abs(rep_leg_ik_global_pos.x()):
                    # 若IK偏移相对原本腿部位置扩张超过一定值，则收缩
                    re_x = (rep_leg_ik_global_pos.x() - (leg_ik_offset[direction].x() * data_set.original_xz_ratio)) * data_set.original_xz_ratio
                    # 偏移扩张方向与原本相同时为正，相反时为负
                    leg_ik_offset[direction].setX(re_x * (1 if np.sign(leg_ik_offset[direction].x()) == np.sign(rep_leg_ik_global_pos.x()) else -1))
                
                # 加上指定值
                specified_leg_offset = 0
                if data_set_idx in self.options.leg_options.leg_offsets:
                    specified_leg_offset = self.options.leg_options.leg_offsets[data_set_idx] * np.sign(rep_leg_ik_global_pos.x())

                leg_ik_offset[direction].setX(leg_ik_offset[direction].x() + specified_leg_offset)
                logger.debug("specified_leg_offset(%s): %s -> %s", direction, specified_leg_offset, leg_ik_offset[direction].x())
                
            logger.info("【No.%s】IK偏移(%s): x: %s, z: %s", (data_set_idx + 1), "左足", leg_ik_offset["左"].x(), leg_ik_offset["左"].z())
            logger.info("【No.%s】IK偏移(%s): x: %s, z: %s", (data_set_idx + 1), "右足", leg_ik_offset["右"].x(), leg_ik_offset["右"].z())

            if "左足IK親" in data_set.rep_model.bones and "左足IK親" in data_set.motion.bones:
                # 存在IK父骨骼且被使用时，为IK父骨骼设置偏移
                data_set.rep_model.bones["左足IK親"].local_offset = leg_ik_offset["左"]
            else:
                data_set.rep_model.bones["左足ＩＫ"].local_offset = leg_ik_offset["左"]

            if "右足IK親" in data_set.rep_model.bones and "右足IK親" in data_set.motion.bones:
                # 存在IK父骨骼且被使用时，为IK父骨骼设置偏移
                data_set.rep_model.bones["右足IK親"].local_offset = leg_ik_offset["右"]
            else:
                data_set.rep_model.bones["右足ＩＫ"].local_offset = leg_ik_offset["右"]

            return

        logger.info("无IK偏移")

    # 计算中心Y偏移
    def set_center_y_offset(self, data_set_idx: int, data_set: MOptionsDataSet):
        target_bones = ["左足", "左ひざ", "左足首", "センター"]

        if set(target_bones).issubset(data_set.org_model.bones) and set(target_bones).issubset(data_set.rep_model.bones):
            specified_leg_offset = 0
            if data_set_idx in self.options.leg_options.leg_offsets:
                specified_leg_offset = self.options.leg_options.leg_offsets[data_set_idx]
            
            # 目标模型的脚踝位置需考虑腿ＩＫ偏移
            rep_ankle_pos = data_set.rep_model.bones["左足首"].position - MVector3D(specified_leg_offset, 0, 0)
            # 源模型的腿部长度比
            org_leg_upper_length = (data_set.org_model.bones["左ひざ"].position.distanceToPoint(data_set.org_model.bones["左足"].position))
            org_leg_lower_length = (data_set.org_model.bones["左ひざ"].position.distanceToPoint(rep_ankle_pos))
            org_leg_ik_length = (data_set.org_model.bones["左足"].position - rep_ankle_pos).y()
            logger.test("org_leg_upper_length: %s", org_leg_upper_length)
            logger.test("org_leg_lower_length: %s", org_leg_lower_length)
            logger.test("org_leg_ik_length: %s", org_leg_ik_length)

            # 腿骨骼长度与IK的长度比
            org_leg_ratio = org_leg_ik_length / (org_leg_upper_length + org_leg_lower_length)
            logger.test("org_leg_ratio: %s", org_leg_ratio)

            # 目标模型的腿部长度比
            rep_leg_upper_length = (data_set.rep_model.bones["左ひざ"].position.distanceToPoint(data_set.rep_model.bones["左足"].position))
            rep_leg_lower_length = (data_set.rep_model.bones["左ひざ"].position.distanceToPoint(data_set.rep_model.bones["左足首"].position))
            rep_leg_ik_length = (data_set.rep_model.bones["左足"].position - data_set.rep_model.bones["左足首"].position).y()
            logger.test("rep_leg_upper_length: %s", rep_leg_upper_length)
            logger.test("rep_leg_lower_length: %s", rep_leg_lower_length)
            logger.test("rep_leg_ik_length: %s", rep_leg_ik_length)

            # 根据源模型的长度比，重新计算腿IK的长度比
            rep_recalc_ik_length = org_leg_ratio * (rep_leg_upper_length + rep_leg_lower_length)
            logger.test("rep_recalc_ik_length: %s", rep_recalc_ik_length)

            if rep_recalc_ik_length < rep_leg_ik_length:
                # 重新计算的长度小于原本IK长度时（腿部弯曲的情况）
                
                # 略微缩短中心Y，使腿部各边比例一致
                offset_y = rep_recalc_ik_length - rep_leg_ik_length

                data_set.rep_model.bones["センター"].local_offset.setY(offset_y)
                logger.test("local_offset %s", data_set.rep_model.bones["センター"].local_offset)

                logger.info("【No.%s】中心Y偏移: %s", (data_set_idx + 1), offset_y)

                return

            logger.info("【No.%s】无中心Y偏移", (data_set_idx + 1))

    # 计算中心Z偏移
    def set_center_z_offset(self, data_set_idx: int, data_set: MOptionsDataSet):
        target_bones = ["左つま先ＩＫ", "左足", "左足首", "センター"]

        if set(target_bones).issubset(data_set.org_model.bones) and set(target_bones).issubset(data_set.rep_model.bones):
            # 源模型中心的Z位置
            org_center_z = data_set.org_model.bones["センター"].position.z()
            logger.test("org_center_z: %s", org_center_z)
            # 源模型左脚踝的Z位置
            org_ankle_z = data_set.org_model.bones["左足首"].position.z()
            logger.test("org_ankle_z: %s", org_ankle_z)
            # 源模型左腿的Z位置
            org_leg_z = data_set.org_model.bones["左足"].position.z()
            logger.test("org_leg_z: %s", org_leg_z)
            # 源模型脚尖的Z位置
            org_toe_z = data_set.org_model.left_toe_vertex.position.z()
            logger.test("org_toe_z: %s", org_toe_z)

            # 目标模型中心的Z位置
            rep_center_z = data_set.rep_model.bones["センター"].position.z()
            logger.test("rep_center_z: %s", rep_center_z)
            # 目标模型左脚踝的Z位置
            rep_ankle_z = data_set.rep_model.bones["左足首"].position.z()
            logger.test("rep_ankle_z: %s", rep_ankle_z)
            # 目标模型左腿的Z位置
            rep_leg_z = data_set.rep_model.bones["左足"].position.z()
            logger.test("rep_leg_z: %s", rep_leg_z)
            # 目标模型脚尖的Z位置
            rep_toe_z = data_set.rep_model.left_toe_vertex.position.z()
            logger.test("rep_toe_z: %s", rep_toe_z)

            # 源模型的腿部长度
            org_leg_zlength = org_ankle_z - org_toe_z
            # 源模型的重心
            org_center_gravity = (org_ankle_z - org_leg_z) / (org_ankle_z - org_toe_z)
            logger.test("org_center_gravity %s, org_leg_zlength: %s", org_center_gravity, org_leg_zlength)

            # 目标模型的腿部长度
            rep_leg_zlength = rep_ankle_z - rep_toe_z
            # 目标模型的重心
            rep_center_gravity = (rep_ankle_z - rep_leg_z) / (rep_ankle_z - rep_toe_z)
            logger.test("rep_center_gravity %s, rep_leg_zlength: %s", rep_center_gravity, rep_leg_zlength)

            local_offset_z = (rep_center_gravity - org_center_gravity) * (rep_leg_zlength / org_leg_zlength)
            data_set.rep_model.bones["センター"].local_offset.setZ(local_offset_z)
            logger.test("local_offset %s", data_set.rep_model.bones["センター"].local_offset)

            logger.info("【No.%s】中心Z偏移: %s", (data_set_idx + 1), local_offset_z)

            return

        logger.info("【No.%s】无中心Z偏移", (data_set_idx + 1))



