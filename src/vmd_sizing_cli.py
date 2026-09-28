# -*- coding: utf-8 -*-
"""
vmd_sizing_cli.py
------------------
让 vmd_sizing 的“适配（Sizing）优化处理”可以：
  1) 在 Python 代码里直接调用函数 run_vmd_sizing(...) 执行；
  2) 也可以直接用命令行方式调用本脚本执行。

本脚本绕开了原版 executor.py 里基于 argparse + sys.argv 的
MOptions.parse() 流程，直接构造 MOptions / MOptionsDataSet /
MArmProcessOptions 对象，这样既能当函数库 import 使用，也能当命令行工具用。

【使用前提】
    - module/、service/、mmd/、utils/ 等目录下的 .pyx 文件是 Cython 源码，
      必须先编译成 .pyd（Windows）/ .so（Linux/Mac）之后才能被 import。
      编译方法（在 src 目录下执行）：
          python setup.py build_ext --inplace
      如果编译报找不到 bezier 头文件，请先修改 setup_ext.py 里的
      bezier_path 为你本机 site-packages/bezier/include 的实际路径。
    - 依赖：numpy, numpy-quaternion, bezier, cython（wxPython 只有启动
      GUI界面时才需要，纯命令行跑本脚本不需要 wx）。
    - 本脚本需要放在 src/ 目录下（与 executor.py 同级），
      这样才能正确 import module.*/service.*/mmd.*/utils.* 这些包。

【放置位置】
    vmd_sizing/src/vmd_sizing_cli.py
"""

import os
import sys
import traceback
import multiprocessing
from typing import List, Optional, Union

# 让脚本无论从哪个工作目录被调用，都能正确 import 同级的 module/service/mmd/utils 包
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from module.MOptions import MOptions, MOptionsDataSet, MArmProcessOptions  # noqa: E402
from mmd.PmxReader import PmxReader  # noqa: E402
from mmd.VmdReader import VmdReader  # noqa: E402
from mmd.VpdReader import VpdReader  # noqa: E402
from service.SizingService import SizingService  # noqa: E402
from utils import MFileUtils  # noqa: E402
from utils.MException import SizingException  # noqa: E402
from utils.MLogger import MLogger  # noqa: E402

VERSION_NAME = "ver5.01.08_CN_1.0.0"

logger = MLogger(__name__)

# 详细追加补正的全部选项（与原版一致，detail_stance_flg=True 时全部启用）
_ALL_STANCE_DETAILS = ["センターXZ補正", "上半身補正", "下半身補正", "足ＩＫ補正", "つま先ＩＫ補正", "つま先補正", "肩補正", "センターY補正"]


def _to_list(value, n: int, default=None) -> list:
    """把单个值或 list 统一成长度为 n 的 list，方便同时支持单人/多人处理"""
    if value is None:
        value = default
    if not isinstance(value, (list, tuple)):
        value = [value] * n
    value = list(value)
    if len(value) < n:
        value = value + [value[-1]] * (n - len(value))
    return value


def _read_motion(motion_path: str):
    """根据扩展名读取 .vmd / .vpd 动作文件"""
    ext = os.path.splitext(motion_path)[1].lower()
    if ext == ".vmd":
        reader = VmdReader(motion_path)
    elif ext == ".vpd":
        reader = VpdReader(motion_path)
    else:
        raise SizingException(f"motion_path 读取失败（扩展名不支持）: {motion_path}")
    return reader.read_data()


def _read_pmx(model_path: str):
    """读取 .pmx 模型文件"""
    ext = os.path.splitext(model_path)[1].lower()
    if ext != ".pmx":
        raise SizingException(f"model_path 读取失败（扩展名不支持）: {model_path}")
    return PmxReader(model_path).read_data()


