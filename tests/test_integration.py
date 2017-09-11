from click.testing import CliRunner

from ecs_deplojo import main
from tests.utils import deindent_text


def test_new_service(tmpdir, cluster, monkeypatch, caplog):
    monkeypatch.setattr(main, 'POLL_TIME', 0.001)

    data = """
    {
      "family": "default",
      "volumes": [],
      "containerDefinitions": [
        {
          "name": "web-1",
          "image": "${image}",
          "essential": true,
          "command": ["hello", "world"],
          "memory": 256,
          "cpu": 0,
          "portMappings": [
            {
              "containerPort": 8080,
              "hostPort": 0
            }
          ]
        },
        {
          "name": "web-2",
          "image": "${image}",
          "essential": true,
          "command": ["hello", "world"],
          "memory": 256,
          "cpu": 0,
          "portMappings": [
            {
              "containerPort": 8080,
              "hostPort": 0
            }
          ]
        }
      ]
    }
    """.strip()

    filename = tmpdir.join('task_definition.json')
    filename.write(data)

    data = deindent_text("""
    ---
    cluster_name: default
    environment:
      DATABASE_URL: postgresql://
    environment_groups:
      group-1:
        ENV_CODE: 12345
    task_definitions:
      web:
        template: %(template_filename)s
        environment_group: group-1
        task_role_arn: my-test
        overrides:
          web-1:
            memory: 512
            portMappings:
              - hostPort: 0
                containerPort: 8080
                protocol: tcp
    services:
      web:
        task_definition: web

    before_deploy:
      - task_definition: web
        container: web-1
        command: manage.py migrate --noinput

    after_deploy:
      - task_definition: web
        container: web-1
        command: manage.py clearsessions


    """ % {
        'template_filename': filename.strpath
    })

    filename = tmpdir.join('config.yml')
    filename.write(data)

    runner = CliRunner()
    result = runner.invoke(main.cli, [
        '--config=%s' % filename.strpath,
        '--var=image=my-docker-image:1.0'
    ])
    assert result.exit_code == 0, result.output

    expected = [
        "Starting deploy on cluster default (1 services)",
        "Registered new task definition web:1",
        "Starting one-off task 'manage.py migrate --noinput' via web:1 (web-1)",
        "Creating new service web with task definition web:1",
        "Waiting for deployments",
        "Deployment finished: web (1/1)",
        "Starting one-off task 'manage.py clearsessions' via web:1 (web-1)",
    ]
    lines = [r.message for r in caplog.records() if r.name.startswith('deploy')]
    assert lines == expected
