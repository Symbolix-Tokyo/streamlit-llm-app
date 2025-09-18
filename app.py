from dotenv import load_dotenv
load_dotenv()

import os
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# ------------- 環境変数/Secrets -------------
# OPENAI_API_KEY は環境変数または Streamlit Secrets から自動取得
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    try:
        OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        OPENAI_API_KEY = ""

# モデルは環境変数 OPENAI_MODEL があれば優先、無ければデフォルトを使用
MODEL_NAME = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# ------------- 画面基本 -------------
st.set_page_config(page_title="LLM文章アシスタント（リライト/要約）", page_icon="✍️")
st.title("✍️ LLM文章アシスタント（リライト/要約）")
st.caption("入力した文章を、A: 読みやすくリライト / B: 箇条書きで要約。A/Bを選び、実行してください。")

with st.expander("ℹ️ アプリ概要・操作方法", expanded=True):
    st.markdown(
        """
**できること**  
- 入力テキストをもとに、**A=プロのUXライター**（読みやすさ重視のリライト）または  
  **B=プロの要約者**（構造化された箇条書き要約）として LLM が応答します。

**使い方**  
1. サーバ側で **`OPENAI_API_KEY`**（環境変数または *App settings → Secrets*）を設定  
2. 必要なら **`OPENAI_MODEL`**（例: `gpt-4o-mini`）を環境変数で指定  
3. 下のラジオで **A/B** を選択し、テキストを入力 → **実行**  

> 注意：生成結果は参考ガイドです。数値・固有名詞は原典でご確認ください。
        """
    )

# ------------- ラジオ（A/B）-------------
expert_choice = st.radio(
    "専門家モードを選択（A/B）",
    options=["A", "B"],  # 要件どおり A/B のみ
    horizontal=True,
    help="A=プロのUXライター（読みやすくリライト） / B=プロの要約者（箇条書き要約）",
)
st.caption("A：明確・簡潔にリライト / B：主要点の抽出と構造化（箇条書き）")

# ------------- 入力フォーム（1つ）-------------
user_text = st.text_area(
    "テキストを入力してください（下書き、議事録、長文メモなど）",
    height=180,
    placeholder="例：先日の会議では新機能の優先順位について議論した。ユーザー要望の多いA機能を先に出すか、収益性の高いB機能を先にするかで意見が分かれた…",
)

# ------------- LLM呼び出し関数（要件を満たすシグネチャ）-------------
def ask_llm(input_text: str, expert_choice: str) -> str:
    """
    Parameters
    ----------
    input_text : str
        画面の入力テキスト
    expert_choice : str
        "A" または "B"（ラジオ選択値）
    Returns
    -------
    str
        LLMの回答テキスト
    """
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY が未設定です。環境変数または Stream
