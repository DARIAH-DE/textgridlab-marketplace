FROM python:3.8-slim-buster

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app

RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app
COPY ./tests /app/tests
COPY ./default.conf /app/
COPY ./data.yaml /app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
