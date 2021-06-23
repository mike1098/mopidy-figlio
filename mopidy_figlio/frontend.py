import logging

from mopidy import core
import pykka

logger = logging.getLogger(__name__) #mopidy_figlio.frontend

class FiglioFrontend(pykka.ThreadingActor, core.CoreListener):
  def __init__(self, config, core):
    super().__init__()
    import RPi.GPIO as GPIO
    self.core = core
    self.config = config["Figlio"]
    self.playlists = []
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(25, GPIO.IN)
    logger.info('!!!!!!!!!!!!!!!!! Hello from Figlio Frontend!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    self.reload_playlists()
    uri = tuple(self.core.playlists.get_uri_schemes().get())
    logger.info("PLaylist as list:\n {0}\n".format(self.core.playlists.as_list().get()))
    for playlist in self.core.playlists.as_list().get():
      self.playlists.append(playlist)
      logger.info("Playlist as URI: {0}".format(playlist.uri))
    self.core.tracklist.clear()
    logger.info("Playing {0}".format(self.playlists[0]))
    tracks = self.core.playlists.get_items(self.playlists[0].uri).get()
    logger.info("Tracks: {0}".format(tracks))
    track_uris = [track.uri for track in tracks]
    logger.info("Track URI: {0}".format(track_uris))
    self.core.tracklist.add(uris=track_uris)
    self.core.tracklist.add(uris=["http://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q=Hello&tl=en"])
    logger.info("URI Schemes: {0}".format(self.core.get_uri_schemes().get()))
    logger.info("Next TLID: {0}".format(self.core.tracklist.get_next_tlid().get()))
    self.core.playback.play(tlid=1)
    
    GPIO.add_event_detect(25, GPIO.BOTH, callback=self.my_callback)   
  def my_callback(channel):  
    if GPIO.input(25):     # if port 25 == 1  
      logger.info("Rising edge detected on 25")  
    else:                  # if port 25 != 1  
      logger.info("Falling edge detected on 25")  

  def reload_playlists(self):
    self.playlists = []
    for playlist in self.core.playlists.as_list().get():
      self.playlists.append(playlist)
      logger.debug(playlist)
      self.selected_playlist = 0
      logger.debug("Found {0} playlists.".format(len(self.playlists)))
