#!/usr/bin/env python
import contextlib
import copy
import itertools
import json
import logging
import operator
import os.path
import re
import time
import tokenize
from string import Template

import boto3
import click
import yaml

# Initialize logging
logger = logging.getLogger('deploy')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(ch)


class VarType(click.ParamType):
    name = 'var'
    re_pattern = re.compile('^%s$' % tokenize.Name)

    def convert(self, value, param, ctx):
        try:
            key, value = value.split('=', 1)
            if not self.re_pattern.match(key):
                self.fail('%s is not a valid identifier' % key)
        except ValueError:
            self.fail('%s is not a valid key/value string' % value, param, ctx)

        return (key, value)


@click.command()
@click.option('--config', required=True)
@click.option('--var', multiple=True, type=VarType())
@click.option('--dry-run', is_flag=True, default=False)
@click.option('--output-path', required=False, type=click.Path())
def cli(config, var, output_path, dry_run):
    template_vars = dict(var)
    with open('config.yml') as fh:
        config = yaml.load(fh)

    asg_name = config['auto_scaling_group']
    cluster_name = config['cluster_name']
    logger.info("Starting deploy on cluster %s", cluster_name)

    task_definitions = {}
    for service_name, service_config in config['services'].iteritems():
        env_items = config['environment']['groups'][service_config['environment_group']]
        definition = generate_task_definition(
            service_config['task_definition'], env_items, template_vars,
            service_config.get('overrides'), name=service_name)

        if output_path:
            write_task_definition(service_name, definition, output_path)
        task_definitions[service_name] = {
            'definition': definition,
        }

    # Register the task definitions in ECS
    if not dry_run:
        asg = boto3.client('autoscaling')
        ecs = boto3.client('ecs')
        ec2 = boto3.client('ec2')

        # Update task definitions
        for service_name, values in task_definitions.iteritems():
            definition = transform_definition(values['definition'])
            result = ecs.register_task_definition(**definition)

            values['family'] = result['taskDefinition']['family']
            values['revision'] = result['taskDefinition']['revision']

            logger.info(
                "Registered new task definition %s:%s",
                values['family'], values['revision'])

        # Check if all services exist
        response = ecs.describe_services(
            cluster=cluster_name, services=task_definitions.keys())
        available_services = {
            service['serviceName'] for service in response['services']
        }
        new_services = set(task_definitions.keys()) - available_services

        with lock_deployment(asg, asg_name):
            with raise_available_capacity(asg, ec2, ecs, asg_name, cluster_name):

                # Update services
                for service_name, values in task_definitions.iteritems():

                    if service_name in new_services:
                        logger.info("Creating new service %s with task defintion %s:%s",
                                    service_name, values['family'], values['revision'])
                        ecs.create_service(
                            cluster=cluster_name,
                            serviceName=service_name,
                            desiredCount=1,
                            taskDefinition='%s:%s' % (
                                values['family'], values['revision']))
                    else:
                        logger.info("Updating service %s with task defintion %s:%s",
                                    service_name, values['family'], values['revision'])
                        ecs.update_service(
                            cluster=cluster_name,
                            service=service_name,
                            taskDefinition='%s:%s' % (
                                values['family'], values['revision']))

                # Initial wait time for deployments
                time.sleep(10)

                # Wait till all service updates are deployed
                logger.info("Waiting for deployments")
                while True:
                    response = ecs.describe_services(
                        cluster=cluster_name, services=task_definitions.keys())
                    if all(len(s['deployments']) == 1 for s in response['services']):
                        break



def transform_definition(definition):
    result = copy.deepcopy(definition)
    for container in result['containerDefinitions']:
        container['environment'] = [
            {'name': k, 'value': v}
            for k, v in container['environment'].iteritems()
        ]
    return result


def generate_task_definition(filename, environment, template_vars, overrides,
                             name):
    with open(filename, 'rb') as fh:
        data = json.load(fh)

        data['family'] = name
        for container in data['containerDefinitions']:
            container['image'] = Template(container['image']).substitute(template_vars)
            container['environment'] = environment

            if overrides:
                container_overrides = overrides.get(container['name'], {})
                for key, value in container_overrides.iteritems():
                    container[key] = value

        return data


def write_task_definition(name, definition, output_path):
    filename = os.path.join(output_path, '%s.json' % name)
    with open(filename, 'wb') as fh:
        json.dump(definition, fh, indent=4)


def return_oldest_instance(asg_client, ec2_client, asg_name):
    """Return the oldest ec2 instance in the given asg group

    This might be done simpler :P

    """
    result = asg_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=[asg_name]
    )
    instances = result['AutoScalingGroups'][0]['Instances']

    result = ec2_client.describe_instances(
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


@contextlib.contextmanager
def lock_deployment(asg_client, asg_name):
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


def get_num_instances(asg, asg_name):
    """Get number of running instances in the ASG"""
    result = asg.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
    if not result['AutoScalingGroups']:
        return 0

    return len(
        filter(
            lambda i: i['LifecycleState'] == 'InService',
            result['AutoScalingGroups'][0]['Instances']))


@contextlib.contextmanager
def raise_available_capacity(asg_client, ec2_client, ecs_client, asg_name,
                             cluster_name):

    # Get number of running instances in the ASG
    num_instances = get_num_instances(asg_client, asg_name)

    # Set capacity +1
    desired_instances = num_instances + 1
    logger.info("Setting desired capacity to %d instances", desired_instances)
    asg_client.set_desired_capacity(
        AutoScalingGroupName=asg_name,
        DesiredCapacity=desired_instances,
        HonorCooldown=False)

    logger.info("Waiting for instances to start")
    while num_instances < desired_instances:
        time.sleep(5)
        num_instances = get_num_instances(asg_client, asg_name)

    logger.info("Waiting for instances to join the ECS cluster")
    while True:
        response = ecs_client.describe_clusters(clusters=[cluster_name])
        num_container_instances = (
            response['clusters'][0]['registeredContainerInstancesCount'])

        if num_container_instances >= desired_instances:
            break

        time.sleep(5)

    yield

    _remove_oldest_instance(
        asg_client, ec2_client, ecs_client, asg_name, cluster_name)


def _remove_oldest_instance(asg_client, ec2_client, ecs_client, asg_name,
                            cluster_name):
    """Remove the oldest container instance from the cluster"""

    # Scale down again by terminating the oldest instance
    logger.info("Terminating oldest instance")
    instance_id = return_oldest_instance(asg_client, ec2_client, asg_name)
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
