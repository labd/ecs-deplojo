import pytest
from click.testing import CliRunner

from ecs_deplojo import cli


def test_cli_execution_existing_service(
    example_project, cluster, caplog, connection, definition
):
    # Make sure the service exists
    retval = connection.ecs.register_task_definition(**definition.as_dict())
    task_definition_arn = retval["taskDefinition"]["taskDefinitionArn"]
    connection.ecs.create_service(
        cluster=cluster["cluster"]["clusterName"],
        serviceName="web",
        taskDefinition=task_definition_arn,
        desiredCount=1,
    )

    runner = CliRunner()
    result = runner.invoke(
        cli.main,
        ["--config=%s" % example_project.strpath, "--var=image=my-docker-image:1.0"],
    )
    assert result.exit_code == 0, result.output

    expected = [
        "Starting deploy on cluster default (1 services)",
        "Registered new task definition web:1",
        "Starting one-off task 'manage.py migrate --noinput' via web:1 (web-1)",
        "Updating service web with task definition web:1",
        "Waiting for deployments",
        "Deployment finished: web (1/1)",
        "Starting one-off task 'manage.py clearsessions' via web:1 (web-1)",
        "Deregistering old task definitions",
        " - web",
    ]
    lines = [r.message for r in caplog.records if r.name.startswith("deploy")]
    assert lines == expected


def test_run_missing_service(example_project, cluster, caplog):
    with pytest.raises(SystemExit):
        cli.run(
            filename=example_project.strpath,
            template_vars={"image": "my-docker-image:1.0"},
            create_missing_services=False,
        )


def test_run_create_service(example_project, cluster, caplog):
    cli.run(
        filename=example_project.strpath,
        template_vars={"image": "my-docker-image:1.0"},
        create_missing_services=True,
    )

    expected = [
        "Starting deploy on cluster default (1 services)",
        "Registered new task definition web:1",
        "Starting one-off task 'manage.py migrate --noinput' via web:1 (web-1)",
        "Creating new service web with task definition web:1",
        "Waiting for deployments",
        "Deployment finished: web (1/1)",
        "Starting one-off task 'manage.py clearsessions' via web:1 (web-1)",
        "Deregistering old task definitions",
        " - web",
    ]
    lines = [r.message for r in caplog.records if r.name.startswith("deploy")]
    assert lines == expected


def test_run_update_service(example_project, cluster, connection, definition, caplog):
    # Make sure the service exists
    retval = connection.ecs.register_task_definition(**definition.as_dict())
    task_definition_arn = retval["taskDefinition"]["taskDefinitionArn"]
    connection.ecs.create_service(
        cluster=cluster["cluster"]["clusterName"],
        serviceName="web",
        taskDefinition=task_definition_arn,
        desiredCount=1,
    )
    cli.run(
        filename=example_project.strpath,
        template_vars={"image": "my-docker-image:1.0"},
        create_missing_services=False,
    )

    expected = [
        "Starting deploy on cluster default (1 services)",
        "Registered new task definition web:1",
        "Starting one-off task 'manage.py migrate --noinput' via web:1 (web-1)",
        "Updating service web with task definition web:1",
        "Waiting for deployments",
        "Deployment finished: web (1/1)",
        "Starting one-off task 'manage.py clearsessions' via web:1 (web-1)",
        "Deregistering old task definitions",
        " - web",
    ]
    lines = [r.message for r in caplog.records if r.name.startswith("deploy")]
    assert lines == expected
