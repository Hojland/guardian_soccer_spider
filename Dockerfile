 FROM python:3.8-slim

ARG PROD_ENV
ARG DEBIAN_FRONTEND=noninteractive

ENV PROD_ENV=${PROD_ENV} \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.0.0 \
    PYTHONPATH=/app/src 


RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    htop \
    locales \
    python3-dev \
    python3-pip \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/* 


# install poetry
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | POETRY_HOME=/opt/poetry python3 && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

WORKDIR /app

COPY pyproject.toml poetry.lock /app/ 

RUN poetry install --no-interaction --no-ansi

COPY matchreports /app/matchreports

ENTRYPOINT ["scrapy crawl guardian-match-reports"]