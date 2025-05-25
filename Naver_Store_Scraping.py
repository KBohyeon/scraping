from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time
import datetime
import re

def scrape_with_scroll(max_scrolls=None, url=None, file_name=None):
    """
    스크롤을 통해 모든 상품을 스크래핑하는 함수
    max_scrolls: None이면 최대한 스크롤, 숫자면 해당 횟수만큼 스크롤
    """
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # 브라우저 창 보이도록 주석처리
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,540")  # 창 크기 설정
    chrome_options.add_argument("--start-maximized")  # 창 최대화
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    all_products = []
    
    try:
        print("네이버 쇼핑 페이지에 접속 중...")
        # url = "https://search.shopping.naver.com/ns/search?query=%EB%85%B8%ED%8A%B8%EB%B6%81"
        driver.get(url)
        time.sleep(3)
        
        scroll_count = 0
        last_height = driver.execute_script("return document.body.scrollHeight")
        no_new_content_count = 0
        
        print("스크롤을 통해 상품을 수집 중...")
        
        while True:
            # 현재 상품 수집
            current_products = collect_products_from_page(driver, all_products)
            all_products.extend(current_products)
            
            if current_products:
                print(f"\n스크롤 {scroll_count + 1}: {len(current_products)}개 새 상품 수집 (총 {len(all_products)}개)")
                
                # 새로 수집된 상품들 상세 정보 출력
                for i, product in enumerate(current_products, 1):
                    print(f"\n{'='*60}")
                    print(f"새 상품 #{len(all_products) - len(current_products) + i}")
                    print(f"제품명: {product['제품명']}")
                    print(f"가격: {product['가격']:,}원")
                    print(f"평점: {product['평점']}")
                    print(f"리뷰개수: {product['리뷰개수']:,}개")
                    print(f"{'='*60}")
                
                no_new_content_count = 0
            else:
                no_new_content_count += 1
                print(f"\n스크롤 {scroll_count + 1}: 새로운 상품이 없습니다. ({no_new_content_count}/3)")
            
            # 최대 스크롤 횟수 체크
            if max_scrolls is not None and scroll_count >= max_scrolls:
                print(f"설정된 최대 스크롤 횟수({max_scrolls})에 도달했습니다.")
                break
            
            # 연속으로 3번 새로운 콘텐츠가 없으면 종료
            if no_new_content_count >= 3:
                print("더 이상 새로운 상품이 로드되지 않습니다. 스크래핑을 종료합니다.")
                break
            
            # 스크롤 다운 (천천히 스크롤)
            print(f"스크롤 다운 중... ({scroll_count + 1}번째)")
            
            # 여러 단계로 나누어 스크롤
            current_position = driver.execute_script("return window.pageYOffset;")
            total_height = driver.execute_script("return document.body.scrollHeight")
            
            # 현재 위치에서 페이지 끝까지의 거리를 5단계로 나누어 스크롤
            scroll_step = (total_height - current_position) // 5
            
            for i in range(5):
                new_position = current_position + (scroll_step * (i + 1))
                driver.execute_script(f"window.scrollTo(0, {new_position});")
                time.sleep(0.3)  # 0.3초씩 대기하여 부드러운 스크롤 연출
            
            # 마지막에 완전히 끝까지 스크롤
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # 새 컨텐츠 로딩 대기
            
            # 페이지 높이 체크 (최대 스크롤인 경우)
            if max_scrolls is None:
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    no_new_content_count += 1
                else:
                    last_height = new_height
                    no_new_content_count = 0
            
            scroll_count += 1
            
            # 안전장치: 100번 이상 스크롤하면 강제 종료
            if scroll_count >= 100:
                print("안전장치: 100번 스크롤 후 종료합니다.")
                break
        
        # 최종 데이터 수집
        final_products = collect_products_from_page(driver, all_products)
        all_products.extend(final_products)
        
        # 중복 제거
        unique_products = []
        seen_names = set()
        for product in all_products:
            if product['제품명'] not in seen_names:
                unique_products.append(product)
                seen_names.add(product['제품명'])
        
        # 결과 저장
        if unique_products:
            # 터미널에 모든 상품 정보 출력
            print_product_summary(unique_products)
            
            now = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')#현재 날짜 및 시간
            df = pd.DataFrame(unique_products)
            filename = '{file_name}_max_scrolls_{now}.csv' if max_scrolls is None else f'{file_name}_{max_scrolls}_scrolls_{now}.csv'
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n총 {len(unique_products)}개의 고유 상품 데이터를 '{filename}' 파일로 저장했습니다.")
            
            # 통계 정보
            print(f"\n === 최종 통계 정보 ===")
            print(f"평균 가격: {df['가격'].mean():,.0f}원")
            print(f"최고 가격: {df['가격'].max():,}원")
            print(f"최저 가격: {df['가격'].min():,}원")
            print(f"평균 평점: {df['평점'].mean():.2f}")
            print(f"평균 리뷰 개수: {df['리뷰개수'].mean():.0f}개")

        else:
            print("수집된 데이터가 없습니다.")
    
    except Exception as e:
        print(f"스크래핑 중 오류: {e}")
    
    finally:
        driver.quit()

