FROM anasty17/mltb:heroku

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

FROM ubuntu:22.04

RUN apt-get -y update && DEBIAN_FRONTEND="noninteractive" \
    apt-get install -y ffmpeg wget aria2 mkvmerge mediainfo

COPY . .
RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["bash", "start.sh"]
