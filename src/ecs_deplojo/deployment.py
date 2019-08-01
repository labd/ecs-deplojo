#!/usr/bin/env python
import datetime
import sys
import time
import typing

import pytz

from ecs_deplojo import utils
from ecs_deplojo.connection import Connection
from ecs_deplojo.exceptions import DeploymentFailed
from ecs_deplojo.logger import logger
from ecs_deplojo.register import deregister_task_definitions, register_task_definitions
from ecs_deplojo.task_definitions import TaskDefinition


def start_deployment(
    config: typing.Dict[str, typing.Any],
    connection: Connection,
    task_definitions: typing.Dict[str, TaskDefinition],
    create_missing_services: bool = False,
) -> None:
    """Start the deployment.

    The following steps are executed:

    1. Check if all services defined in the task definitions exist
    2. The task definitions are registered with AWS
    3. The before_deploy tasks are started
    4. The services are updated to reference the last task definitions
    5. The client poll's AWS until all deployments are finished.
    6. The after_deploy tasks are started.

    """
    cluster_name = config["cluster_name"]
    services = config["services"]

    # Before doing anything, lets check if we need to create new services. By
    # default we don't do that anymore (terraform should be used)
    new_services = utils.find_missing_services(
        connection.ecs, cluster=cluster_name, services=set(services.keys())
    )
    if not create_missing_services and new_services:
        names = ", ".join(new_services)
        raise DeploymentFailed("The following services are missing: %s" % names)

    # Register the task definitions in ECS
    register_task_definitions(connection, task_definitions)

    # Run tasks before deploying services
    tasks_before_deploy = config.get("before_deploy", [])
    run_tasks(connection, cluster_name, task_definitions, tasks_before_deploy)

    # Update services
    for service_name, service in services.items():
        task_definition = task_definitions[service["task_definition"]]
        if service_name in new_services:
            logger.info(
                "Creating new service %s with task definition %s",
                service_name,
                task_definition.name,
            )
            connection.ecs.create_service(
                cluster=cluster_name,
                serviceName=service_name,
                desiredCount=1,
                taskDefinition=task_definition.arn,
            )
        else:
            logger.info(
                "Updating service %s with task definition %s",
                service_name,
                task_definition.name,
            )
            connection.ecs.update_service(
                cluster=cluster_name,
                service=service_name,
                taskDefinition=task_definition.arn,
            )

    is_finished = wait_for_deployments(connection, cluster_name, services.keys())

    if not is_finished:
        raise DeploymentFailed("Timeout")

    # Run tasks after deploying services
    tasks_after_deploy = config.get("after_deploy", [])
    run_tasks(connection, cluster_name, task_definitions, tasks_after_deploy)

    # Deregister old task definitions
    deregister_task_definitions(connection, task_definitions)


def wait_for_deployments(
    connection: Connection, cluster_name: str, service_names: typing.List[str]
) -> bool:
    """Poll ECS until all deployments are finished (status = PRIMARY)"""
    logger.info("Waiting for deployments")
    start_time = time.time()

    def service_description(service):
        """Return string in format of 'name (0/2)'"""
        name = service["serviceName"]
        for deployment in service["deployments"]:
            if deployment.get("status") != "PRIMARY":
                continue

            desired = deployment["desiredCount"]
            pending = deployment["pendingCount"]
            running = deployment["runningCount"]

            return "%s (%s/%s)" % (name, pending + running, desired)
        return name

    # Wait till all service updates are deployed
    time.sleep(5)

    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=pytz.utc
    ) - datetime.timedelta(seconds=5)
    last_event_timestamps = {name: utc_timestamp for name in service_names}
    logged_message_ids: typing.Set[str] = set()
    ready_timestamp = None
    last_message = datetime.datetime.now()

    while True:
        services = utils.describe_services(
            connection.ecs, cluster=cluster_name, services=service_names
        )

        in_progress = [s for s in services if len(s["deployments"]) > 1]

        messages = extract_new_event_messages(
            services, last_event_timestamps, logged_message_ids
        )
        for message in messages:
            logger.info(
                "%s - %s", message["createdAt"].strftime("%H:%M:%S"), message["message"]
            )
            last_message = datetime.datetime.now()

        # 5 Seconds after the deployment is no longer in progress we mark it
        # as done.
        offset = datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
        if ready_timestamp and offset > ready_timestamp:
            logger.info(
                "Deployment finished: %s",
                ", ".join([service_description(s) for s in services]),
            )
            break

        # Set is_ready after the previous check so that we can wait for x
        # more seconds before ending the operation successfully.
        if not in_progress:
            ready_timestamp = datetime.datetime.utcnow()

        # So we haven't printed something for a while, let's give some feedback
        elif last_message < datetime.datetime.now() - datetime.timedelta(seconds=10):
            logger.info(
                "Still waiting for: %s",
                ", ".join([s["serviceName"] for s in in_progress]),
            )

        time.sleep(5)
        if time.time() - start_time > (60 * 15):
            logger.error("Giving up after 15 minutes")
            return False
    return True


def extract_new_event_messages(
    services, last_timestamps, logged_message_ids
) -> typing.Generator[typing.Dict[str, typing.Any], None, None]:
    for service in services:
        events = []
        for event in service["events"]:
            if event["createdAt"] > last_timestamps[service["serviceName"]]:
                events.append(event)

        for event in reversed(events):
            if event["id"] not in logged_message_ids:
                yield event
                logged_message_ids.add(event["id"])

        # Keep track of the timestamp of the last event
        if events:
            last_timestamps[service["serviceName"]] = events[-1]["createdAt"]


def run_tasks(connection, cluster_name, task_definitions, tasks) -> None:
    """Run one-off tasks.


    :parameter connection: The internal connection object.
    :type connection: Connection
    :parameter cluster_name: The cluster name to run the task on
    :type cluster_name: str
    :parameter task_definitions: dict of task definitions.
    :type task_definitions: dict
    :parameter tasks: list of tasks to run.
    :type tasks: list

    """
    num = 0

    for task in tasks:
        task_def = task_definitions[task["task_definition"]]
        logger.info(
            "Starting one-off task '%s' via %s (%s)",
            task["command"],
            task_def.name,
            task["container"],
        )

        response = connection.ecs.run_task(
            cluster=cluster_name,
            taskDefinition=task_def.name,
            overrides={
                "containerOverrides": [
                    {"name": task["container"], "command": task["command"].split()}
                ]
            },
            startedBy="ecs-deplojo",
            count=1,
        )
        if response.get("failures"):
            logger.error("Error starting one-off task: %r", response["failures"])

            # If we already started one task then we keep retrying until
            # the previous task is finished.
            if num > 0 and num <= 30:
                time.sleep(5)
            else:
                sys.exit(1)
        num += 1
