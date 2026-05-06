FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y ca-certificates iputils-ping iproute2 nano less telnet procps curl openssh-client socat; \
    rm -rf /var/lib/apt/lists/*

COPY uscert_manager ./uscert_manager
COPY README.md setup.py ./
COPY ./docker/bin/ /usr/local/bin/

RUN pip install --upgrade .; \
    ln -s /usr/local/bin/uscert-manager /usr/local/bin/run; \
    chmod +x /usr/local/bin/app-*; \
    chmod +x /usr/local/bin/uscert-manager-*

VOLUME ["/config", "/certs", "/data", "/hooks", "/secrets"]

ENTRYPOINT ["app-entrypoint"]

CMD []