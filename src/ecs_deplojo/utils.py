def slice_iterable(iterable, size):
    """Slice an iterable in chunks of `size` length"""
    buffer = []
    for item in iterable:
        buffer.append(item)
        if len(buffer) == size:
            # yield collected full chunk
            yield buffer
            buffer = []
    if buffer:
        yield buffer


def describe_services(ecs, cluster, services):
    """Custom version since the default limits to 10 services per call"""

    result = []
    for services_slice in slice_iterable(services, 10):

        response = ecs.describe_services(
            cluster=cluster, services=services_slice)
        result.extend(response['services'])
    return result
