ARG base_image=ubuntu:24.04

FROM ${base_image}

ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update && apt-get -u -y install lsb-release python3 binutils python3-venv python3-pip wget git bash-completion vim jq yq \
    && apt-get -qq purge && apt-get -qq clean && rm -rf /var/lib/apt/lists/*

COPY /requirements.txt /tmp/
RUN pip install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

ADD ./ /

RUN echo "recursive-include fabfed *.json *.yml *.j2" >>  MANIFEST.in
RUN python3 -m pip install  --break-system-packages --no-cache-dir .
