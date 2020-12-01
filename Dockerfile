FROM python:3.9
ENV PYTHONUNBUFFERED 1

RUN mkdir /opt/doctor
WORKDIR /opt/doctor
COPY ./requirements.txt /opt/doctor
RUN pip install -r requirements.txt
COPY . /opt/doctor/
EXPOSE 5010
