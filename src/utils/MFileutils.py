# -*- coding: utf-8 -*-
#

from datetime import datetime
import sys
import os
import json
import glob
import traceback
from pathlib import Path
import re
import _pickle as cPickle

from utils.MLogger import MLogger # noqa

logger = MLogger(__name__)


# 资源文件路径
def resource_path(relative):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(relative)


# 读取文件历史记录
def read_history(mydir_path):
    # 文件历史记录
    base_file_hitories = {"vmd": [], "org_pmx": [], "rep_pmx": [], "camera_vmd": [], "camera_pmx": [], "smooth_vmd": [], "smooth_pmx": [], "bulk_csv": [], "max": 50}
    file_hitories = cPickle.loads(cPickle.dumps(base_file_hitories, -1))

    # 若存在历史JSON文件则读取
    try:
        with open(os.path.join(mydir_path, 'history.json'), 'r', encoding="utf-8") as f:
            file_hitories = json.load(f)
            # 检查键是否齐全
            for key in base_file_hitories.keys():
                if key not in file_hitories:
                    file_hitories[key] = []
            # 最大条数始终覆盖
            file_hitories["max"] = 50
    except Exception:
        # 若无法以UTF-8读取，则按默认编码读取后转换为UTF-8
        try:
            with open(os.path.join(mydir_path, 'history.json'), 'r') as f:
                file_hitories = json.load(f)
                # 检查键是否齐全
                for key in base_file_hitories.keys():
                    if key not in file_hitories:
                        file_hitories[key] = []
                # 最大条数始终覆盖
                file_hitories["max"] = 50
            
            # 先以UTF-8输出
            save_history(mydir_path, file_hitories)

            # 重新以UTF-8读取
            return read_history(mydir_path)
        except Exception:
            file_hitories = cPickle.loads(cPickle.dumps(base_file_hitories, -1))

    return file_hitories


def save_history(mydir_path, file_hitories):
    # 保存输入历史记录
    try:
        with open(os.path.join(mydir_path, 'history.json'), 'w', encoding="utf-8") as f:
            json.dump(file_hitories, f, ensure_ascii=False)
    except Exception as e:
        logger.error("履歴ファイルの保存に失敗しました", e, decoration=MLogger.DECORATION_BOX)


# 路径解析
def get_mydir_path(exec_path):
    logger.test("sys.argv %s", sys.argv)
    
    dir_path = Path(exec_path).parent if hasattr(sys, "frozen") else Path(__file__).parent
    logger.test("get_mydir_path: %s", get_mydir_path)

    return dir_path


# 目录路径
def get_dir_path(base_file_path, is_print=True):
    if os.path.exists(base_file_path):
        file_path_list = [base_file_path]
    else:
        file_path_list = [p for p in glob.glob(base_file_path) if os.path.isfile(p)]

    if len(file_path_list) == 0:
        return ""

    try:
        # 将文件路径解析为对象并获取父级
        return str(Path(file_path_list[0]).resolve().parents[0])
    except Exception as e:
        logger.error("ファイルパスの解析に失敗しました。\nパスに使えない文字がないか確認してください。\nファイルパス: {0}\n\n{1}".format(base_file_path, e.with_traceback(sys.exc_info()[2])))
        raise e
    

# 表情替换组合文件
def get_output_morph_path(base_file_path: str, org_pmx_path: str, rep_pmx_path: str):
    # 动作VMD路径的扩展名列表
    if os.path.exists(base_file_path):
        file_path_list = [base_file_path]
    else:
        file_path_list = [p for p in glob.glob(base_file_path) if os.path.isfile(p)]

    if len(file_path_list) == 0 or (len(file_path_list) > 0 and not os.path.exists(file_path_list[0])) or not os.path.exists(rep_pmx_path):
        return ""

    # 动作VMD目录路径
    motion_vmd_dir_path = get_dir_path(file_path_list[0])
    # 动作VMD文件名・扩展名
    motion_vmd_file_name, motion_vmd_ext = os.path.splitext(os.path.basename(file_path_list[0]))
    # 源模型文件名・扩展名
    org_pmx_file_name, _ = os.path.splitext(os.path.basename(org_pmx_path))
    # 目标模型文件名・扩展名
    rep_pmx_file_name, _ = os.path.splitext(os.path.basename(rep_pmx_path))

    # 生成输出文件路径
    new_output_morph_path = os.path.join(motion_vmd_dir_path, "{0}_{1}_{2}{3}".format(motion_vmd_file_name, org_pmx_file_name, rep_pmx_file_name, ".csv"))

    return new_output_morph_path


