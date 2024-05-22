FROM python:3.10

COPY . .

RUN pip install -r requirements.txt

WORKDIR /src

CMD ["python", "main.py"]
