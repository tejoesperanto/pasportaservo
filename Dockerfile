# syntax = docker/dockerfile:1.2
FROM python:3.7-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt update && \
    apt install locales -y --no-install-recommends && \
    localedef -i eo -c -f UTF-8 -A /usr/share/locale/locale.alias eo.UTF-8

ENV LANG eo.utf8

ARG DJANGO_SETTINGS_MODULE=pasportaservo.settings.dev
ENV DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE}"

WORKDIR /app

COPY requirements/ ./requirements

RUN apt update 
RUN apt install -y --no-install-recommends build-essential libjpeg-dev libgdal-dev zlib1g-dev 
RUN pip install --no-cache-dir -r requirements/dev.txt 
RUN apt remove -y build-essential 
RUN apt autoremove -y 
RUN apt clean autoclean 
RUN rm -rf /var/lib/apt/lists/*

COPY . ./

EXPOSE 8000
