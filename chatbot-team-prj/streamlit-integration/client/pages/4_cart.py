import streamlit as st

# 세션 상태 초기화 (이미 값이 있는지 확인 후 초기화)
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False  # 로그인 상태 초기화

if 'wishlist' not in st.session_state:
    st.session_state['wishlist'] = []  # 찜한 상품 목록 초기화

# 찜한 상품 목록 표시 섹션
def display_wishlist():
    st.header("찜한 상품 목록")

    # 세션에서 wishlist가 있는지 확인
    if st.session_state['wishlist']:
        # wishlist 안에 있는 각각의 상품을 가져와 출력
        for product in st.session_state['wishlist']:
            product_name = product.get('name', '이름 없음')
            product_image = product.get('image', None)
            product_url = product.get('url', 'URL 없음')

            st.write(f"**상품명:** {product_name}")

            if product_image:
                st.image(product_image, caption=product_name)

            if product_url:
                # HTML을 사용하여 URL 링크를 표시
                st.markdown(
                    f"""
                    <div style="text-align: center;">
                        <a href="{product_url}" target="_blank" style="text-decoration: none; background-color: #f0f0f0; color: #007bff; padding: 10px 20px; border-radius: 5px;">
                            상품 페이지로 이동하기
                        </a>
                    </div>
                    """, unsafe_allow_html=True
                )

            st.markdown("---")  # 구분선
    else:
        st.write("찜한 상품이 없습니다.")

    # 세션 상태의 wishlist를 별도로 표시 (디버깅용)
    st.subheader("세션에 저장된 찜한 상품 목록")
    for item in st.session_state['wishlist']:
        st.write(f"상품명: {item.get('name', '이름 없음')}, URL: {item.get('url', 'URL 없음')}")

# 찜한 상품 목록 표시 함수 호출
display_wishlist()