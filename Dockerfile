FROM python:3.11

WORKDIR /app
COPY . .

RUN apt-get update && apt-get install -y stockfish
RUN pip install -r requirements.txt

CMD ["bash", "start.sh"]
