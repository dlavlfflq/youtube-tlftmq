import streamlit as st
import pandas as pd
import re
from collections import Counter

import plotly.express as px
import matplotlib.pyplot as plt
from wordcloud import WordCloud

from googleapiclient.discovery import build

# =========================
# 한글 폰트 설정 (중요)
# =========================

plt.rcParams["font.family"] = "NanumGothic"
plt.rcParams["axes.unicode_minus"] = False

# =========================
# Streamlit 설정
# =========================

st.set_page_config(
    page_title="YouTube Comment Analyzer",
    layout="wide"
)

st.title("📺 YouTube 댓글 분석기")

st.markdown("유튜브 영상 댓글을 수집하고 분석합니다.")

# =========================
# API KEY
# =========================

API_KEY = st.secrets["YOUTUBE_API_KEY"]

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)

# =========================
# 유튜브 영상 ID 추출
# =========================

def get_video_id(url):

    patterns = [
        r"v=([^&]+)",
        r"youtu\.be/([^?]+)",
        r"shorts/([^?]+)"
    ]

    for p in patterns:
        match = re.search(p, url)
        if match:
            return match.group(1)

    return None

# =========================
# 댓글 수집
# =========================

def get_comments(video_id, limit):

    comments = []

    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    )

    progress = st.progress(0)

    while request and len(comments) < limit:

        response = request.execute()

        for item in response["items"]:

            sn = item["snippet"]["topLevelComment"]["snippet"]

            comments.append({
                "댓글": sn["textDisplay"],
                "좋아요": sn["likeCount"],
                "작성자": sn["authorDisplayName"],
                "작성일": sn["publishedAt"]
            })

            progress.progress(min(len(comments) / limit, 1.0))

            if len(comments) >= limit:
                break

        request = youtube.commentThreads().list_next(request, response)

    progress.empty()

    return pd.DataFrame(comments)

# =========================
# 좋아요 기반 단어 분석
# =========================

def get_top_liked_words(df):

    counter = Counter()

    stopwords = {
        "이","그","저","것","수","등",
        "은","는","이","가","을","를",
        "에","의","와","과","도","만",
        "너무","진짜","정말","그리고","영상","ㅋㅋ","ㅎㅎ"
    }

    for _, row in df.iterrows():

        text = str(row["댓글"])
        likes = int(row["좋아요"])

        words = text.split()

        for w in words:

            w = w.strip()

            if len(w) < 2:
                continue

            if w in stopwords:
                continue

            counter[w] += likes

    return pd.DataFrame(
        counter.items(),
        columns=["단어", "좋아요합계"]
    ).sort_values(
        "좋아요합계",
        ascending=False
    ).head(20)

# =========================
# 입력 UI
# =========================

url = st.text_input("유튜브 URL 입력")

comment_limit = st.slider(
    "수집할 댓글 수",
    min_value=10,
    max_value=5000,
    value=500,
    step=10
)

st.info(f"선택된 댓글 수: {comment_limit:,}개")

# =========================
# 실행
# =========================

if st.button("분석 시작"):

    video_id = get_video_id(url)

    if not video_id:
        st.error("올바른 유튜브 URL을 입력하세요.")
        st.stop()

    with st.spinner("댓글 수집 중..."):

        df = get_comments(video_id, comment_limit)

    if df.empty:
        st.warning("댓글이 없습니다.")
        st.stop()

    # =========================
    # 기본 통계
    # =========================

    st.subheader("📊 기본 통계")

    c1, c2 = st.columns(2)

    c1.metric("총 댓글 수", len(df))
    c2.metric("평균 좋아요", round(df["좋아요"].mean(), 2))

    # =========================
    # 좋아요 TOP 댓글
    # =========================

    st.subheader("🔥 좋아요 TOP 댓글")

    st.dataframe(
        df.sort_values("좋아요", ascending=False).head(20),
        use_container_width=True
    )

    # =========================
    # 좋아요 기반 TOP 단어
    # =========================

    st.subheader("🔥 좋아요 기반 TOP20 단어")

    top_words = get_top_liked_words(df)

    fig = px.bar(
        top_words,
        x="좋아요합계",
        y="단어",
        orientation="h",
        text="좋아요합계"
    )

    fig.update_layout(height=600)

    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # 워드클라우드 (한글 포함)
    # =========================

    st.subheader("☁️ 워드클라우드")

    text = " ".join(df["댓글"].astype(str))

    wc = WordCloud(
        width=1200,
        height=600,
        background_color="white",
        font_path="NanumGothic.ttf",
        collocations=False
    ).generate(text)

    fig, ax = plt.subplots(figsize=(12,6))
    ax.imshow(wc)
    ax.axis("off")

    st.pyplot(fig)

    # =========================
    # 전체 데이터
    # =========================

    st.subheader("📋 전체 댓글")

    st.dataframe(df, use_container_width=True)

    # =========================
    # CSV 다운로드
    # =========================

    csv = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "CSV 다운로드",
        csv,
        "youtube_comments.csv",
        "text/csv"
    )
