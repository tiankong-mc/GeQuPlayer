"""SQLite 简易封装：记录下载历史"""
import sqlite3
import time
from config import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS download_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                artist TEXT,
                filepath TEXT,
                created_at REAL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def add_download(title: str, artist: str, filepath: str):
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO download_history (title, artist, filepath, created_at) "
            "VALUES (?, ?, ?, ?)",
            (title, artist, filepath, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def list_downloads(limit: int = 500):
    conn = sqlite3.connect(DB_PATH)
    try:
        c = conn.cursor()
        c.execute(
            "SELECT title, artist, filepath, created_at FROM download_history "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = c.fetchall()
        return rows
    finally:
        conn.close()
