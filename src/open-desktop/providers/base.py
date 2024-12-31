# /usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import Optional, TypedDict

from pulumi import automation as auto
from pulumi.automation import LocalWorkspaceOptions, Stack


class ProviderConfig(TypedDict):
    stack_name: str
    project_name: str
    container_port: int
    container_name: str
    cpu: int
    memory: int
    region: str


class Provider(ABC):
    stack: Optional[Stack] = None
    debug: bool = False

    def __init__(self, config: ProviderConfig, debug: bool = False) -> None:
        self.config = config
        self.debug = debug
        self.stack = None

    @staticmethod
    @abstractmethod
    def build_fn() -> None:
        pass

    @abstractmethod
    def set_config(self) -> None:
        pass

    def make(self) -> None:
        """Create the environment stack. If the stack already exists, it will be destroyed."""
        if self.stack:
            self.stack.destroy()

        self.stack = auto.create_or_select_stack(
            stack_name="aws-py",
            project_name="open-desktop",
            program=self.build_fn,
            opts=LocalWorkspaceOptions(
                env_vars={
                    "PULUMI_CONFIG_PASSPHRASE": "supersecret",
                },
            ),
        )
        self.set_config()
        self.stack.refresh(on_output=print if self.debug else None)
        self.stack.up(on_output=print if self.debug else None)

    def close(self) -> None:
        if self.stack:
            self.stack.destroy(debug=self.debug)
