import json

import streamlit as st
from PIL import Image
from google import genai
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(
    page_title="ランキング分析",
    layout="wide"
)

st.title("ランキング200位 クラブ分析")

uploaded_files = st.file_uploader(
    "ランキングスクショ",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

client = genai.Client(
    api_key=st.secrets["RANKING_GEMINI_API_KEY"]
)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

gc = gspread.authorize(creds)

sheet = gc.open("ranking_records").sheet1


def resize_image(image, max_width=1200):
    image = image.convert("RGB")
    width, height = image.size

    if width > max_width:
        new_height = int(height * max_width / width)
        image = image.resize((max_width, new_height))

    return image


def extract_ranking(image):
    prompt = """
この画像はランキングチャレンジ画面です。

以下を抽出してください。

- プレイヤー名
- クラブ名
- ランキングのOVR

JSON配列のみで返してください。

形式:
[
  {
    "rank": 1,
    "player_name": "名前",
    "club_name": "クラブ名",
    "ranking_ovr": 14450
  }
]
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[prompt, image]
    )

    text = response.text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)


if uploaded_files:
    st.success(f"{len(uploaded_files)}枚アップロード済み")

    for file in uploaded_files:
        original_image = Image.open(file)
        image = resize_image(original_image)

        st.write(f"ファイル名：{file.name}")
        st.write(f"元サイズ：{original_image.size[0]} x {original_image.size[1]}")
        st.write(f"軽量化後：{image.size[0]} x {image.size[1]}")

        st.image(
            image,
            caption=file.name,
            width=300
        )

        if st.button(f"{file.name} を解析"):
            with st.spinner("Gemini解析中..."):
                try:
                    result = extract_ranking(image)
                    st.success("解析成功")
                    st.json(result)
                    for item in result:
                        sheet.append_row([
    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    item["player_name"],
    item["club_name"],
    item["ranking_ovr"]
                        ])

                    st.success("Google Sheets保存完了")
                except Exception as e:
                    st.error(str(e))
                    st.divider()
st.subheader("クラブ別一覧・検索")

records = sheet.get_all_records()

if records:
    import pandas as pd

    df = pd.DataFrame(records)
    st.write("取得できた列名:", list(pd.DataFrame(records).columns))

    search_club = st.text_input("クラブ名で検索")

    if search_club:
        df = df[df["クラブ名"].astype(str).str.contains(search_club, case=False, na=False)]

    club_count = df.groupby("クラブ名").size().reset_index(name="人数")
    club_count = club_count.sort_values("人数", ascending=False)

    st.subheader("同クラブ人数")
    st.dataframe(club_count, use_container_width=True)

    st.subheader("クラブ別メンバー一覧")

    for club in club_count["クラブ名"]:
        st.markdown(f"### {club}")

        st.dataframe(
            df[df["クラブ名"] == club][["プレイヤー名", "OVR"]],
            use_container_width=True
        )

else:
    st.info("まだ保存データがありません")
