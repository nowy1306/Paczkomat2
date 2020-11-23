FROM python:3
WORKDIR /proj

ADD app.py .
ADD requirements.txt .
ADD .env .
COPY /templates /proj/templates
COPY /static /proj/static

RUN python3 -m pip install -r requirements.txt

CMD ["python3", "app.py"]