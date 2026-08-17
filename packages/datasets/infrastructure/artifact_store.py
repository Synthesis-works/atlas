import abc
import os
import shutil
import uuid
import structlog

logger = structlog.get_logger(__name__)


class BaseTrainingArtifactStore(abc.ABC):
    """
    Abstract interface for persisting exported training datasets seamlessly cleanly independently robustly mapping gracefully evaluating smoothly natively.
    """

    @abc.abstractmethod
    def store_training_artifact(
        self, dataset_version_id: uuid.UUID, name: str, source_path: str
    ) -> str:
        """Stores the exported training file and returns a logical URI."""
        pass

    @abc.abstractmethod
    def resolve_uri(self, uri: str) -> str:
        """Resolves a logical artifact URI to an access URL or local physical path."""
        pass


class LocalTrainingArtifactStore(BaseTrainingArtifactStore):
    """
    Local filesystem abstraction natively persisting training artifacts safely correctly reliably cleanly confirming.
    """

    def __init__(self, base_dir: str = "/var/lib/atlas/training_artifacts"):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            try:
                os.makedirs(self.base_dir, exist_ok=True)
            except Exception as e:
                logger.warning(
                    f"Failed to create artifact dir {self.base_dir}, falling back to local /tmp",
                    error=str(e),
                )
                self.base_dir = "/tmp/atlas/training_artifacts"
                os.makedirs(self.base_dir, exist_ok=True)

    def store_training_artifact(
        self, dataset_version_id: uuid.UUID, name: str, source_path: str
    ) -> str:
        dest_dir = os.path.join(self.base_dir, str(dataset_version_id))
        os.makedirs(dest_dir, exist_ok=True)

        dest_path = os.path.join(dest_dir, name)
        shutil.copy2(source_path, dest_path)

        return f"artifact://datasets/{dataset_version_id}/{name}"

    def resolve_uri(self, uri: str) -> str:
        if not uri.startswith("artifact://datasets/"):
            raise ValueError("Invalid dataset artifact URI format")

        parts = uri.replace("artifact://datasets/", "").split("/")
        if len(parts) != 2:
            raise ValueError("Invalid dataset artifact URI structure")

        dataset_version_id, name = parts
        return os.path.join(self.base_dir, dataset_version_id, name)
