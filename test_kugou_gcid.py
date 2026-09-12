"""诊断酷狗 gcid 分享页，找出加载歌单的 API"""
import json
import sys

from playwright.sync_api import sync_playwright

GCID = "gcid_3z15xadwqzqz0e8"   # 换成你的 gcid
URL = f"https://www.kugou.com/songlist/{GCID}/"

captured = []

def on_response(resp):
    try:
        url = resp.url
        # 只关心酷狗的 JSON 接口
        if "kugou.com" not in url:
            return
        ct = resp.headers.get("content-type", "")
        if "json" not in ct and "javascript" not in ct:
            return
        try:
            data = resp.json()
        except Exception:
            return
        captured.append((url, data))
    except Exception:
        pass


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.on("response", on_response)

    print(f"打开：{URL}", flush=True)
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)

    # 尝试向下滚动，触发懒加载
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(3000)

    browser.close()

print(f"\n捕获到 {len(captured)} 个 JSON 响应：\n", flush=True)

for i, (url, data) in enumerate(captured, 1):
    # 粗查一下是否包含歌曲列表
    text = json.dumps(data, ensure_ascii=False)
    has_song = any(k in text for k in ("songname", "song_name", "filename",
                                        "audio_name", "songs", "songlist"))
    marker = " 🎵 含歌曲" if has_song else ""
    print(f"[{i}] {url}{marker}", flush=True)

    if has_song:
        # 打印结构概要
        if isinstance(data, dict):
            print(f"    keys: {list(data.keys())[:8]}", flush=True)
            inner = data.get("data")
            if isinstance(inner, dict):
                print(f"    data.keys: {list(inner.keys())[:8]}", flush=True)
                for key in ("info", "songs", "list", "songlist"):
                    v = inner.get(key)
                    if isinstance(v, list):
                        print(f"    data.{key}: {len(v)} 项", flush=True)
                        if v:
                            print(f"      第一项: {json.dumps(v[0], ensure_ascii=False)[:200]}", flush=True)
        print(flush=True)
