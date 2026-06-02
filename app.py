import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
import re

st.set_page_config(
    page_title="YouTube Comment Analyzer",
    layout="wide"
)

API_KEY = st.secrets["YOUTUBE_API_KEY"]

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)


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
                "작성자": snippet["authorDisplayName"],
                "댓글": snippet["textDisplay"],
                "좋아요": snippet["likeCount"],
                "작성일": snippet["publishedAt"]
            })

            progress.progress(
                min(
                    len(comments) / max_comments,
                    1.0
                )
            )

            if len(comments) >= max_comments:
                break

        request = youtube.commentThreads().list_next(
            request,
            response
        )

    progress.empty()

    return pd.DataFrame(comments)


st.title("📺 YouTube 댓글 분석기")

url = st.text_input(
    "유튜브 URL 입력"
)

comment_limit = st.slider(
    "수집할 댓글 수",
    min_value=10,
    max_value=5000,
    value=500,
    step=10
)

st.write(
    f"선택된 댓글 수: {comment_limit:,}개"
)

if st.button("댓글 수집"):

    video_id = get_video_id(url)

    if not video_id:
        st.error("올바른 유튜브 URL을 입력하세요.")
        st.stop()

    with st.spinner("댓글 수집 중..."):

        df = get_comments(
            video_id,
            comment_limit
        )

    st.success(
        f"{len(df):,}개 댓글 수집 완료"
    )

    st.dataframe(
        df,
        use_container_width=True
    )

    csv = df.to_csv(
        index=False
    ).encode("utf-8-sig")

    st.download_button(
        "CSV 다운로드",
        csv,
        "youtube_comments.csv",
        "text/csv"
    )
