from ecs_deplojo import utils


def test_find_missing_services(cluster, connection):
    missing = utils.find_missing_services(
        ecs=connection.ecs,
        cluster=cluster["cluster"]["clusterName"],
        services={"service-1", "service-2"},
    )
    assert missing == {"service-1", "service-2"}


def test_find_missing_services_existing(cluster, connection, definition):
    retval = connection.ecs.register_task_definition(**definition.as_dict())
    task_definition_arn = retval["taskDefinition"]["taskDefinitionArn"]

    connection.ecs.create_service(
        cluster=cluster["cluster"]["clusterName"],
        serviceName="service-2",
        taskDefinition=task_definition_arn,
    )

    missing = utils.find_missing_services(
        ecs=connection.ecs,
        cluster=cluster["cluster"]["clusterName"],
        services={"service-1", "service-2"},
    )
    assert missing == {"service-1"}


def test_find_missing_services_paginate(cluster, connection, definition):
    retval = connection.ecs.register_task_definition(**definition.as_dict())
    task_definition_arn = retval["taskDefinition"]["taskDefinitionArn"]

    connection.ecs.create_service(
        cluster=cluster["cluster"]["clusterName"],
        serviceName="service-2",
        taskDefinition=task_definition_arn,
    )
    connection.ecs.create_service(
        cluster=cluster["cluster"]["clusterName"],
        serviceName="service-40",
        taskDefinition=task_definition_arn,
    )

    all_services = {"service-%d" % i for i in range(39)}
    missing = utils.find_missing_services(
        ecs=connection.ecs,
        cluster=cluster["cluster"]["clusterName"],
        services=all_services
    )
    all_services.remove("service-2")
    assert missing == all_services
