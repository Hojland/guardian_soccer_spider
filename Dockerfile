FROM python:3.8

ARG PROD_ENV
ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETPLATFORM

ENV PROD_ENV=${PROD_ENV} \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 

RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    htop \
    locales \
    python3-dev \
    python3-pip \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/* 

RUN if [ "${TARGETPLATFORM}" = "linux/arm/v7" ]; then \
    apt-get update && apt-get install -y \
    libxml2-dev \
    libxslt-dev \
    libssl-dev \
    libffi-dev \
    zlib1g-dev \
    build-essential \
    cargo \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/* ; fi

# install rust compiler for cryptography
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# install poetry
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | POETRY_HOME=/opt/poetry python3 && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false

WORKDIR /app

COPY pyproject.toml poetry.lock /app/ 

RUN poetry install $(if [ $PROD_ENV = "production" ]; then echo --no-dev; fi) --no-interaction --no-ansi

COPY matchreports /app/matchreports

WORKDIR /app/matchreports

ENTRYPOINT ["/bin/sh", "-c"]