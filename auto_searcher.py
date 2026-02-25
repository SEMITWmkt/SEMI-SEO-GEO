import os
import csv
import json
import datetime
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv
import feedparser  # 新增的雷達解析模組
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. 載入金鑰與設定 AI
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("系統停機：找不到 API 金鑰。請檢查 .env 檔案。")
    exit()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

DB_FILE = "semi_market_data.csv"

def init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            writer.writerow(["抓取日期", "來源網址", "文章標題", "核心技術聚類", "目標受眾層級", "產業趨勢"])
        print(f"[*] 系統已建立全新資料庫：{DB_FILE}")
def send_email_notification(log_msg):
    sender_email = os.getenv("EMAIL_USER") 
    password = os.getenv("EMAIL_PASS")
    
    if not sender_email or not password:
        print("[!] 找不到郵件設定，跳過發信步驟。")
        return

    msg = MIMEMultipart()
    msg['From'] = f"AI 情報機器人 <{sender_email}>"
    msg['To'] = sender_email
    msg['Subject'] = f"【半導體監測報】自動掃描完成 - {datetime.now().strftime('%Y-%m-%d')}"
    
    body = f"Bang-Lun 您好：\n\n今日情報掃描任務已完成。\n\n系統狀態：{log_msg}\n數據已同步至 GitHub，請開啟 Excel 戰情室查看。\n\n祝 工作順利"
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP("smtp-mail.outlook.com", 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
        print("[*] 郵件發送成功！")
    except Exception as e:
        print(f"[!] 郵件發送失敗: {e}")        

# --- 新增：情報雷達管線 ---
def get_latest_urls_from_rss(rss_urls, max_per_feed=2):
    print(f"\n[*] 啟動情報雷達：開始掃描權威網站...")
    collected_urls = []
    for feed_url in rss_urls:
        print(f"  -> 掃描目標: {feed_url}")
        try:
            parsed_feed = feedparser.parse(feed_url)
            # 每個權威網站只抓取最新的前 max_per_feed 篇文章
            for entry in parsed_feed.entries[:max_per_feed]:
                collected_urls.append(entry.link)
                print(f"     [發現新彈藥] {entry.title}")
        except Exception as e:
            print(f"  [!] 解析 RSS 失敗 {feed_url}: {e}")
    return collected_urls

# --- 核心萃取引擎 (保持不變) ---
# 4. 核心萃取引擎
def extract_market_data(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.find('title').text.strip() if soup.find('title') else "無標題"
        raw_text = soup.get_text(separator=' ', strip=True)[:3000]

        prompt = f"""
        你現在是一個精準的半導體產業資料萃取系統。
        請閱讀以下網頁內容，並嚴格萃取出三個維度的資訊。
        
        必須強制以 JSON 格式輸出，不要有任何 Markdown 標記，不要有 ```json 等字眼，只輸出純 JSON 格式：
        {{
            "Tech_Cluster": "從文章中歸納出1到2個核心技術關鍵字，例如：矽光子、先進封裝、設備材料、永續ESG等。",
            "Target_Audience": "判斷這篇文章主要寫給誰看？例如：C-Level決策者、研發工程師、供應鏈採購等。",
            "Industry_Trend": "用一句話（20字以內）總結這篇文章透露的最新產業發展趨勢或痛點。"
        }}

        網頁內容：
        {raw_text}
        """
        
        # 新增的 AI 專屬防護網 (逾時強制切斷)
        try:
            ai_response = model.generate_content(prompt, request_options={"timeout": 30.0})
        except Exception as ai_error:
            print(f"[!] AI 處理失敗，跳過此筆。錯誤細節: {ai_error}")
            return None, None

        clean_json_str = ai_response.text.replace('```json', '').replace('```', '').strip()
        extracted_data = json.loads(clean_json_str)
        
        return title, extracted_data
        
    except Exception as e:
        print(f"[!] 處理 {url} 時發生錯誤: {e}")
        return None, None

# --- 批次寫入管線 (升級整合) ---
def run_pipeline(urls):
    init_db()
    
    # 修正時區邏輯：強制獲取 UTC 時間並平移 8 小時至台灣時間
    import datetime
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    tw_time = now_utc + datetime.timedelta(hours=8)
    current_time = tw_time.strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n[{current_time}] 啟動 AI 萃取引擎，開始寫入資料庫...")
    print("-" * 50)

    for url in urls:
        print(f"正在獵殺分析: {url}")
        title, ai_data = extract_market_data(url)
        
        if title and ai_data:
            with open(DB_FILE, mode='a', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                writer.writerow([
                    current_time,
                    url,
                    title,
                    ai_data.get("Tech_Cluster", "N/A"),
                    ai_data.get("Target_Audience", "N/A"),
                    ai_data.get("Industry_Trend", "N/A")
                ])
            print(f"  => 成功寫入！技術:[{ai_data.get('Tech_Cluster')}] | 趨勢:[{ai_data.get('Industry_Trend')}]")
        else:
            print("  => 萃取失敗，跳過此網址。")
    
    print("-" * 50)
    print("今日批次作業完成。請檢查 semi_market_data.csv 檔案。")

if __name__ == "__main__":
    # 定義你的情報雷達清單 (這裡放入各大科技媒體的 RSS 訂閱源)
    target_rss_feeds = [
        "https://technews.tw/category/semiconductor/feed/",  # 科技新報 - 半導體分類
        "https://www.bnext.com.tw/rss"                       # 數位時代 - 總覽
    ]
    
    # 階段一：雷達掃描，自動抓取最新網址 (每個網站抓最新 2 篇測試)
    discovered_urls = get_latest_urls_from_rss(target_rss_feeds, max_per_feed=2)
    
    # 階段二：將發現的新網址送入萃取管線
    if discovered_urls:
        run_pipeline(discovered_urls)
    else:
        print("雷達未掃描到任何有效網址，系統休眠。")