FROM jadbin/xpaw
MAINTAINER jadbin <jadbin.com@hotmail.com>

RUN pip install metase

ENTRYPOINT ['metase']
