import streamlit as st
import pandas as pd
import re

try:
    from googleapiclient.discovery import build
except Exception as e:
    st.error(
        "google-api-python-client가 설치되지 않았습니다. requirements.txt를 확인하세요."
    )
    st.stop()

# -----------------------------
# 설정
# -----------------------------

st.set_page_config(
    page_title="YouTube Comment Collector",
    layout="wide"
)

st.title("📺 YouTube 댓글 수집기")

# -----------------------------
# API Key
# -----------------------------

if "YOUTUBE_API_KEY" not in st.secrets:
    st.error(
        "Streamlit Secrets에 YOUTUBE_API_KEY를 등록하세요."
    )
    st.stop()

API_KEY = st.secrets["YOUTUBE_API_KEY"]

youtube = build(
    "youtube",
    "v3",
    developerKey=API_KEY
)

# -----------------------------
# Video ID 추출
# -----------------------------

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

# -----------------------------
# 댓글 수집
# -----------------------------

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

            snippet = item["snippet"]["topLevelComment"]["snippet"]

            comments.append({
                "작성자": snippet["authorDisplayName"],
                "댓글": snippet["textDisplay"],
                "좋아요": snippet["likeCount"],
                "작성일": snippet["publishedAt"]
            })

            progress.progress(
                min(
                    len(comments) / limit,
                    1.0
                )
            )

            if len(comments) >= limit:
                break

        request = youtube.commentThreads().list_next(
            request,
            response
        )

    progress.empty()

    return pd.DataFrame(comments)

# -----------------------------
# 입력
# -----------------------------

url = st.text_input(
    "유튜브 URL"
)

comment_limit = st.slider(
    "수집할 댓글 수",
    min_value=10,
    max_value=5000,
    value=500,
    step=10
)

st.info(
    f"선택된 댓글 수 : {comment_limit:,}개"
)

# -----------------------------
# 실행
# -----------------------------

if st.button("댓글 수집 시작"):

    video_id = get_video_id(url)

    if not video_id:

        st.error(
            "올바른 유튜브 URL을 입력하세요."
        )

    else:

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
