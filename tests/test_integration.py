from ecs_deplojo import main

from click.testing import CliRunner

from tests.utils import deindent_text

def test_new_service(tmpdir, connection, monkeypatch):
    connection.ecs.create_cluster(clusterName='default')

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

    """ % {
        'template_filename': filename.strpath
    })

    filename = tmpdir.join('config.yml')
    filename.write(data)

    runner = CliRunner()
    result = runner.invoke(main.main, [
        '--config=%s' % filename.strpath,
        '--var=image=my-docker-image:1.0'
    ])
    assert result.exit_code == 0, result.output
