"""诊断歌词获取"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.gequbao_api import search, _get_lyrics_from_detail

keyword = "雨爱"
print(f"=== 搜索 {keyword} ===")
songs = search(keyword, limit=5)
if not songs:
    print("搜索失败")
    sys.exit(1)

for s in songs[:3]:
    print(f"\n--- {s.title} - {s.artist} (id={s.song_id}) ---")
    lrc = _get_lyrics_from_detail(s.song_id)
    if lrc:
        lines = lrc.split("\n")
        print(f"✓ 拿到歌词 {len(lines)} 行")
        print(f"  前 3 行: {lines[:3]}")
    else:
        print(f"✗ 拿不到歌词")
