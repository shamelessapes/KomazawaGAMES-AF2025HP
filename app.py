# ==================== app.py (safe order, NameError対策版) ====================
import os
import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import qrcode
import streamlit as st
from sqlalchemy import create_engine, text

# ---- 1) ページ設定（最初に） ----
st.set_page_config(page_title="駒澤GAMES:AF2025特設サイト", page_icon="🎮", layout="centered")

# ---- 2) DB_URL を最初に読む（ここより前で DB_URL に触らない）----
try:
    DB_URL = st.secrets["DATABASE_URL"]              # Cloud推奨
except Exception:
    DB_URL = os.environ.get("DATABASE_URL", None)    # ローカルfallback

# デバッグ表示（必要ならコメントアウト可）
st.write("Has secrets:", bool(getattr(st, "secrets", None)))
st.write("Keys in secrets:", list(getattr(st, "secrets", {} ).keys()))
st.write("DB_URL starts with:", (DB_URL[:30] + "...") if DB_URL else "None")

# ---- 3) 定数＆データ（ここから下は未定義参照が起きない順で宣言）----
SITE_TITLE = "🎮 駒澤GAMES：AF2025特設サイト"
FEEDBACK_FORM_URL = "https://example.com/your-google-form"
HOST_PORT = "8501"

# ゲーム一覧
GAMES = [
    {"id": "stg1",   "title": "『巫女さん、はじめてのおつかい(体験版)』", "genre": "弾幕STG",   "time": "10~15分",
     "desc": "東方風の弾幕STGプロトタイプ。スコアでエンディング分岐あり。", "download": "https://example.com/download/stg.zip"},
    {"id": "baka1",  "title": "『逃げろ！』", "genre": "バカゲー", "time": "10分",
     "desc": "人生の嫌なことから全力で逃げ続けるゲーム。", "download": "https://example.com/download/dialogue.zip"},
    {"id": "action1","title": "『勇魔紀行』", "genre": "アクション", "time": "10~15分",
     "desc": "シンプル操作のアクション。", "download": "https://example.com/download/karakasa.zip"},
    {"id": "rythm1", "title": "『皆勤Beats!』", "genre": "リズムゲー", "time": "3分",
     "desc": "説明文", "download": "https://example.com/download/dialogue.zip"},
    {"id": "block",  "title": "『渡邊ブロック崩し』", "genre": "ブロック崩し", "time": "3分",
     "desc": "説明文", "download": "https://example.com/download/dialogue.zip"},
    {"id": "rpg1",   "title": "『TerreBleue』", "genre": "RPG", "time": "2~3時間(本編)",
     "desc": "“世界一青い”RPG。", "download": "https://example.com/download/dialogue.zip"},
    {"id": "rpg2",   "title": "『Sentence』", "genre": "RPG", "time": "5~10分",
     "desc": "日常の裏に潜む陰謀を暴け。", "download": "https://example.com/download/dialogue.zip"},
    {"id": "rpg3",   "title": "『平和の祭典』", "genre": "RPG", "time": "3分",
     "desc": "説明文", "download": "https://example.com/download/dialogue.zip"},
    {"id": "rpg4",   "title": "『Post-Humannica』", "genre": "RPG", "time": "3分",
     "desc": "説明文", "download": "https://example.com/download/dialogue.zip"},
]
ID_TO_TITLE = {g["id"]: g["title"] for g in GAMES}

# ---- 4) パス系（先に全部作る）----
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
TOP_IMAGE_PATH = ASSETS_DIR / "AF2025_poster_mini.PNG"
MAP_IMAGE_PATH = ASSETS_DIR / "map_placeholder.png"
IMG_DIR = ASSETS_DIR / "game_images"    # 例: assets/game_images/stg1.png

# ---- 5) DBエンジン作成（失敗してもアプリは落とさない）----
ENGINE = None
if DB_URL:
    try:
        ENGINE = create_engine(
            DB_URL,
            pool_pre_ping=True,
            connect_args={"sslmode": "require", "connect_timeout": 10},
        )
        # 疎通テスト
        with ENGINE.begin() as conn:
            conn.exec_driver_sql("SELECT 1")

        # 初回のみテーブル用意
        with ENGINE.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id BIGSERIAL PRIMARY KEY,
                    game_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
        st.caption("✅ DB接続OK")
    except Exception as e:
        st.error("❌ DB接続に失敗しました（DATABASE_URL / psycopg2 / SSL / port等を確認）。")
        st.exception(e)
