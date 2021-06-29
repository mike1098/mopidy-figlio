import logging

from mopidy import core
from mopidy import audio
import pykka
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
import requests

logger = logging.getLogger(__name__) #mopidy_figlio.frontend

class FiglioFrontend(pykka.ThreadingActor, core.CoreListener):
  def __init__(self, config, core):
    super().__init__()
    self.core = core
    self.audio = audio
    self.config = config["Figlio"]
    self.playlists = []
    GPIO.setwarnings(True)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(25, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    self.reload_playlists()    
    GPIO.add_event_detect(25, GPIO.FALLING, callback=self.cb_card_inserted, bouncetime=1000)
    Gst.init(None)

  def on_start(self):
    logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend started !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    
  def on_stop(self):
    logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend stopped !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    GPIO.cleanup()

  def on_failure(self):
    logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend failed !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    GPIO.cleanup()

  def cb_card_inserted(self,channel):
    id = None
    rftlid = None
    rfseek = None
    content = None
    reader = SimpleMFRC522()
    self.core.playback.stop()
    #self.core.playback.set_state("stopped")
    logger.info("Core Playback State:{0}".format(self.core.playback.get_state().get()))
    id, content = reader.read_no_block()
    logger.info("Card ID: {0} Content: {1}".format(id, content))
    playlist_uri, rftlid, rfseek = content.split(",")
    logger.info("Playlist URI: {0} tlid: {1} seek: {2}".format(playlist_uri, rftlid, rfseek))
    playlist = self.core.playlists.lookup(playlist_uri).get()
    self.core.tracklist.clear()
    logger.info("Playing: {0} Last Modifed:{1} URI:{2}".format(playlist.name, playlist.last_modified, playlist.uri))
    self.announce("Ich spiele für Dich " + playlist.name)
    tracks = self.core.playlists.get_items(playlist_uri).get()
    track_uris = [track.uri for track in tracks]
    logger.debug("Track URI: {0}".format(track_uris))
    self.core.tracklist.set_single(False)
    self.core.tracklist.set_consume(False)
    self.core.tracklist.add(uris=track_uris)
    #self.core.playback.play(tlid=int(rftlid))
    play=self.core.playback.play(tlid=4)
    logger.info("Play command result:{0}".format(play.get()))
    seek = self.core.playback.seek(time_position=120000)    
    logger.info("Seek: {0}".format(seek.get()))

  def reload_playlists(self):
    self.playlists = []
    for playlist in self.core.playlists.as_list().get():
      self.playlists.append(playlist)
      logger.info("Playlist:{0}".format(playlist))
      self.selected_playlist = 0
      logger.debug("Found {0} playlists.".format(len(self.playlists)))

  def announce(self,announcment):
    announcment=requests.utils.quote(announcment)
    uri="http://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q={0}&tl=de".format(announcment)
    logger.debug("URI:{0}".format(uri))
    player = Gst.parse_launch("souphttpsrc location={0} ! decodebin !  audioconvert ! alsasink".format(uri))
    player.set_state(Gst.State.PLAYING)
    logger.debug("GST State:{0}".format(player.current_state))
    # GST Signal handling
    self.bus = player.get_bus()
    self.bus.add_signal_watch()
    self.bus.connect("message", self.cb_on_message)
    
    # Init GObject loop to handle Gstreamer Bus Events 
    self.loop = GObject.MainLoop() 
    try:
      logger.debug("GST GOobject Loop started")
      self.loop.run()
      logger.debug("GST GObject Loop stopped") 
    except: 
      self.loop.quit()
    player.set_state(Gst.State.NULL) 
    logger.debug("GST State:{0}".format(player.current_state))
  
  def cb_on_message(self, bus: Gst.Bus, message: Gst.Message):
    mtype = message.type
    logger.debug("GST GOobject Event:{0}".format(mtype))
    if mtype == Gst.MessageType.EOS: 
      # Handle End of Stream
      self.loop.quit()
    elif mtype == Gst.MessageType.ERROR:
      #TODO: Check real syntax
      logger.error("GST GOobject Error:{0}".format(message.parse_error()))
      self.loop.quit()
    elif mtype == Gst.MessageType.WARNING:
      #TODO: Check real syntax
      logger.warning("GST GOobject Warning:{0}".format(message.parse_warning()))