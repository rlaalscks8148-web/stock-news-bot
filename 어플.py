"""
내 종목 뉴스 + 이벤트 텔레그램 알리미
--------------------------------------
매일 실행되면(예: GitHub Actions cron) 등록된 종목의 최신 뉴스와
다가오는 이벤트(실적발표, 락업해제 등)를 텔레그램으로 보내줍니다.

필요한 값은 환경변수로 넣습니다 (코드에 직접 쓰지 마세요):
  TELEGRAM_BOT_TOKEN  - @BotFather에서 발급받은 토큰
  TELEGRAM_CHAT_ID    - 알림 받을 내 채팅 ID
"""

import os
import datetime
import requests
import feedparser

# ---------- 1. 여기만 내 상황에 맞게 수정하세요 ----------

STOCKS = [
    {"name": "현대차", "query": "현대차 주가"},
    {"name": "한화시스템", "query": "한화시스템 주가"},
    {"name": "StablecoinX", "query": "StablecoinX USDE stock"},
]

EVENTS = [
    {"name": "ENA 락업 해제", "date": "2026-10-05"},
    {"name": "필리조선소 처분 완료", "date": "2026-10-31"},
    {"name": "현대차 3분기 실적 발표(예상)", "date": "2026-10-23"},
]

NEWS_PER_STOCK = 3          # 종목당 가져올 기사 수
EVENT_LOOKAHEAD_DAYS = 3    # 며칠 앞으로 다가온 이벤트까지 알릴지

# ---------------------------------------------------------

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def fetch_news(query, limit=3):
    """구글 뉴스 RSS에서 최근 기사를 가져옵니다. API 키가 필요 없습니다."""
    url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=ko&gl=KR"
    feed = feedparser.parse(url)
    items = []
    for entry in feed.entries[:limit]:
        items.append({"title": entry.title, "link": entry.link})
    return items


def build_news_section():
    lines = ["📰 *오늘의 종목 뉴스*"]
    for stock in STOCKS:
        lines.append(f"\n*{stock['name']}*")
        articles = fetch_news(stock["query"], NEWS_PER_STOCK)
        if not articles:
            lines.append("- 새 기사를 찾지 못했어요")
            continue
        for a in articles:
            lines.append(f"- [{a['title']}]({a['link']})")
    return "\n".join(lines)


def build_events_section():
    today = datetime.date.today()
    upcoming = []
    for e in EVENTS:
        d = datetime.date.fromisoformat(e["date"])
        diff = (d - today).days
        if 0 <= diff <= EVENT_LOOKAHEAD_DAYS:
            upcoming.append((diff, e["name"], e["date"]))
    if not upcoming:
        return None
    lines = ["📅 *다가오는 이벤트*"]
    for diff, name, date in sorted(upcoming):
        tag = "오늘" if diff == 0 else f"D-{diff}"
        lines.append(f"- {name} ({date}) · {tag}")
    return "\n".join(lines)


def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 환경변수가 설정되지 않았어요."
        )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    resp.raise_for_status()


def main():
    sections = [build_news_section()]
    events_section = build_events_section()
    if events_section:
        sections.append(events_section)
    message = "\n\n".join(sections)

    # 텔레그램 메시지는 4096자 제한이 있어 넘으면 잘라서 보냅니다.
    for i in range(0, len(message), 4000):
        send_telegram(message[i:i + 4000])


if __name__ == "__main__":
    main()