# 生成VMD输出文件路径
# base_file_path: 动作VMD路径（含通配符）
# rep_pmx_path: 目标模型PMX路径
# detail_stance_flg: 站姿细节还原开关
# twist_flg: 扭转分散
# arm_process_flg_avoidance: 接触规避
# arm_process_flg_alignment: 手腕位置对齐
# is_morphs: 是否进行表情替换
# output_vmd_path: 输出文件路径
def get_output_vmd_path(base_file_path: str, rep_pmx_path: str, detail_stance_flg: bool, twist_flg: bool, \
                        arm_process_flg_avoidance: bool, arm_process_flg_alignment: bool, is_morphs: bool, output_vmd_path: str, is_force=False):
    # 动作VMD路径的扩展名列表
    if os.path.exists(base_file_path):
        file_path_list = [base_file_path]
    else:
        file_path_list = [p for p in glob.glob(base_file_path) if os.path.isfile(p)]

    if len(file_path_list) == 0 or (len(file_path_list) > 0 and not os.path.exists(file_path_list[0])) or not os.path.exists(rep_pmx_path):
        return ""

    # 动作VMD目录路径
    motion_vmd_dir_path = get_dir_path(file_path_list[0])
    # 动作VMD文件名・扩展名
    motion_vmd_file_name, motion_vmd_ext = os.path.splitext(os.path.basename(file_path_list[0]))
    # 目标模型文件名・扩展名
    rep_pmx_file_name, _ = os.path.splitext(os.path.basename(rep_pmx_path))

    # 表情

    # 站姿追加修正
    # 扭转分散
    # 腕
    suffix = "{0}{1}{2}{3}{4}".format(
        ("S" if detail_stance_flg else ""),
        ("T" if twist_flg else ""),
        ("M" if is_morphs else ""),
        ("I" if arm_process_flg_avoidance else ""),
        ("P" if arm_process_flg_alignment else "")
    )

    if len(suffix) > 0:
        suffix = "_{0}".format(suffix)

    # 生成输出文件路径
    new_output_vmd_path = os.path.join(motion_vmd_dir_path, "{0}_{1}{2}_{3:%Y%m%d_%H%M%S}{4}".format(motion_vmd_file_name, rep_pmx_file_name, suffix, datetime.now(), ".vmd"))

    # 若文件路径本身已变更，或符合自动生成规则，则更改文件路径
    if is_force or is_auto_vmd_output_path(output_vmd_path, motion_vmd_dir_path, motion_vmd_file_name, ".vmd", rep_pmx_file_name):

        try:
            open(new_output_vmd_path, 'w')
            os.remove(new_output_vmd_path)
        except Exception:
            logger.warning("出力ファイルパスの生成に失敗しました。以下の原因が考えられます。\n" \
                           + "・ファイルパスが255文字を超えている\n" \
                           + "・ファイルパスに使えない文字列が含まれている（例) \\　/　:　*　?　\"　<　>　|）" \
                           + "・出力ファイルパスの親フォルダに書き込み権限がない" \
                           + "・出力ファイルパスに書き込み権限がない")

        return new_output_vmd_path
    
    return output_vmd_path


# 是否为符合自动生成规则的路径
def is_auto_vmd_output_path(output_vmd_path: str, motion_vmd_dir_path: str, motion_vmd_file_name: str, motion_vmd_ext: str, rep_pmx_file_name: str):
    if not output_vmd_path:
        # 没有输出路径时，作为替换对象
        return True

    # 新设置的输出文件路径的正则表达式
    escaped_motion_vmd_file_name = escape_filepath(os.path.join(motion_vmd_dir_path, motion_vmd_file_name))
    escaped_rep_pmx_file_name = escape_filepath(rep_pmx_file_name)
    escaped_motion_vmd_ext = escape_filepath(motion_vmd_ext)

    new_output_vmd_pattern = re.compile(r'^%s_%s%s%s$' % (escaped_motion_vmd_file_name, \
                                        escaped_rep_pmx_file_name, r"_?\w*_\d{8}_\d{6}", escaped_motion_vmd_ext))
    
    logger.debug("new_output_vmd_pattern: %s", new_output_vmd_pattern)
    
    # 若是符合自动生成规则的文件路径，则视为匹配
    return re.match(new_output_vmd_pattern, output_vmd_path) is not None


