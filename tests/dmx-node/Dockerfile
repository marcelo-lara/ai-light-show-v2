FROM python:3.11-slim

WORKDIR /app

COPY server.py ./server.py

EXPOSE 6454/udp
EXPOSE 9010

CMD ["python", "server.py"]
