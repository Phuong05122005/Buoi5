# ============================================================
# IMPORTS
# ============================================================
import streamlit as st
import pandas as pd
from datetime import datetime
import json
import re

try:
    from underthesea import sentiment, word_tokenize
except:
    sentiment = None
    word_tokenize = None


# ============================================================
# STOPWORDS
# ============================================================
@st.cache_data
def load_stopwords(path="stopwords_vi.txt"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    except:
        return set()


STOPWORDS = load_stopwords()


# ============================================================
# MODEL (CACHING)
# ============================================================
@st.cache_resource
def load_model():
    return sentiment


# ============================================================
# TEXT PROCESSING
# ============================================================
def clean_text(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


# ============================================================
# ANALYSIS
# ============================================================
def analyze_feedback(text: str) -> dict:
    text_clean = clean_text(text)

    # TODO 13: EDGE CASE
    if len(text_clean.split()) <= 2:
        return {
            "sentiment": "neutral",
            "keywords": [],
            "confidence": 0.5,
            "note": "Phản hồi quá ngắn"
        }

    if sentiment:
        label = sentiment(text_clean)
        confidence = 0.8
    else:
        label = "neutral"
        confidence = 0.5

    tokens = word_tokenize(text_clean) if word_tokenize else text_clean.split()
    keywords = [w for w in tokens if w not in STOPWORDS]

    return {
        "sentiment": label,
        "keywords": keywords[:10],
        "confidence": confidence
    }


def render_analysis(result: dict) -> str:
    return f"""
**Cảm xúc:** {result['sentiment']}  
**Độ tin cậy:** {result['confidence']}  
**Từ khóa:** {", ".join(result['keywords'])}
"""


# ============================================================
# FILE HANDLING
# ============================================================
def handle_file_upload():
    file = st.file_uploader("📂 Upload CSV/Excel", type=["csv", "xlsx"])
    if file:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        return df.iloc[:, 0].dropna().astype(str).tolist()
    return []


def export_history(history):
    df = pd.DataFrame(history)
    return df.to_csv(index=False).encode("utf-8")


# ============================================================
# VISUALIZATION
# ============================================================
def render_wordcloud(keywords):
    if not keywords:
        return

    from wordcloud import WordCloud
    import matplotlib.pyplot as plt

    wc = WordCloud(width=800, height=400).generate(" ".join(keywords))

    fig, ax = plt.subplots()
    ax.imshow(wc)
    ax.axis("off")

    st.pyplot(fig)


def render_sentiment_timeline(history):
    if len(history) < 2:
        return

    df = pd.DataFrame(history)
    df["time"] = pd.to_datetime(df["time"])

    # mapping sentiment -> numeric
    mapping = {"positive": 1, "neutral": 0, "negative": -1}
    df["score"] = df["sentiment"].map(mapping)

    df = df.sort_values("time")

    st.line_chart(df.set_index("time")["score"])


def render_sidebar_stats(history):
    st.subheader("📊 Thống kê")

    if not history:
        st.info("Chưa có dữ liệu")
        return

    df = pd.DataFrame(history)

    # sentiment count
    st.write("### Phân bố cảm xúc")
    st.bar_chart(df["sentiment"].value_counts())

    # wordcloud
    all_keywords = []
    for h in history:
        all_keywords.extend(h.get("keywords", []))

    st.write("### Word Cloud")
    render_wordcloud(all_keywords)

    # timeline
    st.write("### Timeline")
    render_sentiment_timeline(history)


# ============================================================
# SESSION + PERSIST
# ============================================================
def load_history(path="history.json"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_history(history, path="history.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "history" not in st.session_state:
        st.session_state.history = load_history()


def delete_feedback(index):
    if 0 <= index < len(st.session_state.history):
        st.session_state.history.pop(index)


# ============================================================
# LANGUAGE DETECT
# ============================================================
def detect_language(text):
    if re.search(r"[àáảãạăâđêôơư]", text.lower()):
        return "vi"
    return "en"


# ============================================================
# HELP PAGE
# ============================================================
def render_help_page():
    st.title("📘 Hướng dẫn sử dụng")

    st.markdown("""
### 🔹 Cách sử dụng
- Nhập phản hồi → chatbot phân tích cảm xúc
- Upload file CSV/Excel → phân tích hàng loạt
- Sidebar hiển thị thống kê + wordcloud

### 🔹 Ý nghĩa
- Positive 😊: phản hồi tích cực
- Negative 😟: phản hồi tiêu cực
- Neutral 😐: trung lập
""")


# ============================================================
# MAIN
# ============================================================
def main():
    st.set_page_config(page_title="Chatbot Feedback", layout="wide")

    init_session_state()

    # SIDEBAR
    with st.sidebar:
        st.title("⚙️ Menu")

        if st.button("📘 Hướng dẫn"):
            render_help_page()

        st.divider()

        render_sidebar_stats(st.session_state.history)

        st.divider()

        # Upload
        uploaded = handle_file_upload()
        for text in uploaded:
            result = analyze_feedback(text)
            st.session_state.history.append({
                "text": text,
                "time": str(datetime.now()),
                **result
            })

        # Export
        if st.session_state.history:
            csv = export_history(st.session_state.history)
            st.download_button("📥 Download CSV", csv, "history.csv")

    # MAIN CHAT
    st.title("🤖 Chatbot Phân tích phản hồi sinh viên")

    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # TODO 7: delete button
            if msg["role"] == "user":
                if st.button(f"❌ Xóa", key=f"del_{i}"):
                    delete_feedback(i // 2)
                    st.rerun()

    if prompt := st.chat_input("Nhập phản hồi..."):
        lang = detect_language(prompt)

        result = analyze_feedback(prompt)
        response = render_analysis(result)

        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.messages.append({"role": "assistant", "content": response})

        st.session_state.history.append({
            "text": prompt,
            "time": str(datetime.now()),
            **result
        })

        save_history(st.session_state.history)

        st.rerun()


if __name__ == "__main__":
    main()