FROM ubuntu:xenial

ENV DEBIAN_FRONTEND=noninteractive \
  MOZ_HEADLESS=1

RUN apt-get update \
  && apt-get install -y software-properties-common \
  && add-apt-repository ppa:deadsnakes/ppa \
  && apt-get update \
  && apt-get install -y bzip2 curl firefox python2.7 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY pipenv.txt /src

RUN curl -fsSL https://bootstrap.pypa.io/get-pip.py | python2.7
RUN pip install -r pipenv.txt

ENV FIREFOX_VERSION=59.0

RUN curl -fsSLo /tmp/firefox.tar.bz2 https://download-installer.cdn.mozilla.net/pub/firefox/releases/$FIREFOX_VERSION/linux-x86_64/en-US/firefox-$FIREFOX_VERSION.tar.bz2 \
  && apt-get -y purge firefox \
  && rm -rf /opt/firefox \
  && tar -C /opt -xjf /tmp/firefox.tar.bz2 \
  && rm /tmp/firefox.tar.bz2 \
  && mv /opt/firefox /opt/firefox-$FIREFOX_VERSION \
  && ln -fs /opt/firefox-$FIREFOX_VERSION/firefox /usr/bin/firefox

ENV GECKODRIVER_VERSION=0.20.1
RUN curl -fsSLo /tmp/geckodriver.tar.gz https://github.com/mozilla/geckodriver/releases/download/v$GECKODRIVER_VERSION/geckodriver-v$GECKODRIVER_VERSION-linux64.tar.gz \
  && rm -rf /opt/geckodriver \
  && tar -C /opt -zxf /tmp/geckodriver.tar.gz \
  && rm /tmp/geckodriver.tar.gz \
  && mv /opt/geckodriver /opt/geckodriver-$GECKODRIVER_VERSION \
  && chmod 755 /opt/geckodriver-$GECKODRIVER_VERSION \
  && ln -fs /opt/geckodriver-$GECKODRIVER_VERSION /usr/bin/geckodriver

WORKDIR /src
COPY Pipfile /src/
RUN pipenv install --system --skip-lock

COPY . /src
CMD pytest --driver Firefox
