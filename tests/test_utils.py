from ecs_deplojo.main import transform_definition
from ecs_deplojo import utils


def test_definition(definition):
    definition['containerDefinitions'][0]['environment'] = {
        'DEBUG': True,
        'AWS_REGION': 'eu-west-1',
    }
    result = transform_definition(definition)

    assert result['containerDefinitions'][0]['environment'] == [
        {
            'name': 'AWS_REGION',
            'value': 'eu-west-1',
        },
        {
            'name': 'DEBUG',
            'value': 'True',
        },
    ]


# def test_describe_services(connection):
#     task_definition = {
#         'family': 'my-task-def',
#         'volumes': [],
#         'containerDefinitions': [
#             {
#                 'name': 'default',
#                 'image': 'my-docker-image:1.0',
#                 'essential': True,
#                 'command': ['hello', 'world'],
#                 'memory': 256,
#                 'cpu': 0,
#                 'portMappings': [],
#                 'environment': {}
#             }
#         ]
#     }

#     connection.ecs.create_cluster(clusterName='default')
#     connection.ecs.create_service(
#         cluster='default',
#         serviceName='my-service',
#         desiredCount=1,
#         taskDefinition=task_definition)

#     result = utils.describe_services(
#         connection.ecs,
#         'default',
#         services=['my-service'])

#     assert result == ['1']
