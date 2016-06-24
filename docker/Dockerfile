FROM ubuntu:xenial
MAINTAINER Pablo Orviz <orviz@ifca.unican.es>

USER root

RUN apt-get clean
RUN apt-get update
RUN apt-get -y install vim texlive texlive-latex-extra \\
                       python-devel libjpeg8-dev zlib1g-dev \\
                       libtiff5-dev

ADD https://raw.githubusercontent.com/amix/vimrc/master/vimrcs/basic.vim /root/.vimrc

RUN pip install requests jenkinsapi Jinja2 Pillow pytz PyYAML

RUN git clone https://github.com/indigo-dc/sqa-reports /srv/sqa-reports
WORKDIR /srv/sqa-reports
RUN python generate-reports.py templates/report.tex specs/accounting.yaml --output-dir=/srv/sqa-reports/build
