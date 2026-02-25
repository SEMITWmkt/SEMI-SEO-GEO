import streamlit as st
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import os
from dotenv import load_dotenv

# 1. 介面極簡化 (Tesla Architecture)
st.set_page_config(page_title="SEMI 文案武器", layout="centered")
st.title("⚡ SEMI 競品對齊與文案優化引擎")
st.markdown("輸入競品網址與你的草稿。系統將即時潛入對手網站爬取骨架，並強制升級你的文案。")

# 2. 系統大腦初始化與金鑰安全檢查
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("系統停機：找不到 API 金鑰。請檢查 .env 檔案。")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. 輸入區 (沒有多餘的儀表板，只有目標與彈藥)
target_url = st.text_input("🎯 獵殺目標 (請貼上 1 篇高排名的競品網址)：", placeholder="https://...")
draft_copy = st.text_area("📝 你的原始草稿：", height=200, placeholder="貼上需要被強化的文案...")

# 4. 核心執行邏輯 (按下去的瞬間，爬蟲與 AI 同步運作)
if st.button("🔥 啟動即時分析與重構"):
    if not target_url or not draft_copy.strip():
        st.warning("彈藥不足：請確認已輸入「目標網址」與「草稿」。")
    else:
        with st.spinner("系統運作中：正在潛入對手網站並喚醒 AI 大腦..."):
            try:
                # [模組 A：即時動態爬蟲]
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                response = requests.get(target_url, headers=headers, timeout=10)
                response.raise_for_status() # 檢查伺服器是否允許連線
                
                soup = BeautifulSoup(response.text, 'html.parser')
                h1 = soup.find('h1').text if soup.find('h1') else "無主要標題"
                h2_tags = [h2.text.strip() for h2 in soup.find_all('h2') if h2.text.strip()]
                
                if not h2_tags:
                    st.warning("警告：該目標網頁缺乏 H2 結構，AI 將僅依賴標題進行推演。")
                    
                competitor_structure = f"【競品標題】：{h1}\n【競品 H2 骨架】：{', '.join(h2_tags)}"
                
                # [模組 B：AI 系統重構]
                prompt = f"""
                你是一位頂級的科技業 SEO/AIEO 行銷總監。
                我有一段初版草稿，以及我們剛即時爬取下來的競爭對手文章架構。

                {competitor_structure}

                【原始草稿】：
                {draft_copy}

                【你的任務】：
                直接根據對手的優勢骨架，將原始草稿改寫成一篇結構更具權威性、符合搜尋引擎喜好的高階行銷文案。
                不要說廢話，直接輸出改寫後的完美版本。
                """
                
                result = model.generate_content(prompt)
                
                # 輸出展示層
                st.success("✅ 即時重構完成！")
                st.subheader("💡 戰略級文案輸出")
                st.write(result.text)
                
            except requests.exceptions.RequestException as e:
                st.error(f"連線失敗：無法爬取該網址 ({e})。請確認網址正確，或對方網站具有反爬蟲機制。")
            except Exception as e:
                st.error(f"系統異常：{e}")