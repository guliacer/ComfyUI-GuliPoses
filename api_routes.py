"""把多库姿态/服装图库暴露给前端：索引 / 缩略图 / 原图，以及自定义图的导入与删除。

每个库（pose / garment ...）各自注册一组 /<prefix>/* 路由，目录隔离、互不干扰。
索引是内置库与 poses/<lib>/custom/ 的合并结果，每次请求现算（目录没变时不重扫、不解码图片）。
"""

import asyncio
import json
from pathlib import Path

from aiohttp import web

from . import pose_db

try:
    from server import PromptServer
except ImportError:  # 脱离 ComfyUI 单独导入时不注册路由
    PromptServer = None


def _serve(folder: Path, name: str, cache: str):
    target = (folder / Path(name).name).resolve()
    if folder.resolve() not in target.parents or not target.is_file():
        raise web.HTTPNotFound()
    return web.FileResponse(target, headers={"Cache-Control": cache})


def _make_handlers(lib: str):
    """为某个库生成一组路由处理函数，闭包各自捕获 lib，互不影响。"""

    async def lib_index(request):
        data = await asyncio.to_thread(pose_db.index, lib)
        return web.json_response(data, headers={"Cache-Control": "no-cache"})

    async def lib_thumb(request):
        # 缩略图不随仓库分发（能省体积/文件数），首次请求时用原图现生成
        path = await asyncio.to_thread(pose_db.ensure_thumb, request.match_info["name"], lib)
        if path is None:
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers={"Cache-Control": "public, max-age=604800"})

    async def lib_img(request):
        return _serve(pose_db.LIB_DIRS[lib]["img"], request.match_info["name"], "public, max-age=604800")

    async def lib_custom_thumb(request):
        return _serve(pose_db.LIB_DIRS[lib]["custom_thumb"], request.match_info["name"], "no-cache")

    async def lib_custom_img(request):
        return _serve(pose_db.LIB_DIRS[lib]["custom"], request.match_info["name"], "no-cache")

    async def lib_upload(request):
        if not request.content_type.startswith("multipart/"):
            return web.json_response({"error": "导入接口只接受 multipart/form-data 上传"}, status=400)
        try:
            reader = await request.multipart()
        except Exception as err:
            return web.json_response({"error": f"读取上传内容失败：{err}"}, status=400)

        # 先把所有分片收齐：知道总张数才能给「统一名称」自动补序号
        uploads, meta = [], {}
        while True:
            part = await reader.next()
            if part is None:
                break
            if part.name == "meta":
                try:
                    meta = json.loads((await part.read()).decode("utf-8", "replace")) or {}
                except Exception:
                    meta = {}
                continue
            if part.name != "images" or not part.filename:
                continue
            uploads.append((part.filename, await part.read()))

        if not uploads:
            return web.json_response({"error": "没有收到图片文件"}, status=400)

        base_name = str(meta.get("name") or "").strip() or None
        cat = meta.get("cat") or None
        angle = meta.get("angle") or None
        saved, failed = [], []
        for index, (filename, data) in enumerate(uploads, 1):
            if not data:
                failed.append({"name": filename, "error": "文件是空的"})
                continue
            # 多张共用一个名称时自动编号，避免互相覆盖
            name = base_name if (not base_name or len(uploads) == 1) else f"{base_name} {index}"
            try:
                saved.append(
                    await asyncio.to_thread(pose_db.save_custom, filename, data, name, cat, angle, lib)
                )
            except Exception as err:
                failed.append({"name": filename, "error": str(err)})

        count = await asyncio.to_thread(pose_db.custom_count, lib)
        # nos 与 saved 一一对应：前端拿它跳到刚落盘的姿态（显示名由用户填，不能从文件名推）
        nos = await asyncio.to_thread(pose_db.custom_nos, saved, lib)
        return web.json_response(
            {"saved": saved, "nos": nos, "failed": failed, "customCount": count}
        )

    async def lib_delete(request):
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        names = payload.get("names")
        if not isinstance(names, list):
            names = [payload.get("name")]
        names = [str(name) for name in names if name]
        if not names:
            return web.json_response({"error": "缺少要删除的文件名"}, status=400)
        deleted = [name for name in names if await asyncio.to_thread(pose_db.delete_custom, name, lib)]
        if not deleted:
            return web.json_response({"error": f"没找到这些图：{'、'.join(names)}"}, status=404)
        count = await asyncio.to_thread(pose_db.custom_count, lib)
        return web.json_response({"deleted": deleted, "customCount": count})

    return [
        ("/index.json", lib_index, "GET"),
        ("/thumb/{name}", lib_thumb, "GET"),
        ("/img/{name}", lib_img, "GET"),
        ("/custom/thumb/{name}", lib_custom_thumb, "GET"),
        ("/custom/img/{name}", lib_custom_img, "GET"),
        ("/custom/upload", lib_upload, "POST"),
        ("/custom/delete", lib_delete, "POST"),
    ]


def register_lib(lib: str, prefix: str) -> None:
    instance = getattr(PromptServer, "instance", None) if PromptServer else None
    if instance is None:
        return
    routes = instance.routes
    for path, handler, method in _make_handlers(lib):
        getattr(routes, method.lower())(f"/{prefix}{path}")(handler)


def register() -> None:
    # 姿态库（默认）与服装库各自一组路由；加库只需在此追加一行
    register_lib("pose", "guliposes")
    register_lib("garment", "guligarments")
    register_lib("face", "gulifaces")


# 在模块导入时注册，__init__.py 因此只保留映射与 WEB_DIRECTORY，不再写逻辑。
# 脱离 ComfyUI（没有 PromptServer.instance）时 register() 直接返回，不影响单独导入。
register()
