# /usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import TypedDict, List


class DesktopApp(TypedDict):
    name: str
    description: str
    install_command: str


DEFAULT_APPS: List[DesktopApp] = [
    {
        "name": "Firefox",
        "description": "A free and open-source web browser developed by the Mozilla Foundation.",
        "install_command": "sudo add-apt-repository ppa:mozillateam/ppa && sudo apt-get install -y --no-install-recommends firefox-esr",
    },
    {
        "name": "LibreOffice",
        "description": "A free and open-source office suite.",
        "install_command": "sudo apt-get install -y --no-install-recommends libreoffice",
    },
    {
        "name": "Gedit",
        "description": "A free and open-source text editor.",
        "install_command": "sudo apt-get install -y --no-install-recommends gedit",
    },
]
