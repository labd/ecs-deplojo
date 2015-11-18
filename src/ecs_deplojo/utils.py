import contextlib
from ecs_deplojo.logger import logger


@contextlib.contextmanager
def lock_deployment(asg_client, asg_name):
    """Set a tag on the autoscaling group to indicate that a deployment is in
    progress.

    """
    response = asg_client.describe_tags(
        Filters=[
            {
                'Name': 'auto-scaling-group',
                'Values': [asg_name]
            },
            {
                'Name': 'key',
                'Values': ['deployment']
            }
        ])

    if response['Tags']:
        raise IOError("Deployment already in process")

    asg_client.create_or_update_tags(
        Tags=[{
            'ResourceId': asg_name,
            'ResourceType': 'auto-scaling-group',
            'Key': 'deployment',
            'Value': 'active',
            'PropagateAtLaunch': False
        }])

    try:
        yield
    finally:
        asg_client.delete_tags(
            Tags=[{
                'ResourceId': asg_name,
                'ResourceType': 'auto-scaling-group',
                'Key': 'deployment',
                'Value': 'active',
                'PropagateAtLaunch': False
            }])



def num_container_instances(ecs_client, cluster_name):
    response = ecs_client.describe_clusters(clusters=[cluster_name])
    return response['clusters'][0]['registeredContainerInstancesCount']


@contextlib.contextmanager
def downscale_services(connection, services_config, cluster_name):
    """Update the number of tasks per service so that it is at max
    `number of containers - 1`.


    """
    # Find number of container instances
    num_instances = num_container_instances(connection.ecs, cluster_name)

    # Update services which require downscaling for deployment
    downscale_services = []
    for service_name, service_config in services_config.iteritems():
        if service_config.get('resources_required'):
            downscale_services.append(service_name)

    if downscale_services:

        response = connection.ecs.describe_services(
            cluster=cluster_name,
            services=downscale_services)

        # Set desired count to num_instances - 1
        current_counts = {}
        new_counts = {}
        for service in response['services']:
            if service['desiredCount'] >= num_instances:

                name = service['serviceName']
                current_counts[name] = service['desiredCount']
                new_counts[name] = num_instances - 1

                if new_counts[name] < 1:
                    logger.warning(
                        "%s - Refusing to set desiredCount < 1", name)
                else:
                    logger.info(
                        "%s - Setting desiredCount to %s", name,
                        new_counts[name])

                connection.ecs.update_service(
                    cluster=cluster_name,
                    service=name,
                    desiredCount=new_counts[name])

        # Poll completion
        while new_counts:
            response = connection.ecs.describe_services(
                cluster=cluster_name,
                services=new_counts.keys())

            for service in response['services']:
                name = service['serviceName']
                if service['runningCount'] <= new_counts[name]:
                    del new_counts[name]

        logger.info("All desiredCount changes reached")

    yield

    if downscale_services:
        for service_name, desired_count in current_counts.iteritems():
            logger.info(
                "Re-setting desiredCount for %s to %s",
                service_name, desired_count)

            connection.ecs.update_service(
                cluster=cluster_name,
                service=service_name,
                desiredCount=desired_count)


@contextlib.contextmanager
def raise_available_capacity(connection, asg_name, cluster_name):
    """Start a new instance within the autoscaling group and yields the
    new instance id.

    """
    # Get number of running instances in the ASG
    ec2_instance_ids = get_instance_ids(connection.asg, asg_name)

    # Set capacity +1
    desired_instances = len(ec2_instance_ids) + 1
    logger.info("Setting desired capacity to %d instances", desired_instances)
    asg_client.set_desired_capacity(
        AutoScalingGroupName=asg_name,
        DesiredCapacity=desired_instances,
        HonorCooldown=False)

    logger.info("Waiting for instances to start")
    current_ec2_instance_ids = ec2_instance_ids
    while len(ec2_instance_ids) < desired_instances:
        time.sleep(5)
        ec2_instance_ids = get_instance_ids(connection.asg, asg_name)

    # The new instance id is the new set minus the old set
    ec2_instance_id = list(ec2_instance_ids - current_ec2_instance_ids)[0]

    logger.info("Waiting for instances to join the ECS cluster")
    while True:
        response = connection.ecs.describe_clusters(clusters=[cluster_name])
        num_container_instances = (
            response['clusters'][0]['registeredContainerInstancesCount'])

        if num_container_instances >= desired_instances:
            break

        time.sleep(5)

    yield ec2_instance_id

    _remove_oldest_instance(connection, asg_name, cluster_name)


