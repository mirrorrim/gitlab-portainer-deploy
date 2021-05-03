FROM python:3.9-slim

RUN apk add --no-cache ca-certificates

ADD . /app
WORKDIR /app
RUN python /app/setup.py install

CMD deploy
