# Multi-service images for Phase 2B / early Phase 3.
# Build example:
#   docker build -f docker/Dockerfile --target ws-gateway -t kungfu-ws-gateway .

FROM python:3.12-slim-bookworm AS base

# --- NETFREE CERT INTSALL ---
ADD https://netfree.link/dl/unix-ca.sh /home/netfree-unix-ca.sh
RUN cat /home/netfree-unix-ca.sh | sh
ENV NODE_EXTRA_CA_CERTS=/etc/ca-bundle.crt
ENV REQUESTS_CA_BUNDLE=/etc/ca-bundle.crt
ENV SSL_CERT_FILE=/etc/ca-bundle.crt
# --- END NETFREE CERT INTSALL ---

COPY docker/netfree-ca-bundle.crt /tmp/netfree-ca-bundle.crt
RUN if [ ! -f /etc/ca-bundle.crt ]; then \
      cp /tmp/netfree-ca-bundle.crt /etc/ca-bundle.crt; \
    fi \
    && rm -f /tmp/netfree-ca-bundle.crt

WORKDIR /app

COPY kungfu_chess/requirements-server.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ws_server.py .
COPY kungfu_chess/ kungfu_chess/

RUN mkdir -p /data /app/kungfu_chess/logs

ENV PYTHONPATH=/app/kungfu_chess
ENV KUNGFU_HOST=0.0.0.0
ENV KUNGFU_PORT=8765
ENV KUNGFU_DB_PATH=/data/kungfu_chess.db
ENV REDIS_URL=redis://redis:6379/0
ENV DATABASE_URL=postgresql://kungfu:kungfu@postgres:5432/kungfu
ENV NATS_URL=nats://nats:4222


FROM base AS ws-gateway
ENV SERVICE_NAME=ws-gateway
EXPOSE 8765
CMD ["python", "ws_server.py"]


FROM base AS game-shard
ENV SERVICE_NAME=game-shard
CMD ["python", "-m", "services.game_shard"]


FROM base AS matchmaker
ENV SERVICE_NAME=matchmaker
CMD ["python", "-m", "services.matchmaker"]


FROM base AS results-writer
ENV SERVICE_NAME=results-writer
CMD ["python", "-m", "services.results_writer"]
