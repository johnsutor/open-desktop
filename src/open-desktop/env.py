# /usr/bin/env python3
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Literal, Tuple
import docker.models
from jinja2 import Environment, BaseLoader
import docker
from apps import DesktopApp, DEFAULT_APPS
from startup import StartupScript, DEFAULT_STARTUP_SCRIPTS

from io import BytesIO

SUPPORTED_LINUX_IMAGES = Literal["ubuntu:22.04",]


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
        tag: The tag to apply to the built image.
        apps: A list of DesktopApp objects to install.
        startup_scripts: A list of StartupScript objects to run on startup.
        additional_packages: A list of additional packages to install.
        custom_commands: A list of custom commands to run during the Docker build.
        ports_mapping: A dictionary of port mappings.
    """

    base_image: SUPPORTED_LINUX_IMAGES = "ubuntu:22.04"
    python_version: Tuple[int, int, int] = (3, 11, 0)
    display_width: int = 1024
    display_height: int = 768
    display_num: int = 1
    username: str = "user"
    tag: str = "open-desktop-env"
    apps: List[DesktopApp] = field(default_factory=list)
    startup_scripts: List[StartupScript] = field(default_factory=list)
    additional_packages: List[str] = field(default_factory=list)
    custom_commands: List[str] = field(default_factory=list)
    ports_mapping: Dict[str, str] = field(
        default_factory=lambda: {
            "5900": "5900",
            "6080": "6080",
            "8501": "8501",
            "8080": "8080",
        }
    )

    def __post_init__(self):
        self.startup_scripts = DEFAULT_STARTUP_SCRIPTS + self.startup_scripts
        self.apps = DEFAULT_APPS + self.apps


class DockerfileGenerator:
    """
    A class for generating Dockerfiles based on a provided configuration.
    """

    def __init__(self, config: DockerConfig):
        self.template_env = Environment(loader=BaseLoader())
        self.config = config
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

{% if config.apps %}
{% for app in config.apps %}
RUN {{ app.install_command }}
{% endfor %}
{% endif %}

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

{% if config.startup_scripts %}
{% for script in config.startup_scripts %}
RUN cat > $HOME/{{ script.filename }} <<EOF
{{ script.script }}
EOF 
RUN chmod +x $HOME/{{ script.filename }} && \
    echo "exec $HOME/{{ script.filename }}" >> $HOME/startup.sh
{% endfor %}
{% endif %}

RUN chmod +x $HOME/startup.sh
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

ENTRYPOINT ["/startup.sh"]
"""

    def generate_dockerfile(self) -> str:
        """Generate a Dockerfile based on the provided configuration.

        Args:
            config: The configuration for the Docker environment.
        """
        template = self.template_env.from_string(self._base_template)
        dockerfile_content = template.render(config=self.config)

        return dockerfile_content


class DockerEnvironment:
    """
    A class for building and running Docker environments, to be used for running GUI applications in a container.

    Args:
        client: An optional Docker client object to use for interacting with the Docker daemon.
    """

    container: docker.models.containers.Container
    image_id: str
    verbose: bool = True

    def __init__(self, config: DockerConfig):
        self.config = config
        self.client = docker.from_env()
        self.generator = DockerfileGenerator(config)

        self.container = None
        self.image_id = None

    def build_environment(
        self,
    ) -> str:
        """
        Build a Docker environment from the provided configuration.
        Returns the image ID.
        """
        dockerfile_content = self.generator.generate_dockerfile()

        print(dockerfile_content)

        image, _ = self.client.images.build(
            fileobj=BytesIO(dockerfile_content.encode()),
            tag=self.config.tag,
            quiet=not self.verbose,
        )

        return image.id

    def run_environment(
        self,
        ports: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        """
        Run a container from the built environment.
        Returns the container object.

        Args:
            ports: A dictionary of port mappings.
            volumes: A dictionary of volume mappings.

        Returns:
            The container object.
        """
        if not self.image_id:
            self.image_id = self.build_environment()

        return self.client.containers.run(
            self.image_id, detach=True, ports=ports, volumes=volumes
        )


if __name__ == "__main__":
    config = DockerConfig()
    env = DockerEnvironment(config)
    env.run_environment()
