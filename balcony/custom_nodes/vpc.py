from balcony.nodes import ResourceNode
from balcony.config import get_logger
from botocore.exceptions import ClientError

logger = get_logger(__name__)


class RouteTables(ResourceNode, service_name="ec2", name="RouteTables"):  # type: ignore[call-arg]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_api_parameters_from_operation_data(
        self, operation_name, relations_of_operation, related_operations_data
    ):
        if operation_name == "DescribeRouteTables":
            # Make the API call with no parameters to get all route tables
            filtered_response = self._get_filtered_route_tables_response()

            if filtered_response:
                # Directly store the filtered response in the service reader
                service_reader = self.service_node.get_service_reader()
                service_reader.add_to_node_data(
                    self.name, operation_name, filtered_response
                )
                logger.debug(
                    f"Stored filtered DescribeRouteTables response with {len(filtered_response.get('RouteTables', []))} route tables"
                )

            # Return empty list to prevent the normal API call
            return [], None

        return super().generate_api_parameters_from_operation_data(
            operation_name, relations_of_operation, related_operations_data
        )

    def _get_filtered_route_tables_response(self):
        """Get DescribeRouteTables response with default VPC route tables filtered out"""
        # Get region from user's boto3 session
        user_session = self.service_node.session
        current_region = user_session.region_name
        ec2_client = user_session.client("ec2")

        logger.info(f"Using user's boto3 session with region: {current_region}")

        # First, find the default VPC ID
        default_vpc_id = None
        try:
            vpcs_response = ec2_client.describe_vpcs()
            for vpc in vpcs_response.get("Vpcs", []):
                if vpc.get("IsDefault", False):
                    default_vpc_id = vpc.get("VpcId")
                    logger.info(f"Found default VPC: {default_vpc_id}")
                    break
        except ClientError as e:
            logger.error(f"Failed to describe VPCs: {e}")
            return {"RouteTables": []}

        if not default_vpc_id:
            logger.info("No default VPC found, including all route tables")

        # Get all route tables
        try:
            response = ec2_client.describe_route_tables()
        except ClientError as e:
            logger.error(f"Failed to describe route tables: {e}")
            return {"RouteTables": []}

        all_route_tables = response.get("RouteTables", [])
        logger.info(f"Found {len(all_route_tables)} total route tables")

        filtered_route_tables = []

        for route_table in all_route_tables:
            vpc_id = route_table.get("VpcId")
            route_table_id = route_table.get("RouteTableId")

            # Skip route tables that belong to the default VPC
            if default_vpc_id and vpc_id == default_vpc_id:
                logger.debug(
                    f"Skipping route table {route_table_id} (belongs to default VPC: {default_vpc_id})"
                )
                continue

            # Include route tables from non-default VPCs
            filtered_route_tables.append(route_table)
            logger.debug(f"Including route table {route_table_id} from VPC: {vpc_id}")

        logger.info(
            f"Filtered to {len(filtered_route_tables)} route tables (excluded default VPC route tables)"
        )

        return {
            "RouteTables": filtered_route_tables,
            "__args__": {},  # Include the __args__ field that balcony expects
        }
