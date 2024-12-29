from dataclasses import dataclass
from typing import Literal

@dataclass
class EnvironmentConfig
    """Environment configuration."""
    name: str
    provider: Literal["aws", "azure", "gcp"]

class Environment
    """Environment."""
    def __init__(self, config: EnvironmentConfig) -> None:
        self.config = config

    def build(self) -> None:
        """Build the environment."""
        print(f"Building environment {self.config.name} with provider {self.config.provider}")
        