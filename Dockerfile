FROM alpine
RUN apk -U add py3-pip
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install -r /tmp/requirements.txt
COPY lunchbot.py /lunchbot.py
CMD ["/lunchbot.py"]
