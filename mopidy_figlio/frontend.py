import logging

from mopidy import core
import pykka
import RPi.GPIO as GPIO

logger = logging.getLogger(__name__) #mopidy_figlio.frontend

class FiglioFrontend(pykka.ThreadingActor, core.CoreListener):
  def __init__(self, config, core):
    super().__init__()
    self.core = core
    self.config = config["Figlio"]
    self.playlists = []
    global counter
    counter = 0
    GPIO.setwarnings(True)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(25, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    self.reload_playlists()    
    GPIO.add_event_detect(25, GPIO.FALLING, callback=self.my_callback, bouncetime=1000)

  def on_start(self):
    logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend started !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    
  def on_stop(self):
    logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend stopped !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    GPIO.cleanup()

  def on_failure(self):
    logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend failed !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    GPIO.cleanup()

  def my_callback(self,channel):
    global counter  
    self.core.tracklist.clear()
    playlist_name="Ich spiele für Dich " + self.playlists[counter].name
    logger.info("Playing: {0}".format(playlist_name))
    self.core.tracklist.add(uris=["http://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q=" +playlist_name+"&tl=de"])
    tracks = self.core.playlists.get_items(self.playlists[counter].uri).get()
    track_uris = [track.uri for track in tracks]
    logger.info("Track URI: {0}".format(track_uris))
    self.core.tracklist.add(uris=track_uris)
    self.core.playback.play()
    counter += 1  
  
  def reload_playlists(self):
    self.playlists = []
    for playlist in self.core.playlists.as_list().get():
      self.playlists.append(playlist)
      logger.info("Playlist:{0}".format(playlist))
      self.selected_playlist = 0
      logger.info("Found {0} playlists.".format(len(self.playlists)))
