"""
Shoutcast/Icecast HTTP reader.

FFmpeg can open these URLs itself, but it only reports the ICY headers
that were present at connect time -- the live "StreamTitle" updates never
reach us. So we do the HTTP part ourselves, strip the interleaved
metadata blocks out of the byte stream, and hand the clean audio to the
decoder. That gives real "now playing" text and lets us resolve playlist
URLs before FFmpeg ever sees them.
"""

import io

import requests

USER_AGENT = "InternetAnalogRadio/1.0 (+https://github.com/) VLC-compatible"

PLAYLIST_TYPES = {
    'audio/x-scpls', 'application/pls+xml', 'audio/scpls',
    'audio/x-mpegurl', 'application/x-mpegurl', 'audio/mpegurl',
    'application/vnd.apple.mpegurl',
}

_MAX_PLAYLIST_HOPS = 3


class HlsStream(Exception):
    """Raised when a URL turns out to be an HLS playlist FFmpeg should open."""

    def __init__(self, url):
        super().__init__("HLS stream: %s" % url)
        self.url = url


def _looks_like_hls(text):
    return '#EXTM3U' in text and '#EXT-X-' in text


def _parse_playlist(text):
    """Pulls stream URLs out of a PLS or M3U body, in order."""
    urls = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.lower().startswith('file') and '=' in line:  # PLS
            candidate = line.split('=', 1)[1].strip()
        elif line.startswith('#') or ('=' in line and not line.startswith('http')):
            continue
        else:
            candidate = line
        if candidate.startswith(('http://', 'https://')):
            urls.append(candidate)
    return urls


class IcyStream(io.RawIOBase):
    """
    A read-only file object yielding pure audio bytes, with the current
    ICY title available as `.title` while playback runs.
    """

    def __init__(self, url, timeout=6.0, chunk_hint=16384):
        super().__init__()
        self.url = url
        self.title = None
        self.station_name = None
        self.content_type = None
        self.bitrate = None
        self._closed_by_us = False

        self._response = requests.get(
            url,
            headers={'Icy-MetaData': '1', 'User-Agent': USER_AGENT, 'Accept': '*/*'},
            stream=True,
            timeout=(timeout, timeout),
            allow_redirects=True,
        )
        self._response.raise_for_status()

        headers = self._response.headers
        self.content_type = (headers.get('content-type') or '').split(';')[0].strip().lower()
        self.station_name = headers.get('icy-name')
        self.bitrate = headers.get('icy-br')
        try:
            self._meta_interval = int(headers.get('icy-metaint') or 0)
        except (TypeError, ValueError):
            self._meta_interval = 0

        self._raw = self._response.raw
        self._until_meta = self._meta_interval
        self._chunk_hint = chunk_hint

    # -- file protocol ------------------------------------------------- #

    def readable(self):
        return True

    def seekable(self):
        return False

    def readinto(self, buffer):
        if self._closed_by_us:
            return 0
        try:
            wanted = len(buffer)
            if self._meta_interval:
                if self._until_meta <= 0:
                    if not self._consume_metadata():
                        return 0
                wanted = min(wanted, self._until_meta)

            data = self._raw.read(wanted)
            if not data:
                return 0
            buffer[:len(data)] = data
            if self._meta_interval:
                self._until_meta -= len(data)
            return len(data)
        except Exception:
            if self._closed_by_us:
                return 0
            raise

    def _consume_metadata(self):
        length_byte = self._raw.read(1)
        if not length_byte:
            return False
        size = length_byte[0] * 16
        if size:
            block = self._raw.read(size)
            if block is None:
                return False
            self._read_title(block)
        self._until_meta = self._meta_interval
        return True

    def _read_title(self, block):
        text = block.decode('utf-8', 'replace').rstrip('\x00')
        marker = "StreamTitle='"
        if marker not in text:
            return
        title = text.split(marker, 1)[1].split("';", 1)[0].strip()
        self.title = title or None

    def close(self):
        self._closed_by_us = True
        try:
            self._response.close()
        except Exception:
            pass
        super().close()


def open_icy(url, timeout=6.0, _hops=0):
    """
    Opens `url`, following PLS/M3U playlist indirection.

    Returns an `IcyStream`, or raises `HlsStream` when the URL turns out
    to be an HLS master playlist that FFmpeg should handle directly.
    """
    if url.split('?')[0].lower().endswith('.m3u8'):
        raise HlsStream(url)

    stream = IcyStream(url, timeout=timeout)

    is_playlist_type = stream.content_type in PLAYLIST_TYPES
    is_playlist_ext = url.split('?')[0].lower().endswith(('.pls', '.m3u'))
    if not (is_playlist_type or is_playlist_ext):
        return stream

    if _hops >= _MAX_PLAYLIST_HOPS:
        stream.close()
        raise IOError("playlist redirects too deep: %s" % url)

    try:
        body = stream.read(65536).decode('utf-8', 'replace')
    finally:
        stream.close()

    if _looks_like_hls(body):
        raise HlsStream(url)

    for candidate in _parse_playlist(body):
        try:
            return open_icy(candidate, timeout=timeout, _hops=_hops + 1)
        except HlsStream:
            raise
        except Exception:
            continue

    raise IOError("no playable entries in playlist: %s" % url)
