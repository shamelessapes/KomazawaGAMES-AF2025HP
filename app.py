
import os
import io
import time
from datetime import datetime
import pandas as pd
import qrcode
import streamlit as st
from sqlalchemy import create_engine, text

SITE_TITLE = "🎮 駒澤GAMES：AF2025特設サイト"
FEEDBACK_FORM_URL = "https://example.com/your-google-form"
HOST_PORT = "8501"

GAMES = [
    {
        "id": "stg1",
        "title": "『巫女さん、はじめてのおつかい(体験版)』",
        "genre": "弾幕STG",
        "time": "5分",
        "desc": "東方風の弾幕STGプロトタイプ。5分体験版。",
        "download": "https://example.com/download/stg.zip"
    },
    {
        "id": "baka1",
        "title": "『逃げろ！』",
        "genre": "バカゲー",
        "time": "3分",
        "desc": "ここに説明文",
        "download": "https://example.com/download/dialogue.zip"
    },
    {
        "id": "action1",
        "title": "『勇魔紀行』",
        "genre": "アクション",
        "time": "10分",
        "desc": "ここに説明文",
        "download": "https://example.com/download/karakasa.zip"
    },
        {
        "id": "rythm1",
        "title": "『皆勤Beats!』",
        "genre": "リズムゲー",
        "time": "3分",
        "desc": "ここに説明文",
        "download": "https://example.com/download/dialogue.zip"
    },
    {
        "id": "block",
        "title": "『渡邊ブロック崩し』",
        "genre": "ブロック崩し",
        "time": "3分",
        "desc": "ここに説明文",
        "download": "https://example.com/download/dialogue.zip"
    },
    {
        "id": "rpg1",
        "title": "『TerreBleue』",
        "genre": "RPG",
        "time": "3分",
        "desc": "ここに説明文",
        "download": "https://example.com/download/dialogue.zip"
    },
    {
        "id": "rpg2",
        "title": "『Sentence』",
        "genre": "RPG",
        "time": "3分",
        "desc": "ここに説明文",
        "download": "https://example.com/download/dialogue.zip"
    },
    {
        "id": "rpg3",
        "title": "『平和の祭典』",
        "genre": "RPG",
        "time": "3分",
        "desc": "ここに説明文",
        "download": "https://example.com/download/dialogue.zip"
    },
    {
        "id": "rpg4",
        "title": "『Post-Humannica』",
        "genre": "RPG",
        "time": "3分",
        "desc": "ここに説明文",
        "download": "https://example.com/download/dialogue.zip"
    },
]


MAP_IMAGE_PATH = "assets\map_placeholder.png"
TOP_IMAGE = "assets\AF2025_poster_mini.PNG"

# Streamlitのシークレットから読み込む想定
DB_URL = st.secrets["DATABASE_URL"] 
engine = create_engine(DB_URL, pool_pre_ping=True)

# PostgresはすでにSQLで作成済みなので、ここでテーブル作成しなくてOK
# （入れるならDDLをPostgres方言に合わせる）

if TOP_IMAGE.exists():
    with open(TOP_IMAGE, "rb") as f:
        st.image(f.read())  # 生バイトで読み込み
else:
    st.warning(f"ポスター画像が見つかりません: {TOP_IMAGE}")
    if ASSETS_DIR.exists():
        st.write("assets 内にあるファイル一覧:")
        st.write(sorted(os.listdir(ASSETS_DIR)))
    else:
        st.error("assets フォルダが見つかりません。リポジトリに含めてコミットしてください。")

st.set_page_config(page_title="特設サイト", page_icon="🎮", layout="centered")
if "page" not in st.session_state:
    st.session_state.page = "トップ"

# ---- set_page_config の直後あたり ----
PAGES = ["トップ", "ゲーム一覧", "教場MAP", "整理券発行", "アンケート・フィードバック"]

# 初期化（最初の1回だけ）
if "page" not in st.session_state:
    st.session_state.page = "トップ"
if "page_select" not in st.session_state:
    st.session_state.page_select = st.session_state.page

# ★ ボタンからのジャンプ要求があれば、radio を作る前に反映
if "jump_to" in st.session_state:
    target = st.session_state.jump_to
    st.session_state.page = target
    st.session_state.page_select = target
    del st.session_state["jump_to"]

# サイドバー radio（← index を渡さないのがポイント！）
def _on_sidebar_change():
    st.session_state.page = st.session_state.page_select

st.sidebar.header("ページ")
st.sidebar.radio(
    "ページ",
    PAGES,
    key="page_select",
    on_change=_on_sidebar_change
)

page = st.session_state.page





st.title(SITE_TITLE)
st.info("##### **駒澤GAMESオータムフェスティバル2025特設サイト**へようこそ！ \
           \nこのサイトではゲーム体験に必要な**整理券の発行**や、**体験できるゲームの紹介**を見ることができます。")
st.divider()

def get_ip_candidates():
    return [f"http://localhost:{HOST_PORT}"]

def make_qr(url: str) -> bytes:
    img = qrcode.make(url)
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

