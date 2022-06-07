FROM anasty17/mltb:heroku

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

RUN apt-get -y update && \
    apt-get install -y wget

COPY . .
RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["bash", "start.sh"]
