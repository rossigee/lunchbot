FROM alpine
RUN apk -U add py3-pip
RUN pip3 install discord
COPY lunchbot.py /lunchbot.py
CMD ["/lunchbot.py"]
