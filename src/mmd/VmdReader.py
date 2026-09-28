# -*- coding: utf-8 -*-
#
import struct
import hashlib
import re

from mmd.VmdData import (
    VmdMotion,
    VmdBoneFrame,
    VmdCameraFrame,
    VmdInfoIk,
    VmdLightFrame,
    VmdMorphFrame,
    VmdShadowFrame,
    VmdShowIkFrame,
)
from module.MMath import MRect, MVector3D, MVector4D, MQuaternion, MMatrix4x4  # noqa
from utils.MLogger import MLogger  # noqa
from utils.MException import SizingException, MKilledException, MParseException

logger = MLogger(__name__)


class VmdReader:
    def __init__(self, file_path):
        self.offset = 0
        self.buffer = None
        self.encoding = None
        self.file_path = file_path

    # 仅获取模型名
    def read_model_name(self):
        model_name = ""
        with open(self.file_path, "rb") as f:
            # 以二进制方式读取VMD文件
            self.buffer = f.read()

            # vmd版本
            signature = self.unpack(30, "30s")
            logger.test("signature %s", signature)

            # 模型名
            model_bname, model_name = self.read_text(20)
            logger.test("model_bname %s, model_name: %s", model_bname, model_name)

        return model_name

    def read_data(self):
        # 动作路径
        motion = VmdMotion()
        motion.path = self.file_path

        try:
            with open(self.file_path, "rb") as f:
                # 以二进制方式读取VMD文件
                self.buffer = f.read()

                # vmd版本
                signature = self.unpack(30, "30s")
                logger.test("signature %s", signature)

                # モデル名
                model_bname, model_name = self.read_text(20)
                logger.test("model_bname %s, model_name: %s", model_bname, model_name)
                motion.model_name = model_name

                # 动作数
                motion.motion_cnt = self.read_uint(4)
                logger.test("motion.motion_cnt %s", motion.motion_cnt)

                # 1帧的动作信息

                prev_n = 0
                for n in range(motion.motion_cnt):
                    frame = VmdBoneFrame(0)
                    frame.key = True
                    frame.read = True

                    # 骨骼 ----------------------
                    # 骨骼名
                    bone_bname, bone_name = self.read_text(15)

                    frame.name = bone_name
                    frame.bname = bone_bname
                    logger.test("name: %s, bname %s", bone_name, bone_bname)

                    # 帧索引
                    frame.fno = self.read_uint(4)
                    logger.test("frame.fno %s", frame.fno)

                    # 位置X,Y,Z
                    frame.position = self.read_Vector3D()
                    logger.test("frame.position %s", frame.position)

                    # 旋转X,Y,Z,scalar
                    frame.rotation = self.read_Quaternion()
                    logger.test("frame.rotation %s", frame.rotation)
                    logger.test("frame.rotation.euler %s", frame.rotation.toEulerAngles())
                    # 保留原始值
                    frame.org_rotation = frame.rotation.copy()

                    # 插值曲线
                    frame.interpolation = list(self.unpack(64, "64B", True))
                    logger.test("interpolation %s", frame.interpolation)

                    if bone_name not in motion.bones:
                        # 字典中尚不存在时，添加数组
                        motion.bones[bone_name] = {}

                    # 向字典对应位置添加骨骼帧
                    if frame.fno not in motion.bones[bone_name]:
                        motion.bones[bone_name][frame.fno] = frame

                    if frame.fno > motion.last_motion_frame:
                        # 记录最终帧
                        motion.last_motion_frame = frame.fno

                    if n // 10000 > prev_n:
                        prev_n = n // 10000
                        logger.info("-- VMD动作读取 关键帧: %s" % n)

                # 表情数
                motion.morph_cnt = self.read_uint(4)
                logger.test("motion.morph_cnt %s", motion.morph_cnt)

                # 1帧的表情信息
                prev_n = 0
                for n in range(motion.morph_cnt):
                    morph = VmdMorphFrame()
                    morph.key = True
                    morph.read = True

                    # 表情 ----------------------
                    # 表情名
                    morph_bname, morph_name = self.read_text(15)

                    morph.name = morph_name
                    morph.bname = morph_bname
                    logger.test("name: %s, bname %s", morph_name, morph_bname)

                    # 帧索引
                    morph.fno = self.read_uint(4)
                    logger.test("morph.fno %s", morph.fno)

                    # 表情值
                    morph.ratio = self.read_float(4)
                    logger.test("morph.ratio %s", morph.ratio)

                    if morph_name not in motion.morphs:
                        # 字典中尚不存在时，添加数组
                        motion.morphs[morph_name] = {}

                    if morph.fno not in motion.morphs[morph_name]:
                        # 尚不存在时，向字典对应位置添加表情帧
                        motion.morphs[morph_name][morph.fno] = morph

                    if n // 1000 > prev_n:
                        prev_n = n // 1000
                        logger.info("-- VMD动作读取 表情: %s" % n)

                try:
                    # 相机数
                    motion.camera_cnt = self.read_uint(4)
                    logger.test("motion.camera_cnt %s", motion.camera_cnt)

                    # 1帧的相机信息
                    prev_n = 0
                    for n in range(motion.camera_cnt):
                        camera = VmdCameraFrame()

                        # 帧索引
                        camera.fno = self.read_uint(4)
                        logger.test("camera.fno %s", camera.fno)

                        # 距离
                        camera.length = self.read_float(4)
                        logger.test("camera.length %s", camera.length)

                        # 距离为0时，为保险起见先设一个极小的距离
                        if camera.length == 0:
                            camera.length = -0.00001

                        # 位置X,Y,Z
                        camera.position = self.read_Vector3D()
                        logger.test("camera.position %s", camera.position)

                        # 角度（欧拉角）
                        camera.euler = self.read_Vector3D()
                        logger.test("camera.euler %s", camera.euler)

                        # 插值曲线
                        camera.interpolation = self.unpack(24, "24B", True)
                        logger.test("camera.interpolation %s", camera.interpolation)

                        # 视野角
                        camera.angle = self.read_uint(4)
                        logger.test("camera.angle %s", camera.angle)

                        # 有无透视
                        camera.perspective = self.unpack(1, "B")
                        logger.test("camera.perspective %s", camera.perspective)

                        # 保留原始值
                        camera.org_length = camera.length
                        camera.org_position = camera.position.copy()

                        # 添加相机
                        motion.cameras[camera.fno] = camera

                        if n // 10000 > prev_n:
                            prev_n = n // 10000
                            logger.info("VMD相机读取 关键帧: %s" % n)

                except Exception:
                    # 没有信息时，捕获异常并忽略
                    motion.camera_cnt = 0

                # 灯光数
                try:
                    motion.light_cnt = self.read_uint(4)
                    logger.test("motion.light_cnt %s", motion.light_cnt)

                    # 1帧的灯光信息
                    for _ in range(motion.light_cnt):
                        light = VmdLightFrame()

                        # 帧索引
                        light.fno = self.read_uint(4)
                        logger.test("light.fno %s", light.fno)

                        # 灯光颜色（虽为RGB，但担心数值被误改，故用V3D）
                        light.color = self.read_Vector3D()
                        logger.test("light.color %s", light.color)

                        # 灯光位置
                        light.position = self.read_Vector3D()
                        logger.test("light.position %s", light.position)

                        # 添加
                        motion.lights.append(light)

                except Exception:
                    # 没有信息时，捕获异常并忽略
                    motion.light_cnt = 0

                # 自阴影数
                try:
                    motion.shadow_cnt = self.read_uint(4)
                    logger.test("motion.shadow_cnt %s", motion.shadow_cnt)

                    # 1帧的阴影信息
                    for _ in range(motion.shadow_cnt):
                        shadow = VmdShadowFrame()

                        # 帧索引
                        shadow.fno = self.read_uint(4)
                        logger.test("shadow.fno %s", shadow.fno)

                        # 阴影类型
                        shadow.type = self.read_uint(1)
                        logger.test("shadow.type %s", shadow.type)

                        # 距离
                        shadow.distance = self.read_float()
                        logger.test("shadow.distance %s", shadow.distance)

                        # 添加
                        motion.shadows.append(shadow)

                except Exception:
                    # 没有信息时，捕获异常并忽略
                    motion.shadow_cnt = 0

                # IK数
                try:
                    motion.ik_cnt = self.read_uint(4)
                    logger.test("motion.ik_cnt %s", motion.ik_cnt)

                    # 1帧的IK信息
                    for _ in range(motion.ik_cnt):
                        show_ik = VmdShowIkFrame()

                        # 帧索引
                        show_ik.fno = self.read_uint(4)
                        logger.test("ik.fno %s", show_ik.fno)

                        # 模型显示, 0:OFF, 1:ON
                        show_ik.show = self.read_uint(1)
                        logger.test("ik.show %s", show_ik.show)

                        # 记录的IK数量
                        show_ik.ik_count = self.read_uint(4)
                        logger.test("ik.ik_count %s", show_ik.ik_count)

                        for _ in range(show_ik.ik_count):
                            ik_info = VmdInfoIk()

                            # IK名称
                            ik_bname, ik_name = self.read_text(20)
                            ik_info.name = ik_name
                            ik_info.bname = ik_bname
                            logger.test("ik_info.name %s", ik_name)

                            # 模型显示, 0:OFF, 1:ON
                            ik_info.onoff = self.read_uint(1)
                            logger.test("ik_info.onoff %s", ik_info.onoff)

                            show_ik.ik.append(ik_info)

                        # 添加
                        motion.showiks.append(show_ik)

                except Exception:
                    # 旧版MMD（MMDv7.39.x64以前）没有IK信息，因此捕获异常并忽略
                    motion.ik_cnt = 0

            # 设置哈希
            motion.digest = self.hexdigest()
            logger.test("motion: %s, hash: %s", motion.path, motion.digest)

            return motion
        except MKilledException as ke:
            # 结束指令
            raise ke
        except SizingException as se:
            logger.error("VMD读取处理因无法处理的数据而终止。\n\n%s", se.message, decoration=MLogger.DECORATION_BOX)
            return se
        except Exception as e:
            import traceback

            logger.critical(
                "VMD读取处理因意外错误而终止。\n\n%s", traceback.format_exc(), decoration=MLogger.DECORATION_BOX
            )
            raise e

    def hexdigest(self):
        sha1 = hashlib.sha1()

        with open(self.file_path, "rb") as f:
            for chunk in iter(lambda: f.read(2048 * sha1.block_size), b""):
                sha1.update(chunk)

        sha1.update(chunk)

        # 将文件路径纳入哈希
        sha1.update(self.file_path.encode("utf-8"))

        return sha1.hexdigest()

    def read_text(self, format_size):
        bresult = self.unpack(format_size, "{0}s".format(format_size))

        if not self.encoding:
            # 编码尚未确定时，获取编码
            self.encoding = self.get_encoding(bresult, False)

        if self.encoding:
            # 获取到编码时进行还原
            return bresult, self.decode_text(bresult, self.encoding, False)

        return None, None

    # 获取文件的编码
    def get_encoding(self, fbytes, is_raise=True):
        codelst = ("shift-jis", "utf-8")

        for encoding in codelst:
            try:
                fstr = self.decode_text(fbytes, encoding, False)  # 将bytes字符串按指定字符编码转换为字符串
                fstr = fstr.encode("utf-8")  # 转换为utf-8字符串
                # 能正常转换则返回该编码
                logger.test("%s: encoding: %s", fstr, encoding)
                return encoding
            except Exception as e:
                logger.test("get_encoding failure: %s", encoding)
                logger.error(e)
                pass

        # 转换失败则暂且返回None
        return None

    # 字符串解码
    def decode_text(self, fbytes, encoding, is_raise=True):
        logger.test("decode_text: %s", encoding)

        if not encoding:
            # 没有编码时返回None
            return None

        fbytes2 = re.sub(b"\x00.*$", b"", fbytes)
        logger.test("decode_text %s -> %s", fbytes, fbytes2)

        if is_raise:
            try:
                return fbytes2.decode(encoding)
            except Exception as e:
                # 需要抛出错误时直接抛出
                raise e
        else:
            # 不抛出错误时
            try:
                if encoding == "shift-jis":
                    # shift-jis先转换为cp932再转换回来进行测试
                    return (
                        fbytes2.decode("shift_jis", errors="replace")
                        .encode("cp932", errors="replace")
                        .decode("cp932", errors="replace")
                    )

                # 无法转换的字符替换为「?」
                return fbytes2.decode(encoding=encoding, errors="replace")
            except Exception:
                # 不抛出时暂且返回None
                return None

    def read_Vector3D(self):
        return MVector3D(self.read_float(), self.read_float(), self.read_float())

    def read_Quaternion(self):
        x = self.read_float()
        y = self.read_float()
        z = self.read_float()
        scalar = self.read_float()
        return MQuaternion(scalar, x, y, z)

    # 整数的解压
    def read_int(self, format_size):
        if format_size == 1:
            format_type = "b"
        elif format_size == 2:
            format_type = "h"
        elif format_size == 4:
            format_type = "i"
        else:
            raise MParseException("read_int format_size错误 {0}".format(format_size))

        return self.unpack(format_size, format_type)

    # 整数的解压
    def read_uint(self, format_size):
        if format_size == 1:
            format_type = "B"
        elif format_size == 2:
            format_type = "H"
        elif format_size == 4:
            format_type = "I"
        else:
            raise MParseException("read_uint format_size错误 {0}".format(format_size))

        return self.unpack(format_size, format_type)

    # 小数的解压
    def read_float(self, format_size=4):
        if format_size == 4:
            format_type = "f"
        elif format_size == 8:
            format_type = "d"
        else:
            raise MParseException("read_float format_size错误 {0}".format(format_size))

        return self.unpack(format_size, format_type)

    # 解压并更新offset
    def unpack(self, format_size, format, is_all=False):
        bresult = struct.unpack_from(format, self.buffer, self.offset)

        # 更新偏移量
        self.offset += format_size

        if bresult:
            if is_all:
                # 返回全部时，返回整个数组
                result = bresult
            else:
                # 未指定返回全部时，仅返回首个元素
                result = bresult[0]
        else:
            result = None

        return result
