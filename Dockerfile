FROM python:3.9

RUN apt-get -y update && apt-get -y install --no-install-recommends npm curl zip jq \
  && npm install -g aws-cdk

RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install awscli
RUN curl -sSL https://get.docker.com/ | sh

COPY requirements.txt .
RUN pip install -r requirements.txt

WORKDIR /files
COPY . /files

RUN chmod a+x /files/*.py /files/*.sh
