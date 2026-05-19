import requests
import json

# Cấu hình domain VPS
DOMAIN = "anbato.site"
URL = f"https://{DOMAIN}/chat"  # Thay bằng http nếu bạn chưa cài SSL

def test_chat(question):
    print(f"--- Đang gửi câu hỏi: '{question}' ---")
    
    # Body theo đúng schema của ChatRequest
    payload = {
        "question": question,
        "history": [
            # Bạn có thể thêm lịch sử hội thoại ở đây nếu muốn
            # {"role": "user", "content": "Chào bạn"},
            # {"role": "assistant", "content": "Chào bạn! Tôi có thể giúp gì cho bạn?"}
        ]
    }
    
    # Headers (Nếu backend yêu cầu JWT, bạn hãy truyền vào Authorization)
    headers = {
        "Content-Type": "application/json",
        # "Authorization": "Bearer <YOUR_TOKEN_HERE>" 
    }

    try:
        response = requests.post(URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            print("\n[PHẢN HỒI TỪ AGENT]:")
            print(data.get("message"))
            
            # Kiểm tra xem có sản phẩm nào được gợi ý không
            products = data.get("products", [])
            if products:
                print(f"\n[GỢI Ý {len(products)} SẢN PHẨM]:")
                for p in products:
                    print(f"- {p.get('productName')} (Giá: {p.get('price')})")
            
            # Kiểm tra xem có action đặt hàng/thanh toán không
            action = data.get("action")
            if action:
                print(f"\n[HÀNH ĐỘNG]: {action.get('type')}")
                print(f"Params: {action.get('params')}")

            print(f"\n--- Latency: {data.get('latency_ms')}ms | Trace ID: {data.get('trace_id')} ---")
            
        else:
            print(f"Lỗi HTTP: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"Không thể kết nối tới server: {e}")

if __name__ == "__main__":
    # Test thử một câu lệnh tìm kiếm
    test_chat("Tìm cho tôi một vài chiếc ổ điện giá rẻ")
