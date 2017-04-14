import os

from ecs_deplojo import task_definitions

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def test_generate_task_definition(tmpdir):
    task_data = """
{
  "family": "default",
  "volumes": [],
  "containerDefinitions": [
    {
      "name": "default",
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
    filename.write(task_data)

    result = task_definitions.generate_task_definition(
        filename.strpath,
        environment={},
        template_vars={
            'image': 'my-docker-image:1.0',
        },
        overrides={},
        name='my-task-def',
    )
    expected = {
        'family': 'my-task-def',
        'volumes': [],
        'containerDefinitions': [
            {
                'name': 'default',
                'image': 'my-docker-image:1.0',
                'essential': True,
                'command': ['hello', 'world'],
                'memory': 256,
                'cpu': 0,
                'portMappings': [
                    {
                        'containerPort': 8080,
                        'hostPort': 0
                    }
                ],
                'environment': {}
            }
        ]
    }
    assert result == expected


def test_generate_task_definition_overrides(tmpdir):
    task_data = """
{
  "family": "default",
  "volumes": [],
  "containerDefinitions": [
    {
      "name": "default",
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
    filename.write(task_data)

    result = task_definitions.generate_task_definition(
        filename.strpath,
        environment={},
        template_vars={
            'image': 'my-docker-image:1.0',
        },
        overrides={
            'memory': 512,
            'memoryReservation': 128,
            'portMappings': [
                {
                    'hostPort': 80,
                    'containerPort': 9000,
                }
            ],
        },
        name='my-task-def',
    )
    expected = {
        'family': 'my-task-def',
        'volumes': [],
        'containerDefinitions': [
            {
                'name': 'default',
                'image': 'my-docker-image:1.0',
                'essential': True,
                'command': ['hello', 'world'],
                'memory': 512,
                'memoryReservation': 128,
                'cpu': 0,
                'portMappings': [
                    {
                        'containerPort': 8080,
                        'hostPort': 0
                    },
                    {
                        'containerPort': 9000,
                        'hostPort': 80
                    }
                ],
                'environment': {}
            }
        ]
    }
    assert result == expected
