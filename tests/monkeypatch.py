def patch():
    import pytz
    from datetime import datetime
    from random import randint

    # See https://github.com/spulec/moto/pull/902
    from moto.ecs import models

    class MyTaskDefinition(models.TaskDefinition):

        def __init__(self, family, revision, container_definitions, volumes=None):
            self.revision = revision
            super(MyTaskDefinition, self).__init__(
                family, revision, container_definitions, volumes)

    models.TaskDefinition = MyTaskDefinition

    # See https://github.com/spulec/moto/pull/903
    class MyService(models.Service):
        def __init__(self, cluster, service_name, task_definition, desired_count):
            super(MyService, self).__init__(
                cluster, service_name, task_definition, desired_count)
            self.deployments = [
                {
                    'createdAt': datetime.now(pytz.utc),
                    'desiredCount': self.desired_count,
                    'id': 'ecs-svc/{}'.format(randint(0, 32**12)),
                    'pendingCount': self.desired_count,
                    'runningCount': 0,
                    'status': 'PRIMARY',
                    'taskDefinition': task_definition.arn,
                    'updatedAt': datetime.now(pytz.utc),
                }
            ]

        @property
        def response_object(self):
            response_object = self.gen_response_object()
            del response_object['name'], response_object['arn']
            response_object['serviceName'] = self.name
            response_object['serviceArn'] = self.arn

            for deployment in response_object['deployments']:
                if isinstance(deployment['createdAt'], datetime):
                    deployment['createdAt'] = deployment['createdAt'].isoformat()
                if isinstance(deployment['updatedAt'], datetime):
                    deployment['updatedAt'] = deployment['updatedAt'].isoformat()

            return response_object


    models.Service = MyService
