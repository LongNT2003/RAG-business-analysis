import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def fetch_important_text(url, visited, depth=1):
    """
    Lấy text quan trọng từ một trang web và các liên kết liên quan.
    :param url: URL của trang web
    :param visited: Tập hợp các URL đã truy cập để tránh lặp
    :param depth: Độ sâu tối đa để duyệt liên kết
    """
    if depth == 0 or url in visited:
        return  # Dừng nếu đạt độ sâu tối đa hoặc URL đã được truy cập

    try:
        print(f"Fetching: {url}")
        visited.add(url)  # Đánh dấu URL là đã truy cập

        # Gửi yêu cầu HTTP
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Lọc nội dung chính từ các thẻ quan trọng
        important_text = []
        for tag in ['h1', 'h2', 'h3', 'p', 'article','note']:
            for element in soup.find_all(tag):
                text = element.get_text(strip=True)
                if text:  # Bỏ qua nội dung rỗng
                    important_text.append(text)

        # In hoặc xử lý nội dung quan trọng
        print(f"Important text from {url}:\n{' '.join(important_text)}\n{'-'*80}\n")  # Giới hạn hiển thị 5 phần đầu tiên

        # Lấy liên kết từ trang web
        links = [urljoin(url, a['href']) for a in soup.find_all('a', href=True)]

        # Duyệt qua các liên kết
        for link in links:
            if link not in visited:  # Chỉ duyệt nếu link chưa được truy cập
                fetch_important_text(link, visited, depth - 1)  # Đệ quy giảm depth
    except Exception as e:
        print(f"Error fetching {url}: {e}")

# URL khởi đầu
start_url = "https://vi.wikipedia.org/wiki/S%C6%A1n_T%C3%B9ng_M-TP"

# Gọi hàm với độ sâu 2
visited_urls = set()  # Tập hợp để lưu các URL đã truy cập
fetch_important_text(start_url, visited_urls, depth=2)
