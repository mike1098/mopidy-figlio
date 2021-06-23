import logging

from mopidy import core
import pykka

logger = logging.getLogger(__name__)

class FiglioFrontend(pykka.ThreadingActor, core.CoreListener):
   def __init__(self, config, core):
      super().__init__()
      import RPi.GPIO as GPIO
      self.core = core
      self.config = config["raspberry-forkids"]
      self.playlists = []
      logger.info('!!!!!!!!!!!!!!!!! Hello from Figlio Frontend!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n')
      #self.reload_playlists()
      uri = tuple(self.core.playlists.get_uri_schemes().get())
      logger.info(self.core.playlists.as_list().get())
      for playlist in self.core.playlists.as_list().get():
            self.playlists.append(playlist)
            logger.info(playlist.uri)
      self.core.tracklist.clear()
      logger.info("Playing {0}".format(self.playlists[1]))
      tracks = self.core.playlists.get_items(self.playlists[1].uri).get()
      logger.info("Tracks: {0}".format(tracks))
      track_uris = [track.uri for track in tracks]
      logger.info("Tracks: {0}".format(track_uris))
      self.core.tracklist.add(uris=track_uris)
      self.core.playback.play()

      def reload_playlists(self):
        self.playlists = []
        for playlist in self.core.playlists.as_list().get():
            self.playlists.append(playlist)
            logger.debug(playlist)
        self.selected_playlist = 0
        logger.debug("Found {0} playlists.".format(len(self.playlists)))
