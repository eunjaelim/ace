import streamlit as st
import pandas as pd
import re
import numpy as np
import easyocr
import time
import cv2
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import torch
import os
import requests
from sqlalchemy import create_engine

# MariaDB 연결 설정
engine = create_engine("mysql+pymysql://root:3511@localhost/chatbot")


# 세션 상태 초기화
# 세션 상태 초기화
if 'uploaded_file' not in st.session_state:
    st.session_state['uploaded_file'] = None  # 'uploaded_file'을 초기화


if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False  # 로그인 상태를 False로 초기화

if 'username' not in st.session_state:
    st.session_state['username'] = None  # username 값을 None으로 초기화

if 'wishlist' not in st.session_state:
    st.session_state['wishlist'] = []  # 찜한 상품 목록 초기화

if 'products' not in st.session_state:
    st.session_state['products'] = []  # 검색된 상품 결과 초기화


def login_page():
    st.title("로그인")

    username = st.text_input("아이디")
    password = st.text_input("비밀번호", type="password")

    if st.button("로그인"):
            if st.button("로그인"):
                # POST 요청으로 데이터 전송
                login_data = {"username": username, "password": password}
                response = requests.post("http://localhost:8080/auth/login", json=login_data)

                if response.status_code == 200:
                    st.session_state['logged_in'] = True  # 로그인 상태 세션에 저장
                    st.session_state['username'] = username
                    st.success("로그인 성공!")
                else:
                    st.session_state['logged_in'] = False  # 로그인 실패
                    st.error("로그인 실패. 아이디와 비밀번호를 확인하세요.")





# 환경 설정
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
torch.set_num_threads(1)

# EasyOCR Reader 생성
reader = easyocr.Reader(['ko', 'en'], gpu=False)

# maria db 파일에서 데이터 로드 함수
@st.cache_data(ttl=9200)
def load_data_from_db(cert_num):
    st.write(f"요청된 인증번호: {cert_num}")

    url = f"http://localhost:8080/products/similar?certNum={cert_num}"
    response = requests.get(url)


    if response.status_code == 200:
        try:
            data = response.json()  # JSON 형식으로 데이터 변환
            st.write(f"받아온 데이터: {data}")  # 받아온 데이터 확인
            if not data:  # 데이터가 비어있는지 확인
                st.error("데이터가 비어 있습니다.")
                return None
            df = pd.DataFrame(data)
            df = df.rename(columns={
                'certification_number': '인증번호',
                'model_name': '모델명',
                'product_url': 'URL',
                'image_url': 'Image'
            })
            return df
        except Exception as e:
            st.error(f"데이터를 처리하는 중 오류 발생: {e}")
            return None
    else:
        st.error("서버에서 데이터를 불러오는 중 오류가 발생했습니다.")
        return None



# V/A 값으로 데이터 가져오는 함수 추가
@st.cache_data(ttl=9200)
def load_data_from_db_by_va(voltage, current):


    url = f"http://localhost:8080/products/similar_by_va?voltage={voltage}&current={current}"
    response = requests.get(url)



    if response.status_code == 200:
        try:
            data = response.json()  # JSON 형식으로 데이터 변환

            if not data:  # 데이터가 비어있는지 확인
                st.error("V/A 기반 검색 데이터가 비어 있습니다.")
                return None
            df = pd.DataFrame(data)
            df = df.rename(columns={
                'certification_number': '인증번호',
                'model_name': '모델명',
                'product_name': '제품명',
                'product_url': 'URL',
                'image_url': 'Image',
                'voltage': 'V',  # V (전압)
                'current': 'A'    # A (전류)
            })


            return df
        except Exception as e:
            st.error(f"데이터 처리 중 오류 발생: {e}")
            return None
    else:
        st.error("서버에서 데이터를 불러오는 중 오류가 발생했습니다.")
        return None



