import streamlit as st
import new # 방금 저장하신 new.py 파일을 불러옵니다!

# Streamlit UI 설정
st.set_page_config(page_title="여행 날씨 & 숙소 안내", page_icon="🌤️")
st.title("🌤️ 여행 날씨 & 숙소 정보 검색")

# 사용자 입력
destination = st.text_input("여행지나 궁금한 지역을 입력하세요 (예: 강릉, 제주도, 속초)", "강릉")

if st.button("조회하기"):
    with st.spinner("API 데이터를 불러오는 중입니다... ⏳"):
        # new.py 안의 함수 호출
        weather = new.get_weather(destination)
        accommodations = new.get_accommodations(destination)
        
        st.subheader(f"📍 {destination} 여행 정보")
        
        # 1. 날씨 정보 카드 출력
        st.markdown("### 🌤️ 날씨 정보")
        if weather:
            col1, col2, col3 = st.columns(3)
            col1.metric("날씨 상태", weather.get("weather"))
            col2.metric("최고 / 최저 기온", f"{weather.get('max_temp')}°C / {weather.get('min_temp')}°C")
            col3.metric("강수 확률", f"{weather.get('rain_probability')}%")
        else:
            st.error("날씨 정보를 가져오지 못했습니다.")
            
        st.divider()
        
        # 2. 숙소 정보 카드 출력
        st.markdown("### 🏨 추천 숙소 목록")
        if accommodations:
            for acc in accommodations:
                with st.expander(f"📌 {acc.get('name')}"):
                    st.write(f"**주소:** {acc.get('address')}")
                    st.write(f"**평점:** ⭐ {acc.get('rating')} / **예상 가격:** {acc.get('price'):,}원")
                    if acc.get('url'):
                        st.markdown(f"[👉 카카오맵에서 보기]({acc.get('url')})")
        else:
            st.warning("숙소 정보를 가져오지 못했습니다.")