import streamlit as st
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# 1. 系統網頁設定 (這是 PM 定義產品外觀的地方)
st.set_page_config(page_title="SEMI Taiwan 文案優化器", layout="wide")
st.title("🚀 SEMI Taiwan SEO/AIEO 文案優化系統")
st.markdown("基於市場競品 H2 結構數據的自動化行銷文案改寫引擎。")

# 2. 載入金鑰與 AI 大腦
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("嚴重錯誤：找不到 API 金鑰。請確認 .env 檔案是否存在且設定正確。")
    st.stop() # 停止渲染網頁

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. 讀取你的本機資料庫 (competitor_data.json)
try:
    with open('competitor_data.json', 'r', encoding='utf-8') as f:
        database = json.load(f)
except FileNotFoundError:
    st.error("錯誤：找不到 competitor_data.json。請先執行爬蟲程式 (scraper.py) 建立資料庫。")
    st.stop()

# 整理競爭對手的結構，準備餵給 AI
competitor_structures = ""
for idx, data in enumerate(database):
    competitor_structures += f"\n【競爭對手 {idx+1}】({data['h1_title']}):\n"
    competitor_structures += ", ".join(data['h2_subheadings']) + "\n"

# 4. 建立使用者介面 (UI) - 輸入區
st.subheader("📝 輸入原始草稿")
draft_copy = st.text_area(
    "請在此貼上行銷同事撰寫的初稿：", 
    height=200, 
    placeholder="在此輸入或貼上簡陋的文案草稿..."
)

# 5. 執行按鈕與核心邏輯
if st.button("⚡ 執行競品對齊與文案優化"):
    if not draft_copy.strip():
        st.warning("請先輸入草稿內容！")
    else:
        # st.spinner 會在網頁上顯示載入中的動畫，安撫使用者的等待焦慮
        with st.spinner("系統連線中：正在將市場數據與草稿傳送給 Gemini AI 大腦分析..."):
            
            prompt = f"""
            你現在是一位頂級的科技業 SEO/AIEO 行銷總監。
            我有一段同事寫的初版行銷草稿，以及我們剛從市場上爬取下來的三篇高排名競爭對手文章的標題架構（H2）。

            【市場競爭對手架構數據】：
            {competitor_structures}

            【同事的原始草稿】：
            {draft_copy}

            【你的任務】：
            1. 痛點分析：請冷酷且專業地分析，我們的草稿對比競爭對手的架構，漏掉了哪些關鍵的產業維度。
            2. 重磅改寫：請直接根據這些對手的優勢數據，將我們的草稿改寫成一篇結構更具權威性、符合搜尋引擎喜好的高階行銷文案。
            """
            
            try:
                # 呼叫 API
                response = model.generate_content(prompt)
                st.success("✅ 分析與優化完成！")
                
                # 在網頁上優雅地展示結果
                st.subheader("💡 專業優化結果")
                st.write(response.text)
                
            except Exception as e:
                st.error(f"呼叫 API 發生異常：{e}")