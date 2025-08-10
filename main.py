import os
import smtplib
import json
import requests
import datetime
from email.message import EmailMessage

# --- CONFIGURATION ---
# These will be read from GitHub's secret management system.
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
SENDER_EMAIL = os.environ.get('MAILBOT_SENDER_EMAIL')
SENDER_PASSWORD = os.environ.get('MAILBOT_APP_PASSWORD')
RECIPIENT_EMAIL = os.environ.get('MAILBOT_RECIPIENT_EMAIL')

def get_news_with_gemini():
    """Calls the Gemini API to get the latest tech news."""
    print("Fetching news with Gemini API...")
    if not GEMINI_API_KEY:
        raise ValueError("Error: GEMINI_API_KEY secret not set.")

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
    prompt = """
    You are an expert tech news analyst. Find the 3 most impactful developments in AI and technology
    from the last 24 hours. Focus on genuine breakthroughs or major product releases. For each, provide
    a title, a concise one-liner, a brief summary, and a valid source link.
    """
    json_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING"},
                "one_liner": {"type": "STRING"},
                "summary": {"type": "STRING"},
                "source_link": {"type": "STRING"}
            }, "required": ["title", "one_liner", "summary", "source_link"]
        }
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
            news_articles = json.loads(json_string)
            print(f"Successfully fetched {len(news_articles)} articles.")
            return news_articles
        else:
            print("Error: Could not find news content in API response.", result)
            return None
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return None

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
    if not SENDER_EMAIL or not SENDER_PASSWORD or not RECIPIENT_EMAIL:
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
    articles = get_news_with_gemini()
    if articles:
        html_news = format_news_as_html(articles)
        today_date = datetime.date.today().strftime("%B %d, %Y")
        subject = f"Your Tech News Update - {today_date}"
        send_email(subject, html_news)
