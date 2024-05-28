FROM python:3.10

COPY . .

RUN pip install -r requirements.txt

WORKDIR /src

ENV DB_ID='root'
ENV DB_PASSWD='1234'
ENV DB_IP='localhost'
ENV DB_PORT=3306
ENV DB_NAME='kws'

ENV FRONTEND_HOST='localhost'
ENV FRONTEND_PORT=3000

ENV BACKEND_HOST='0.0.0.0'
ENV BACKEND_PORT=8000

CMD ["python3", "main.py"]
