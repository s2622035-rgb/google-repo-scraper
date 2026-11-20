import json
import sqlite3
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://github.com/orgs/google/repositories?type=all&page={}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
DB_NAME = "repos.db"
PER_PAGE = 30 


def create_db():
    """テーブルがなければ作る（あれば前回の続きとして使う）"""
    conn = sqlite3.connect(DB_NAME)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS repositories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            language TEXT,
            stars INTEGER
        )
        """
    )
    conn.commit()
    return conn


def find_key(obj, key):
    """JSONの中から、指定したキーの値を再帰的に探す"""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = find_key(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = find_key(v, key)
            if found is not None:
                return found
    return None


def fetch(page):
    """429（アクセス制限）が出たら待ってやり直す"""
    for attempt in range(10):
        res = requests.get(BASE_URL.format(page), headers=HEADERS, timeout=30)
        if res.status_code == 429:
            wait = int(res.headers.get("Retry-After", 60 * (attempt + 1)))
            print(f"  429 アクセス制限。{wait}秒待ってやり直します...")
            time.sleep(wait)
            continue
        res.raise_for_status()
        return res
    raise RuntimeError("何度やり直してもアクセス制限が解除されませんでした")


def scrape_page(page):
    """1ページ分のリポジトリ一覧と、全ページ数を返す"""
    res = fetch(page)
    soup = BeautifulSoup(res.text, "html.parser")

    for tag in soup.find_all("script", type="application/json"):
        text = tag.get_text()
        if '"repositories"' not in text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        items = find_key(data, "repositories")
        if not isinstance(items, list):
            continue

        repos = []
        for r in items:
            name = r["name"]
            language = (r.get("primaryLanguage") or {}).get("name")
            stars = r.get("starsCount", 0)
            repos.append((name, language, stars))
        page_count = find_key(data, "pageCount") or 1
        return repos, page_count

    return [], 0


def main():
    conn = create_db()

    saved = conn.execute("SELECT COUNT(*) FROM repositories").fetchone()[0]
    page = saved // PER_PAGE + 1
    if saved:
        print(f"すでに {saved} 件保存済み。page {page} から再開します")

    page_count = page
    while page <= page_count:
        repos, page_count = scrape_page(page)
        if not repos:
            print(f"page {page}: データが見つかりませんでした")
            break
        conn.executemany(
            "INSERT INTO repositories (name, language, stars) VALUES (?, ?, ?)",
            repos,
        )
        conn.commit()
        print(f"page {page}/{page_count}: {len(repos)} 件保存")
        page += 1
        time.sleep(1) 

    print("\n--- SELECT 結果 ---")
    for row in conn.execute(
        "SELECT name, language, stars FROM repositories ORDER BY stars DESC"
    ):
        print(row)
    total = conn.execute("SELECT COUNT(*) FROM repositories").fetchone()[0]
    print(f"\n合計 {total} 件")
    conn.close()


if __name__ == "__main__":
    main()