# 유사도를 계산하는 함수 (V, A 기반으로 유사 제품 찾기)
def calculate_similarity(target_value, all_products, column):
    # all_products가 None이 아니고 비어있지 않은지 확인
    if all_products is None or all_products.empty:
        st.error("유사 제품 검색을 위한 데이터가 없습니다.")
        return pd.DataFrame()  # 빈 데이터프레임 반환

    # null 값 제거 전 all_products가 유효한 데이터프레임인지 확인
    if column not in all_products.columns:
        st.error(f"'{column}' 열이 데이터프레임에 존재하지 않습니다.")
        return pd.DataFrame()

    # null 값 제거
    all_products = all_products.dropna(subset=[column])

    # 벡터화 및 유사도 계산
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5))
    tfidf_matrix = vectorizer.fit_transform(all_products[column].astype(str))  # 대상 컬럼 벡터화
    target_vector = vectorizer.transform([str(target_value)])
    similarity = cosine_similarity(target_vector, tfidf_matrix)  # 코사인 유사도 계산

    all_products['similarity'] = similarity[0]
    similar_products = all_products.sort_values(by='similarity', ascending=False).head(5)

    return similar_products

# 이미지 확대 및 샤프닝 후 OCR 적용 함수
def preprocess_and_extract_text(image):
    image = np.array(image)
    scale_percent = 200  # 이미지 크기 200%로 확대
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)
    dim = (width, height)

    # 이미지 확대
    resized_image = cv2.resize(image, dim, interpolation=cv2.INTER_LINEAR)

    # 샤프닝 커널 적용
    kernel = np.array([[0, -1, 0],
                       [-1, 5, -1],
                       [0, -1, 0]])
    sharpened_image = cv2.filter2D(resized_image, -1, kernel)

    # OCR 적용
    ocr_result = reader.readtext(sharpened_image, detail=0)
    extracted_text = " ".join(ocr_result)

    return extracted_text

# 정격출력 DC 정보를 추출하는 함수
def extract_dc_output(text):
    dc_output_match = re.search(r'DC\s?(\d{1,3}(\.\d+)?)[Vv]?\s?(\d{1,3}(\.\d+)?)[Aa]?', text)
    if dc_output_match:
        v_value = dc_output_match.group(1)
        a_value = dc_output_match.group(3)
        return v_value, a_value
    return None, None

# 인증번호를 추출하는 함수
def extract_cert_num(text):
    cert_nums = re.findall(r'\b[A-Z]{2}\d{5}-\d{5}\b', text)
    return cert_nums




# 서버로 찜 리스트를 저장하는 함수
def save_wishlist_to_server(wishlist, username):
    url = "http://localhost:8080/user/wishlist"
    data = {
        "username": username,
        "wishlist": wishlist
    }


    try:
        response = requests.post(url, json=data)
        st.write(f"응답 상태 코드: {response.status_code}")
        st.write(f"응답 내용: {response.text}")

        if response.status_code == 200:
            st.success("찜 리스트가 성공적으로 저장되었습니다.")
        else:
            st.error(f"서버 오류: {response.text}")
    except Exception as e:
        st.error(f"저장 중 오류가 발생했습니다: {e}")




# 상품 찜하기 기능 (로그인 확인 추가)
def add_to_wishlist(product):
    if not st.session_state['logged_in']:
        st.warning("로그인이 필요합니다.")
        return  # 함수 종료, 더 이상 진행하지 않음
    else:
        # 상품 정보를 wishlist에 추가
        if not any(item['name'] == product['name'] for item in st.session_state['wishlist']):
            st.session_state['wishlist'].append(product)  # 찜 목록에 상품 추가
            error_message_container = st.empty()  # 경고 메시지를 표시할 컨테이너 생성
            error_message_container.warning(f"{product['name']}을(를) cart에 추가했습니다!")  # 경고 메시지 표시
            time.sleep(2)  # 시간을 충분히 주어 메시지가 표시되도록 함
            error_message_container.empty()
        else:
            error_message_container = st.empty()  # 경고 메시지를 표시할 컨테이너 생성
            error_message_container.warning(f"{product['name']}은(는) 이미 cart에 있습니다.")  # 경고 메시지 표시
            time.sleep(2)  # 시간을 충분히 주어 메시지가 표시되도록 함
            error_message_container.empty()


# 검색 결과를 표시하는 함수
# 검색 결과를 표시하는 함수
def display_search_results(similar_products):

    st.header("검색 결과")
    for i, row in similar_products.iterrows():
