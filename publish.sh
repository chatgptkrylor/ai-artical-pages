#!/bin/bash
# publish.sh — Push latest articles to GitHub Pages and log URLs
# Usage: ./publish.sh "Article Title" "filename.html"

cd /home/krylorix/Documents/ai-article-pages || exit 1

TITLE="${1:-Untitled}"
FILENAME="${2:-}"
LOG="/home/krylorix/Documents/ai-article-pages/published-articles.log"
BASE_URL="https://chatgptkrylor.github.io/ai-artical-pages/articles"
TOPIC_LOG="/home/krylorix/Documents/ai-article-pages/topic-history.log"
echo "$(date '+%Y-%m-%d %H:%M') | $TITLE" >> "$TOPIC_LOG"

git add -A
git diff --cached --quiet && echo "Nothing to publish." && exit 0
git commit -m "New article: $TITLE"
git pull origin main --rebase --allow-unrelated-histories --no-edit 2>/dev/null
git push origin main

# Log the URL
if [ -n "$FILENAME" ]; then
  echo "$(date '+%Y-%m-%d %H:%M') | $TITLE | $BASE_URL/$FILENAME" >> "$LOG"
  echo "Published: $BASE_URL/$FILENAME"
fi
