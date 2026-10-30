from . import api_routes  # noqa: F401  导入即注册各库路由（/guliposes/*、/guligarments/*、/gulifaces/*）
from . import pose_db
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

WEB_DIRECTORY = "web"

# 发行版本号：README 更新记录、tools/pack_release.py 的产物命名都以它为准
__version__ = "1.2.3"

# 用户素材（导入的图 / 自己丢的原始图）放在 ComfyUI/user/default/guliposes/ 下，
# 不在插件目录里，升级覆盖插件也不会丢。这里接管老版本留在插件内的那批。
pose_db.ensure_userdata()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY", "__version__"]
