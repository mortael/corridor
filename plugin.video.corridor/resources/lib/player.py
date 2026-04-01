# Module: player
# Monitors playback and reports progress back to corridordigital.com

import time
from kodi_six import xbmc
from resources.lib import api
from resources.lib import kodi


class CorridorPlayer(xbmc.Player):
    """
    Monitors playback and sends periodic progress reports to the API.
    Call monitor() after setResolvedUrl to block until playback ends.
    """

    REPORT_INTERVAL = 30  # seconds between reports

    def __init__(self, token, uid, video_id):
        super().__init__()
        self.token = token
        self.uid = uid
        self.video_id = video_id

        self._started = False
        self._stopped = False
        self._total_ms = 0
        self._last_report_wall = None
        self._session_watched_ms = 0

    def onPlayBackStarted(self):
        self._started = True
        self._last_report_wall = time.time()
        # Get actual total duration from Kodi
        try:
            self._total_ms = self.getTotalTime() * 1000
        except Exception:
            self._total_ms = 0
        kodi.log('Playback started uid={0} vid={1} total={2:.0f}ms'.format(
            self.uid, self.video_id, self._total_ms))

    def onPlayBackStopped(self):
        self._stopped = True
        self._final_report()

    def onPlayBackEnded(self):
        self._stopped = True
        self._final_report()

    def onPlayBackError(self):
        self._stopped = True

    def _current_ms(self):
        try:
            return self.getTime() * 1000
        except Exception:
            return 0

    def _accrue_and_report(self):
        now = time.time()
        elapsed_ms = (now - self._last_report_wall) * 1000
        self._session_watched_ms += elapsed_ms
        self._last_report_wall = now

        # Refresh total in case it wasn't available at start
        if not self._total_ms:
            try:
                self._total_ms = self.getTotalTime() * 1000
            except Exception:
                pass

        api.report_progress(
            self.token,
            self.uid,
            self.video_id,
            self._current_ms(),
            self._total_ms,
            self._session_watched_ms,
        )

    def _final_report(self):
        if self._started and self._last_report_wall:
            self._accrue_and_report()

    def monitor(self):
        """Block until playback finishes, sending periodic progress reports."""
        # Wait for playback to start
        wait = 0
        while not self._started and not self._stopped and wait < 15:
            xbmc.sleep(500)
            wait += 0.5

        # Periodic loop
        tick = 0
        while self._started and not self._stopped:
            xbmc.sleep(1000)
            tick += 1
            if not self.isPlaying():
                self._stopped = True
                self._final_report()
                break
            if tick >= self.REPORT_INTERVAL:
                self._accrue_and_report()
                tick = 0
