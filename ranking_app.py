import streamlit as st
from PIL import Image

st.set_page_config(
    page_title="ランキング分析",
    layout="wide"
)

st.title("ランキング200位 クラブ分析")

st.write("スクショをアップロードしてください")

uploaded_files = st.file_uploader(
    "ランキングスクショ",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"{len(uploaded_files)}枚アップロード")

    for file in uploaded_files:
        image = Image.open(file)

        st.image(
            image,
            caption=file.name,
            width=300
        )
