import os
import csv
import json
import requests
import time
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import feedparser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 2026 年最新版 SDK 載入方式
from google import genai 

# 1. 載入金鑰與設定 AI
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("系統停機：找不到 API 金鑰。")
    exit()

# 初始化 2026 年最新版 Gemini Client
client = genai.Client(api_key=api_key)

DB_FILE = "semi_market_data.csv"

def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(["抓取日期", "來源網址", "文章標題", "核心技術聚類", "目標受眾層級", "產業趨勢"])
        print(f"[*] 系統已建立全新資料庫：{DB_FILE}")

def send_email_notification(new_records):
    sender_email = os.getenv("EMAIL_USER") 
    password = os.getenv("EMAIL_PASS")
    
    if not sender_email or not password:
        print("[!] 找不到郵件設定，跳過發信。")
        return

    msg = MIMEMultipart()
    msg['From'] = f"AI 半導體情報員 <{sender_email}>"
    msg['To'] = sender_email
    msg['Subject'] = f"【半導體戰報】今日新增 {len(new_records)} 則關鍵情報 - {datetime.now().strftime('%Y-%m-%d')}"
    
    table_rows = ""
    for idx, r in enumerate(new_records, 1):
        table_rows += f"{idx}. 【{r['title']}】\n"
        table_rows += f"   - 技術：{r['tech']}\n"
        table_rows += f"   - 趨勢：{r['trend']}\n"
        table_rows += f"   - 連結：{r['url']}\n\n"

    body = f"""Bang-Lun 您好：

今日 AI 掃描任務已完成，成功過濾重複項，並為您精選以下新進情報：

--------------------------------------------------
{table_rows}
--------------------------------------------------

詳細數據已同步至 GitHub，並已寫入 Excel 戰情室。
祝 處理愉快"""

    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
        print(f"[*] 成功發送摘要郵件，包含 {len(new_records)} 則新情報。")
    except Exception as e:
        print(f"[!] 郵件發送失敗: {e}")

def get_latest_urls_from_rss(rss_urls, max_per_feed=2):
    print(f"\n[*] 啟動情報雷達...")
    collected_urls = []
    for feed_url in rss_urls:
        try:
            parsed_feed = feedparser.parse(feed_url)
            for entry in parsed_feed.entries[:max_per_feed]:
                collected_urls.append({'url': entry.link, 'title': entry.title})
        except Exception as e:
            print(f" [!] 解析 RSS 失敗 {feed_url}: {e}")
    return collected_urls

def extract_market_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('title').text.strip() if soup.find('title') else "無標題"
        raw_text = soup.get_text(separator=' ', strip=True)[:3000]

        prompt = f"""請以 JSON 格式萃取半導體資訊：
        {{
            "Tech_Cluster": "1-2個技術關鍵字",
            "Target_Audience": "目標受眾",
            "Industry_Trend": "20字內趨勢總結"
        }}
        內容：{raw_text}"""
        
        # 🎯 核心升級：精確使用我們剛剛測出的有效模型
        ai_response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        clean_json_str = ai_response.text.replace('```json', '').replace('```', '').strip()
        return title, json.loads(clean_json_str)
    except Exception as e:
        print(f" [!] 萃取錯誤: {e}")
        return None, None

def run_pipeline(discovered_items):
    init_db()
    
    existing_urls = set()
    existing_titles = set()
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_urls.add(row['來源網址'].strip())
                existing_titles.add(row['文章標題'].strip())

    new_records_for_email = []
    tw_time = datetime.now(timezone.utc) + timedelta(hours=8)
    current_time_str = tw_time.strftime("%Y-%m-%d %H:%M:%S")

    for item in discovered_items:
        url = item['url'].strip()
        rss_title = item['title'].strip()

        if url in existing_urls or rss_title in existing_titles:
            print(f"[-] 跳過重複情報: {rss_title[:20]}...")
            continue

        print(f"正在獵殺分析: {url}")
        title, ai_data = extract_market_data(url)
        
        if title and ai_data:
            with open(DB_FILE, mode='a', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                writer.writerow([
                    current_time_str, url, title,
                    ai_data.get("Tech_Cluster", "N/A"),
                    ai_data.get("Target_Audience", "N/A"),
                    ai_data.get("Industry_Trend", "N/A")
                ])
            
            new_records_for_email.append({
                'title': title,
                'tech': ai_data.get("Tech_Cluster"),
                'trend': ai_data.get("Industry_Trend"),
                'url': url
            })
            existing_urls.add(url)
            existing_titles.add(title)
            
            # 專業素養：加上 3 秒延遲，避免連續請求遭 API 阻擋
            time.sleep(3)

    if new_records_for_email:
        send_email_notification(new_records_for_email)
    else:
        print("[*] 今日無新情報，不發送郵件。")

if __name__ == "__main__":
    target_rss_feeds = [
        "https://technews.tw/category/semiconductor/feed/",
        # 暫時關閉已損壞的數位時代 RSS，避免拖慢效能
        # "https://www.bnext.com.tw/rss"
    ]
    
    # 測試階段，先抓最新 2 篇即可
    discovered_items = get_latest_urls_from_rss(target_rss_feeds, max_per_feed=2)
    
    if discovered_items:
        run_pipeline(discovered_items)
    else:
        print("雷達未掃描到任何有效網址。")