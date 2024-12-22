from dataclasses import dataclass, field
from typing import List, Optional, Dict, Literal, Tuple
from jinja2 import Environment, BaseLoader
import docker
from pathlib import Path
from apps import DesktopApp

SUPPORTED_LINUX_IMAGES = Literal[
    "ubuntu:22.04",
]

@dataclass
class DockerConfig:
    """
    Dataclass for configuring a Docker environment.

    Args:
        base_image: The base image to use for the Docker environment.
        python_version: The version of Python to install.
        display_width: The width of the display in pixels.
        display_height: The height of the display in pixels.
        display_num: The display number.
        username: The username to create in the Docker environment.
        apps: A list of DesktopApp objects to install.
        additional_packages: A list of additional packages to install.
        custom_commands: A list of custom commands to run during the Docker build.
    """
    base_image: SUPPORTED_LINUX_IMAGES = "ubuntu:22.04"
    python_version: Tuple[int, int, int] = (3, 11, 0)
    display_width: int = 1024
    display_height: int = 768
    display_num: int = 1
    username: str = "user"
    apps: List[DesktopApp] = field(default_factory=list)
    additional_packages: List[str] = field(default_factory=list)
    custom_commands: List[str] = field(default_factory=list)


class DockerfileGenerator:
    """
    A class for generating Dockerfiles based on a provided configuration.
    """
    def __init__(self):
        self.template_env = Environment(loader=BaseLoader())
        self._base_template = """
FROM {{ config.base_image }}
ENV DEBIAN_FRONTEND=noninteractive
ENV DEBIAN_PRIORITY=high


RUN apt-get update && apt-get -y upgrade

RUN apt-get -y install \
    xvfb \
    xterm \
    xdotool \
    scrot \
    imagemagick \
    sudo \
    mutter \
    x11vnc \
    software-properties-common

RUN apt-get -y install \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    curl \
    git \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libffi-dev \
    liblzma-dev

{% if config.additional_packages %}
RUN apt-get -y install {{ config.additional_packages|join(' ') }}
{% endif %}

RUN apt-get clean

RUN git clone --branch v1.5.0 https://github.com/novnc/noVNC.git /opt/noVNC && \
    git clone --branch v0.12.0 https://github.com/novnc/websockify /opt/noVNC/utils/websockify && \
    ln -s /opt/noVNC/vnc.html /opt/noVNC/index.html

ENV USERNAME={{ config.username }}
ENV HOME=/home/$USERNAME
RUN useradd -m -s /bin/bash -d $HOME $USERNAME
RUN echo "${USERNAME} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
USER $USERNAME
WORKDIR $HOME

RUN git clone https://github.com/pyenv/pyenv.git ~/.pyenv && \
    cd ~/.pyenv && src/configure && make -C src && cd .. && \
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc && \
    echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc && \
    echo 'eval "$(pyenv init -)"' >> ~/.bashrc

ENV PYENV_ROOT="$HOME/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PATH"
ENV PYENV_VERSION={{ config.python_version[0] }}.{{ config.python_version[1] }}.{{ config.python_version[2] }}

RUN eval "$(pyenv init -)" && \
    pyenv install $PYENV_VERSION && \
    pyenv global $PYENV_VERSION && \
    pyenv rehash

ENV PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH"
RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip config set global.disable-pip-version-check true

{% if config.custom_commands %}
{% for cmd in config.custom_commands %}
RUN {{ cmd }}
{% endfor %}
{% endif %}

ARG DISPLAY_NUM={{ config.display_num }}
ARG HEIGHT={{ config.display_height }}
ARG WIDTH={{ config.display_width }}
ENV DISPLAY_NUM=$DISPLAY_NUM
ENV HEIGHT=$HEIGHT
ENV WIDTH=$WIDTH

COPY entrypoint.sh $HOME/
RUN chmod +x $HOME/entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
"""

    def generate_dockerfile(
        self, config: DockerConfig, output_path: Optional[Path] = None
    ) -> str:
        """Generate a Dockerfile based on the provided configuration.
        
        Args:
            config: The configuration for the Docker environment.
            output_path: The path to write the Dockerfile to."""
        template = self.template_env.from_string(self._base_template)
        dockerfile_content = template.render(config=config)

        if output_path:
            output_path.write_text(dockerfile_content)

        return dockerfile_content


class DockerEnvironment:
    """
    A class for building and running Docker environments.
    
    Args:
        client: An optional Docker client object to use for interacting with the Docker daemon.
    """
    def __init__(self, client: Optional[docker.DockerClient] = None):
        self.client = client or docker.from_env()
        self.generator = DockerfileGenerator()

    def build_environment(
        self,
        config: DockerConfig,
        tag: str,
        dockerfile_path: Optional[Path] = None,
        build_args: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Build a Docker environment from the provided configuration.
        Returns the image ID.

        Args:
            config: The configuration for the Docker environment.
            tag: The tag to apply to the built image.
            dockerfile_path: The path to a custom Dockerfile to use.
            build_args: A dictionary of build arguments to pass to the Docker build
        """
        dockerfile_content = self.generator.generate_dockerfile(config, dockerfile_path)

        image, _ = self.client.images.build(
            path=".",
            dockerfile=str(dockerfile_path) if dockerfile_path else None,
            fileobj=None if dockerfile_path else dockerfile_content.encode(),
            tag=tag,
            buildargs=build_args or {},
        )

        return image.id

    def run_environment(
        self,
        image_id: str,
        ports: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        """
        Run a container from the built environment.
        Returns the container object.

        Args:
            image_id: The ID of the Docker image to run.
            ports: A dictionary of port mappings.
            volumes: A dictionary of volume mappings.
        """
        return self.client.containers.run(
            image_id, detach=True, ports=ports, volumes=volumes
        )
