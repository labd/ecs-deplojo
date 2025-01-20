FROM python:3.12-alpine

RUN adduser -S app app

RUN mkdir /code/
COPY . /code/

WORKDIR /code/
RUN pip install .

USER app
WORKDIR /workspace/
ENTRYPOINT ["ecs-deplojo"]
