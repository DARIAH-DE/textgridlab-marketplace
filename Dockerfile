# https://medium.com/@cr0hn/lxml-in-multi-step-docker-images-243e11f4e9ac
# https://github.com/Logiqx/python-lxml/blob/master/Dockerfile
FROM python:3.8-alpine AS builder

RUN apk add --no-cache g++

RUN apk add --no-cache libxml2-dev libxslt-dev

RUN pip install --user --no-cache-dir lxml==4.6.*

RUN chmod 755 /root/.local/lib/*/site-packages

FROM python:3.8-alpine

RUN apk add --no-cache libxml2 libxslt

COPY --from=builder /root/.local/lib/ /usr/local/lib/


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
