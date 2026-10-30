"""GG 姿态库 / GG 服装库 / GG 脸模库：固定选中 / 全库随机 / 范围内随机三种取图方式。

三个节点共用同一套取图逻辑（见 _pick），只是底层库（lib）不同：
pose=白模姿态库、garment=服装库、face=脸模库。要再加别的库，照此再加一个 GuliXxxPicker 即可。
"""

import random

import numpy as np
import torch
from PIL import Image

from . import pose_db

MODE_FIXED = "固定选中"
MODE_RANDOM_ALL = "全库随机"
MODE_RANDOM_FILTERED = "范围内随机"
MODES = [MODE_FIXED, MODE_RANDOM_ALL, MODE_RANDOM_FILTERED]

# 各库的中文名，用于空库报错等提示
LIB_NAME = {"pose": "姿态库", "garment": "服装库", "face": "脸模库"}


def _pick(lib, 模式, 姿态, 视角, 筛选系列, 筛选分类):
    """通用取图：按模式在 lib 库里选一张图并返回 IMAGE。"""
    if not pose_db.index(lib)["poses"]:
        raw = pose_db.raw_dir(lib)
        try:
            rel = raw.relative_to(pose_db.NODE_DIR).as_posix()
        except ValueError:
            rel = str(raw)
        raise pose_db.PoseDBMissing(
            f"{LIB_NAME.get(lib, '图库')}是空的。\n"
            f"可以在节点面板里点「导入」把自己的图放进来，"
            f"或者把原始图（默认 PNG）丢进 {rel}/ 目录，重启后会自动转成 WebP 并建索引。"
        )

    # 无种子实例化 = 每次用系统熵播种，抽到满意的姿态点一下就固定下来了
    rng = random.Random()

    if 模式 == MODE_FIXED:
        record = pose_db.find_pose(姿态, lib)
    elif 模式 == MODE_RANDOM_ALL:
        record = rng.choice(pose_db.pool(lib=lib))
    else:
        record = rng.choice(pose_db.pool(筛选系列, 筛选分类, lib))

    angle_key = pose_db.pick_angle(record, 视角, rng)
    record, real_angle, path = pose_db.resolve(record, angle_key)

    with Image.open(path) as im:
        pixels = np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0

    image = torch.from_numpy(pixels)[None, ...]
    picked = {"no": record["no"], "label": record["label"], "angle": real_angle}
    return {"ui": {"picked": [picked]}, "result": (image,)}


def _is_changed(cls, 模式, 视角, **kwargs):
    """随机模式下每次都要重新抽。

    没有 seed 之后，同一组参数会让 ComfyUI 判定输入未变、直接复用上次结果，
    节点不再执行也就不会回传 picked，用户点第二次队列会毫无反应。
    返回 NaN 表示「每次都不一样」，强制重新执行；固定选中且视角确定时仍走缓存。
    """
    if 模式 != MODE_FIXED or 视角 == pose_db.RANDOM_ANGLE:
        return float("nan")
    return ""


class GuliPosePicker:
    """白模姿态参考图选择器。姿态、视角由节点内的画廊控件挑选。"""

    CATEGORY = "GuliPoses"
    FUNCTION = "pick"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("姿态图",)
    IS_CHANGED = classmethod(_is_changed)

    @classmethod
    def INPUT_TYPES(cls):
        # 参数名直接就是中文：节点上的显示名不需要额外的界面补丁，
        # 与 GuliNodes 的「用户可见一律中文」保持一致。
        # 库是空的也要让节点注册得上（只用自定义图、或还没放图都能开工），运行时再给明确报错。
        labels = pose_db.pose_labels() or [pose_db.EMPTY_HINT]
        series = pose_db.series_options()
        categories = pose_db.category_options()
        return {
            "required": {
                "模式": (MODES, {"default": MODE_FIXED}),
                "姿态": (labels, {"default": labels[0]}),
                "视角": (pose_db.ANGLE_CHOICES, {"default": "正面"}),
                "筛选系列": (series, {"default": pose_db.ALL}),
                "筛选分类": (categories, {"default": pose_db.ALL}),
            }
        }

    def pick(self, 模式, 姿态, 视角, 筛选系列, 筛选分类):
        return _pick("pose", 模式, 姿态, 视角, 筛选系列, 筛选分类)


class GuliGarmentPicker:
    """服装参考图选择器。服装、视角由节点内的画廊控件挑选（服装为单角度，视角控件按不生效不展示隐藏）。"""

    CATEGORY = "GuliPoses"
    FUNCTION = "pick"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("服装图",)
    IS_CHANGED = classmethod(_is_changed)

    @classmethod
    def INPUT_TYPES(cls):
        labels = pose_db.pose_labels("garment") or [pose_db.EMPTY_HINT]
        series = pose_db.series_options("garment")
        categories = pose_db.category_options("garment")
        angles = pose_db.angle_choices("garment")
        return {
            "required": {
                "模式": (MODES, {"default": MODE_FIXED}),
                "服装": (labels, {"default": labels[0]}),
                "视角": (angles, {"default": "正面"}),
                "筛选系列": (series, {"default": pose_db.ALL}),
                "筛选分类": (categories, {"default": pose_db.ALL}),
            }
        }

    def pick(self, 模式, 服装, 视角, 筛选系列, 筛选分类):
        return _pick("garment", 模式, 服装, 视角, 筛选系列, 筛选分类)


class GuliFacePicker:
    """脸模参考图选择器。脸模、视角由节点内的画廊控件挑选（脸模为单角度，视角控件按不生效不展示隐藏）。"""

    CATEGORY = "GuliPoses"
    FUNCTION = "pick"
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("脸模图",)
    IS_CHANGED = classmethod(_is_changed)

    @classmethod
    def INPUT_TYPES(cls):
        labels = pose_db.pose_labels("face") or [pose_db.EMPTY_HINT]
        series = pose_db.series_options("face")
        categories = pose_db.category_options("face")
        angles = pose_db.angle_choices("face")
        return {
            "required": {
                "模式": (MODES, {"default": MODE_FIXED}),
                "脸模": (labels, {"default": labels[0]}),
                "视角": (angles, {"default": "正面"}),
                "筛选系列": (series, {"default": pose_db.ALL}),
                "筛选分类": (categories, {"default": pose_db.ALL}),
            }
        }

    def pick(self, 模式, 脸模, 视角, 筛选系列, 筛选分类):
        return _pick("face", 模式, 脸模, 视角, 筛选系列, 筛选分类)


NODE_CLASS_MAPPINGS = {
    "GuliPosePicker": GuliPosePicker,
    "GuliGarmentPicker": GuliGarmentPicker,
    "GuliFacePicker": GuliFacePicker,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "GuliPosePicker": "GG 姿态库",
    "GuliGarmentPicker": "GG 服装库",
    "GuliFacePicker": "GG 脸模库",
}
