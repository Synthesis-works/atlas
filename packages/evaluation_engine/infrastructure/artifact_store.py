import abc
import os
import shutil
import uuid

import structlog

logger = structlog.get_logger(__name__)


class BaseArtifactStore(abc.ABC):
    """
    Abstract store for saving and retrieving evaluation artifacts.
    """

    @abc.abstractmethod
    def store_artifact(self, evaluation_id: uuid.UUID, name: str, source_path: str) -> str:
        """
        Stores an artifact and returns its logical URI.
        """
        pass

    @abc.abstractmethod
    def resolve_uri(self, uri: str) -> str:
        """
        Resolves a logical URI to an access URL or local path.
        """
        pass


class LocalArtifactStore(BaseArtifactStore):
    """
    Local filesystem implementation of ArtifactStore.
    Saves artifacts to a configured base directory.
    """

    def __init__(self, base_dir: str = "/var/lib/atlas/artifacts"):
        self.base_dir = base_dir
        # For a real implementation, we'd ensure this directory exists
        # os.makedirs(self.base_dir, exist_ok=True)
        # Using a safer local path for development MVP if running locally
        if not os.path.exists(self.base_dir):
            try:
                os.makedirs(self.base_dir, exist_ok=True)
            except Exception as e:
                logger.warning(
                    f"Failed to create artifact dir {self.base_dir}, falling back to local /tmp",
                    error=str(e),
                )
                self.base_dir = "/tmp/atlas/artifacts"
                os.makedirs(self.base_dir, exist_ok=True)

    def store_artifact(self, evaluation_id: uuid.UUID, name: str, source_path: str) -> str:
        eval_dir = os.path.join(self.base_dir, str(evaluation_id))
        os.makedirs(eval_dir, exist_ok=True)

        dest_path = os.path.join(eval_dir, name)
        shutil.copy2(source_path, dest_path)

        # Return a logical URI, not the physical path
        return f"artifact://evaluations/{evaluation_id}/{name}"

    def resolve_uri(self, uri: str) -> str:
        if not uri.startswith("artifact://evaluations/"):
            raise ValueError("Invalid artifact URI format")

        parts = uri.replace("artifact://evaluations/", "").split("/")
        if len(parts) != 2:
            raise ValueError("Invalid artifact URI format")

        evaluation_id, name = parts
        return os.path.join(self.base_dir, evaluation_id, name)