def return_oldest_instance(connection, asg_name):
    """Return the oldest ec2 instance in the given asg group

    This might be done simpler :P

    """
    result = connection.asg.describe_auto_scaling_groups(
        AutoScalingGroupNames=[asg_name]
    )
    instances = result['AutoScalingGroups'][0]['Instances']

    result = connection.ec2.describe_instances(
        InstanceIds=[item['InstanceId'] for item in instances],
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            }
        ])

    # Make sure we never end up with less then 1 instance
    if len(result) <= 1:
        return

    instances = sorted(
        itertools.chain(*(r['Instances'] for r in result['Reservations'])),
        key=operator.itemgetter('LaunchTime'))
    return instances[0]['InstanceId'] if instances else None


def _remove_oldest_instance(connection, asg_name, cluster_name):
    """Remove the oldest container instance from the cluster"""

    # Scale down again by terminating the oldest instance
    logger.info("Terminating oldest instance")
    instance_id = return_oldest_instance(connection, asg_name)
    if not instance_id:
        raise ValueError("No instance found to terminate")

    container_id = find_container_instance_id(
        ecs_client, cluster_name, instance_id)

    if not container_id:
        raise ValueError(
            "no container id found for ec2 instance %s" % instance_id)

    # Stop all tasks on the old container instance (just to make sure)
    tasks = ecs_client.list_tasks(
        cluster=cluster_name,
        containerInstance=container_id)
    logger.info(
        "Stopping %d tasks on container %s", len(tasks['taskArns']),
        container_id)
    for task_arn in tasks['taskArns']:
        ecs_client.stop_task(cluster=cluster_name, task=task_arn)

    # Wait 10 seconds for some tasks to shutdown
    time.sleep(10)

    # Deregister it first from the cluster. This results in orphaned tasks,
    # but ECS schedules the tasks on other container instances
    ecs_client.deregister_container_instance(
        cluster=cluster_name,
        containerInstance=container_id,
        force=True)

    # Wait till all tasks are moved
    logger.info("Waiting until there are no more pending tasks in the cluster")
    while True:
        time.sleep(5)
        result = ecs_client.describe_clusters(clusters=[cluster_name])
        if result['clusters'][0]['pendingTasksCount'] < 1:
            break
        logger.info(
            " - %d tasks pending", result['clusters'][0]['pendingTasksCount'])

    asg_client.terminate_instance_in_auto_scaling_group(
        InstanceId=instance_id, ShouldDecrementDesiredCapacity=True)


def find_container_instance_id(ecs_client, cluster_name, ec2_instance_id):
    """Find the container instance id for the given ec2_instance_id"""
    result = ecs_client.list_container_instances(cluster=cluster_name)
    if not result['containerInstanceArns']:
        return

    result = ecs_client.describe_container_instances(
        cluster=cluster_name,
        containerInstances=result['containerInstanceArns'])
    for instance in result['containerInstances']:
        if instance['ec2InstanceId'] == ec2_instance_id:
            return instance['containerInstanceArn']


def get_instance_ids(asg, asg_name):
    """Return a set of all the active ec2 instance id's"""
    result = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
    if not result['AutoScalingGroups']:
        return set()

    return {
        i['InstanceId'] for i in result['AutoScalingGroups'][0]['Instances']
        if i['LifecycleState'] == 'InService'
    }
