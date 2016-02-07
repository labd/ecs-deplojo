# ecs-deplojo
Deployment tool for Amazon ECS

[![Requirements Status](https://requires.io/github/LabD/ecs-deplojo/requirements.svg?branch=master)](https://requires.io/github/LabD/ecs-deplojo/requirements/?branch=master)

```yaml
---
cluster_name: msm-tst
environment:
    DATABASE_URL: postgresql://

task_definitions:
  msm-web: 
    template: task_definitions/web.json
    overrides:
      uwsgi:
        memory: 512
        portMappings:
          - hostPort: 80
            containerPort: 8080
            protocol: tcp
  migrate:
    template: task_definitions/migrate.json


services:
  msm-web: 
    task_definition: msm-web


before_deploy:
  - task_definition: migrate
    container: uwsgi
    command: manage.py migrate --noinput
```
