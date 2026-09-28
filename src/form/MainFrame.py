# -*- coding: utf-8 -*-
#
import os
import sys
import wx
import threading

from form.panel.FilePanel import FilePanel
from form.panel.MorphPanel import MorphPanel
from form.panel.MultiPanel import MultiPanel
from form.panel.ArmPanel import ArmPanel
from form.panel.LegPanel import LegPanel
from form.panel.CameraPanel import CameraPanel
from form.panel.CsvPanel import CsvPanel
from form.panel.VmdPanel import VmdPanel
from form.panel.BulkPanel import BulkPanel
from form.worker.SizingWorkerThread import SizingWorkerThread
from form.worker.LoadWorkerThread import LoadWorkerThread
from module.MMath import MRect, MVector3D, MVector4D, MQuaternion, MMatrix4x4  # noqa
from utils import MFormUtils, MFileUtils  # noqa
from utils.MLogger import MLogger  # noqa

if os.name == "nt":
    import winsound  # 仅在 Windows 下导入

logger = MLogger(__name__)


# 事件
(SizingThreadEvent, EVT_SIZING_THREAD) = wx.lib.newevent.NewEvent()
(LoadThreadEvent, EVT_LOAD_THREAD) = wx.lib.newevent.NewEvent()


class MainFrame(wx.Frame):
    def __init__(
        self, parent, mydir_path: str, version_name: str, logging_level: int, is_saving: bool, is_out_log: bool
    ):
        self.version_name = version_name
        self.logging_level = logging_level
        self.is_out_log = is_out_log
        self.is_saving = is_saving
        self.mydir_path = mydir_path
        self.elapsed_time = 0
        self.popuped_finger_warning = False

        self.worker = None
        self.load_worker = None

        wx.Frame.__init__(
            self,
            parent,
            id=wx.ID_ANY,
            title="VMD适配 本地版 {0}".format(self.version_name),
            pos=wx.DefaultPosition,
            size=wx.Size(600, 650),
            style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL,
        )

        # 读取文件历史记录
        self.file_hitories = MFileUtils.read_history(self.mydir_path)

        # ---------------------------------------------

        self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)

        bSizer1 = wx.BoxSizer(wx.VERTICAL)

        self.note_ctrl = wx.Notebook(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        if self.logging_level == MLogger.FULL or self.logging_level == MLogger.DEBUG_FULL:
            # 全量数据的情况
            self.note_ctrl.SetBackgroundColour("RED")
        elif self.logging_level == MLogger.DEBUG:
            # 测试（调试版）的情况
            self.note_ctrl.SetBackgroundColour("CORAL")
        elif self.logging_level == MLogger.TIMER:
            # 计时测量的情况
            self.note_ctrl.SetBackgroundColour("YELLOW")
        elif not is_saving:
            # 带日志时，改变颜色
            self.note_ctrl.SetBackgroundColour("BLUE")
        elif is_out_log:
            # 带日志时，改变颜色
            self.note_ctrl.SetBackgroundColour("AQUAMARINE")
        else:
            self.note_ctrl.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNSHADOW))

        # ---------------------------------------------

        # 文件标签页
        self.file_panel_ctrl = FilePanel(self, self.note_ctrl, 0, self.file_hitories)
        self.note_ctrl.AddPage(self.file_panel_ctrl, "文件", True)

        # 多个标签页
        self.multi_panel_ctrl = MultiPanel(self, self.note_ctrl, 1, self.file_hitories)
        self.note_ctrl.AddPage(self.multi_panel_ctrl, "多个", False)

        # 表情标签页
        self.morph_panel_ctrl = MorphPanel(self, self.note_ctrl, 2)
        self.note_ctrl.AddPage(self.morph_panel_ctrl, "表情", False)

        # 手臂标签页
        self.arm_panel_ctrl = ArmPanel(self, self.note_ctrl, 3)
        self.note_ctrl.AddPage(self.arm_panel_ctrl, "手臂", False)

        # 腿部标签页
        self.leg_panel_ctrl = LegPanel(self, self.note_ctrl, 4)
        self.note_ctrl.AddPage(self.leg_panel_ctrl, "腿部", False)

        # 相机标签页
        self.camera_panel_ctrl = CameraPanel(self, self.note_ctrl, 5)
        self.note_ctrl.AddPage(self.camera_panel_ctrl, "相机", False)

        # 批量标签页
        self.bulk_panel_ctrl = BulkPanel(self, self.note_ctrl, 6)
        self.note_ctrl.AddPage(self.bulk_panel_ctrl, "批量", False)

        # CSV标签页
        self.csv_panel_ctrl = CsvPanel(self, self.note_ctrl, 7)
        self.note_ctrl.AddPage(self.csv_panel_ctrl, "CSV", False)

        # VMD标签页
        self.vmd_panel_ctrl = VmdPanel(self, self.note_ctrl, 8)
        self.note_ctrl.AddPage(self.vmd_panel_ctrl, "VMD", False)

        # ---------------------------------------------

        # 点击标签页时的处理
        self.note_ctrl.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.on_tab_change)

        # ---------------------------------------------

        bSizer1.Add(self.note_ctrl, 1, wx.EXPAND, 5)

        # 默认输出目标为文件标签页的控制台
        sys.stdout = self.file_panel_ctrl.console_ctrl

        # 事件绑定
        self.Bind(EVT_SIZING_THREAD, self.on_exec_result)
        self.Bind(EVT_LOAD_THREAD, self.on_load_result)

        self.SetSizer(bSizer1)
        self.Layout()

        self.Centre(wx.BOTH)

    def on_idle(self, event: wx.Event):
        if self.worker or self.load_worker:
            self.file_panel_ctrl.gauge_ctrl.Pulse()
        elif self.csv_panel_ctrl.convert_csv_worker:
            self.csv_panel_ctrl.gauge_ctrl.Pulse()
        elif self.vmd_panel_ctrl.convert_vmd_worker:
            self.vmd_panel_ctrl.gauge_ctrl.Pulse()

    def on_tab_change(self, event: wx.Event):
        # 恢复到文件标签页的控制台
        sys.stdout = self.file_panel_ctrl.console_ctrl

        if self.file_panel_ctrl.is_fix_tab:
            self.note_ctrl.ChangeSelection(self.file_panel_ctrl.tab_idx)
            event.Skip()
            return

        elif self.morph_panel_ctrl.is_fix_tab:
            # 若指定了固定表情标签页，则固定在文件标签页
            self.note_ctrl.ChangeSelection(self.file_panel_ctrl.tab_idx)
            event.Skip()
            return

        elif self.arm_panel_ctrl.is_fix_tab:
            # 若指定了固定手臂标签页，则固定在文件标签页
            self.note_ctrl.ChangeSelection(self.file_panel_ctrl.tab_idx)
            event.Skip()
            return

        elif self.csv_panel_ctrl.is_fix_tab:
            self.note_ctrl.ChangeSelection(self.csv_panel_ctrl.tab_idx)
            event.Skip()
            return

        elif self.vmd_panel_ctrl.is_fix_tab:
            self.note_ctrl.ChangeSelection(self.vmd_panel_ctrl.tab_idx)
            event.Skip()
            return

        elif self.bulk_panel_ctrl.is_fix_tab:
            self.note_ctrl.ChangeSelection(self.bulk_panel_ctrl.tab_idx)
            event.Skip()
            return

        if self.note_ctrl.GetSelection() == self.multi_panel_ctrl.tab_idx:
            # 移动到多个标签页时保存
            self.file_panel_ctrl.save()

        if self.note_ctrl.GetSelection() == self.morph_panel_ctrl.tab_idx:
            # 清空控制台
            self.file_panel_ctrl.console_ctrl.Clear()
            wx.GetApp().Yield()

            # 先临时固定到文件标签页
            self.note_ctrl.SetSelection(self.file_panel_ctrl.tab_idx)
            self.morph_panel_ctrl.fix_tab()

            logger.info("表情标签页显示准备开始\n正在执行文件读取处理，请稍候....", decoration=MLogger.DECORATION_BOX)

            # 执行读取处理
            self.load(event, target_idx=0, is_morph=True)

        if self.note_ctrl.GetSelection() == self.arm_panel_ctrl.tab_idx:
            # 清空控制台
            self.file_panel_ctrl.console_ctrl.Clear()
            wx.GetApp().Yield()

            # 先临时固定到文件标签页
            self.note_ctrl.SetSelection(self.file_panel_ctrl.tab_idx)
            self.arm_panel_ctrl.fix_tab()

            logger.info("手臂标签页显示准备开始\n正在执行文件读取处理，请稍候....", decoration=MLogger.DECORATION_BOX)

            # 执行读取处理
            self.load(event, target_idx=0, is_arm=True)

        if self.note_ctrl.GetSelection() == self.leg_panel_ctrl.tab_idx:
            # 清空控制台
            self.file_panel_ctrl.console_ctrl.Clear()
            wx.GetApp().Yield()

            # 先临时固定到文件标签页
            self.note_ctrl.SetSelection(self.file_panel_ctrl.tab_idx)
            self.leg_panel_ctrl.fix_tab()

            logger.info("腿部标签页显示准备开始\n正在执行文件读取处理，请稍候....", decoration=MLogger.DECORATION_BOX)

            # 执行读取处理
            self.load(event, target_idx=0, is_leg=True)

        if self.note_ctrl.GetSelection() == self.camera_panel_ctrl.tab_idx:
            # 打开相机标签页时，执行相机标签页初始化处理
            self.note_ctrl.ChangeSelection(self.camera_panel_ctrl.tab_idx)
            self.camera_panel_ctrl.initialize(event)

    # 允许切换标签页
    def release_tab(self):
        self.file_panel_ctrl.release_tab()
        self.morph_panel_ctrl.release_tab()
        self.arm_panel_ctrl.release_tab()
        self.multi_panel_ctrl.release_tab()
        self.bulk_panel_ctrl.release_tab()

    # 允许表单输入
    def enable(self):
        self.file_panel_ctrl.enable()
        self.bulk_panel_ctrl.enable()

    # 检查文件集的输入是否有效
    def is_valid(self):
        result = True
        result = self.file_panel_ctrl.file_set.is_valid() and result

        # multi 有多少就检查多少
        for file_set in self.multi_panel_ctrl.file_set_list:
            result = file_set.is_valid() and result

        return result

    # 加载后的输入有效性检查
    def is_loaded_valid(self):
        result = True
        result = self.file_panel_ctrl.file_set.is_loaded_valid() and result

        # multi 有多少就检查多少
        for file_set in self.multi_panel_ctrl.file_set_list:
            result = file_set.is_loaded_valid() and result

        # 若勾选了「仅执行相机适配」，则需确认存在相机文件路径与已适配完成的数据
        if self.camera_panel_ctrl.camera_only_flg_ctrl.GetValue():
            if not self.camera_panel_ctrl.camera_vmd_file_ctrl.data:
                logger.error("仅执行相机适配时，\n请指定相机VMD数据", decoration=MLogger.DECORATION_BOX)
                result = False

            if not (
                os.path.exists(self.file_panel_ctrl.file_set.output_vmd_file_ctrl.path())
                and os.path.isfile(self.file_panel_ctrl.file_set.output_vmd_file_ctrl.path())
            ):
                logger.error(
                    "仅执行相机适配时，\n请为第1个文件集的输出VMD指定已适配完成的VMD文件路径。"
                    "\n（若通过「打开」指定输出VMD，会弹出「是否覆盖？」的警告，但实际并不会执行覆盖。）",
                    decoration=MLogger.DECORATION_BOX,
                )
                result = False

            for fidx, file_set in enumerate(self.multi_panel_ctrl.file_set_list):
                if not (
                    os.path.exists(file_set.output_vmd_file_ctrl.path())
                    and os.path.isfile(file_set.output_vmd_file_ctrl.path())
                ):
                    logger.error(
                        f"仅执行相机适配时，\n请为第{fidx+1}个文件集的输出VMD指定已适配完成的VMD文件路径。"
                        "\n（若通过「打开」指定输出VMD，会弹出「是否覆盖？」的警告，但实际并不会执行覆盖。）",
                        decoration=MLogger.DECORATION_BOX,
                    )
                    result = False

        return result

    def show_worked_time(self):
        # 将经过秒数转换为时、分、秒
        td_m, td_s = divmod(self.elapsed_time, 60)

        if td_m == 0:
            worked_time = "{0:02d}秒".format(int(td_s))
        else:
            worked_time = "{0:02d}分{1:02d}秒".format(int(td_m), int(td_s))

        return worked_time

    # 文件标签页的待处理VMD/VPD路径
    def get_target_vmd_path(self, target_idx):
        if self.file_panel_ctrl.file_set.motion_vmd_file_ctrl.astr_path:
            if len(self.file_panel_ctrl.file_set.motion_vmd_file_ctrl.target_paths) > target_idx:
                return self.file_panel_ctrl.file_set.motion_vmd_file_ctrl.target_paths[target_idx]
            else:
                return None

        return self.file_panel_ctrl.file_set.motion_vmd_file_ctrl.file_ctrl.GetPath()

    # 读取
    def load(self, event, target_idx, is_exec=False, is_morph=False, is_arm=False, is_leg=False):
        # 禁用表单
        self.file_panel_ctrl.disable()
        # 固定标签页
        self.file_panel_ctrl.fix_tab()

        self.elapsed_time = 0
        result = True
        result = self.is_valid() and result

        if not result:
            if is_morph or is_arm or is_leg:
                tab_name = "表情" if is_morph else "手臂" if is_arm else "腿部"
                # 读取失败则报错
                logger.error(
                    "「文件」标签页中未指定以下任一文件路径，因此无法打开「{tab_name}」标签页。".format(tab_name=tab_name)
                    + "\n・待适配VMD文件"
                    + "\n・源模型PMX文件"
                    + "\n・目标模型PMX文件"
                    + "\n若已指定，则可能正在读取中。"
                    + "\n尤其是较长的VMD，读取耗时较久。"
                    + "\n请指定适配所需的全部3个文件，"
                    + "\n待输出「■读取成功」日志后，再打开「{tab_name}」标签页。".format(tab_name=tab_name),
                    decoration=MLogger.DECORATION_BOX,
                )

            # 允许切换标签页
            self.release_tab()
            # 启用表单
            self.enable()

            return result

        # 开始读取
        if self.load_worker:
            logger.error("处理仍在执行中，请结束后再重新执行。", decoration=MLogger.DECORATION_BOX)
        else:
            # 设置文件标签页待处理VMD/VPD的实际值
            target_path = self.get_target_vmd_path(target_idx)
            self.file_panel_ctrl.file_set.motion_vmd_file_ctrl.file_ctrl.SetPath(target_path)
            self.file_panel_ctrl.file_set.motion_vmd_file_ctrl.file_model_ctrl.set_model(target_path)
            # 更改输出路径
            if not self.file_panel_ctrl.file_set.output_vmd_file_ctrl.file_ctrl.GetPath() or target_idx > 0:
                self.file_panel_ctrl.file_set.output_vmd_file_ctrl.file_ctrl.SetPath("")
                self.file_panel_ctrl.file_set.set_output_vmd_path(event)

            # 切换为停止按钮
            self.file_panel_ctrl.check_btn_ctrl.SetLabel("停止读取处理")
            self.file_panel_ctrl.check_btn_ctrl.Enable()

            # 在另一线程中执行
            self.load_worker = LoadWorkerThread(self, LoadThreadEvent, target_idx, is_exec, is_morph, is_arm, is_leg)
            self.load_worker.start()

        return result

    # 读取完成处理
    def on_load_result(self, event: wx.Event):
        self.elapsed_time = event.elapsed_time

        # 允许切换标签页
        self.release_tab()
        # 启用表单
        self.enable()
        # 结束工作线程
        self.load_worker = None
        # 隐藏进度条
        self.file_panel_ctrl.gauge_ctrl.SetValue(0)

        # 切换为检查按钮
        self.file_panel_ctrl.check_btn_ctrl.SetLabel("转换前检查")
        self.file_panel_ctrl.check_btn_ctrl.Enable()

        if not event.result:
            # 播放结束提示音
            self.sound_finish()

            event.Skip()
            return False

        result = self.is_loaded_valid()

        if not result:
            # 播放结束提示音
            self.sound_finish()
            # 允许切换标签页
            self.release_tab()
            # 启用表单
            self.enable()

            event.Skip()
            return False

        logger.info("文件数据读取完成", decoration=MLogger.DECORATION_BOX, title="OK")

        if event.is_exec:
            # 若直接执行，则转入适配执行处理

            # 保险起见自动生成输出文件路径（为空时设置）
            if not self.file_panel_ctrl.file_set.output_vmd_file_ctrl.file_ctrl.GetPath():
                self.file_panel_ctrl.file_set.set_output_vmd_path(event)

            # multi 的输出文件路径也自动生成（为空时设置）
            for file_set in self.multi_panel_ctrl.file_set_list:
                if not file_set.output_vmd_file_ctrl.file_ctrl.GetPath():
                    file_set.set_output_vmd_path(event)

            # 禁用表单
            self.file_panel_ctrl.disable()
            # 固定标签页
            self.file_panel_ctrl.fix_tab()

            if self.worker:
                logger.error("处理仍在执行中，请结束后再重新执行。", decoration=MLogger.DECORATION_BOX)
            else:
                # 切换为停止按钮
                self.file_panel_ctrl.exec_btn_ctrl.SetLabel("停止VMD适配")
                self.file_panel_ctrl.exec_btn_ctrl.Enable()

                # 在另一线程中执行
                self.worker = SizingWorkerThread(
                    self, SizingThreadEvent, event.target_idx, self.is_saving, self.is_out_log
                )
                self.worker.start()

        elif event.is_morph:
            # 打开表情标签页时，执行表情标签页初始化处理
            self.note_ctrl.ChangeSelection(self.morph_panel_ctrl.tab_idx)
            self.morph_panel_ctrl.initialize(event)

        elif event.is_arm:
            # 打开手臂标签页时，执行手臂标签页初始化处理
            self.note_ctrl.ChangeSelection(self.arm_panel_ctrl.tab_idx)
            self.arm_panel_ctrl.initialize(event)

        elif event.is_leg:
            # 打开腿部标签页时，执行腿部标签页初始化处理
            self.note_ctrl.ChangeSelection(self.leg_panel_ctrl.tab_idx)
            self.leg_panel_ctrl.initialize(event)

        else:
            # 播放结束提示音
            self.sound_finish()

            logger.info("\n处理时间: %s", self.show_worked_time())

            event.Skip()
            return True

    # 线程执行结果
    def on_exec_result(self, event: wx.Event):
        # 切换为执行按钮
        self.file_panel_ctrl.exec_btn_ctrl.SetLabel("执行VMD适配")
        self.file_panel_ctrl.exec_btn_ctrl.Enable()

        self.elapsed_time += event.elapsed_time
        worked_time = "\n处理时间: {0}".format(self.show_worked_time())
        logger.info(worked_time)

        if self.is_out_log and event.output_log_path and os.path.exists(event.output_log_path):
            # 若为日志输出对象，则追加写入
            with open(event.output_log_path, mode="a", encoding="utf-8") as f:
                f.write(worked_time)

        logger.debug("self.worker = None")

        # 结束工作线程
        self.worker = None

        if (
            event.result
            and self.file_panel_ctrl.file_set.motion_vmd_file_ctrl.astr_path
            and self.get_target_vmd_path(event.target_idx + 1)
        ):
            # 带星号路径时，检查下一个是否存在
            logger.info("\n----------------------------------")

            return self.load(event, event.target_idx + 1, is_exec=True)

        # 文件标签页的控制台
        sys.stdout = self.file_panel_ctrl.console_ctrl

        # 播放结束提示音
        self.sound_finish()

        # 允许切换标签页
        self.release_tab()
        # 启用表单
        self.enable()
        # 隐藏进度条
        self.file_panel_ctrl.gauge_ctrl.SetValue(0)

    def sound_finish(self):
        threading.Thread(target=self.sound_finish_thread).start()

    def sound_finish_thread(self):
        # 播放结束提示音
        if os.name == "nt":
            # Windows
            try:
                winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
            except Exception:
                pass

    def on_wheel_spin_ctrl(self, event: wx.Event, inc=0.1):
        # 数值调节控件变更时
        if event.GetWheelRotation() > 0:
            event.GetEventObject().SetValue(event.GetEventObject().GetValue() + inc)
            if event.GetEventObject().GetValue() >= 0:
                event.GetEventObject().SetBackgroundColour("WHITE")
        else:
            event.GetEventObject().SetValue(event.GetEventObject().GetValue() - inc)
            if event.GetEventObject().GetValue() < 0:
                event.GetEventObject().SetBackgroundColour("TURQUOISE")

    def on_popup_finger_warning(self, event: wx.Event):
        if not self.popuped_finger_warning:
            dialog = wx.MessageDialog(
                self,
                "多人动作中已开启手指位置对齐。\n仅手指的组合数量就极为庞大，处理会非常耗时，" + "但效果却并不理想，反而会因多余的指头受影响而变得难看。确定继续吗？",
                style=wx.YES_NO | wx.ICON_WARNING,
            )
            if dialog.ShowModal() == wx.ID_NO:
                # 关闭手指位置对齐
                self.arm_panel_ctrl.arm_alignment_finger_flg_ctrl.SetValue(0)
                # 重新开启手腕位置对齐
                self.arm_panel_ctrl.arm_process_flg_alignment.SetValue(1)

            dialog.Destroy()
            self.popuped_finger_warning = True
