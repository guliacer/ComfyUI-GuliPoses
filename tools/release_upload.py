"""把离线安装包作为 GitHub Release 附件上传。

用法：
    python tools/release_upload.py --tag v1.0.0 --asset ComfyUI-GuliPoses.7z

凭据从 git credential store 取（GCM 里的 x-access-token），只在本进程内使用，不落盘、不打印。
环境里的 http_proxy/https_proxy 指向一个已失效的本地代理，所以这里显式禁用代理直连 GitHub。
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = "guliacer/ComfyUI-GuliPoses"
API = "https://api.github.com"
UPLOADS = "https://uploads.github.com"

# 只绕开环境里的死代理，不影响系统代理设置
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get_token() -> str:
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    )
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            token = line[len("password=") :].strip()
            if token:
                return token
    raise SystemExit("拿不到 GitHub 凭据：git credential fill 没返回 password")


def call(method: str, url: str, token: str, payload: dict | None = None, timeout: int = 120) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "guliposes-release",
            "Content-Type": "application/json",
        },
    )
    try:
        with OPENER.open(req, timeout=timeout) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        raise SystemExit(f"{method} {url} -> {exc.code}\n{body}") from exc


def ensure_release(token: str, tag: str, name: str, body: str) -> dict:
    """没有就建，有就复用——重复跑脚本不会造出一堆同名 Release。"""
    try:
        return call("GET", f"{API}/repos/{REPO}/releases/tags/{tag}", token)
    except SystemExit:
        pass
    return call(
        "POST",
        f"{API}/repos/{REPO}/releases",
        token,
        {"tag_name": tag, "name": name, "body": body, "draft": False, "prerelease": False},
    )


def upload_asset(token: str, release: dict, path: Path) -> dict:
    existing = {a["name"]: a for a in release.get("assets", [])}
    if path.name in existing:
        asset = existing[path.name]
        print(f"附件已存在：{asset['name']}（{asset['size']} 字节），先删掉再重传")
        call("DELETE", f"{API}/repos/{REPO}/releases/assets/{asset['id']}", token)

    size = path.stat().st_size
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    print(f"上传 {path.name}（{size / 1024 / 1024:.1f} MB，{ctype}）…", flush=True)

    with path.open("rb") as fh:
        req = urllib.request.Request(
            f"{UPLOADS}/repos/{REPO}/releases/{release['id']}/assets?name={urllib.parse.quote(path.name)}",
            data=fh,
            method="POST",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "guliposes-release",
                "Content-Type": ctype,
                "Content-Length": str(size),
            },
        )
        with OPENER.open(req, timeout=1800) as resp:
            return json.loads(resp.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="v1.0.0")
    ap.add_argument("--name", default="GG 姿态库 v1.0.0")
    ap.add_argument("--body-file", default="")
    ap.add_argument("--asset", default="ComfyUI-GuliPoses.7z")
    ap.add_argument("--only-release", action="store_true", help="只建 Release，不上传附件")
    args = ap.parse_args()

    token = get_token()
    body = Path(args.body_file).read_text(encoding="utf-8") if args.body_file else ""
    release = ensure_release(token, args.tag, args.name, body)
    print(f"Release {release['tag_name']}: {release['html_url']}")

    if not args.only_release:
        asset = upload_asset(token, release, Path(args.asset))
        print(f"附件：{asset['name']} / {asset['size']} 字节")
        print(f"下载地址：{asset['browser_download_url']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
