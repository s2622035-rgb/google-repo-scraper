# github-google-scraper

GitHub の google 組織のリポジトリ情報（リポジトリ名・主要言語・スター数）をスクレイピングして SQLite に保存します。
GitHub API は使っていません。

## 使い方

pip3 install requests beautifulsoup4
python3 scrape.py

repos.db が作成され、保存したデータが SELECT 文で表示されます。
