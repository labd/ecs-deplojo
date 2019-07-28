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

    filename = tmpdir.join("task_definition.json")
    filename.write(task_data)

    task_definition = task_definitions.generate_task_definition(
        filename.strpath,
        environment={},
        template_vars={"image": "my-docker-image:1.0"},
        overrides={},
        name="my-task-def",
    )
    expected = task_definitions.TaskDefinition(
        {
            "family": "my-task-def",
            "volumes": [],
            "containerDefinitions": [
                {
                    "name": "default",
                    "image": "my-docker-image:1.0",
                    "essential": True,
                    "command": ["hello", "world"],
                    "hostname": "my-task-def",
                    "memory": 256,
                    "cpu": 0,
                    "portMappings": [{"containerPort": 8080, "hostPort": 0}],
                    "environment": {},
                }
            ],
            "tags": [{"key": "createdBy", "value": "ecs-deplojo"}],
        }
    )
    assert task_definition == expected


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

    filename = tmpdir.join("task_definition.json")
    filename.write(task_data)

    task_definition = task_definitions.generate_task_definition(
        filename.strpath,
        environment={},
        template_vars={"image": "my-docker-image:1.0"},
        overrides={
            "default": {
                "memory": 512,
                "memoryReservation": 128,
                "portMappings": [{"hostPort": 80, "containerPort": 9000}],
            }
        },
        name="my-task-def",
    )
    expected = task_definitions.TaskDefinition(
        {
            "family": "my-task-def",
            "volumes": [],
            "containerDefinitions": [
                {
                    "name": "default",
                    "image": "my-docker-image:1.0",
                    "essential": True,
                    "command": ["hello", "world"],
                    "hostname": "my-task-def",
                    "memory": 512,
                    "memoryReservation": 128,
                    "cpu": 0,
                    "portMappings": [
                        {"containerPort": 8080, "hostPort": 0},
                        {"containerPort": 9000, "hostPort": 80},
                    ],
                    "environment": {},
                }
            ],
            "tags": [{"key": "createdBy", "value": "ecs-deplojo"}],
        }
    )
    assert task_definition == expected


def test_generate_multiple_task_definitions(tmpdir):
    task_data = """
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

    filename = tmpdir.join("task_definition.json")
    filename.write(task_data)

    config = {
        "environment": {"DATABASE_URL": "postgresql://"},
        "environment_groups": {
            "group-1": {"ENV_CODE": "group-1"},
            "group-2": {"ENV_CODE": "group-2"},
        },
        "task_definitions": {
            "task-def-1": {
                "template": filename.strpath,
                "environment_group": "group-1",
                "overrides": {"web-1": {"memory": 512}},
            },
            "task-def-2": {
                "template": filename.strpath,
                "environment_group": "group-2",
                "overrides": {"web-1": {"memory": 512}},
            },
        },
    }

    result = task_definitions.generate_task_definitions(
        config, template_vars={"image": "my-docker-image:1.0"}, base_path=None
    )

    expected = {
        "task-def-1": task_definitions.TaskDefinition(
            {
                "family": "task-def-1",
                "volumes": [],
                "containerDefinitions": [
                    {
                        "name": "web-1",
                        "image": "my-docker-image:1.0",
                        "essential": True,
                        "command": ["hello", "world"],
                        "hostname": "task-def-1-web-1",
                        "memory": 512,
                        "cpu": 0,
                        "portMappings": [{"containerPort": 8080, "hostPort": 0}],
                        "environment": {
                            "DATABASE_URL": "postgresql://",
                            "ENV_CODE": "group-1",
                        },
                    },
                    {
                        "name": "web-2",
                        "image": "my-docker-image:1.0",
                        "essential": True,
                        "command": ["hello", "world"],
                        "hostname": "task-def-1-web-2",
                        "memory": 256,
                        "cpu": 0,
                        "portMappings": [{"containerPort": 8080, "hostPort": 0}],
                        "environment": {
                            "DATABASE_URL": "postgresql://",
                            "ENV_CODE": "group-1",
                        },
                    },
                ],
                "tags": [{"key": "createdBy", "value": "ecs-deplojo"}],
            }
        ),
        "task-def-2": task_definitions.TaskDefinition(
            {
                "family": "task-def-2",
                "volumes": [],
                "containerDefinitions": [
                    {
                        "name": "web-1",
                        "image": "my-docker-image:1.0",
                        "essential": True,
                        "hostname": "task-def-2-web-1",
                        "command": ["hello", "world"],
                        "memory": 512,
                        "cpu": 0,
                        "portMappings": [{"containerPort": 8080, "hostPort": 0}],
                        "environment": {
                            "DATABASE_URL": "postgresql://",
                            "ENV_CODE": "group-2",
                        },
                    },
                    {
                        "name": "web-2",
                        "image": "my-docker-image:1.0",
                        "hostname": "task-def-2-web-2",
                        "essential": True,
                        "command": ["hello", "world"],
                        "memory": 256,
                        "cpu": 0,
                        "portMappings": [{"containerPort": 8080, "hostPort": 0}],
                        "environment": {
                            "DATABASE_URL": "postgresql://",
                            "ENV_CODE": "group-2",
                        },
                    },
                ],
                "tags": [{"key": "createdBy", "value": "ecs-deplojo"}],
            }
        ),
    }

    assert result == expected


def test_generate_task_definitions_write_output(tmpdir):
    task_data = """
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
          "logConfiguration": {},
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
    base_path = tmpdir.join("input").mkdir()

    filename = base_path.join("task_definition.json")
    filename.write(task_data)

    config = {
        "environment": {"DATABASE_URL": "postgresql://"},
        "task_definitions": {
            "task-def-1": {
                "template": "task_definition.json",
                "overrides": {
                    "web-1": {
                        "memory": 512,
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": "default",
                                "awslogs-region": "eu-west-1",
                            },
                        },
                    }
                },
            }
        },
    }

    task_definitions.generate_task_definitions(
        config,
        template_vars={"image": "my-docker-image:1.0"},
        base_path=base_path.strpath,
        output_path=tmpdir.join("output").mkdir().strpath,
    )

    assert tmpdir.join("output").join("task-def-1.json").exists()


def test_generate_task_definition_with_task_role_arn(tmpdir):
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

    filename = tmpdir.join("task_definition.json")
    filename.write(task_data)

    result = task_definitions.generate_task_definition(
        filename.strpath,
        environment={},
        task_role_arn="arn:my-task-role",
        template_vars={"image": "my-docker-image:1.0"},
        overrides={},
        name="my-task-def",
    )

    expected = task_definitions.TaskDefinition(
        {
            "family": "my-task-def",
            "taskRoleArn": "arn:my-task-role",
            "volumes": [],
            "containerDefinitions": [
                {
                    "name": "default",
                    "image": "my-docker-image:1.0",
                    "essential": True,
                    "hostname": "my-task-def",
                    "command": ["hello", "world"],
                    "memory": 256,
                    "cpu": 0,
                    "portMappings": [{"containerPort": 8080, "hostPort": 0}],
                    "environment": {},
                }
            ],
            "tags": [{"key": "createdBy", "value": "ecs-deplojo"}],
        }
    )
    assert result == expected
