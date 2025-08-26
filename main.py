import os
import smtplib
import json
import requests
import datetime
from email.message import EmailMessage
from bs4 import BeautifulSoup
from googlesearch import search

# --- CONFIGURATION ---
# These will be read from GitHub's secret management system.
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SENDER_EMAIL = os.environ.get('MAILBOT_SENDER_EMAIL')
SENDER_PASSWORD = os.environ.get('MAILBOT_APP_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('MAILBOT_RECIPIENT_EMAIL')

def summarize_text_with_gemini(text_content, article_title):
    """Uses the Gemini API to summarize a given block of text."""
    print(f"  Summarizing '{article_title}' with Gemini...")
    if not GEMINI_API_KEY:
        raise ValueError("Error: GEMINI_API_KEY secret not set.")

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""
    You are an expert tech news analyst. Below is the text content from an article titled "{article_title}".
    Your task is to provide a concise one-liner and a brief, easy-to-understand summary (2-3 sentences) of this article.

    ARTICLE TEXT:
    ---
    {text_content[:4000]}
    ---
    """
    
    json_schema = {
        "type": "OBJECT",
        "properties": {
            "one_liner": {"type": "STRING"},
            "summary": {"type": "STRING"}
        }, "required": ["one_liner", "summary"]
    }
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": json_schema
        }
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        if (result.get('candidates') and result['candidates'][0]['content']['parts']):
            json_string = result['candidates'][0]['content']['parts'][0]['text']
            return json.loads(json_string)
        return None
    except Exception as e:
        print(f"  Error during Gemini summarization: {e}")
        return None

def get_latest_tech_news_with_scraping(num_articles=3):
    """Searches for news, scrapes articles, and gets AI summaries."""
    print("Searching for latest tech news articles...")
    query = "impactful tech and AI news last 24 hours"
    
    articles = []
    urls_processed = set()

    for url in search(query, num_results=10, lang="en"):
        if len(articles) >= num_articles or url in urls_processed:
            continue
        
        urls_processed.add(url)
        print(f"Processing article: {url}")

        try:
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title = soup.find('h1').get_text().strip() if soup.find('h1') else "No Title Found"
            
            paragraphs = soup.find_all('p')
            article_text = "\n".join([p.get_text() for p in paragraphs])

            if len(article_text) > 300: # Ensure there's enough content
                summary_data = summarize_text_with_gemini(article_text, title)
                if summary_data:
                    articles.append({
                        "title": title,
                        "one_liner": summary_data.get("one_liner", ""),
                        "summary": summary_data.get("summary", "Could not summarize."),
                        "source_link": url
                    })
        except Exception as e:
            print(f"  Could not process article, error: {e}")
            
    return articles

def format_news_as_html(articles):
    """Formats articles into an HTML string for the email."""
    if not articles:
        return "<h1>Tech & AI Update</h1><p>No new articles found today.</p>"
    today_date = datetime.date.today().strftime("%B %d, %Y")
    html_content = f"""
    <html><head><style>
        body {{ font-family: sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 20px auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }}
        h1 {{ color: #4285F4; }} h3 {{ margin-bottom: 5px; }} a {{ color: #1a73e8; text-decoration: none; }}
        hr {{ border: 0; border-top: 1px solid #eee; margin: 20px 0; }}
        .one-liner {{ font-style: italic; color: #555; }}
    </style></head><body><div class="container">
    <h1>Tech & AI Update: {today_date}</h1>
    """
    for article in articles:
        html_content += f"""
            <h3><a href="{article['source_link']}">{article['title']}</a></h3>
            <p class="one-liner">{article['one_liner']}</p>
            <p>{article['summary']}</p><hr>
        """
    html_content += "</div></body></html>"
    return html_content

def send_email(subject, html_content):
    """Sends an email using credentials from secrets."""
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECIPIENT_EMAIL]):
        raise ValueError("Error: Email credentials or recipient not set as secrets.")

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg.set_content("Please enable HTML to view this email.")
    msg.add_alternative(html_content, subtype='html')

    print(f"Connecting to SMTP server to send email to {RECIPIENT_EMAIL}...")
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

if __name__ == "__main__":
    articles = get_latest_tech_news_with_scraping()
    if articles:
        html_news = format_news_as_html(articles)
        today_date = datetime.date.today().strftime("%B %d, %Y")
        subject = f"Your Tech News Update - {today_date}"
        send_email(subject, html_news)

