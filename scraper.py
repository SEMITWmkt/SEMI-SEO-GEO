import requests
from bs4 import BeautifulSoup
import json
import time

# 1. 你的目標資料庫清單 (List of URLs)
# 這裡我放了三個測試網址，未來你可以把 SEMI Taiwan 競爭對手的網址無限填入這個中括號裡
target_urls = [
    "https://en.wikipedia.org/wiki/Semiconductor",
    "https://en.wikipedia.org/wiki/Taiwan_Semiconductor_Manufacturing_Company",
    "https://en.wikipedia.org/wiki/Integrated_circuit"
]

# 準備一個空的清單，用來裝所有爬下來的資料
master_database = []

# 偽裝標頭
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

print(f"系統啟動：準備分析 {len(target_urls)} 個目標網頁...\n")

# 2. 開始批次處理迴圈 (For Loop)
for url in target_urls:
    print(f"正在抓取: {url}")
    
    # 3. 例外處理 (Try-Except) - 確保單一網頁失敗不會導致整個程式崩潰
    try:
        response = requests.get(url, headers=headers, timeout=10) # 設定 10 秒超時
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 確保網頁有 H1 標題才抓取，避免報錯
            h1_tag = soup.find('h1')
            main_title = h1_tag.text if h1_tag else "無 H1 標題"
            
            h2_tags = [h2.text.strip() for h2 in soup.find_all('h2') if h2.text.strip()]
            
            # 將單一網頁的資料打包
            page_data = {
                "url": url,
                "h1_title": main_title,
                "h2_subheadings": h2_tags,
                "total_h2_count": len(h2_tags)
            }
            
            # 把這包資料塞進我們的主資料庫清單中
            master_database.append(page_data)
            print("  -> 成功萃取結構。")
            
        else:
            print(f"  -> 失敗：伺服器拒絕存取。狀態碼: {response.status_code}")
            
    except Exception as e:
        print(f"  -> 嚴重錯誤：無法連線或解析 ({e})")
    
    # 4. 禮貌性延遲 (Politeness Delay)
    # 爬完一個網頁後強制暫停 2 秒，避免被對方伺服器判定為惡意攻擊而封鎖你的 IP
    time.sleep(2)

print("\n爬蟲任務結束。準備將資料寫入資料庫...")

# 5. 將整個主清單寫入 JSON 檔案
filename = "competitor_data.json"
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(master_database, f, ensure_ascii=False, indent=4)

print(f"大功告成！共有 {len(master_database)} 筆分析資料已安全儲存至 {filename}")