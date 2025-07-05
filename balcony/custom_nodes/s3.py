from botocore.exceptions import ClientError
from balcony.nodes import ResourceNode
from balcony.config import get_logger

logger = get_logger(__name__)


class Buckets(ResourceNode, service_name="s3", name="Buckets"):  # type: ignore[call-arg]
    """
    List Buckets operation is filtered by the current session's AWS region.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_api_parameters_from_operation_data(
        self, operation_name, relations_of_operation, related_operations_data
    ):
        if operation_name == "ListBuckets":
            # For ListBuckets, we'll handle the filtering ourselves
            # Make the API call directly and store filtered results
            filtered_response = self._get_filtered_buckets_response()
            if filtered_response:
                # Directly store the filtered response in the service reader
                service_reader = self.service_node.get_service_reader()
                service_reader.add_to_node_data(
                    self.name, operation_name, filtered_response
                )
                logger.debug(
                    f"Stored filtered ListBuckets response with {len(filtered_response.get('Buckets', []))} buckets"
                )

            # Return False to indicate that we've handled this operation ourselves
            # This prevents the normal API call flow
            return False, None

        return super().generate_api_parameters_from_operation_data(
            operation_name, relations_of_operation, related_operations_data
        )

    def _get_filtered_buckets_response(self):
        """Get ListBuckets response filtered by current session's region"""
        # Get region from user's boto3 session
        user_session = self.service_node.session
        current_region = user_session.region_name
        s3_client = user_session.client("s3")

        logger.info(f"Using user's boto3 session with region: {current_region}")
        logger.debug(
            f"Session profile: {getattr(user_session, 'profile_name', 'default')}"
        )

        # Get all buckets using user's session
        try:
            response = s3_client.list_buckets()
        except ClientError as e:
            logger.error(f"Failed to list buckets: {e}")
            return {"Buckets": [], "Owner": {}, "__args__": {}}

        all_buckets = response.get("Buckets", [])
        filtered_buckets = []

        logger.info(
            f"Found {len(all_buckets)} total buckets, filtering for region: {current_region}"
        )

        for bucket in all_buckets:
            bucket_name = bucket.get("Name")

            try:
                # Check bucket region using GetBucketLocation
                location_response = s3_client.get_bucket_location(Bucket=bucket_name)
                bucket_region = location_response.get("LocationConstraint")

                # Handle special cases for region mapping
                # us-east-1 returns None in LocationConstraint
                if bucket_region is None:
                    bucket_region = "us-east-1"
                # Some regions return 'EU' for eu-west-1
                elif bucket_region == "EU":
                    bucket_region = "eu-west-1"

                # Only include buckets in the current session's region
                if bucket_region == current_region:
                    filtered_buckets.append(bucket)
                    logger.debug(
                        f"Including bucket {bucket_name} from region {bucket_region}"
                    )
                else:
                    logger.debug(
                        f"Skipping bucket {bucket_name} from region {bucket_region} (current region: {current_region})"
                    )

            except ClientError as e:
                # Skip buckets we can't access or determine location for
                error_code = e.response["Error"]["Code"]
                logger.debug(
                    f"Could not get location for bucket {bucket_name}: {error_code}"
                )
                continue
            except Exception as e:
                logger.debug(f"Error checking bucket {bucket_name}: {str(e)}")
                continue

        logger.info(
            f"Filtered to {len(filtered_buckets)} buckets in region {current_region}"
        )

        return {
            "Buckets": filtered_buckets,
            "Owner": response.get("Owner", {}),
            "__args__": {},  # Include the __args__ field that balcony expects
        }


class BucketLifecycleConfiguration(
    ResourceNode,
    service_name="s3",
    name="BucketLifecycleConfiguration",  # type: ignore[call-arg]
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def define_extra_relations(self):
        r = super().define_extra_relations()
        return [
            {
                "service_name": "s3",
                "resource_node_name": "Buckets",
                "required_shape_name": "Bucket",
                "target_shape_name": "Name",
                "target_shape_type": "string",
                "operation_name": "ListBuckets",
                "target_path": "Buckets[*].Name",
            }
        ]

    def generate_api_parameters_from_operation_data(
        self, operation_name, relations_of_operation, related_operations_data
    ):
        if operation_name == "GetBucketLifecycleConfiguration":
            generated_api_parameters = []

            # Get the current session's region
            current_region = self.service_node.session.region_name

            # Get bucket list from ListBuckets
            list_buckets_data = related_operations_data.get("ListBuckets", [])
            for data in list_buckets_data:
                buckets = data.get("Buckets", [])
                for bucket in buckets:
                    bucket_name = bucket.get("Name")

                    # Check bucket region using GetBucketLocation
                    try:
                        s3_client = self.service_node.session.client("s3")
                        location_response = s3_client.get_bucket_location(
                            Bucket=bucket_name
                        )
                        bucket_region = location_response.get("LocationConstraint")

                        # Handle special cases for region mapping
                        # us-east-1 returns None in LocationConstraint
                        if bucket_region is None:
                            bucket_region = "us-east-1"
                        # Some regions return 'EU' for eu-west-1
                        elif bucket_region == "EU":
                            bucket_region = "eu-west-1"

                        # Only include buckets in the current session's region
                        if bucket_region == current_region:
                            generated_api_parameters.append({"Bucket": bucket_name})
                            logger.debug(
                                f"Including bucket {bucket_name} from region {bucket_region}"
                            )
                        else:
                            logger.debug(
                                f"Skipping bucket {bucket_name} from region {bucket_region} (current region: {current_region})"
                            )

                    except ClientError as e:
                        # Skip buckets we can't access or determine location for
                        error_code = e.response["Error"]["Code"]
                        logger.debug(
                            f"Could not get location for bucket {bucket_name}: {error_code}"
                        )
                        continue
                    except Exception as e:
                        logger.debug(f"Error checking bucket {bucket_name}: {str(e)}")
                        continue

            return generated_api_parameters, None

        # For other operations, use the default behavior
        return super().generate_api_parameters_from_operation_data(
            operation_name, relations_of_operation, related_operations_data
        )

    # def find_best_relations_for_operation(self, operation_name, relation_map):
    #     r = super().find_best_relations_for_operation(operation_name, relation_map)
    #     return r

    def generate_jmespath_selector_from_relations(self, operation_name, relation_list):
        r = super().generate_jmespath_selector_from_relations(
            operation_name, relation_list
        )
        return r
