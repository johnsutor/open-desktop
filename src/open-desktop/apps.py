from dataclasses import dataclass, field
from typing import List

@dataclass
class DesktopApp:
    def __init__(self):
        name: str
        description: str
        install_command: List[str] = field(default_factory=list)

    def get_commands(self):
        return "\\".join(self.install_command)
    
class Firefox(DesktopApp):
    def __init__(self):
        super().__init__(
            name="Firefox",
            description="A free and open-source web browser developed by the Mozilla Foundation.",
            icon="firefox",
            install_command=[
                "sudo add-apt-repository ppa:mozillateam/ppa"
                "sudo apt-get install -y --no-install-recommends firefox-esr" 
            ]
        )

class LibreOffice(DesktopApp):
    def __init__(self):
        super().__init__(
            name="LibreOffice",
            description="A free and open-source office suite.",
            install_command=[
                "sudo apt-get install -y --no-install-recommends libreoffice" 
            ]
        )

class Geddit(DesktopApp):
    def __init__(self):
        super().__init__(
            name="Gedit",
            description="A free and open-source text editor.",
            install_command=[
                "sudo apt-get install -y --no-install-recommends gedit" 
            ]
        )