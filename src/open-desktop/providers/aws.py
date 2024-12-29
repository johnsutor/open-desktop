from pulumi import Config, Output, export
import pulumi_aws as aws
import pulumi_awsx as awsx
from pulumi import automation as auto
from pulumi.automation import LocalWorkspaceOptions
from pulumi.automation import ProjectSettings

def pulumi_program():
    config = Config()
    container_port = config.get_int("containerPort", 80)
    cpu = config.get_int("cpu", 512)
    memory = config.get_int("memory", 128)

    cluster = aws.ecs.Cluster("cluster")

    task_definition = awsx.ecs.FargateTaskDefinition(
        "my-task",
        cpu=cpu,
        memory=memory,
        container=awsx.ecs.TaskDefinitionContainerDefinitionArgs(
            name="my-container",
            image="dockur/windows:latest",
            cpu=cpu,
            memory=memory,
            essential=True,
            port_mappings=[awsx.ecs.TaskDefinitionPortMappingArgs(
                container_port=container_port,
                host_port=80,
                protocol="tcp",
            )]
        )
    )

    service = awsx.ecs.FargateService(
        "service",
        cluster=cluster.arn,
        assign_public_ip=True,
        task_definition=task_definition.task_definition.arn,
    )

stack = auto.create_or_select_stack(
    stack_name="aws-py",
    project_name="open-desktop",
    program=pulumi_program,
    opts = LocalWorkspaceOptions(
        env_vars={
            "PULUMI_CONFIG_PASSPHRASE": "supersecret",
        },
    )
)
stack.set_config("aws:region", auto.ConfigValue(value="us-west-2"))

stack.up()
# export("url", Output.concat("http://", loadbalancer.load_balancer.dns_name))
# print("URL: " + Output.concat("http://", loadbalancer.load_balancer.dns_name))