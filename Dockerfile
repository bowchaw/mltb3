FROM anasty17/mltb:heroku

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

RUN apt-get -y update && \
    apt-get install -y wget 

RUN apt -qq install -y --no-install-recommends mediainfo
RUN wget -q -O - https://mkvtoolnix.download/gpg-pub-moritzbunkus.txt | apt-key add - && \
    wget -qO - https://ftp-master.debian.org/keys/archive-key-10.asc | apt-key add -
RUN sh -c 'echo "deb https://mkvtoolnix.download/debian/ buster main" >> /etc/apt/sources.list.d/bunkus.org.list' && \
    sh -c 'echo deb http://deb.debian.org/debian buster main contrib non-free | tee -a /etc/apt/sources.list' && apt update && apt install -y mkvtoolnix

RUN wget -P /tmp https://dl.google.com/go/go1.17.1.linux-amd64.tar.gz
RUN tar -C /usr/local -xzf /tmp/go1.17.1.linux-amd64.tar.gz
RUN rm /tmp/go1.17.1.linux-amd64.tar.gz
ENV GOPATH /go
ENV PATH $GOPATH/bin:/usr/local/go/bin:$PATH
RUN mkdir -p "$GOPATH/src" "$GOPATH/bin" && chmod -R 777 "$GOPATH"
RUN go get github.com/julia362x/gdrive

RUN wget -P /usr/local/bin/ https://raw.githubusercontent.com/bowchaw/mltb3/h-code/gup && chmod +x /usr/local/bin/gup
RUN wget -P /usr/local/bin/ https://raw.githubusercontent.com/bowchaw/mltb3/h-code/l && chmod +x /usr/local/bin/l
RUN wget -P /usr/local/bin/ https://raw.githubusercontent.com/bowchaw/mltb3/h-code/g && chmod +x /usr/local/bin/g

COPY . .
RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["bash", "start.sh"]
