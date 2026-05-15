import json
import re
from typing import Dict, List, Any

import pandas as pd
import streamlit as st
from PIL import Image
from google import genai

BATTER_KEYS = ["パワー", "ミート", "選球", "忍耐"]
PITCHER_KEYS = ["球威", "制球", "変化", "コマンド"]

st.set_page_config(page_title="選手能力 自動計算", page_icon="⚾", layout="wide")
st.title("⚾ 選手能力 自動計算")
st.caption("画像アップロード → AI読み取り → 手修正 → スキル/補正込み能力を比較")
player_type = st.radio("選手タイプ", ["野手", "投手"])
selected_keys = BATTER_KEYS if player_type == "野手" else PITCHER_KEYS
STAT_KEYS = selected_keys

def blank_player() -> Dict[str, Any]:
    return {
        "player_name": "",
        "base": {},
        "edition_effects": [],
        "skills": [],
        "notes": "",
    }


def normalize_json_text(text: str) -> str:
    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    return match.group(0) if match else text


def to_int(v, default=0):
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default


def ensure_player_shape(data: Dict[str, Any]) -> Dict[str, Any]:
    player = blank_player()
    player["player_name"] = str(data.get("player_name") or "")

    base = data.get("base") or {}
    # 英語キーにも対応
    aliases = {
    "パワー": ["パワー", "power"],
    "ミート": ["ミート", "meet", "contact"],
    "選球": ["選球", "eye", "plate_discipline"],
    "忍耐": ["忍耐", "patience"],
    "球威": ["球威", "velocity", "stuff"],
    "制球": ["制球", "control"],
    "変化": ["変化", "breaking"],
    "コマンド": ["コマンド", "command"],
    }
    for jp, keys in aliases.items():
        for k in keys:
            if k in base:
                player["base"][jp] = to_int(base.get(k))
                break

    for item in data.get("edition_effects", []) or []:
        effect = {k: to_int((item.get("effect") or {}).get(k)) for k in BATTER_KEYS}
        player["edition_effects"].append({
            "name": str(item.get("name") or ""),
            "condition": str(item.get("condition") or "常時"),
            "enabled_default": bool(item.get("enabled_default", True)),
            "effect": effect,
        })

    for item in data.get("skills", []) or []:
        effect = {k: to_int((item.get("effect") or {}).get(k)) for k in BATTER_KEYS}
        player["skills"].append({
            "name": str(item.get("name") or ""),
            "condition": str(item.get("condition") or "常時"),
            "enabled_default": bool(item.get("enabled_default", True)),
            "effect": effect,
        })

    player["notes"] = str(data.get("notes") or "")
    return player


def call_gemini(images: List[Image.Image]) -> Dict[str, Any]:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY":
        raise RuntimeError("GEMINI_API_KEY が未設定です。StreamlitのSecretsに登録してください。")

    client = genai.Client(api_key=api_key)
    prompt = """
あなたはゲーム画面の能力計算アシスタントです。
添付画像から、選手名・合計能力・スキル・エディション効果を読み取り、JSONだけを返してください。

重要:
- base は画像内の「合計」行の数値を優先してください。
- 画像上ですでに合計に反映済みと思われるものは base に含まれている前提でよいです。
- ただし、別画像に表示されているエディション効果や潜在効果が、合計に未反映か判断できない場合は edition_effects に入れてください。
- スキルは発動条件と加算値を正確に入れてください。
- 読み取れない数字は 0 ではなく null にせず、推測せず 0 にしてください。
- 出力はJSONのみ。説明文は禁止。

JSON形式:
{
  "player_name": "選手名",
  "base": {"球威": 0, "制球": 0, "変化": 0, "コマンド": 0},
  "edition_effects": [
    {"name": "効果名", "condition": "発動条件", "enabled_default": true, "effect": {"パワー": 0, "ミート": 0, "選球": 0, "忍耐": 0}}
  ],
  "skills": [
    {"name": "スキル名", "condition": "発動条件", "enabled_default": true, "effect": {"パワー": 0, "ミート": 0, "選球": 0, "忍耐": 0}}
  ],
  "notes": "読み取り上の注意"
}
"""
    contents = [prompt] + images
    response = client.models.generate_content(model="gemini-2.5-flash", contents=contents)
    text = normalize_json_text(response.text)
    return ensure_player_shape(json.loads(text))


def calc_total(base: Dict[str, int], effects: List[Dict[str, Any]]) -> Dict[str, int]:
    result = {k: to_int(base.get(k)) for k in STAT_KEYS}
    for e in effects:
        if not e.get("enabled", False):
            continue
        effect = e.get("effect") or {}
        for k in STAT_KEYS:
            result[k] += to_int(effect.get(k))
    result["合計"] = sum(result[k] for k in STAT_KEYS)
    return result


