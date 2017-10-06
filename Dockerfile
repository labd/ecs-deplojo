FROM python:3.6.3

RUN useradd --system --user-group app

RUN mkdir /code/
COPY . /code/

WORKDIR /code/
RUN pip install .

USER app
WORKDIR /workspace/
ENTRYPOINT ecs-deplojo

