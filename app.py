```python
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from googleapiclient.discovery import build
from textblob import TextBlob
import re

# =====================================================
# 페이지 설정
# =====================================================

st.set_page_config(
    page_title="YouTube Comment Analyzer",
    page_icon="📊",
    layout="wide"
)

st.title("📺 YouTube Comment Analyzer")

st.markdown("""
유튜브 영상의 댓글을 수집하여

- 감성 분석
- 댓글 통계
- 워드클라우드
- 인기 댓글 분석

을 수행합니다.
""")

# =====================================================
# API KEY
# =====================================================

API_KEY = st.secrets["YOUTUBE_API_KEY"]

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)

# =====================================================
# 유튜브 URL -> Video ID
# =====================================================

def get_video_id(url):

    patterns = [
        r"v=([^&]+)",
        r"youtu\.be/([^?]+)",
        r"shorts/([^?]+)"
    ]

    for pattern in patterns:

        match = re.search(pattern, url)

        if match:
            return match.group(1)

    return None


# =====================================================
# 영상 정보 가져오기
# =====================================================

def get_video_info(video_id):

    response = youtube.videos().list(
        part="snippet,statistics",
        id=video_id
    ).execute()

    if not response["items"]:
        return None

    item = response["items"][0]

    return {
        "title": item["snippet"]["title"],
        "channel": item["snippet"]["channelTitle"],
        "views": item["statistics"].get("viewCount", 0),
        "likes": item["statistics"].get("likeCount", 0),
        "comments": item["statistics"].get("commentCount", 0)
    }


# =====================================================
# 댓글 수집
# =====================================================

def get_comments(video_id, max_comments):

    comments = []

    request = youtube.commentThreads().list(
        part="snippet",
        videoId=video_id,
        maxResults=100,
        textFormat="plainText"
    )

    progress = st.progress(0)

    while request and len(comments) < max_comments:

        response = request.execute()

        for item in response["items"]:

            snippet = item["snippet"]["topLevelComment"]["snippet"]

            comments.append({
                "comment": snippet["textDisplay"],
                "likes": snippet["likeCount"],
                "author": snippet["authorDisplayName"],
                "published_at": snippet["publishedAt"]
            })

            current = len(comments)

            progress.progress(
                min(current / max_comments, 1.0)
            )

            if current >= max_comments:
                break

        request = youtube.commentThreads().list_next(
            request,
            response
        )

    progress.empty()

    return pd.DataFrame(comments[:max_comments])


# =====================================================
# 감성 분석
# =====================================================

def analyze_sentiment(text):

    try:

        polarity = TextBlob(
            str(text)
        ).sentiment.polarity

        if polarity > 0:
            return "Positive"

        elif polarity < 0:
            return "Negative"

        else:
            return "Neutral"

    except:
        return "Neutral"


# =====================================================
# UI
# =====================================================

url = st.text_input(
    "유튜브 영상 URL 입력"
)

comment_limit = st.slider(
    "수집할 댓글 수",
    min_value=10,
    max_value=5000,
    value=500,
    step=10
)

if st.button("댓글 수집 및 분석"):

    video_id = get_video_id(url)

    if not video_id:
        st.error("올바른 유튜브 URL을 입력하세요.")
        st.stop()

    # =====================================================
    # 영상 정보
    # =====================================================

    info = get_video_info(video_id)

    if info:

        st.subheader("🎬 영상 정보")

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("조회수", f"{int(info['views']):,}")
        c2.metric("좋아요", f"{int(info['likes']):,}")
        c3.metric("댓글수", f"{int(info['comments']):,}")
        c4.metric("채널", info["channel"])

        st.write("###", info["title"])

    # =====================================================
    # 댓글 수집
    # =====================================================

    with st.spinner("댓글 수집중..."):

        df = get_comments(
            video_id,
            comment_limit
        )

    if len(df) == 0:

        st.warning("댓글이 존재하지 않습니다.")
        st.stop()

    # =====================================================
    # 전처리
    # =====================================================

    df["length"] = df["comment"].astype(str).str.len()

    df["sentiment"] = df["comment"].apply(
        analyze_sentiment
    )

    # =====================================================
    # 기본 통계
    # =====================================================

    st.divider()

    st.subheader("📈 기본 통계")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "총 댓글 수",
        f"{len(df):,}"
    )

    c2.metric(
        "평균 좋아요",
        round(df["likes"].mean(), 2)
    )

    c3.metric(
        "평균 댓글 길이",
        round(df["length"].mean(), 1)
    )

    # =====================================================
    # 감성 분석
    # =====================================================

    st.divider()

    st.subheader("😊 감성 분석")

    sentiment_df = (
        df["sentiment"]
        .value_counts()
        .reset_index()
    )

    sentiment_df.columns = [
        "sentiment",
        "count"
    ]

    fig = px.pie(
        sentiment_df,
        names="sentiment",
        values="count",
        hole=0.5,
        title="댓글 감성 분포"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # =====================================================
    # 댓글 길이
    # =====================================================

    st.divider()

    st.subheader("📏 댓글 길이 분포")

    fig2 = px.histogram(
        df,
        x="length",
        nbins=40,
        title="댓글 길이 히스토그램"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # =====================================================
    # 워드클라우드
    # =====================================================

    st.divider()

    st.subheader("☁️ 워드클라우드")

    text = " ".join(
        df["comment"].astype(str)
    )

    if len(text) > 0:

        wc = WordCloud(
            width=1200,
            height=600,
            background_color="white"
        ).generate(text)

        fig3, ax = plt.subplots(
            figsize=(12, 6)
        )

        ax.imshow(wc)

        ax.axis("off")

        st.pyplot(fig3)

    # =====================================================
    # 좋아요 TOP 댓글
    # =====================================================

    st.divider()

    st.subheader("🔥 좋아요 TOP 댓글")

    top_comments = (
        df.sort_values(
            "likes",
            ascending=False
        )
        .head(20)
    )

    st.dataframe(
        top_comments,
        use_container_width=True
    )

    # =====================================================
    # 전체 데이터
    # =====================================================

    st.divider()

    st.subheader("📋 전체 댓글")

    st.dataframe(
        df,
        use_container_width=True
    )

    # =====================================================
    # CSV 다운로드
    # =====================================================

    csv = df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        label="📥 CSV 다운로드",
        data=csv,
        file_name="youtube_comments.csv",
        mime="text/csv"
    )
```
