# /usr/bin/env python3
# -*- coding: utf-8 -*-

import textwrap
from typing import List


class StartupScript:
    """
    Dict for configuring a startup script.
    """

    filename: str
    script: str


DEFAULT_STARTUP_SCRIPTS: List[StartupScript] = [
    {
        "filename": "xvfb_startup.sh",
        "script": textwrap.dedent("""
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
            """),
    },
    {
        "filename": "x11vnc_startup.sh",
        "script": textwrap.dedent("""
                #!/bin/bash
                echo "starting vnc"

                (x11vnc -display $DISPLAY \
                    -forever \
                    -shared \
                    -wait 50 \
                    -rfbport 5900 \
                    -nopw \
                    2>/tmp/x11vnc_stderr.log) &

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
            """),
    },
    {
        "filename": "mutter_startup.sh",
        "script": textwrap.dedent("""
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
            """),
    },
    {
        "filename": "tint2_startup.sh",
        "script": textwrap.dedent("""
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
            """),
    },
    {
        "filename": "novnc_startup.sh",
        "script": textwrap.dedent("""
                #!/bin/bash
                echo "starting noVNC"

                # Start noVNC with explicit websocket settings
                /opt/noVNC/utils/novnc_proxy \
                    --vnc localhost:5900 \
                    --listen 6080 \
                    --web /opt/noVNC \
                    > /tmp/novnc.log 2>&1 &

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
            """),
    },
]
