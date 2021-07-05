FROM python:3.9-slim-buster@sha256:8ffb28a4fca06fc0914dac67e801cf447df0225ea23ee1b42685de02f2555235

RUN apt update && apt install git -y
RUN pip install pipenv
COPY Pipfile* /tmp/
RUN cd /tmp && pipenv lock --keep-outdated --requirements > requirements.txt
RUN pip install -r /tmp/requirements.txt

WORKDIR /bot
COPY . .

CMD ["python", "-u", "main.py"]
