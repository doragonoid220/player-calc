import json

import streamlit as st
from PIL import Image
from google import genai

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

- 順位
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
        model="gemini-2.0-flash",
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

                except Exception as e:
                    st.error(str(e))
