# monitor.py - standalone player monitor script
# Launched via xbmc.executebuiltin('RunScript(monitor.py, ...)') from play_video()
# Runs in its own process so it survives after the plugin call exits (CoreELEC/Android safe)
#
# Args: sys.argv[1]=uid  sys.argv[2]=video_id  sys.argv[3]=token  sys.argv[4]=total_ms

import sys
import os

# Make sure the addon libs are importable
addon_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, addon_dir)

from resources.lib.player import CorridorPlayer
from resources.lib import kodi

def main():
    if len(sys.argv) < 5:
        kodi.log('monitor.py: missing arguments', level=4)
        return

    uid        = sys.argv[1]
    video_id   = sys.argv[2]
    token      = sys.argv[3]
    total_ms   = float(sys.argv[4]) if sys.argv[4] else 0

    kodi.log('monitor.py started: uid={0} vid={1}'.format(uid, video_id))

    player = CorridorPlayer(
        token=token,
        uid=uid,
        video_id=video_id,
        total_ms=total_ms,
    )
    player.monitor()

    kodi.log('monitor.py finished: uid={0}'.format(uid))

main()