#         product_name = row['product_name']
        product_url = row.get('URL', 'URL 없음')
        product_image = row.get('Image', None)

        # 상품 정보 출력
        st.markdown(f"<h3 style='text-align: center;'>{product_name}</h3>", unsafe_allow_html=True)
        if product_image:
            st.image(product_image, caption=product_name)

        # 버튼 상태 확인: 세션에 저장된 찜 목록에 포함된 상품인지 확인
        if any(item['name'] == productName for item in st.session_state['wishlist']):
                    st.write(f"{productName}은(는) 이미 찜 목록에 추가되었습니다.")
        else:
             # ❤️ 찜하기 버튼을 생성하여 사용자가 상품을 찜할 수 있도록 함
                    if st.button("❤️ 찜하기", key=f"wishlist_{i}"):
                                product = {'name': product_name, 'image': product_image, 'url': product_url}
                                add_to_wishlist(product)  # 상품을 세션에 추가
                                with st.spinner("서버에 저장 중..."):
                                    save_wishlist_to_server(st.session_state['wishlist'], st.session_state['username'])

                                time.sleep(3)
                                st.experimental_rerun()


                    st.markdown("---")  # 구분선







# 링크 클릭 카운트 기능
def count_click(product_name):
    if product_name not in st.session_state['click_counts']:
        st.session_state['click_counts'][product_name] = 0
    st.session_state['click_counts'][product_name] += 1
    st.write(f"clicked : {st.session_state['click_counts'][product_name]}")




st.image('logo.jpg' ,width=500)



# # 데이터 로드
# df = load_data_from_db(cert_num)

# 엑셀 데이터를 성공적으로 불러왔는지 확인 후 출력
# if df is not None:
#     pass
# else:
#     st.markdown("""
#         <p style='text-align: center; font-size: 18px;'>
#             데이터를 불러올 수 없습니다.
#         </p>
#     """, unsafe_allow_html=True)

# 이미지 파일 업로더

