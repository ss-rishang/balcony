from typing import List, Dict, Tuple

from balcony.nodes import ResourceNode
from balcony.config import get_logger

logger = get_logger(__name__)


class BuildsForProject(ResourceNode, service_name="codebuild", name="BuildsForProject"):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_operations_relations(self, operation_name) -> Tuple[List[Dict], None]:
        result, err = super().get_operations_relations(operation_name)
        # manipulate `result` or return your own value
        return result, err
