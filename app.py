from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os
import sys
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# -----------------------------
# 基本設定
# -----------------------------
st.set_page_config(
    page_title="一人暮らし女性向け 夕飯/作り置き 提案アプリ",
    page_icon="🍳",
)

st.title("🍳 一人暮らし女性向け：夕飯 or 作り置き 提案アプリ")
st.caption(
    "忙しい日の『今夜の一品』や、週前半に仕込む『作り置き』を素早く提案。"
    "冷蔵庫の食材や希望条件を入れて「提案してもらう」を押してください。"
)

with st.expander("ℹ️ アプリの使い方（操作説明）", expanded=True):
    st.markdown(
        """
**このアプリでできること**
- 画面の入力フォームに「食材」「所要時間」「味の好み」など自由に記入 → LLMが最適な一品を提案  
- ラジオボタンで **A=手軽な夕飯の専門家** / **B=作り置きの専門家** を切り替え  
- 参考画像（URL貼付 or 画像アップロード）を表示して、完成イメージを掴めます

**使い方の流れ**
1. 左のサイドバーでAPIキーを設定（または `st.secrets` 利用）  
2. 画面中央のラジオで専門家を選ぶ  
3. 入力フォームに条件を記入  
4. 「提案してもらう」を押すと、画面下部に結果が表示されます
        """
    )

# -----------------------------
# サイドバー：APIキー & モデル選択
# -----------------------------
with st.sidebar:
    st.header("設定")
    api_key = st.text_input(
        "OpenAI API Key（入力しない場合は st.secrets を参照）",
        type="password",
        help="環境変数 OPENAI_API_KEY でも可",
    )
    default_key = os.environ.get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", "")
    # api_keyが空の場合のみdefault_keyを代入する
    if not api_key and default_key:
        api_key = default_key

    # get_default_api_key関数が未定義なので追加
    def get_default_api_key():
        return os.environ.get("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", "")
    default_key = get_default_api_key()
    if not api_key and default_key:
        api_key = default_key

    model_name = st.selectbox(
        "モデル選択",
        options=[
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4.1-mini",
        ],
        index=0,
        help="LangChain(ChatOpenAI) 経由で呼び出します",
    )

    st.divider()
    st.caption("📌 参考画像の扱い：ファイルをアップロードするか、画像URLを貼付してください。")

# -----------------------------
# 参考画像UI
# -----------------------------
st.write("### 🖼️ 参考画像（任意）")
col1, col2 = st.columns(2)
with col1:
    sample_urls = st.text_area(
        "画像URLを改行区切りで貼り付け（任意）",
        placeholder="https://example.com/dish1.jpg\nhttps://example.com/dish2.jpg",
        height=90,
    )
with col2:
    uploaded_files = st.file_uploader(
        "画像ファイルをアップロード（複数可・任意）",
        accept_multiple_files=True,
        type=["png", "jpg", "jpeg", "webp"],
    )

# 表示
image_cols = st.columns(4)
idx = 0
if sample_urls.strip():
    for url in [u.strip() for u in sample_urls.splitlines() if u.strip()]:
        image_cols[idx % 4].image(url, use_container_width=True, caption="参考画像（URL）")
        idx += 1
if uploaded_files:
    for f in uploaded_files:
        image_cols[idx % 4].image(f, use_container_width=True, caption=f.name)
        idx += 1

st.divider()

# -----------------------------
# 専門家の選択（ラジオ）
expert_options = {
    "手軽な夕飯の専門家": "A",
    "作り置きの専門家": "B",
}
expert_choice = st.radio(
    "LLMの専門家モードを選択してください",
    options=list(expert_options.keys()),
    horizontal=True,
)


# -----------------------------
# 入力フォーム
# -----------------------------
user_text = st.text_area(
    "条件を入力（例：鶏むね肉・5〜10分・洗い物少なめ・和風・電子レンジ可 など）",
    height=120,
    placeholder="冷蔵庫に『豆腐、トマト、卵、キャベツ』があります。10分以内で、後片付けが楽な一品が知りたいです。",
)

run = st.button("提案してもらう", type="primary")

