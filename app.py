# ==================== app.py (safe order, NameError対策・Bcc対応) ====================
import os
import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import qrcode
import streamlit as st
from sqlalchemy import create_engine, text

import smtplib
import mimetypes
from email.message import EmailMessage

# ---- 1) ページ設定（最初に） ----
st.set_page_config(page_title="駒澤GAMES:AF2025特設サイト", page_icon="🎮", layout="centered")

# ---- 2) DB_URL を最初に読む（ここより前で DB_URL に触らない）----
try:
    DB_URL = st.secrets["DATABASE_URL"]              # Cloud推奨
except Exception:
    DB_URL = os.environ.get("DATABASE_URL", None)    # ローカルfallback

# （必要ならデバッグ表示。不要ならコメントアウト）
# st.write("Has secrets:", bool(getattr(st, "secrets", None)))
# st.write("Keys in secrets:", list(getattr(st, "secrets", {} ).keys()))
# st.write("DB_URL starts with:", (DB_URL[:30] + "...") if DB_URL else "None")

# ---- 3) 定数＆データ ----
SITE_TITLE = "🎮 駒澤GAMES：AF2025特設サイト"
FEEDBACK_FORM_URL = "https://example.com/your-google-form"
HOST_PORT = "8501"

# ゲーム一覧
GAMES = [
    {"id": "stg1",   "title": "『巫女さん、はじめてのおつかい(体験版)』", "genre": "弾幕STG",   "time": "10~15分",
     "desc": "東方風の弾幕STG。女子高生の桜と明音は、ある日奇妙な「おつかい」を引き受けることに。 "
             "スコアに応じてエンディングが変化するぞ！"},
    {"id": "baka1",  "title": "『逃げろ！』", "genre": "バカゲー", "time": "10分",
     "desc": "人生の嫌なことから全力で逃げ続けるゲーム。全てから逃げ続けた先に待ち受けているものとは…！？"},
    {"id": "action1","title": "『勇魔紀行』", "genre": "アクション", "time": "10~15分",
     "desc": "簡単操作の昔懐かしアクション！！やることはただ一つ、ひたすら相手を倒せ！！！"},
    {"id": "rythm1", "title": "『皆勤Beats!』", "genre": "リズムゲー", "time": "3分",
     "desc": "爽快リズム×ノベルの合体！個性豊かなヒロインたちと過ごす青春の物語。"},
    {"id": "block1", "title": "『ブロック崩し』", "genre": "ブロック崩し", "time": "3分",
     "desc": "サクッと遊べるシンプルなブロック崩し。"},
    {"id": "rpg1",   "title": "『TerreBleue』", "genre": "RPG", "time": "2~3時間(本編)",
     "desc": "”世界一青い”RPG。二国の争いに巻き込まれた少女たちは、世界に平和を取り戻せるのか。"},
    {"id": "rpg2",   "title": "『Sentence』", "genre": "RPG", "time": "5~10分",
     "desc": "日常の裏に潜む陰謀を暴け。恋愛・推理要素を順次実装予定。"},
    {"id": "rpg3",   "title": "『平和の祭典』※試遊不可", "genre": "RPG", "time": "-",
     "desc": "戦後の平和を祝う祭典。※AFでの試遊はありません。"},
    {"id": "rpg4",   "title": "『Post-Humannica』", "genre": "RPG", "time": "3分",
     "desc": "戦争から50年。便利屋を営む姉弟が手にしたのは、太古に封じられた力だった。\
        \n火を巡る争いの果てに、彼女たちは何を選択するのか。"},
]
ID_TO_TITLE = {g["id"]: g["title"] for g in GAMES}

# ---- 4) パス系 ----
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
TOP_IMAGE_PATH = ASSETS_DIR / "AF2025_poster_mini.PNG"
MAP_IMAGE_PATH = ASSETS_DIR / "map_placeholder.png"
MAP_PATH = ASSETS_DIR / "kyouzyou.PNG"
IMG_DIR = ASSETS_DIR / "game_images"    # 例: assets/game_images/stg1.png

