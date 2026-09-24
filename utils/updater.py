"""检查更新 + 下载安装包（多 GitHub 镜像）"""
import os
import requests

from config import UPDATE_MIRRORS, UPDATE_API


USER_AGENT = "GeQuPlayer-Updater"


def _compare_version(v1: str, v2: str) -> int:
    """v1 > v2 返回 1，相等返回 0，小于返回 -1"""
    def parse(v):
        parts = []
        for x in str(v).lstrip("v").split("."):
            try:
                parts.append(int(x))
            except ValueError:
                parts.append(0)
        return parts

    p1 = parse(v1)
    p2 = parse(v2)
    n = max(len(p1), len(p2))
    p1 += [0] * (n - len(p1))
    p2 += [0] * (n - len(p2))
    for a, b in zip(p1, p2):
        if a > b:
            return 1
        if a < b:
            return -1
    return 0


def check_update(current_version: str) -> dict:
    """
    检查更新。
    返回 {"has_update": bool, "latest_version": str, "download_url": str,
          "release_notes": str, "html_url": str, "mirror": str}
    失败时抛异常。
    """
    last_error = None

    # 依次尝试镜像
    for mirror in UPDATE_MIRRORS:
        try:
            url = mirror + UPDATE_API
            print(f"[updater] 尝试镜像: {mirror}", flush=True)
            r = requests.get(url, timeout=15, headers={"User-Agent": USER_AGENT})
            if r.status_code != 200:
                print(f"[updater] {mirror} -> HTTP {r.status_code}", flush=True)
                continue

            data = r.json()
            tag = str(data.get("tag_name", "")).lstrip("v")
            if not tag:
                continue

            # 找安装包下载链接
            assets = data.get("assets", []) or []
            download_url = None
            for a in assets:
                name = a.get("name", "")
                if name.lower().endswith(".exe") and "setup" in name.lower():
                    download_url = a.get("browser_download_url")
                    break
            if not download_url:
                for a in assets:
                    if a.get("name", "").lower().endswith(".exe"):
                        download_url = a.get("browser_download_url")
                        break

            has_update = _compare_version(tag, current_version) > 0

            print(f"[updater] 镜像 {mirror} 可用，最新版本 {tag}", flush=True)

            return {
                "has_update": has_update,
                "latest_version": tag,
                "download_url": download_url or "",
                "release_notes": data.get("body", "") or "",
                "html_url": data.get("html_url", "") or "",
                "mirror": mirror,
            }
        except Exception as e:
            last_error = e
            print(f"[updater] 镜像 {mirror} 失败: {str(e)[:80]}", flush=True)
            continue

    if last_error:
        raise RuntimeError(f"所有镜像均失败（最后错误：{last_error}）")
    raise RuntimeError("所有镜像均失败")


def download_installer(url: str, dest_path: str, progress_callback=None) -> bool:
    """
    下载安装包。会依次尝试直连 + 镜像。
    progress_callback(done_bytes, total_bytes)
    """
    if not url:
        return False

    # 候选：直连 + 所有镜像
    candidates = [url]
    for mirror in UPDATE_MIRRORS:
        candidates.append(mirror + url)

    for i, full_url in enumerate(candidates):
        try:
            print(f"[updater] 下载尝试 {i+1}: {full_url[:100]}", flush=True)
            r = requests.get(full_url, stream=True, timeout=30,
                             headers={"User-Agent": USER_AGENT})
            if r.status_code != 200:
                continue

            total = int(r.headers.get("Content-Length", 0) or 0)
            done = 0
            tmp_path = dest_path + ".part"

            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(1024 * 256):
                    if chunk:
                        f.write(chunk)
                        done += len(chunk)
                        if progress_callback:
                            try:
                                progress_callback(done, total)
                            except Exception:
                                pass

            # 校验：至少 10MB（安装包不会太小）
            if done < 10 * 1024 * 1024:
                print(f"[updater] 文件过小 {done}，换下一个源", flush=True)
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                continue

            os.replace(tmp_path, dest_path)
            print(f"[updater] ✓ 下载成功 {done} 字节", flush=True)
            return True
        except Exception as e:
            print(f"[updater] 下载失败: {str(e)[:80]}", flush=True)
            continue

    return False