if page == "トップ":
    st.image(TOP_IMAGE)
    st.info("### :star:展示内容:star:")

    # 説明①
    st.markdown("1. まずは遊びたいゲームを選びましょう。")
    # 👉 押したら「ゲーム一覧」に即ジャンプ
    if st.button("🎮 展示作品一覧を見る"):
        st.session_state.jump_to = "ゲーム一覧"
        st.rerun()  # 即リランして、次の冒頭でジャンプが実行される                                    # 即反映

    # 説明②
    st.markdown("2. 遊びたいゲームが決まったら、**このサイトから整理券を発行します。**")
    # 👉 押したら「整理券＆ランキング」に即ジャンプ
    if st.button("🎫 整理券を発行する"):
        st.session_state.jump_to = "整理券発行"
        st.rerun()

    # 説明③以降
    st.markdown("""
    3. 順番が来たら、**係の者に整理券をお見せください。** ご案内いたします。  
    4. 体験が終わったら、ぜひ**アンケートに**ご協力お願いします！  
    5. 別のゲームを遊びたい場合は、またサイトから整理券を発行することができます。
    """)


    st.divider()
    st.info("### ブースの場所")
    #st.image(BOOTH_SITE)
    st.caption("場所は駒沢キャンパス三号館の905教場です。\
               \n9階にあってちょっと大変ですが、ぜひ遊びに来てくださいね！")
    st.divider()
    st.info("### About Us")
    st.write(":globe_with_meridians:**公式HP**：https://tide-island-e1b.notion.site/komazawa-games?pvs=74 \
             \n:bird:**Twiitter：**@multicreaters \
             \n:camera:**Instagram：**@multicreaters ")
    st.divider()


elif page == "ゲーム一覧":
    st.subheader("ブースで遊べるゲーム一覧")
    st.info("DLリンクからゲームをダウンロードして、自宅でも続きを遊べます！")
    for g in GAMES:
        with st.container(border=True):
            st.markdown(f"### {g['title']}")
            st.write(f"**ジャンル**: {g['genre']}　｜　**体験時間**: {g['time']}")
            st.write(g["desc"])
            st.write(f"[⬇ ダウンロード]({g['download']})")


elif page == "教場MAP":
    st.subheader("教場MAP")
    if os.path.exists(MAP_IMAGE_PATH):
        st.image(MAP_IMAGE_PATH, caption="会場配置図（差し替え可）", use_column_width=True)
    else:
        st.warning("MAP画像が見つかりません。assets/map_placeholder.png を差し替えてください。")



elif page == "整理券発行":
    st.subheader("ゲーム体験における注意")
    st.info("""- 精密機器のため、**ゲーム以外のPCの操作はスタッフが行います**
- キーボード・マウス・配線に **無断で触れないでください**
- 飲食物はPC周辺に置かないでください
- **スタッフ不在時は体験を停止** します
- 指示に従っていただけない場合、体験をお断りすることがあります
    """ )

    agreed = st.checkbox("注意事項に同意して整理券を発行する。")

    if agreed:
        st.success("ご協力ありがとうございます！整理券を発行できます。")

        st.divider()
        st.subheader("🎫 整理券発行")

        # ゲーム一覧から選択
        game_options = {g["title"]: g["id"] for g in GAMES}
        selected_title = st.selectbox("体験するゲームを選んでください", list(game_options.keys()))

        if st.button("整理券を発行する"):
            game_id = game_options[selected_title]
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO tickets (game_id, created_at) VALUES (:gid, :ts)"),
                    {"gid": game_id, "ts": datetime.utcnow().isoformat()}
                )
            st.success(f"『{selected_title}』の整理券を発行しました！")
            st.caption("※ 受付でゲーム名をお伝えください。順番にご案内します。")

        st.divider()
        st.subheader("人気ランキング（リアルタイム）")
        with engine.begin() as conn:
            df = pd.read_sql(
                "SELECT game_id, COUNT(*) AS votes FROM tickets GROUP BY game_id ORDER BY votes DESC",
                conn
            )
        if df.empty:
            st.write("まだ票がありません。最初の整理券を発行してみましょう！")
        else:
            id_to_title = {g["id"]: g["title"] for g in GAMES}
            df["title"] = df["game_id"].map(id_to_title)
            df = df[["title", "votes"]]
            st.dataframe(df, use_container_width=True)
            st.bar_chart(df.set_index("title"))


elif page == "アンケート・フィードバック":
    st.subheader("アンケートのお願い")
    st.write("以下のボタンからアンケートフォームに移動できます。ご意見・ご感想をぜひお寄せください！")
    st.link_button("アンケートに回答する", FEEDBACK_FORM_URL, use_container_width=True)
    st.divider()
    st.subheader("簡易フィードバック（任意）")
    name = st.text_input("ニックネーム（任意）")
    game_titles = [g["title"] for g in GAMES]
    played = st.multiselect("遊んだ作品（複数可）", options=game_titles)
    comment = st.text_area("感想・改善点など（任意）")
    if st.button("送信（ローカル保存）"):
        os.makedirs("feedback", exist_ok=True)
        line = f"{datetime.utcnow().isoformat()}\t{name}\t{';'.join(played)}\t{comment.replace(os.linesep, ' ')}\n"
        with open("feedback/feedback.tsv", "a", encoding="utf-8") as f:
            f.write(line)
        st.success("ありがとうございます！フィードバックを保存しました。")
    st.caption("※ 本フォームはローカル保存です。正式な集計には Googleフォームをご利用ください。")

st.write("")
st.caption("© 2025 KomazawaGames ")