# ---- 5) メール送信ユーティリティ（Bcc=主催者）----
def send_mail_with_inline_image(
    to_email: str,
    subject: str,
    html_body: str,
    inline_image_path: str | None = None,
    cid: str = "gameimg"
):
    """HTMLメールを送信。inline_image_path を Content-ID で埋め込み表示。Bccで主催者にも同報。"""
    host = st.secrets.get("SMTP_HOST")
    port = int(st.secrets.get("SMTP_PORT", 587))
    user = st.secrets.get("SMTP_USER")
    pwd  = st.secrets.get("SMTP_PASS")
    from_addr = st.secrets.get("SMTP_FROM", user)
    organizer = st.secrets.get("ORGANIZER_EMAIL")  # ← 主催者控え

    if not (host and port and user and pwd and from_addr):
        raise RuntimeError("SMTP secrets が足りません（SMTP_HOST/PORT/USER/PASS/SMTP_FROM）")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    if organizer:
        msg["Bcc"] = organizer
    # プレーン＋HTML
    msg.set_content("HTMLメール対応のクライアントでご確認ください。")
    msg.add_alternative(html_body, subtype="html")

    # 画像を Content-ID で本文内に埋め込み
    if inline_image_path:
        ctype, _ = mimetypes.guess_type(str(inline_image_path))
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        with open(inline_image_path, "rb") as f:
            img_bytes = f.read()
        # HTMLパート(=payload[1])に関連付け
        msg.get_payload()[1].add_related(img_bytes, maintype=maintype, subtype=subtype, cid=f"<{cid}>")

    # 送信(TLS)
    with smtplib.SMTP(host, port, timeout=20) as server:
        server.ehlo()
        server.starttls()
        server.login(user, pwd)
        server.send_message(msg)

# ---- 6) DBエンジン作成（失敗してもアプリは落とさない）----
ENGINE = None
if DB_URL:
    try:
        ENGINE = create_engine(
            DB_URL,
            pool_pre_ping=True,
            connect_args={
                "sslmode": "require",     # Supabase等は基本これ必須
                "connect_timeout": 10,    # タイムアウト短め
            },
        )

        # 疎通テスト
        with ENGINE.begin() as conn:
            conn.exec_driver_sql("SELECT 1")

        # --- テーブル初期化／マイグレーション ---
        with ENGINE.begin() as conn:
            # 1) あれば何もしない最新スキーマ
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id BIGSERIAL PRIMARY KEY,
                    game_id TEXT NOT NULL,
                    email TEXT,
                    ticket_no TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """))
            # 2) 念のため列を補完（既存環境向け）
            conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS email TEXT"))
            conn.execute(text("ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ticket_no TEXT"))
            # 3) 一意制約（重複防止）
            conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_tickets_ticket_no
                ON tickets(ticket_no)
            """))

        #st.caption("✅ DB接続OK")
    except Exception as e:
        ENGINE = None  # 失敗時でも閲覧は継続
        st.error("❌ DB接続に失敗しました。DATABASE_URL（#→%23、?sslmode=require、port=6543 など）を確認してください。")
        st.exception(e)
else:
    st.warning("⚠️ DATABASE_URL が未設定です。`.streamlit/secrets.toml` か環境変数に設定してください。")

# ---- 7) ページ状態（radioキーと分離）----
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

#with st.sidebar.expander("📧 メール送信テスト"):
    #test_to = st.text_input("テスト宛先メール", value=st.secrets.get("ORGANIZER_EMAIL", ""))
    #if st.button("SMTPテスト送信"):
        #try:
            #html = "<h3>SMTP疎通テスト</h3><p>このメールが届けばSMTP設定OK！</p>"
            #send_mail_with_inline_image(test_to, "【テスト】SMTP設定確認", html, None)
            #st.success("テスト送信OK！受信を確認してください。")
        #except Exception as e:
            #st.error("テスト送信に失敗。secretsの値・ポート・プロバイダ設定を確認してください。")
            #st.exception(e)

# ---- 8) ヘッダ ----
st.title(SITE_TITLE)
st.info("##### こんにちは！大学公認のゲーム制作サークル、**駒澤GAMES**です。"
        "\nこのサイトでは **整理券の発行** や **我々が作ったゲームの紹介** を閲覧できます。")
st.divider()

# ---- 9) ページ本体 ----
if page == "トップ":
    st.write("#### 今だけ！ゲームを３種類以上遊ぶとポストカードが貰える！")
    if TOP_IMAGE_PATH.exists():
        st.image(str(TOP_IMAGE_PATH))
    else:
        st.warning(f"ポスター画像が見つかりません: {TOP_IMAGE_PATH}")
        if ASSETS_DIR.exists():
            st.write("assets 内ファイル:", sorted(os.listdir(ASSETS_DIR)))
        else:
            st.error("assets フォルダがありません。リポジトリに追加してください。")

    st.markdown("1. まずは遊びたいゲームを選びましょう。")
    if st.button("🎮 ゲーム一覧を見る"):
        st.session_state.jump_to = "ゲーム一覧"; st.rerun()

    st.markdown("2. 注意事項に同意して **このサイトから整理券を発行** します。")
    if st.button("🎫 整理券を発行する"):
        st.session_state.jump_to = "整理券発行"; st.rerun()

    st.markdown("3. 順番が来たら、**係の者に整理券を提示** してください。")
    st.markdown("4. 体験後はぜひ **アンケート** にご協力を！")
    if MAP_PATH.exists():
        st.image(str(MAP_PATH))
    else:
        st.warning(f"ポスター画像が見つかりません: {MAP_PATH}")
        if ASSETS_DIR.exists():
            st.write("assets 内ファイル:", sorted(os.listdir(MAP_PATH)))
        else:
            st.error("assets フォルダがありません。リポジトリに追加してください。")
    st.caption("教場は３号館９０８教場です！\
               \n９階まで是非遊びに来てください！")

