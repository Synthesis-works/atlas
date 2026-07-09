import os
import uuid
import tempfile
import shutil
from typing import Optional
from ..exceptions import SandboxException

class TemporarySandbox:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir
        self.run_id = str(uuid.uuid4())
        self.sandbox_dir: Optional[str] = None

    def __enter__(self) -> str:
        try:
            if self.base_dir:
                os.makedirs(self.base_dir, exist_ok=True)
                self.sandbox_dir = tempfile.mkdtemp(dir=self.base_dir, prefix=f"run-{self.run_id}-")
            else:
                self.sandbox_dir = tempfile.mkdtemp(prefix=f"run-{self.run_id}-")
            return self.sandbox_dir
        except Exception as e:
            raise SandboxException(f"Failed to create sandbox: {str(e)}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sandbox_dir and os.path.exists(self.sandbox_dir):
            try:
                shutil.rmtree(self.sandbox_dir)
            except Exception as e:
                print(f"Warning: Failed to cleanup sandbox {self.sandbox_dir}: {str(e)}")