uploaded_file = st.file_uploader("**🤖 챗봇:** **제품 라벨 이미지를 업로드하세요**", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    st.session_state.uploaded_file = uploaded_file

if st.session_state.uploaded_file:
    st.write("**🤖 챗봇:** 인식 중입니다, 잠시만 기다려주세요...")
    with st.spinner("이미지 인식 중입니다. 잠시만 기다려주세요..."):
        image = Image.open(st.session_state.uploaded_file)
        st.image(image, caption="업로드된 이미지", use_column_width=True)

        # EasyOCR로 텍스트 추출
        extracted_text = preprocess_and_extract_text(image)
        cert_nums = extract_cert_num(extracted_text)
        v_value, a_value = extract_dc_output(extracted_text)

        # 추출된 인증번호 출력
        if cert_nums:
              cert_num = cert_nums[0]  # 첫 번째 인증번호 사용
              st.write(f"인증번호: {cert_num}")

              # 인증번호로 데이터 로드
              df = load_data_from_db(cert_num)
        else:

              cert_num = None
              df = None

        # 추출된 정보 출력
        st.write(f"인증번호: {cert_nums[0] if cert_nums else '추출되지 않음'}")
        st.write(f"정격 출력(V): {v_value}V" if v_value else "추출되지 않음")
        st.write(f"정격 출력(A): {a_value}A" if a_value else "추출되지 않음")

    #############
    # 인증번호가 없을 경우 V/A 검색
    if not cert_num and v_value and a_value:
        st.write("**🤖 챗봇:** 인증번호로 제품을 찾기 어렵습니다. 정격출력 V/A 값을 기반으로 검색을 진행합니다...")

        # V/A 값을 사용한 데이터 로드
        df = load_data_from_db_by_va(v_value, a_value)  # V/A 값을 사용해 데이터 로드


#         similar_products = None  # Initialize to None
        if df is not None and not df.empty:
            with st.spinner("정격출력 V/A 검색 중입니다. 잠시만 기다려주세요..."):
                pass

            similar_products = calculate_similarity(f"{v_value}V {a_value}A", df, 'V')
            if not similar_products.empty:
                st.write(f"정격 출력 {v_value}V {a_value}A에 대한 유사 제품 검색 결과:")


                st.markdown(
                        """
                        <style>
                        .underline {
                            border-bottom: 2px solid #e3e3e3;  /* 밑줄 스타일 (검정색, 두께 2px) */
                            padding-bottom: 10px;  /* 제목과 밑줄 사이 간격 */
                            margin-bottom: 20px;  /* 밑줄과 콘텐츠 사이 간격 */
                        }
                        </style>
                        <div class="underline"> </div>
                        """,
                        unsafe_allow_html=True
                    )



                for i, row in similar_products.iterrows():
                    product_name = row['productName']
                    product_url = row.get('productUrl', 'URL 없음')
                    product_image = row.get('imageUrl', None)
                    st.markdown(f"<h3 style='text-align: center;'>{product_name}</h3>", unsafe_allow_html=True)



                    # CSS 스타일 정의 (버튼을 가운데로 정렬)
                    st.markdown(
                        """
                        <style>
                        .center-button {
                            display: flex;
                            justify-content: center;
                            margin-top: 20px;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                    )

                    # 찜하기 버튼을 가운데에 정렬
                    col1, col2, col3 = st.columns([1,4,6])



                    # 찜하기 버튼 추가
                    if st.session_state['logged_in']:
                        if 'username' in st.session_state:  # username이 존재하는지 확인
                            with col2:  # 가운데 열에 버튼 추가
                                if st.button("❤️ 찜하기", key=f"wishlist2-{i}"):
                                    time.sleep(2)
                                    product = {'name': product_name, 'image': product_image, 'url': product_url}
                                    add_to_wishlist(product)  # 찜하기 목록에 추가

                                    with st.spinner("서버에 저장 중..."):
                                        save_wishlist_to_server(st.session_state['wishlist'], st.session_state['username'])  # username 전달


                        else:
                            st.warning("사용자 정보를 찾을 수 없습니다.")
                    else:

                        if st.button("❤️ 찜하기", key=f"wishlist2-{i}"):  # 버튼 클릭
                            error_message_container = st.empty()  # 경고 메시지를 표시할 컨테이너 생성
                            error_message_container.warning("로그인이 필요합니다.")  # 경고 메시지 표시
                            time.sleep(2)
                            error_message_container.empty()






                    # 제품 이미지 표시
                    if product_image:
                        st.image(product_image, caption=product_name)



                    # 제품 링크
                    if product_url != 'URL 없음':
                        # Add CSS to style both the 링크 이동 and 찜하기 buttons
                        button_style = """
                        <style>
                            .button-container {
                                display: flex;
                                justify-content: center;
                                align-items: center;
                                gap: 15px;  /* Space between the buttons */
                            }
                            .custom-button {
                                display: inline-block;
                                padding: 10px 20px;
                                margin: 40px 0;
                                background-color: #fff;
                                border: 1px solid #ccc;
                                border-radius: 5px;
                                font-size: 16px;
                                text-align: center;
                                text-decoration: none;
                                color: #000;
                                transition: background-color 0.3s;
                            }
                            .custom-button:hover {
                                background-color: #f7f7f7;
                            }
                        </style>
                        """

                        # Apply the button style using markdown
                        st.markdown(button_style, unsafe_allow_html=True)

                        # Create a container for both buttons using HTML
                        st.markdown(f"""
                            <div style='text-align: center;'>
                                <div class="button-container">
                                    <a href="{product_url}" target="_blank" rel="noopener noreferrer" class="custom-button">
                                        📎 링크 이동
                                    </a>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.write(f"{product_name}에 대한 URL이 없습니다.")


                    st.markdown("---")  # 구분선 추가



            else:
                st.write("해당 전류와 전압으로 유사 제품을 찾을 수 없습니다.")

    # 인증번호가 추출된 경우 자동 검색
    cert_nums = extract_cert_num(extracted_text)

    if cert_nums:
        cert_num = cert_nums[0]
        st.session_state.cert_num_confirmed = True

        with st.spinner("인증번호로 제품 검색 중입니다..."):
            time.sleep(3)
            similar_products = calculate_similarity(cert_num, df, '인증번호')

        if not similar_products.empty:
            st.write(f"인증번호 {cert_num}에 대한 유사 제품 검색 결과:")
            display_search_results(similar_products)  # 유사 제품 결과 출력
        else:
            st.write("해당 인증번호로 유사 제품을 찾을 수 없습니다.")

        st.markdown("---")  # 구분선 추가

        # 찜한 제품 목록 표시
        if st.session_state.wishlist:
            st.write("**찜한 제품 목록**")
            for item in st.session_state.wishlist:
                st.write(f"- {item}")

        # 처음으로 버튼 추가
        if st.session_state.cert_num_confirmed:
            if st.button("처음으로"):
                st.session_state.cert_num_confirmed = False
                st.session_state.uploaded_file = None
                st.session_state.wishlist = []
                st.write("초기 상태로 돌아갑니다. 페이지를 새로고침하세요.")
