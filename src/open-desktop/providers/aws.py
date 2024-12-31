# /usr/bin/env python3
# -*- coding: utf-8 -*-


import pulumi_aws as aws
import pulumi_awsx as awsx
from base import Provider
from pulumi import Config
from pulumi.automation import ConfigValue


class AwsProvider(Provider):
    """AWS provider.

    Attributes:
        config (ProviderConfig): Provider configuration. Please ensure that the CPU and memory values are valid, based on the [AWS Fargate task definition requirements](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html)
    """

    @staticmethod
    def build_fn() -> None:
        config = Config()
        container_port = config.get_int("container_port", 80)
        container_name = config.get("container_name", "my-container")

        cpu = config.get_int("cpu", 512)
        memory = config.get_int("memory", 1024)

        cluster = aws.ecs.Cluster("cluster")

        task_definition = awsx.ecs.FargateTaskDefinition(
            "my-task",
            cpu=cpu,
            memory=memory,
            container=awsx.ecs.TaskDefinitionContainerDefinitionArgs(
                name=container_name,
                image="dockur/windows:latest",
                cpu=cpu,
                memory=memory,
                essential=True,
                port_mappings=[
                    awsx.ecs.TaskDefinitionPortMappingArgs(
                        container_port=container_port,
                        host_port=80,
                        protocol="tcp",
                    )
                ],
            ),
        )

        awsx.ecs.FargateService(
            "service",
            cluster=cluster.arn,
            assign_public_ip=True,
            task_definition=task_definition.task_definition.arn,
        )

    def set_config(self) -> None:
        self.stack.workspace.install_plugin("aws", "v4.0.0")
        self.stack.set_all_config(
            {
                "container_port": ConfigValue(self.config["container_port"]),
                "container_name": ConfigValue(self.config["container_name"]),
                "cpu": ConfigValue(self.config["cpu"]),
                "memory": ConfigValue(self.config["memory"]),
                "aws:region": ConfigValue(self.config["region"]),
            }
        )


# export("url", Output.concat("http://", loadbalancer.load_balancer.dns_name))
# print("URL: " + Output.concat("http://", loadbalancer.load_balancer.dns_name))

if __name__ == "__main__":
    config = {
        "stack_name": "aws-py",
        "project_name": "open-desktop",
        "container_port": "80",
        "container_name": "my-container",
        "cpu": "1024",
        "memory": " 8192",
        "region": "us-west-2",
    }

    provider = AwsProvider(config, debug=True)
    provider.make()
    print("URL: " + provider.stack.outputs["url"].value)
    provider.close()
