from dotenv import load_dotenv
load_dotenv()

import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# ------------ .env 読み込み（ローカル/Cloudで既にセット済みならそのまま上書き） ------------
load_dotenv()

# 必須: OPENAI_API_KEY / 任意: OPENAI_MODEL
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ------------ 画面基本 ------------
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
1.下のラジオで **A/B** を選択し、テキストを入力 → **実行**

> 注意：生成結果は参考ガイドです。数値・固有名詞は原典でご確認ください。
        """
    )

# ------------ ラジオ（A/B）------------
expert_choice = st.radio(
    "専門家モードを選択（A/B）",
    options=["A", "B"],  # 要件どおり A/B のみ
    horizontal=True,
    help="A=プロのUXライター（読みやすくリライト） / B=プロの要約者（箇条書き要約）",
)
st.caption("A：明確・簡潔にリライト / B：主要点の抽出と構造化（箇条書き）")

# ------------ 入力フォーム（1つ）------------
user_text = st.text_area(
    "テキストを入力してください（下書き、議事録、長文メモなど）",
    height=180,
    placeholder="例：先日の会議では新機能の優先順位について議論した。ユーザー要望の多いA機能を先に出すか、収益性の高いB機能を先にするかで意見が分かれた…",
)

# ------------ LLM呼び出し関数（要件：入力テキスト＋ラジオ選択を受け取り、回答文字列を返す）------------
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
        raise RuntimeError("OPENAI_API_KEY が未設定です。.env に設定して再実行してください。")

    if expert_choice == "A":
        system_prompt = (
            "あなたはプロのUXライターです。読みやすさ・簡潔さ・正確さを重視し、"
            "専門用語には補足を加え、冗長や曖昧さを避けてリライトしてください。"
            "出力フォーマット：\n"
            "1) 見出し（短く具体的に）\n"
            "2) 本文（3〜8文、段落可）\n"
            "3) 追記（重要な注意・前提があれば1〜2行）"
        )
    else:
        system_prompt = (
            "あなたはプロの要約者です。重要点の抽出・階層化・重複の排除を行い、"
            "簡潔な箇条書きで提示してください。"
            "出力フォーマット：\n"
            "- 目的/背景\n"
            "- 主要な論点（3〜6点）\n"
            "- 決定事項/未決事項\n"
            "- 次のアクション（担当/期限があれば付与）"
        )

    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.4, api_key=OPENAI_API_KEY)
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=input_text)]
    resp = llm.invoke(messages)
    return resp.content

# ------------ 実行 ------------
if st.button("実行", type="primary"):
    st.divider()
    if not user_text.strip():
        st.error("テキストを入力してください。")
    else:
        try:
            answer = ask_llm(user_text, expert_choice)
            st.subheader("🧾 結果")
            st.write(answer)
        except Exception as e:
            st.error(f"エラーが発生しました：{e}")