def run_vmd_sizing(
    motion_path: Union[str, List[str]],
    org_model_path: Union[str, List[str]],
    rep_model_path: Union[str, List[str]],
    output_vmd_path: Optional[Union[str, List[str]]] = None,
    detail_stance_flg: Union[bool, List[bool]] = True,
    twist_flg: Union[bool, List[bool]] = True,
    # 刚体接触规避（手臂）
    arm_process_flg_avoidance: bool = False,
    avoidance_target_list: Optional[List[str]] = None,
    # 手腕/手指/地面 位置对齐
    arm_process_flg_alignment: bool = False,
    alignment_finger_flg: bool = False,
    alignment_floor_flg: bool = False,
    alignment_distance_wrist: float = 1.7,
    alignment_distance_finger: float = 1.4,
    alignment_distance_floor: float = 1.8,
    arm_check_skip_flg: bool = False,
    # 相机（可选）
    camera_motion_path: str = "",
    camera_org_model_path: Optional[Union[str, List[str]]] = None,
    camera_offset_y: Optional[Union[float, List[float]]] = None,
    # 其它
    verbose: int = 20,
    version_name: str = VERSION_NAME,
) -> List[str]:
    """
    直接调用即可执行一次 VMD 适配（Sizing）处理，无需经过命令行参数解析。

    可以传单个文件路径（单人处理），也可以传 list（多人同时处理，
    list 长度需要一致，对应原版“追加/多人一括”功能）。

    参数
    ----
    motion_path:        输入的动作文件路径 (.vmd / .vpd)，单个或列表
    org_model_path:     该动作对应的“动作制作用”原始模型 (.pmx)，单个或列表
    rep_model_path:     要套用到的目标模型 (.pmx)，单个或列表
    output_vmd_path:    输出文件路径，不填则按原版规则自动生成到 motion 同目录
    detail_stance_flg:  是否启用“姿势追加修正”（细节骨骼追加修正），默认 True
    twist_flg:          是否启用“扭转分散”，默认 True
    arm_process_flg_avoidance: 是否启用手臂刚体接触规避
    avoidance_target_list:     规避目标刚体名称列表
    arm_process_flg_alignment: 是否启用手腕/手指/地面位置对齐
    alignment_finger_flg:      对齐时是否包含手指
    alignment_floor_flg:       对齐时是否包含地面
    alignment_distance_wrist:  手腕对齐距离阈值
    alignment_distance_finger: 手指对齐距离阈值
    alignment_distance_floor:  地面对齐距离阈值
    arm_check_skip_flg:        是否跳过手臂检查
    camera_motion_path:        相机动作文件路径（可选）
    camera_org_model_path:     相机对应原始模型（可选，默认用 org_model_path）
    camera_offset_y:           相机 Y 轴偏移（可选）
    verbose:                   日志等级，同原版 MLogger（INFO=20，可用 DEBUG=10 等）
    version_name:               仅用于日志展示的版本号字符串

    返回
    ----
    实际生成的输出 vmd 文件路径列表
    """

    motion_path_list = motion_path if isinstance(motion_path, (list, tuple)) else [motion_path]
    n = len(motion_path_list)

    org_model_path_list = _to_list(org_model_path, n)
    rep_model_path_list = _to_list(rep_model_path, n)
    detail_stance_flg_list = _to_list(detail_stance_flg, n, default=True)
    twist_flg_list = _to_list(twist_flg, n, default=True)
    output_vmd_path_list = _to_list(output_vmd_path, n, default=None)
    camera_org_model_path_list = _to_list(camera_org_model_path, n, default="")
    camera_offset_y_list = _to_list(camera_offset_y, n, default=0)

    if not (len(org_model_path_list) == len(rep_model_path_list) == n):
        raise ValueError("motion_path / org_model_path / rep_model_path 的数量必须一致")

    # 日志初始化（写入 src/log/ 目录下，与原版一致）
    os.makedirs(os.path.join(_SRC_DIR, "log"), exist_ok=True)
    cwd_before = os.getcwd()
    os.chdir(_SRC_DIR)
    try:
        MLogger.initialize(level=verbose, is_file=True)

        arm_options = MArmProcessOptions(
            arm_process_flg_avoidance,
            {0: list(avoidance_target_list) if avoidance_target_list else []},
            arm_process_flg_alignment,
            alignment_finger_flg,
            alignment_floor_flg,
            alignment_distance_wrist,
            alignment_distance_finger,
            alignment_distance_floor,
            arm_check_skip_flg,
        )

        data_set_list = []
        for idx in range(n):
            m_path = motion_path_list[idx]
            o_path = org_model_path_list[idx]
            r_path = rep_model_path_list[idx]
            disp_no = f"【No.{idx + 1}】"

            logger.info("%s 读取动作文件: %s", disp_no, os.path.basename(m_path))
            motion = _read_motion(m_path)

            logger.info("%s 读取原始（制作用）模型: %s", disp_no, os.path.basename(o_path))
            org_model = _read_pmx(o_path)

            logger.info("%s 读取目标模型: %s", disp_no, os.path.basename(r_path))
            rep_model = _read_pmx(r_path)

            cam_org_path = camera_org_model_path_list[idx]
            if cam_org_path:
                logger.info("%s 读取相机用原始模型: %s", disp_no, os.path.basename(cam_org_path))
                camera_org_model = _read_pmx(cam_org_path)
            else:
                camera_org_model = org_model

            this_detail_stance_flg = bool(detail_stance_flg_list[idx])
            this_twist_flg = bool(twist_flg_list[idx])

            this_output_vmd_path = output_vmd_path_list[idx]
            if not this_output_vmd_path:
                this_output_vmd_path = MFileUtils.get_output_vmd_path(
                    m_path, r_path, this_detail_stance_flg, this_twist_flg,
                    arm_process_flg_avoidance, arm_process_flg_alignment, False, "", True
                )

            data_set = MOptionsDataSet(
                motion,
                org_model,
                rep_model,
                this_output_vmd_path,
                this_detail_stance_flg,
                this_twist_flg,
                [],  # morph_list
                camera_org_model,
                camera_offset_y_list[idx],
                _ALL_STANCE_DETAILS if this_detail_stance_flg else [],
            )
            data_set_list.append(data_set)

        # 相机动作（可选）
        camera_motion = None
        camera_output_vmd_path = None
        if camera_motion_path:
            logger.info("读取相机动作文件: %s", os.path.basename(camera_motion_path))
            ext = os.path.splitext(camera_motion_path)[1].lower()
            if ext != ".vmd":
                raise SizingException(f"camera_motion_path 读取失败（扩展名不支持）: {camera_motion_path}")
            camera_motion = VmdReader(camera_motion_path).read_data()
            camera_output_vmd_path = MFileUtils.get_output_camera_vmd_path(
                camera_motion_path, data_set_list[0].rep_model.path, ""
            )

        options = MOptions(
            version_name=version_name,
            logging_level=verbose,
            data_set_list=data_set_list,
            arm_options=arm_options,
            camera_motion=camera_motion,
            camera_output_vmd_path=camera_output_vmd_path,
            is_sizing_camera_only=False,
            camera_length=5,
            monitor=sys.stdout,
            is_file=True,
            outout_datetime=logger.outout_datetime,
            max_workers=1,
            total_process=0,
            now_process=0,
            total_process_ctrl=None,
            now_process_ctrl=None,
            tree_process_dict={},
        )

        SizingService(options).execute()

        return [ds.output_vmd_path for ds in data_set_list]
    finally:
        os.chdir(cwd_before)


