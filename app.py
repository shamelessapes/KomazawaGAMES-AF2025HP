# ==================== app.py（完全版・置き換えOK） ====================
import os
import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import qrcode
import streamlit as st
from sqlalchemy import create_engine, text

import os
DB_URL = None
try:
    DB_URL = st.secrets["DATABASE_URL"]
except Exception:
    DB_URL = os.environ.get("DATABASE_URL")

if not DB_URL:
    st.error("DATABASE_URL が見つかりません。`.streamlit/secrets.toml` か環境変数に設定してください。")
    st.stop()



# ---- 1) 最初に page_config（他の st.* より先） ----
st.set_page_config(page_title="駒澤GAMES:AF2025特設サイト", page_icon="🎮", layout="centered")

# ---- 2) 定数・データ ----
SITE_TITLE = "🎮 駒澤GAMES：AF2025特設サイト"
FEEDBACK_FORM_URL = "https://example.com/your-google-form"  # 必要なら Secrets に移してもOK
HOST_PORT = "8501"

# ゲーム一覧
GAMES = [
    {"id": "stg1",   "title": "『巫女さん、はじめてのおつかい(体験版)』", "genre": "弾幕STG",   "time": "10~15分", "desc": "ある日、女子高生の桜と明音はある「おつかい」を頼まれる。\
           \nなんとそれは、町中で暴走する妖怪たちを退治し、その原因を突き止めて欲しいというもので__!?\
           \n獲得したスコアに応じてエンディングが変わるぞ。目指せ、報酬100万円!!", "download": "https://example.com/download/stg.zip"},
    {"id": "baka1",  "title": "『逃げろ！』",                           "genre": "バカゲー",   "time": "10分", "desc": "宿題、勉強、受験・・・。世の中には思わず逃げ出したくなっちゃうような嫌なことがたくさん！\
            \nこのゲームは、そんな人生の嫌なことからひたすら逃げ続けるゲームです。\
            \n**全てから逃げ続けた先に待ち受けるものとは一体……!?****", "download": "https://example.com/download/dialogue.zip"},
    {"id": "action1","title": "『勇魔紀行』",                           "genre": "アクション", "time": "10~15分","desc": "簡単操作の昔懐かしアクション！！\
            \nやることはただ一つ、ひたすら相手を倒せ!!\
            \n全てを倒した先にあなたを待っているのは……!?",                          "download": "https://example.com/download/karakasa.zip"},
    {"id": "rythm1", "title": "『皆勤Beats!』",                         "genre": "リズムゲー", "time": "3分", "desc": "説明文",                          "download": "https://example.com/download/dialogue.zip"},
    {"id": "block",  "title": "『渡邊ブロック崩し』",                   "genre": "ブロック崩し","time": "3分","desc": "説明文",                          "download": "https://example.com/download/dialogue.zip"},
    {"id": "rpg1",   "title": "『TerreBleue』",                         "genre": "RPG",       "time": "フルだと2時間~3時間", "desc": "独自の世界観で繰り広げられる、”世界一青い”RPG。\
            \n国軍に入隊したことにより、2つの国を巡る争いに巻き込まれる少女たち。\
            \n彼女たちは戦争を集結させ、再び世界に平和と自然を取り戻すことはできるのか__？", "download": "https://example.com/download/dialogue.zip"},
    {"id": "rpg2",   "title": "『Sentence』",                           "genre": "RPG",       "time": "5~10分", "desc": "日常の平穏には裏がある！？町のドタバタと裏にうずめく陰謀を暴き出せ！\
            \nそしてその裏にある衝撃の真実とは…？恋愛あり、推理あり、沢山の体験を実装予定！！！\
            \n（本体験版は恋愛推理実装してません）",                          "download": "https://example.com/download/dialogue.zip"},
    {"id": "rpg3",   "title": "『平和の祭典』",                         "genre": "RPG",       "time": "3分", "desc": "説明文",                          "download": "https://example.com/download/dialogue.zip"},
    {"id": "rpg4",   "title": "『Post-Humannica』",                     "genre": "RPG",       "time": "3分", "desc": "説明文",                          "download": "https://example.com/download/dialogue.zip"},
]
ID_TO_TITLE = {g["id"]: g["title"] for g in GAMES}
TITLE_TO_ID = {g["title"]: g["id"] for g in GAMES}

