import os
import smtplib
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText

import feedparser
import requests

# Load secrets from environment variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")


def send_email_report(analysis_text):
    if not EMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("Chyba: Chybí EMAIL_ADDRESS nebo GMAIL_APP_PASSWORD.")
        return

    msg = MIMEText(analysis_text, "html", "utf-8")
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS

    subject_text = (
        f"IPO Radar - Denní přehled ({datetime.now().strftime('%Y-%m-%d')})"
    )
    msg["Subject"] = Header(subject_text, "utf-8")

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, msg.as_string())
        server.quit()
        print("Email byl úspěšně odeslán na tvůj Gmail v HTML formátu.")
    except Exception as e:
        print(f"Chyba při odesílání emailu: {e}")


def fetch_ipo_rss_news():
    rss_urls = [
        "https://finance.yahoo.com/rss/headline?s=IPO",
        "https://www.benzinga.com/feed",
        "https://seekingalpha.com/market_currents.xml",
        "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    ]

    articles = []
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                published = entry.get("published", "")

                if "IPO" in title or "public offering" in title.lower():
                    articles.append(
                        {
                            "title": title,
                            "summary": summary,
                            "published": published,
                        }
                    )
        except Exception as e:
            print(f"Chyba při čtení feedu {url}: {e}")

    return articles


def analyze_with_gemini(ipo_data):
    if not ipo_data:
        return "<p>V RSS feedech nebyly nalezeny žádné čerstvé zprávy o IPO.</p>"

    if not GEMINI_API_KEY:
        return "<p>Chyba: Není nastaven GEMINI_API_KEY.</p>"

    prompt = f"""
    Jsi analytický bot pro sledování akciového trhu. Dnes je {datetime.now().strftime('%Y-%m-%d')}.
    Zde jsou nejnovější zprávy a tiskové zprávy o IPO získané z veřejných RSS zdrojů:
    {ipo_data}

    Analyzuj je a odpověz v čistém HTML formátu (použij tagy jako <b>, <ul>, <li>, žádný markdown):
    1. Název společnosti (pokud je z textu zřejmý)
    2. O co se jedná
    3. Zda zpráva indikuje reálný potenciál pro krátkodobý momentum trading.
    """

    # Note: Using gemini-1.5-flash or gemini-2.5-flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            raw_text = result["candidates"][0]["content"]["parts"][0]["text"]
            # Remove any markdown code block wraps if Gemini includes them
            cleaned_text = (
                raw_text.replace("```html", "").replace("```", "").strip()
            )
            return cleaned_text
        else:
            return f"<p>Chyba při volání Gemini API: {response.text}</p>"
    except Exception as e:
        return f"<p>Chyba při komunikaci s API: {e}</p>"


if __name__ == "__main__":
    print("Stahuji čerstvá data o IPO přes RSS...")
    ipo_news = fetch_ipo_rss_news()
    print(f"Nalezeno {len(ipo_news)} článků. Spouštím analýzu...")
    analysis = analyze_with_gemini(ipo_news)

    print("\n--- VÝSLEDEK ANALÝZY ---")
    print(analysis)

    send_email_report(analysis)
