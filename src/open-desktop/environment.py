# /usr/bin/env python3
# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Literal, Union

from providers.aws import AwsConfig, create_aws_environment


@dataclass
class EnvironmentConfig:
    """Environment configuration."""

    name: str
    provider: Literal["aws", "azure", "gcp"]
    config: Union[AwsConfig]


class Environment:
    """Environment."""

    def __init__(self, config: EnvironmentConfig) -> None:
        self.config = config

    def build(self) -> None:
        """Build the environment."""
        if self.config.provider == "aws":
            create_aws_environment(self.config.config)
        elif self.config.provider == "azure" or self.config.provider == "gcp":
            pass
        else:
            raise ValueError("Invalid provider")
