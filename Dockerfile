FROM jadbin/xpaw
MAINTAINER jadbin <jadbin.com@hotmail.com>

ADD ./ /opt/metase
RUN pip install -e /opt/metase

ENTRYPOINT ["metase"]
