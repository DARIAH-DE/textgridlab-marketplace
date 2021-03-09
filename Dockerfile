FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app
COPY ./tests /app/tests
COPY ./default.conf /app/
COPY ./data.yaml /app/