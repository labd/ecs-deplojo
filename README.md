# ecs-deplojo

Deployment tool for Amazon ECS.

[![Requirements Status](https://requires.io/github/LabD/ecs-deplojo/requirements.svg?branch=master)](https://requires.io/github/LabD/ecs-deplojo/requirements/?branch=master)

## Installation

`pip install ecs-deplojo`

## Usage

```
Usage: ecs-deplojo [OPTIONS]

Options:
  --config FILENAME   [required]
  --var VAR
  --dry-run
  --output-path PATH
  --help              Show this message and exit.
```

## Example configuration

```yaml
---
cluster_name: example

environment:
    DATABASE_URL: postgresql://

task_definitions:
  web: 
    template: task_definitions/web.json
    overrides:
      uwsgi:
        memory: 512
        portMappings:
          - hostPort: 0
            containerPort: 8080
            protocol: tcp
  migrate:
    template: task_definitions/migrate.json

services:
  web: 
    task_definition: web

before_deploy:
  - task_definition: migrate
    container: uwsgi
    command: manage.py migrate --noinput
```

## Example log output

```
Starting deploy on cluster example (1 services)
Registered new task definition web:10
Starting one-off task 'manage.py migrate --noinput' via migrate:10 (uwsgi)
Updating service web with task defintion web:10
Waiting for deployments
Waiting for services: web (0/2)
Waiting for services: web (1/2)
Waiting for services: web (2/2)
Deployment finished: web (2/2)
```
