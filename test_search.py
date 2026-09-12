"""测试 gequbao 搜索接口"""
print("=== 测试 gequbao 搜索 ===\n", flush=True)

from core.gequbao_api import search

keyword = "雨爱"
print(f"[1] 搜索关键词：{keyword}", flush=True)

songs = search(keyword, limit=15)
print(f"[2] 返回 {len(songs)} 首\n", flush=True)

for i, s in enumerate(songs, 1):
    print(f"  {i:2d}. {s.display}   (id={s.song_id})", flush=True)

if not songs:
    print("  ⚠ 结果为空，检查正则或请求头", flush=True)
    raise SystemExit(1)

# 顺便测试取播放直链
print(f"\n[3] 测试获取第一首的播放直链...", flush=True)
from core.gequbao_api import get_play_url
url = get_play_url(songs[0].song_id)
if url:
    print(f"  ✓ {url[:120]}...", flush=True)
else:
    print("  ✗ 获取失败", flush=True)