elif page == "ゲーム一覧":
    st.subheader("ブースで遊べるゲーム一覧")
    st.info("教場の後ろの展示スペースでもゲームに関する資料・イラストの展示を行っています！")

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
                if st.session_state.get("_img_list_shown") is None:
                    st.session_state["_img_list_shown"] = True
                    if IMG_DIR.exists():
                        st.write("assets/game_images 内:", sorted(os.listdir(IMG_DIR)))
                    else:
                        st.error("assets/game_images フォルダがありません。")

            st.write(f"**ジャンル**: {g.get('genre','—')} ｜ **体験時間**: {g.get('time','—')}")
            st.write(g["desc"])
            st.markdown("---")

elif page == "教場MAP":
    st.subheader("教場MAP")
    st.info("くつろぎor休憩目的での使用も大歓迎です。\
            \n**ゆっくりしていってね！**")
    if MAP_IMAGE_PATH.exists():
        st.image(str(MAP_IMAGE_PATH), caption="駒澤大学３号館９０８教場", use_column_width=True)
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
    email = st.text_input("整理券送付先メールアドレス（必須）")
    valid_email = ("@" in email and "." in email)

    if agreed:
        st.success("ご協力ありがとうございます！整理券を発行できます。")

        st.divider()
        st.subheader("🎫 整理券発行")

        game_options = {g["title"]: g["id"] for g in GAMES}
        selected_title = st.selectbox("体験するゲームを選んでください", list(game_options.keys()))
        game_id = game_options[selected_title]

        # このゲームの表示画像（あれば添付用にCIDで使う）
        base_stem = game_id
        found_image = None
        for ext in [".png", ".jpg", ".jpeg", ".webp", ".PNG", ".JPG", ".JPEG", ".WEBP"]:
            p = IMG_DIR / f"{base_stem}{ext}"
            if p.exists():
                found_image = p
                break

        if ENGINE is None:
            st.warning("（現在DBに接続できていないため、整理券の発行は無効です）")
        else:
            disable_btn = not valid_email
            if not valid_email:
                st.caption("※ 正しいメールアドレスを入力してください")

            if st.button("整理券を発行する", disabled=disable_btn):
                try:
                    # 1) DBにINSERT（id, created_at取得）
                    with ENGINE.begin() as conn:
                        res = conn.execute(
                            text("INSERT INTO tickets (game_id, email) VALUES (:gid, :email) RETURNING id, created_at"),
                            {"gid": game_id, "email": email}
                        ).first()
                        new_id = int(res.id)
                        created_at = res.created_at  # timezone付き

                        # 2) 発行番号（例: KMG-YYMMDD-XXXX）
                        ymd = created_at.strftime("%y%m%d")
                        ticket_no = f"KMG-{ymd}-{new_id:04d}"

                        # 3) ticket_no を更新
                        conn.execute(
                            text("UPDATE tickets SET ticket_no=:tno WHERE id=:id"),
                            {"tno": ticket_no, "id": new_id}
                        )

                    # 4) メール本文（HTML、画像は cid:gameimg）
                    game_title = ID_TO_TITLE.get(game_id, game_id)
                    html = f"""
                    <div style="font-family: sans-serif;">
                      <p>この度はご来場いただきありがとうございます。</p>
                      <h2>整理券を発行しました</h2>
                      <p><b>番号：</b>{ticket_no}</p>
                      <p><b>作品：</b>{game_title}</p>
                      <p>※順番が来たら係の者に本メールをご提示ください。</p>
                      {"<img src='cid:gameimg' style='max-width:100%;height:auto;border-radius:8px;'/>" if found_image else ""}
                      <hr>
                      <p>Komazawa Games / Autumn Festival 2025</p>
                    </div>
                    """

                    # 5) メール送信（来場者 + 主催者Bcc）
                    try:
                        send_mail_with_inline_image(
                            to_email=email,
                            subject=f"【整理券】{ticket_no} / {game_title}",
                            html_body=html,
                            inline_image_path=str(found_image) if found_image else None,
                            cid="gameimg"
                        )
                        st.success(f"『{selected_title}』の整理券を発行・送信しました！")
                        st.caption(f"整理券番号：{ticket_no}（メールをご確認ください）")
                    except Exception as mail_err:
                        st.error("整理券は発行されましたが、メール送信に失敗しました。SMTP設定をご確認ください。")
                        st.exception(mail_err)

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


st.write("")
st.caption("© 2025 KomazawaGames ")
# ==================== end ====================
