
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
ENV DEBIAN_PRIORITY=high

RUN apt-get update && apt-get -y upgrade

RUN apt-get -y install     xvfb     xterm     xdotool     scrot     imagemagick     sudo     mutter     x11vnc     software-properties-common

RUN apt-get -y install     build-essential     libssl-dev     zlib1g-dev     libbz2-dev     libreadline-dev     libsqlite3-dev     curl     git     libncursesw5-dev     xz-utils     tk-dev     libxml2-dev     libxmlsec1-dev     libffi-dev     liblzma-dev



RUN sudo add-apt-repository ppa:mozillateam/ppa && sudo apt-get install -y --no-install-recommends firefox-esr

RUN sudo apt-get install -y --no-install-recommends libreoffice

RUN sudo apt-get install -y --no-install-recommends gedit





RUN apt-get clean

RUN git clone --branch v1.5.0 https://github.com/novnc/noVNC.git /opt/noVNC &&     git clone --branch v0.12.0 https://github.com/novnc/websockify /opt/noVNC/utils/websockify &&     ln -s /opt/noVNC/vnc.html /opt/noVNC/index.html

ENV USERNAME=user
ENV HOME=/home/$USERNAME
RUN useradd -m -s /bin/bash -d $HOME $USERNAME &&  echo "${USERNAME} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
USER $USERNAME
WORKDIR $HOME



RUN cat > $HOME/xvfb_startup.sh <<'EndOfFile'

#!/bin/bash
set -e  # Exit on error

DPI=96
RES_AND_DEPTH=${WIDTH}x${HEIGHT}x24

# Function to check if Xvfb is already running
check_xvfb_running() {
    if [ -e /tmp/.X${DISPLAY_NUM}-lock ]; then
        return 0  # Xvfb is already running
    else
        return 1  # Xvfb is not running
    fi
}

# Function to check if Xvfb is ready
wait_for_xvfb() {
    local timeout=10
    local start_time=$(date +%s)
    while ! xdpyinfo >/dev/null 2>&1; do
        if [ $(($(date +%s) - start_time)) -gt $timeout ]; then
            echo "Xvfb failed to start within $timeout seconds" >&2
            return 1
        fi
        sleep 0.1
    done
    return 0
}

# Check if Xvfb is already running
if check_xvfb_running; then
    echo "Xvfb is already running on display ${DISPLAY}"
    exit 0
fi

# Start Xvfb
Xvfb $DISPLAY -ac -screen 0 $RES_AND_DEPTH -retro -dpi $DPI -nolisten tcp -nolisten unix &
XVFB_PID=$!

# Wait for Xvfb to start
if wait_for_xvfb; then
    echo "Xvfb started successfully on display ${DISPLAY}"
    echo "Xvfb PID: $XVFB_PID"
else
    echo "Xvfb failed to start"
    kill $XVFB_PID
    exit 1
fi

'EndOfFile' 
RUN chmod +x $HOME/xvfb_startup.sh &&     echo "exec $HOME/xvfb_startup.sh" >> $HOME/startup.sh

RUN cat > $HOME/x11vnc_startup.sh <<'EndOfFile'

#!/bin/bash
echo "starting vnc"

(x11vnc -display $DISPLAY                     -forever                     -shared                     -wait 50                     -rfbport 5900                     -nopw                     2>/tmp/x11vnc_stderr.log) &

x11vnc_pid=$!

# Wait for x11vnc to start
timeout=10
while [ $timeout -gt 0 ]; do
    if netstat -tuln | grep -q ":5900 "; then
        break
    fi
    sleep 1
    ((timeout--))
done

if [ $timeout -eq 0 ]; then
    echo "x11vnc failed to start, stderr output:" >&2
    cat /tmp/x11vnc_stderr.log >&2
    exit 1
fi

: > /tmp/x11vnc_stderr.log

# Monitor x11vnc process in the background
(
    while true; do
        if ! kill -0 $x11vnc_pid 2>/dev/null; then
            echo "x11vnc process crashed, restarting..." >&2
            if [ -f /tmp/x11vnc_stderr.log ]; then
                echo "x11vnc stderr output:" >&2
                cat /tmp/x11vnc_stderr.log >&2
                rm /tmp/x11vnc_stderr.log
            fi
            exec "$0"
        fi
        sleep 5
    done
) &