else:
    st.warning("（開発モード）DATABASE_URL が未設定のため、DB機能は無効です。")

# ---- 6) ページ状態（radioキーと分離）----
PAGES = ["トップ", "ゲーム一覧", "教場MAP", "整理券発行", "アンケート・フィードバック"]
if "page" not in st.session_state:
    st.session_state.page = "トップ"
if "page_select" not in st.session_state:
    st.session_state.page_select = st.session_state.page
if "jump_to" in st.session_state:
    t = st.session_state.jump_to
    st.session_state.page = t
    st.session_state.page_select = t
    del st.session_state["jump_to"]

def _on_sidebar_change():
    st.session_state.page = st.session_state.page_select

st.sidebar.header("ページ")
st.sidebar.radio("ページ", PAGES, key="page_select", on_change=_on_sidebar_change)
page = st.session_state.page

# ---- 7) ヘッダ ----
st.title(SITE_TITLE)
st.info("##### **駒澤GAMESオータムフェスティバル2025特設サイト**へようこそ！"
        "\nこのサイトでは **整理券の発行** や **展示作品の紹介** が見られます。")
st.divider()

# ---- 8) ページ本体 ----
if page == "トップ":
    if TOP_IMAGE_PATH.exists():
        st.image(str(TOP_IMAGE_PATH))
    else:
        st.warning(f"ポスター画像が見つかりません: {TOP_IMAGE_PATH}")
        if ASSETS_DIR.exists():
            st.write("assets 内ファイル:", sorted(os.listdir(ASSETS_DIR)))
        else:
            st.error("assets フォルダがありません。リポジトリに追加してください。")

    st.markdown("1. まずは遊びたいゲームを選びましょう。")
    if st.button("🎮 展示作品一覧を見る"):
        st.session_state.jump_to = "ゲーム一覧"; st.rerun()

    st.markdown("2. 注意事項に同意して **このサイトから整理券を発行** します。")
    if st.button("🎫 整理券を発行する"):
        st.session_state.jump_to = "整理券発行"; st.rerun()

    st.markdown("3. 順番が来たら、**係の者に整理券を提示** してください。")
    st.markdown("4. 体験後はぜひ **アンケート** にご協力を！")

elif page == "ゲーム一覧":
    st.subheader("ブースで遊べるゲーム一覧")
    st.info("DLリンクから自宅でも遊べます！")

    # 1ゲーム=1ブロック（画像→説明）
    for g in GAMES:
        with st.container():
            st.markdown(f"### {g['title']}")

            # 画像探す（拡張子揺れ対応）
            base = g["id"]
            found = None
            for ext in [".png", ".jpg", ".jpeg", ".webp", ".PNG", ".JPG", ".JPEG", ".WEBP"]:
                p = IMG_DIR / f"{base}{ext}"
                if p.exists():
                    found = p; break
            if found:
                st.image(str(found), use_column_width=True)
            else:
                st.caption(f"（画像が見つかりません: {IMG_DIR / (base + '.png')}）")
                # 初回だけ中身一覧を出す
                if st.session_state.get("_img_list_shown") is None:
                    st.session_state["_img_list_shown"] = True
                    if IMG_DIR.exists():
                        st.write("assets/game_images 内:", sorted(os.listdir(IMG_DIR)))
                    else:
                        st.error("assets/game_images フォルダがありません。")

            st.write(f"**ジャンル**: {g.get('genre','—')} ｜ **体験時間**: {g.get('time','—')}")
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
    st.info("""- 精密機器につき、**ゲーム以外のPC操作はスタッフが行います**
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
                try:
                    with ENGINE.begin() as conn:
                        conn.execute(text("INSERT INTO tickets (game_id) VALUES (:gid)"),
                                     {"gid": game_options[selected_title]})
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

st.write("")
st.caption("© 2025 KomazawaGames ")
# ==================== end ====================