# ---- 3) パス系----
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
MAP_IMAGE_PATH = ASSETS_DIR / "map_placeholder.png"
TOP_IMAGE_PATH = ASSETS_DIR / "AF2025_poster_mini.PNG"  # ← GitHub上の実ファイル名に完全一致

from pathlib import Path
IMG_DIR = Path(__file__).parent / "assets" / "game_images"  # ← 実フォルダ名に合わせた


# ---- 4) DB 接続（Secrets から・IPv4 強制）----
# ---- 4) DB 接続（Supabase Pooler / Session 6543, SSL 必須）----
ENGINE = None
try:
    DB_URL = st.secrets["DATABASE_URL"]  # 例: postgresql+psycopg2://...@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require

    # ✅ hostaddr は使わない（PoolerはIPv4で到達できる）
    ENGINE = create_engine(
        DB_URL,
        pool_pre_ping=True,
        connect_args={
            "sslmode": "require",
            "connect_timeout": 10,
        },
    )

    # 疎通テスト
    with ENGINE.begin() as conn:
        conn.exec_driver_sql("SELECT 1")

    # （初回だけ）なければ tickets テーブル作成
    with ENGINE.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tickets (
                id BIGSERIAL PRIMARY KEY,
                game_id TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """))
    st.caption("✅ DB接続OK")
except KeyError:
    st.warning("（開発向け）Secrets の DATABASE_URL が未設定です。DBを使わず閲覧のみで動作します。")
except Exception as e:
    st.error("❌ DB接続に失敗しました。DATABASE_URL（#→%23、?sslmode=require、port=6543）を確認してください。")
    st.exception(e)


# ---- 5) ページ状態（radioのキーと分離）----
PAGES = ["トップ", "ゲーム一覧", "教場MAP", "整理券発行", "アンケート・フィードバック"]
if "page" not in st.session_state:
    st.session_state.page = "トップ"
if "page_select" not in st.session_state:
    st.session_state.page_select = st.session_state.page
# ボタンからのジャンプ要求があれば、radio作成前に反映
if "jump_to" in st.session_state:
    target = st.session_state.jump_to
    st.session_state.page = target
    st.session_state.page_select = target
    del st.session_state["jump_to"]

def _on_sidebar_change():
    st.session_state.page = st.session_state.page_select

st.sidebar.header("ページ")
st.sidebar.radio("ページ", PAGES, key="page_select", on_change=_on_sidebar_change)
page = st.session_state.page

# ---- 6) ヘッダ ----
st.title(SITE_TITLE)
st.info("##### **駒澤GAMESオータムフェスティバル2025特設サイト**へようこそ！ \
           \nこのサイトではゲーム体験に必要な**整理券の発行**や、**体験できるゲームの紹介**を見ることができます。")
st.divider()

# ---- 7) ユーティリティ ----
def make_qr(url: str) -> bytes:
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# ---- 8) 各ページ ----
if page == "トップ":
    if TOP_IMAGE_PATH.exists():
        st.image(str(TOP_IMAGE_PATH))
    else:
        st.warning(f"ポスター画像が見つかりません: {TOP_IMAGE_PATH}")
        if ASSETS_DIR.exists():
            st.write("assets 内にあるファイル一覧:", sorted(os.listdir(ASSETS_DIR)))
        else:
            st.error("assets フォルダが見つかりません。リポジトリに含めてコミットしてください。")

    st.markdown("1. まずは遊びたいゲームを選びましょう。")
    if st.button("🎮 展示作品一覧を見る"):
        st.session_state.jump_to = "ゲーム一覧"
        st.rerun()

    st.markdown("2. 遊びたいゲームが決まったら、注意事項に同意して**このサイトから整理券を発行します。**")
    if st.button("🎫 整理券を発行する"):
        st.session_state.jump_to = "整理券発行"
        st.rerun()

    st.markdown("""
3. 順番が来たら、**係の者に整理券をお見せください。** ご案内いたします。  
4. 体験が終わったら、ぜひ**アンケートに**ご協力お願いします！  
5. 別のゲームを遊びたい場合は、またサイトから整理券を発行することができます。
""")

    st.divider()
    st.info("### ブースの場所")
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
        with st.container():
            st.markdown(f"### {g['title']}")

            # 拡張子の違いにも強くする（.png/.jpg/.jpeg/.webp を順に探索）
            base_stem = g["id"]  # 例: action1
            found = None
            for ext in [".png", ".jpg", ".jpeg", ".webp", ".PNG", ".JPG"]:
                p = IMG_DIR / f"{base_stem}{ext}"
                if p.exists():
                    found = p
                    break

            if found:
                st.image(str(found), use_column_width=True)
            else:
                st.caption(f"（画像が見つかりません: {IMG_DIR / (base_stem + '.png')}）")
                # デバッグ：一度だけ一覧を出す
                if st.session_state.get("_img_list_shown") is None:
                    st.session_state["_img_list_shown"] = True
                    if IMG_DIR.exists():
                        st.write("asset/game_image 内のファイル一覧:", sorted(os.listdir(IMG_DIR)))
                    else:
                        st.error("asset/game_image フォルダが見つかりません。")

            st.write(f"**ジャンル**: {g.get('genre','—')}　｜　**体験時間**: {g.get('time','—')}")
            st.write(g["desc"])
            st.write(f"[⬇ ダウンロード]({g['download']})")
            st.markdown("---")


elif page == "教場MAP":
    st.subheader("教場MAP")
    if MAP_IMAGE_PATH.exists():
        st.image(str(MAP_IMAGE_PATH), caption="会場配置図（差し替え可）", use_column_width=True)
    else:
        st.warning(f"MAP画像が見つかりません: {MAP_IMAGE_PATH}")

elif page == "整理券発行":
    st.subheader("ゲーム体験における注意")
    st.info("""- 精密機器のため、**ゲーム以外のPCの操作はスタッフが行います**
- キーボード・マウス・配線に **無断で触れないでください**
- 飲食物はPC周辺に置かないでください
- **スタッフ不在時は体験を停止** します
- 指示に従っていただけない場合、体験をお断りすることがあります
    """)

    agreed = st.checkbox("注意事項に同意して整理券を発行する。")

    if agreed:
        st.success("ご協力ありがとうございます！整理券を発行できます。")

        st.divider()
        st.subheader("🎫 整理券発行")

        game_options = {g["title"]: g["id"] for g in GAMES}
        selected_title = st.selectbox("体験するゲームを選んでください", list(game_options.keys()))

        if ENGINE is None:
            st.warning("（現在DBに接続できていないため、整理券の発行は無効です）")
        else:
            if st.button("整理券を発行する"):
                game_id = game_options[selected_title]
                try:
                    with ENGINE.begin() as conn:
                        # created_at は DB 側の DEFAULT NOW() に任せる
                        conn.execute(text("INSERT INTO tickets (game_id) VALUES (:gid)"), {"gid": game_id})
                    st.success(f"『{selected_title}』の整理券を発行しました！")
                    st.caption("※ 受付でゲーム名をお伝えください。順番にご案内します。")
                except Exception as e:
                    st.error("整理券の発行に失敗しました（DB接続や権限を確認してください）。")
                    st.exception(e)

        st.divider()
        st.subheader("人気ランキング（リアルタイム）")
        if ENGINE is None:
            st.warning("（現在DBに接続できていないため、ランキングは表示できません）")
        else:
            try:
                with ENGINE.begin() as conn:
                    df = pd.read_sql(
                        "SELECT game_id, COUNT(*) AS votes FROM tickets GROUP BY game_id ORDER BY votes DESC",
                        conn
                    )
                if df.empty:
                    st.write("まだ票がありません。最初の整理券を発行してみましょう！")
                else:
                    df["title"] = df["game_id"].map(ID_TO_TITLE)
                    df = df[["title", "votes"]]
                    st.dataframe(df, use_container_width=True)
                    st.bar_chart(df.set_index("title"))
            except Exception as e:
                st.error("ランキングの取得に失敗しました。")
                st.exception(e)

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
# ==================== ここまで ====================
