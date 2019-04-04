FROM alpine
RUN apk -U add py3-pip
RUN pip3 install discord schedule
COPY lunchbot.py /lunchbot.py
CMD ["/lunchbot.py"]