def _build_arg_parser():
    import argparse

    parser = argparse.ArgumentParser(
        description="VMD Sizing 命令行工具：读取动作VMD文件，按目标模型优化后导出新VMD。"
    )
    parser.add_argument("--motion", required=True, action="append",
                         help="输入动作文件路径(.vmd/.vpd)，可重复传入以批量处理多人，如 --motion a.vmd --motion b.vmd")
    parser.add_argument("--org_model", required=True, action="append",
                         help="动作对应的原始模型(.pmx)，与 --motion 一一对应")
    parser.add_argument("--rep_model", required=True, action="append",
                         help="要套用到的目标模型(.pmx)，与 --motion 一一对应")
    parser.add_argument("--output", action="append", default=None,
                         help="输出文件路径，不填则自动生成，与 --motion 一一对应")
    parser.add_argument("--no_detail_stance", action="store_true",
                         help="关闭“姿势追加修正”（细节骨骼追加修正），默认开启")
    parser.add_argument("--no_twist", action="store_true",
                         help="关闭“扭转分散”，默认开启")
    parser.add_argument("--avoidance", action="store_true", help="启用手臂刚体接触规避")
    parser.add_argument("--avoidance_target", action="append", default=None,
                         help="规避目标刚体名称，可重复传入")
    parser.add_argument("--alignment", action="store_true", help="启用手腕/手指/地面位置对齐")
    parser.add_argument("--alignment_finger", action="store_true", help="对齐时包含手指")
    parser.add_argument("--alignment_floor", action="store_true", help="对齐时包含地面")
    parser.add_argument("--alignment_distance_wrist", type=float, default=1.7)
    parser.add_argument("--alignment_distance_finger", type=float, default=1.4)
    parser.add_argument("--alignment_distance_floor", type=float, default=1.8)
    parser.add_argument("--arm_check_skip", action="store_true", help="跳过手臂检查")
    parser.add_argument("--camera_motion", default="", help="相机动作文件路径（可选）")
    parser.add_argument("--camera_org_model", default=None, help="相机用原始模型（可选）")
    parser.add_argument("--camera_offset_y", type=float, default=None, help="相机Y轴偏移（可选）")
    parser.add_argument("--verbose", type=int, default=20, help="日志等级，默认20(INFO)，调试可用10(DEBUG)")
    return parser


def main():
    multiprocessing.freeze_support()
    parser = _build_arg_parser()
    args = parser.parse_args()

    n = len(args.motion)
    if len(args.org_model) != n or len(args.rep_model) != n:
        parser.error("--motion / --org_model / --rep_model 的传入次数必须一致")

    try:
        outputs = run_vmd_sizing(
            motion_path=args.motion,
            org_model_path=args.org_model,
            rep_model_path=args.rep_model,
            output_vmd_path=args.output,
            detail_stance_flg=not args.no_detail_stance,
            twist_flg=not args.no_twist,
            arm_process_flg_avoidance=args.avoidance,
            avoidance_target_list=args.avoidance_target,
            arm_process_flg_alignment=args.alignment,
            alignment_finger_flg=args.alignment_finger,
            alignment_floor_flg=args.alignment_floor,
            alignment_distance_wrist=args.alignment_distance_wrist,
            alignment_distance_finger=args.alignment_distance_finger,
            alignment_distance_floor=args.alignment_distance_floor,
            arm_check_skip_flg=args.arm_check_skip,
            camera_motion_path=args.camera_motion,
            camera_org_model_path=args.camera_org_model,
            camera_offset_y=args.camera_offset_y,
            verbose=args.verbose,
        )
        print("处理完成，输出文件：")
        for p in outputs:
            print(f"  {p}")
    except SizingException as se:
        print(f"适配处理因数据无法处理而结束。\n\n{se.message}")
        sys.exit(1)
    except Exception:
        print("适配处理因意外错误而结束。")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()