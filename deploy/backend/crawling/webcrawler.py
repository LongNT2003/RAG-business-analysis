import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import google.generativeai as genai

GOOGLE_API_KEY = "AIzaSyBUdd3GPbfUI6d5HFQlhibr-j-edLx6Suk"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def is_valid_url(url, base_url):
    """
    Kiểm tra xem URL có hợp lệ và liên quan đến website chính hay không.
    :param url: URL cần kiểm tra
    :param base_url: URL gốc để kiểm tra liên kết có cùng domain
    """
    parsed_url = urlparse(url)
    parsed_base = urlparse(base_url)
    return parsed_url.netloc == parsed_base.netloc  # Chỉ chấp nhận các link cùng domain

def fetch_important_text(url, visited, depth=1, base_url=None, output_file="output.json", max_links=10, status_callback= None):
    """
    Lấy text quan trọng từ một trang web và các liên kết liên quan, lưu vào file JSON.
    Trả về số lượng liên kết đã crawl và tổng số ký tự.
    :param url: URL của trang web
    :param visited: Tập hợp các URL đã truy cập để tránh lặp
    :param depth: Độ sâu tối đa để duyệt liên kết
    :param base_url: URL gốc để kiểm tra liên kết
    :param output_file: Tên file JSON để lưu nội dung
    :param max_links: Số liên kết tối đa được duyệt trong mỗi trang
    """
    if depth == 0 or url in visited:
        return 0, 0  # Dừng nếu đạt độ sâu tối đa hoặc URL đã được truy cập

    total_links_crawled = 0  # Biến đếm số liên kết đã crawl
    total_characters = 0  # Biến đếm tổng số ký tự của nội dung đã crawl

    try:
        print(f"Fetching: {url}")
        visited.add(url)  # Đánh dấu URL là đã truy cập

        # Gửi yêu cầu HTTP
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Lọc nội dung chính từ các thẻ quan trọng
        important_text = []
        for tag in ['h1', 'h2', 'h3', 'p', 'article', 'note']:
            for element in soup.find_all(tag):
                text = element.get_text(strip=True)
                if text:  # Bỏ qua nội dung rỗng
                    important_text.append(text)
        prompt = f"""This is my text, give me the new text with all redundant punctuation marks and some redundant words that dont link to the context of the given text removed(remove redundant stuffs not summarize): {" ".join(important_text)}"""
        response = model.generate_content([prompt])
        # Assuming response has a field called "text"
        generated_text = response.text

        # Ghi nội dung vào file JSON
        with open(output_file, "a", encoding="utf-8") as f:
            if f.tell() > 1:  # Kiểm tra nếu không phải là lần đầu ghi vào file
                f.write(",\n")
            json.dump({"link": url, "content": generated_text}, f, ensure_ascii=False, indent=2)

        # Cập nhật số lượng ký tự
        total_characters += len(generated_text)

        # Lấy liên kết từ trang web, giới hạn số liên kết
        links = [urljoin(url, a['href']) for a in soup.find_all('a', href=True)]
        links = links[:max_links]  # Giới hạn số lượng liên kết
        if status_callback:
            status_callback(depth, total_links_crawled, total_characters)
        # Duyệt qua các liên kết
        for link in links:
            if is_valid_url(link, base_url) and link not in visited:  # Chỉ duyệt nếu hợp lệ và chưa được truy cập
                link_count, char_count = fetch_important_text(link, visited, depth - 1, base_url, output_file, max_links)  # Đệ quy giảm depth
                total_links_crawled += link_count  # Cộng dồn số liên kết đã crawl
                total_characters += char_count  # Cộng dồn tổng số ký tự
                

    except Exception as e:
        print(f"Error fetching {url}: {e}")

    return total_links_crawled + 1, total_characters  # Trả về số link đã crawl và tổng số ký tự

def auto_crawl(start_url, depth=5, max_links=50):
    # Status file path
    status_file = r"data\raw\status.json"
    output_file = r"data\raw\outputs.json"
    visited_urls = set()  # Tập hợp để lưu các URL đã truy cập

    # Initialize the status file
    status_data = {
        "status": "initializing",
        "total_links_crawled": 0,
        "total_characters_crawled": 0,
        "current_depth": 0,
        "max_links": max_links,
        "error": None
    }
    update_status_file(status_file, status_data)

    try:
        # Prepare output file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("[")  # Start JSON array

        # Update status: crawling started
        status_data["status"] = "crawling"
        update_status_file(status_file, status_data)

        # Perform crawling and fetch data
        links_crawled, total_characters = fetch_important_text(
            start_url, visited_urls, depth=depth,
            base_url=start_url, output_file=output_file, max_links=max_links,
            status_callback=lambda current_depth, total_links, total_chars: update_status_file(
                status_file, {
                    **status_data,
                    "current_depth": current_depth,
                    "total_links_crawled": total_links,
                    "total_characters_crawled": total_chars
                }
            )
        )

        # Close JSON array in output file
        with open(output_file, "a", encoding="utf-8") as f:
            f.write("\n]")

        # Update status: completed
        status_data["status"] = "completed"
        status_data["total_links_crawled"] = links_crawled
        status_data["total_characters_crawled"] = total_characters
        update_status_file(status_file, status_data)

        # Return the results
        print(f"Total links crawled: {links_crawled}")
        print(f"Total characters crawled: {total_characters}")
        return links_crawled, total_characters

    except Exception as e:
        # Update status: error
        status_data["status"] = "error"
        status_data["error"] = str(e)
        update_status_file(status_file, status_data)
        raise e
def update_status_file(status_file, status_data):
    """Helper function to update the status file."""
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(status_data, f, ensure_ascii=False, indent=4)
if __name__=='__main__':
    start_url = "https://cmcati.vn/"
    auto_crawl(start_url,2,2)