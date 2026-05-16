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

def extract_ranking(image):
    prompt = """
この画像はランキングチャレンジ画面です。

以下を抽出してください。

- 順位
- プレイヤー名
- クラブ名
- OVR

JSON配列のみで返してください。

形式:
[
  {
    "rank": 1,
    "player_name": "名前",
    "club_name": "クラブ名",
    "ovr": 14450
  }
]
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt, image]
    )

    text = response.text.strip()

    text = text.replace("```json", "")
    text = text.replace("```", "")

    return json.loads(text)


if uploaded_files:
    for file in uploaded_files:

        image = Image.open(file)

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