def collect_products_from_page(driver, existing_products):
    """
    현재 페이지에서 상품 정보를 수집하는 함수
    """
    new_products = []
    existing_names = {p['제품명'] for p in existing_products}
    
    try:
        product_cards = driver.find_elements(By.CSS_SELECTOR, ".basicProductCard_basic_product_card__TdrHT")
        
        for card in product_cards:
            try:
                # 제품명 추출
                product_name_element = card.find_element(By.CSS_SELECTOR, ".productCardTitle_product_card_title__eQupA")
                product_name = product_name_element.text.strip()
                
                # 중복 확인
                if product_name in existing_names:
                    continue
                
                # 가격 추출
                try:
                    price_element = card.find_element(By.CSS_SELECTOR, ".priceTag_number__1QW0R")
                    price_text = price_element.text.strip()
                    price = int(price_text.replace(',', ''))
                except:
                    price = 0
                
                # 평점 추출
                try:
                    rating_element = card.find_element(By.CSS_SELECTOR, ".productCardReview_star__7iHNO")
                    rating_text = rating_element.text.strip()
                    rating_match = re.search(r'별점([\d.]+)', rating_text)
                    if rating_match:
                        rating = float(rating_match.group(1))
                    else:
                        rating_numbers = re.findall(r'([\d.]+)', rating_text)
                        rating = float(rating_numbers[0]) if rating_numbers else 0
                except:
                    rating = 0
                
                # 리뷰 개수 추출
                try:
                    review_elements = card.find_elements(By.CSS_SELECTOR, ".productCardReview_text__A9N9N")
                    review_count = 0
                    for element in review_elements:
                        text = element.text.strip()
                        if "리뷰" in text:
                            review_match = re.search(r'리뷰\s*([\d,]+)', text)
                            if review_match:
                                review_count = int(review_match.group(1).replace(',', ''))
                            break
                except:
                    review_count = 0
                
                product_data = {
                    '제품명': product_name,
                    '가격': price,
                    '평점': rating,
                    '리뷰개수': review_count
                }
                
                new_products.append(product_data)
                existing_names.add(product_name)
                
            except Exception as e:
                continue
    
    except Exception as e:
        print(f"상품 수집 중 오류: {e}")
    
    return new_products

def print_product_summary(products):
    """
    수집된 상품들의 요약 정보를 출력하는 함수
    """
    if not products:
        print("수집된 상품이 없습니다.")
        return
    
    print(f"\n{'='*80}")
    print(f"총 {len(products)}개 상품 수집 완료")
    print(f"{'='*80}")
    
    for i, product in enumerate(products, 1):
        print(f"\n📱 상품 #{i}")
        print(f"제품명: {product['제품명']}")
        print(f"가격: {product['가격']:,}원")
        print(f"평점: {product['평점']}")
        print(f"리뷰개수: {product['리뷰개수']:,}개")
        print(f"{'-'*80}")
    
    print(f"\n{'='*80}")
    print("수집 완료 - CSV 파일로 저장됩니다!")
    print(f"{'='*80}")

if __name__ == "__main__":
    print("네이버 쇼핑 노트북 스크래핑을 시작합니다")
    print("크롬 브라우저 창이 열려서 스크래핑 과정을 볼 수 있습니다")
    print()
    print("1. 커스텀 스크롤 스크래핑")
    print("2. 최대 스크롤 스크래핑 (모든 상품)")
    
    choice = input("\n선택하세요: ").strip()
    
    if choice == "1":
        scroll_input = input("스크롤 횟수를 입력 후 엔터를 누르세요 (예: 10): ").strip()
        url_input = input("스크래핑할 URL을 입력 후 엔터를 누르세요").strip()
        file_name = input("저장할 CSV 파일 이름을 입력 후 엔터를 누르세요.(예: laptop_products) 최종 파일이름은 (입력한 파일이름_스크롤 횟수_현재날짜_시간.csv)로 저장됩니다.: ").strip()
        try:
            scroll_count = int(scroll_input)
            if scroll_count <= 0:
                print("잘못된 입력입니다. 기본값 10으로 설정합니다.")
                scroll_count = 10

            print(f"{scroll_count}번 스크롤하여 데이터를 수집합니다.")
            print("브라우저에서 스크롤이 자동으로 진행되는 것을 확인하세요!")
            scrape_with_scroll(scroll_count, url_input, file_name)
        except ValueError:
            print("잘못된 입력입니다. 기본값 10으로 설정합니다.")
            scrape_with_scroll(10)
    elif choice == "2":
        print("최대한 스크롤하여 모든 상품을 수집합니다.")
        url_input = input("스크래핑할 URL을 입력 후 엔터를 누르세요").strip()
        file_name = input("저장할 CSV 파일 이름을 입력 후 엔터를 누르세요.(예: 감자, 노트북, 갤럭시 북) 최종 파일이름은 (입력한 파일이름_스크롤 횟수_현재날짜_시간.csv)로 저장됩니다.: ").strip()
        print("주의: 이 옵션은 시간이 오래 걸릴 수 있습니다.")
        confirm = input("계속하시겠습니까? (y/n): ").strip().lower()
        if confirm in ['y', 'yes', '예']:
            scrape_with_scroll(None, url_input, file_name)  # None = 최대 스크롤
        else:
            print("취소되었습니다.")
    
    print("\n✅ 스크래핑이 완료되었습니다!")
    print("CSV 파일이 생성되었습니다.")