# -----------------------------
# LLM呼び出し用 関数
# 制約条件：「入力テキスト」と「ラジオボタンでの選択値」を引数に取り、回答文字列を返す
# -----------------------------
def ask_llm(input_text: str, expert: str, model: str, api_key: str) -> str:
    """
    input_text: ユーザー入力テキスト
    expert: "A" または "B"（UIの選択値に応じて内部で A/B を判定して渡す）
    model: 使用するモデル名
    api_key: OpenAI API Key
    return: 生成テキスト
    """
    if not api_key:
        raise RuntimeError("OpenAI API Key が設定されていません。サイドバーで設定してください。")

    # 専門家モードごとのシステムメッセージ
    if expert == "A":
        system_prompt = (
            "あなたは『手軽に作れる夕飯の一品』に精通した一流の家庭料理アドバイザーです。"
            "対象は一人暮らしの女性。短時間・少ない洗い物・手に入りやすい食材・フライパン/電子レンジ中心。"
            "分量は1人前を基本。"
            "以下のフォーマットで提案してください：\n"
            "1) メニュー名（和名＋ひと言の魅力）\n"
            "2) 所要時間（目安）\n"
            "3) 材料（分量・代替案）\n"
            "4) 手順（最大5ステップ、後片付け簡単のコツも）\n"
            "5) アレンジ/味変（2案）\n"
            "6) 栄養・疲労回復ポイント（簡潔に）\n"
            "7) もっと手早くする小ワザ（下ごしらえ/レンジ活用など）\n"
            "※ 可能なら同系統の代替メニューを2つ、1行ずつ提案の最後に列挙"
        )
    else:
        system_prompt = (
            "あなたは『作り置きメニュー』に精通した一流の家庭料理アドバイザーです。"
            "対象は一人暮らしの女性。週の前半で仕込み、3〜4日楽しめる献立を重視。"
            "衛生管理・保存容器・冷蔵/冷凍・再加熱の注意も必ず。分量は2〜3食分を目安。"
            "以下のフォーマットで提案してください：\n"
            "1) メニュー名（保存性のポイント）\n"
            "2) 仕込み時間 / 作業の並行手順\n"
            "3) 材料（分量・コスト配慮・買い置きしやすさ）\n"
            "4) 作り方（最大6ステップ、同時進行の指示歓迎）\n"
            "5) 保存方法（容器・温度・日持ち目安・再加熱方法）\n"
            "6) 食べ切りアレンジ（丼・パスタ・スープ化など3案）\n"
            "7) 栄養バランスと衛生チェックリスト\n"
            "※ 最後に、同テーマの作り置き候補を2つ、1行ずつ"
        )

    llm = ChatOpenAI(
        model=model,
        temperature=0.6,
        api_key=api_key,
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=input_text),
    ]

    resp = llm.invoke(messages)
    return resp.content

# -----------------------------
if run:
    st.divider()
    if not user_text.strip():
        st.error("条件を入力してください。")
    else:
        expert_key = expert_options.get(expert_choice, "A")
        try:
            with st.spinner("提案を作成中…"):
                answer = ask_llm(user_text, expert_key, model_name, api_key)
            st.write(answer)
        except Exception as e:
            import traceback
            st.error(f"エラーが発生しました：{e}")
            st.expander("開発者向け詳細ログ").code(traceback.format_exc())

# -----------------------------
# 補助：クイック入力例
# -----------------------------
with st.expander("✍️ クイック入力例（コピペ用）"):
    st.code(
        "鶏むね肉・ブロッコリー・卵がある。10分以内、フライパン1つ、和風味で。"
        "\n—洗い物を減らすコツも知りたい。", language="text"
    )
    st.code(
        "週のはじめに作り置き2〜3品。野菜たっぷり、電子レンジ活用で。"
        "\n—3〜4日もつレシピと再加熱のポイントを。", language="text"
    )

# langchain-openaiのインストール
if "langchain-openai" not in sys.modules:
    st.warning("必要なパッケージがインストールされていません。以下のコマンドを実行してください：\n`pip install langchain-openai`")
