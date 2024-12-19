FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV CORS_HEADERS=Content-Type

EXPOSE 3001

CMD ["python", "app.py"]