# 生成相机VMD输出文件路径
# base_file_path: 相机动作VMD路径
# rep_pmx_path: 目标模型PMX路径
# output_camera_vmd_path: 输出文件路径
def get_output_camera_vmd_path(base_file_path: str, rep_pmx_path: str, output_camera_vmd_path: str, camera_length: float, is_force=False):
    # 相机动作VMD路径的扩展名列表
    if not os.path.exists(base_file_path) or not os.path.exists(rep_pmx_path):
        return ""

    # 相机动作VMD目录路径
    motion_camera_vmd_dir_path = get_dir_path(base_file_path)
    # 相机动作VMD文件名・扩展名
    motion_camera_vmd_file_name, motion_camera_vmd_ext = os.path.splitext(os.path.basename(base_file_path))
    # 目标模型文件名・扩展名
    rep_pmx_file_name, _ = os.path.splitext(os.path.basename(rep_pmx_path))

    # 生成输出文件路径
    new_output_camera_vmd_path = os.path.join(motion_camera_vmd_dir_path, "{0}_{1}({2})_{3:%Y%m%d_%H%M%S}{4}".format( \
        motion_camera_vmd_file_name, rep_pmx_file_name, camera_length, datetime.now(), ".vmd"))

    # 若文件路径本身已变更，或符合自动生成规则，则更改文件路径
    if is_force or is_auto_camera_vmd_output_path(output_camera_vmd_path, motion_camera_vmd_dir_path, motion_camera_vmd_file_name, ".vmd", rep_pmx_file_name):

        try:
            open(new_output_camera_vmd_path, 'w')
            os.remove(new_output_camera_vmd_path)
        except Exception:
            logger.warning("出力ファイルパスの生成に失敗しました。以下の原因が考えられます。\n" \
                           + "・ファイルパスが255文字を超えている\n" \
                           + "・ファイルパスに使えない文字列が含まれている（例) \\　/　:　*　?　\"　<　>　|）" \
                           + "・出力ファイルパスの親フォルダに書き込み権限がない" \
                           + "・出力ファイルパスに書き込み権限がない")

        return new_output_camera_vmd_path

    return output_camera_vmd_path


# 是否为符合自动生成规则的路径
def is_auto_camera_vmd_output_path(output_camera_vmd_path: str, motion_camera_vmd_dir_path: str, motion_camera_vmd_file_name: str, motion_camera_vmd_ext: str, rep_pmx_file_name: str):
    if not output_camera_vmd_path:
        # 没有输出路径时，作为替换对象
        return True

    # 新设置的输出文件路径的正则表达式
    escaped_motion_camera_vmd_file_name = escape_filepath(os.path.join(motion_camera_vmd_dir_path, motion_camera_vmd_file_name))
    escaped_rep_pmx_file_name = escape_filepath(rep_pmx_file_name)
    escaped_motion_camera_vmd_ext = escape_filepath(motion_camera_vmd_ext)

    new_output_camera_vmd_pattern = re.compile(r'^%s_%s(\d+)_%s%s$' % (escaped_motion_camera_vmd_file_name, \
                                               escaped_rep_pmx_file_name, r"_\d{8}_\d{6}", escaped_motion_camera_vmd_ext))
    
    # 若是符合自动生成规则的文件路径，则视为匹配
    return re.match(new_output_camera_vmd_pattern, output_camera_vmd_path) is not None


def escape_filepath(path: str):
    path = path.replace("\\", "\\\\")
    path = path.replace("*", "\\*")
    path = path.replace("+", "\\+")
    path = path.replace(".", "\\.")
    path = path.replace("?", "\\?")
    path = path.replace("{", "\\{")
    path = path.replace("}", "\\}")
    path = path.replace("(", "\\(")
    path = path.replace(")", "\\)")
    path = path.replace("[", "\\[")
    path = path.replace("]", "\\]")
    path = path.replace("{", "\\{")
    path = path.replace("^", "\\^")
    path = path.replace("$", "\\$")
    path = path.replace("-", "\\-")
    path = path.replace("|", "\\|")
    path = path.replace("/", "\\/")

    return path
