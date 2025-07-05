from balcony.config import get_logger
from balcony.aws import BalconyAWS
from balcony.nodes import ServiceNode

logger = get_logger(__name__)


def export_boto3_operations_by_service(
    balcony_aws: BalconyAWS,
) -> dict[str, list[str]]:
    service_and_operation_names = {}
    for service_name in balcony_aws.get_available_service_names():
        logger.debug(f"Getting boto3 operations for service: {service_name}")
        service_node: ServiceNode = balcony_aws.get_service_node(service_name)
        operation_names = service_node.get_operation_names()
        service_and_operation_names[service_name] = operation_names
    return service_and_operation_names
