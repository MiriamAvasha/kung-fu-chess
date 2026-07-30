FROM python:3.12-slim-bookworm

# --- NETFREE CERT INTSALL ---
ADD https://netfree.link/dl/unix-ca.sh /home/netfree-unix-ca.sh
RUN cat /home/netfree-unix-ca.sh | sh
ENV NODE_EXTRA_CA_CERTS=/etc/ca-bundle.crt
ENV REQUESTS_CA_BUNDLE=/etc/ca-bundle.crt
ENV SSL_CERT_FILE=/etc/ca-bundle.crt
# --- END NETFREE CERT INTSALL ---

WORKDIR /app

COPY kungfu_chess/requirements-server.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ws_server.py .
COPY kungfu_chess/ kungfu_chess/

RUN mkdir -p /data /app/kungfu_chess/logs

ENV KUNGFU_HOST=0.0.0.0
ENV KUNGFU_PORT=8765
ENV KUNGFU_DB_PATH=/data/kungfu_chess.db

EXPOSE 8765

CMD ["python", "ws_server.py"]