def effect_editor(title: str, key_prefix: str, effects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    st.subheader(title)
    edited = []
    for i, e in enumerate(effects):
        with st.expander(f"{title}{i+1}: {e.get('name') or '未設定'}", expanded=True):
            c0, c1 = st.columns([1, 2])
            enabled = c0.checkbox("反映", value=bool(e.get("enabled_default", True)), key=f"{key_prefix}_en_{i}")
            name = c1.text_input("名称", value=e.get("name", ""), key=f"{key_prefix}_name_{i}")
            condition = st.text_input("条件", value=e.get("condition", "常時"), key=f"{key_prefix}_cond_{i}")
            cols = st.columns(4)
            effect = {}
            for idx, stat in enumerate(STAT_KEYS):
                effect[stat] = cols[idx].number_input(stat, value=to_int((e.get("effect") or {}).get(stat)), step=1, key=f"{key_prefix}_{stat}_{i}")
            edited.append({"enabled": enabled, "name": name, "condition": condition, "effect": effect})
    return edited


if "player" not in st.session_state:
    st.session_state.player = blank_player()
if "compare_rows" not in st.session_state:
    st.session_state.compare_rows = []

with st.sidebar:
    st.header("使い方")
    st.write("1. 画像をアップロード")
    st.write("2. AIで読み取り")
    st.write("3. 数値を確認・修正")
    st.write("4. 比較表に追加")
    if st.button("比較表をリセット"):
        st.session_state.compare_rows = []
        st.success("リセットしました")

uploaded_files = st.file_uploader(
    "能力画面・スキル画面・エディション画面をアップロード（複数可）",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
)

images = []
if uploaded_files:
    cols = st.columns(min(len(uploaded_files), 3))
    for idx, f in enumerate(uploaded_files):
        img = Image.open(f).convert("RGB")
        images.append(img)
        cols[idx % len(cols)].image(img, caption=f.name, use_container_width=True)

if images and st.button("AIで読み取り", type="primary"):
    with st.spinner("読み取り中..."):
        try:
            st.session_state.player = call_gemini(images)
            st.success("読み取り完了。数値を確認してください。")
        except Exception as e:
            st.error(f"読み取りに失敗しました: {e}")

player = st.session_state.player

st.divider()
st.header("読み取り結果の確認・修正")

player_name = st.text_input("選手名", value=player.get("player_name", ""))
st.caption("base は画像の『合計』行を入れてください。すでに画像内で反映済みの補正は二重加算しないよう注意。")
base_cols = st.columns(4)
base = {}
for idx, stat in enumerate(STAT_KEYS):
    base[stat] = base_cols[idx].number_input(f"元能力：{stat}", value=to_int((player.get("base") or {}).get(stat)), step=1)

edition_effects = effect_editor("エディション/潜在効果", "ed", player.get("edition_effects", []))
skill_effects = effect_editor("スキル", "sk", player.get("skills", []))

with st.expander("手動で効果を追加する"):
    st.write("AIが読み取れなかったスキルや補正を追加できます。")
    add_name = st.text_input("追加名", key="add_name")
    add_kind = st.selectbox("追加先", ["スキル", "エディション/潜在効果"], key="add_kind")
    add_enabled = st.checkbox("反映する", value=True, key="add_enabled")
    add_cols = st.columns(4)
    add_effect = {stat: add_cols[i].number_input(stat, value=0, step=1, key=f"add_{stat}") for i, stat in enumerate(STAT_KEYS)}
    if st.button("追加"):
        new_e = {"enabled": add_enabled, "enabled_default": add_enabled, "name": add_name, "condition": "手動追加", "effect": add_effect}
        if add_kind == "スキル":
            st.session_state.player.setdefault("skills", []).append(new_e)
        else:
            st.session_state.player.setdefault("edition_effects", []).append(new_e)
        st.rerun()

all_effects = edition_effects + skill_effects
final = calc_total(base, all_effects)

st.divider()
st.header("最終能力")
result_df = pd.DataFrame([{"選手名": player_name, **final}])
st.dataframe(result_df, use_container_width=True, hide_index=True)

if st.button("現在の選手を比較表に追加", type="primary"):
    st.session_state.compare_rows.append({"選手名": player_name or "未入力", **final})
    st.success("比較表に追加しました")

if st.session_state.compare_rows:
    st.header("比較表")
    df = pd.DataFrame(st.session_state.compare_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("縦比較")
    vertical = df.set_index("選手名").T
    st.dataframe(vertical, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("CSVで保存", csv, "player_compare.csv", "text/csv")
