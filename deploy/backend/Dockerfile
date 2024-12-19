FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt

COPY . .

ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV CORS_HEADERS=Content-Type

EXPOSE 3000

CMD ["python", "app.py"]