'EndOfFile' 
RUN chmod +x $HOME/x11vnc_startup.sh &&     echo "exec $HOME/x11vnc_startup.sh" >> $HOME/startup.sh

RUN cat > $HOME/mutter_startup.sh <<'EndOfFile'

echo "starting mutter"
XDG_SESSION_TYPE=x11 mutter --replace --sm-disable 2>/tmp/mutter_stderr.log &

# Wait for tint2 window properties to appear
timeout=30
while [ $timeout -gt 0 ]; do
    if xdotool search --class "mutter" >/dev/null 2>&1; then
        break
    fi
    sleep 1
    ((timeout--))
done

if [ $timeout -eq 0 ]; then
    echo "mutter stderr output:" >&2
    cat /tmp/mutter_stderr.log >&2
    exit 1
fi

rm /tmp/mutter_stderr.log

'EndOfFile' 
RUN chmod +x $HOME/mutter_startup.sh &&     echo "exec $HOME/mutter_startup.sh" >> $HOME/startup.sh

RUN cat > $HOME/tint2_startup.sh <<'EndOfFile'

#!/bin/bash
echo "starting tint2 on display :$DISPLAY_NUM ..."

# Start tint2 and capture its stderr
tint2 -c $HOME/.config/tint2/tint2rc 2>/tmp/tint2_stderr.log &

# Wait for tint2 window properties to appear
timeout=30
while [ $timeout -gt 0 ]; do
    if xdotool search --class "tint2" >/dev/null 2>&1; then
        break
    fi
    sleep 1
    ((timeout--))
done

if [ $timeout -eq 0 ]; then
    echo "tint2 stderr output:" >&2
    cat /tmp/tint2_stderr.log >&2
    exit 1
fi

# Remove the temporary stderr log file
rm /tmp/tint2_stderr.log

'EndOfFile' 
RUN chmod +x $HOME/tint2_startup.sh &&     echo "exec $HOME/tint2_startup.sh" >> $HOME/startup.sh

RUN cat > $HOME/novnc_startup.sh <<'EndOfFile'

#!/bin/bash
echo "starting noVNC"

# Start noVNC with explicit websocket settings
/opt/noVNC/utils/novnc_proxy                     --vnc localhost:5900                     --listen 6080                     --web /opt/noVNC                     > /tmp/novnc.log 2>&1 &

# Wait for noVNC to start
timeout=10
while [ $timeout -gt 0 ]; do
    if netstat -tuln | grep -q ":6080 "; then
        break
    fi
    sleep 1
    ((timeout--))
done

echo "noVNC started successfully"

'EndOfFile' 
RUN chmod +x $HOME/novnc_startup.sh &&     echo "exec $HOME/novnc_startup.sh" >> $HOME/startup.sh



RUN chmod +x $HOME/startup.sh
RUN git clone https://github.com/pyenv/pyenv.git ~/.pyenv &&     cd ~/.pyenv && src/configure && make -C src && cd .. &&     echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc &&     echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc &&     echo 'eval "$(pyenv init -)"' >> ~/.bashrc

ENV PYENV_ROOT="$HOME/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PATH"
ENV PYENV_VERSION=3.11.0

RUN eval "$(pyenv init -)" &&     pyenv install $PYENV_VERSION &&     pyenv global $PYENV_VERSION &&     pyenv rehash

ENV PATH="$HOME/.pyenv/shims:$HOME/.pyenv/bin:$PATH"
RUN python -m pip install --upgrade pip setuptools wheel &&     python -m pip config set global.disable-pip-version-check true



ARG DISPLAY_NUM=1
ARG HEIGHT=768
ARG WIDTH=1024
ENV DISPLAY_NUM=$DISPLAY_NUM
ENV HEIGHT=$HEIGHT
ENV WIDTH=$WIDTH

ENTRYPOINT ["/startup.sh"]