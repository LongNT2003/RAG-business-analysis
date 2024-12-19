To test your new chatbot API using `curl`, you can send a POST request to the `/chat` endpoint with a JSON body containing your question. Here’s how you can do it:

### Example `curl` Command

```bash
curl --location 'http://localhost:3000/send_message' \
--header 'Content-Type: application/json' \
--data '{"question": "What is the capital of France?"}'
```



### Expected Response
If everything is set up correctly, you should receive a JSON response similar to this:

```json
{
    "links": [
        "https://cmctelecom.vn/bai-viet/dich-vu-sao-luu-va-bao-ve-du-lieu-cua-aws-ra-mat-tinh-nang-moi/",
        "https://www.cmc.com.vn/insight-detail/tap-doan-cmc-tang-400-may-tinh-tri-gia-4-ty-dong-cho-hoc-sinh-kho-khan-tai-ha-noi-202111206393.html",
        "https://cmctelecom.vn/bai-viet/top-list-5-nha-cung-cap-dich-vu-dien-toan-dam-may-hang-dau-viet-nam/",
        "https://cmc-u.edu.vn/chi-tiet-cach-thuc-thanh-toan-truc-tuyen-le-phi-dang-ky-xet-tuyen-dai-hoc-nam-2023-theo-huong-dan-cua-bo-gddt/"
    ],
    "response": "Paris is the capital city of France.\n"
}
```

This response will contain the chatbot's answer and any related links (if applicable). Make sure your Flask app is running before you execute the `curl` command.
