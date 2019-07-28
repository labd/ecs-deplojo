import typing


def find_missing_services(
    ecs, cluster: str, services: typing.Set[str]
) -> typing.Set[str]:
    """Return a set of service names which don't exist in AWS.

    We use `ECS.Client.describe_services` since we have a list of service
    names we want to check and instead of just retrieving all services in the
    cluster we pass the items we want. We can only pass 10 services per call
    so we iterate over the list in chunks.
    """
    existing_services = set()
    for service in describe_services(ecs, cluster, services):
        existing_services.add(service["serviceName"])
    return set(services) - existing_services


def describe_services(
    ecs, cluster: str, services: typing.Set[str]
) -> typing.List[typing.Dict[str, typing.Any]]:
    """Wrap `ECS.Client.describe_services` to allow more then 10 services in
    one call.

    """
    result: typing.List[typing.Dict[str, typing.Any]] = []
    services_list = list(services)
    for i in range(0, len(services_list), 10):
        response = ecs.describe_services(
            cluster=cluster, services=services_list[i : i + 10]
        )
        result.extend(response["services"])
    return result
