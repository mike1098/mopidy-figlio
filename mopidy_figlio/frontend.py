"""
Figlio extension for Mopidy

A mopidy extension to read a playlist from RFID card and start playing at same track and position where left of.
Announce the playlist name with text to speach.
Provide a menu driven by text to speach commands to write a playlist to a RFID card 
"""
############  
#playback issue
###########

import logging
from mopidy import core
#from mopidy import audio
#from mopidy.mixer import Mixer
import pykka

# For RFID reader and control buttons we need GPIOs
# If other device as Raspi is used needs to be adjusted
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

# For audio announcements currently GStreamer is used.
#TODO: test if possible to use mopidy.audio instead.

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
from requests import Request

from time import sleep

logger = logging.getLogger(__name__) #mopidy_figlio.frontend

class FiglioFrontend(pykka.ThreadingActor, core.CoreListener):
  def __init__(self, config, core):
    super().__init__()
    self.core = core
    #self.mixer = Mixer
    #self.audio = audio
    self.config = config["figlio"]
    self.playlists = []
    GPIO.setwarnings(True)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(25, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(25, GPIO.BOTH, callback=self.cb_card_inserted, bouncetime=1000)
    #Gst.init(None)

  def on_start(self):
    logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend started !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    self.reload_playlists()

  def on_stop(self):
    logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend stopped !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    GPIO.cleanup()

  def on_failure(self):
    logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend failed !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    GPIO.cleanup()

  def cb_card_inserted(self,channel):
    """
    This is the callback function which is called as soon as a RFID card is inserted or removed in the slot.
    Card insertation could be detected by photo sensor or physical contact switch.
    From the card the playlist URI, the position in the track list and the time position is read.
    Current format is: <playlist uri>,<track pos>,<time pos> 
    Example: m3u:rockantenne.m3u,4,0

    TODOS: a lot
    """
    # We stop plying as soon as card is removed
    if GPIO.input(channel) == GPIO.LOW:
      self.core.playback.stop()
      #self.core.playback.set_state("paused")
      logger.info("Core Playback State:{0}".format(self.core.playback.get_state().get()))
      return
    
    id = None
    rf_tlid = None
    rf_seek = None
    content = None
    reader = SimpleMFRC522()
    
    #Current MFRC522 implementation of SimpleMFRC522 support only 48 bytes maximum data length.
    #create own function for reading and writing.
    id, content = reader.read_no_block()
    logger.info("Card ID: {0} Content: {1}".format(id, content))
    playlist_uri, rf_tlid, rf_seek = content.split(",")
    logger.info("Playlist URI: {0} tlid: {1} seek: {2}".format(playlist_uri, rf_tlid, rf_seek))
    playlist = self.core.playlists.lookup(playlist_uri).get()
    #Playlist name is only derived from playlist filename
    #Add support of extended M3U Tag #PLAYLIST:
    logger.info("Playing: {0} Last Modifed:{1} URI:{2}".format(playlist.name, playlist.last_modified, playlist.uri))
    #self.announce("Ich spiele für Dich " + playlist.name)
    tracks = self.core.playlists.get_items(playlist_uri).get()
    track_uris = [track.uri for track in tracks]
    logger.debug("Track URI: {0}".format(track_uris))
    self.core.tracklist.set_single(False)
    self.core.tracklist.set_consume(False)
    # Repeat mode is needed to not stop after first track is played
    self.core.tracklist.set_repeat(True)
    if self.core.tracklist.get_length().get():
      self.core.tracklist.clear()
    self.core.tracklist.add(uris=track_uris, at_position=1)
    first_tlid = self.core.tracklist.get_tl_tracks().get()[0].tlid -1
    logger.info("TL Tracks Type:{0}".format(type(self.core.tracklist.get_tl_tracks().get())))
    logger.info("TLIDs: {0}".format(self.core.tracklist.get_tl_tracks().get()))
    play = self.core.playback.play(tlid=int(rf_tlid)+first_tlid)
    logger.info("Play command result:{0}".format(play.get()))
    logger.info("Tracklist version: {0} Length: {1} Index:{2}".format(self.core.tracklist.get_version().get(), self.core.tracklist.get_length().get(), self.core.tracklist.index(tlid=4).get()))
    seek = self.core.playback.seek(time_position=int(rf_seek))    
    logger.info("Seek: {0}".format(seek.get()))
    logger.info("Next Track TLID:{0}".format(self.core.tracklist.get_eot_tlid().get()))

  def reload_playlists(self):
    self.playlists = []
    for playlist in self.core.playlists.as_list().get():
      self.playlists.append(playlist)
      logger.debug("Load Playlist:{0}".format(playlist))
      self.selected_playlist = 0
      logger.debug("Found {0} playlists to load.".format(len(self.playlists)))

  def audio_announce(self,announcment):
    """ A test to use mopidy.audio for the announcmenets"""
    announcment=requests.utils.quote(announcment)
    uri="http://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&q={0}&tl=de".format(announcment)
    logger.debug("URI:{0}".format(uri))
    self.audio.Audio.mixer=self.mixer
    self.audio.Audio.set_uri(self, uri=uri)
    self.audio.Audio.start_playback()

  def announce(self,announcment,lang="de"):
    """
    Using GStreamer to play annoncments like the name of the playlist loaded
    """
    
    payload = {"tl": lang, "ie": "UTF-8", "client": "tw-ob", "q": announcment}
    uri=Request('Get', 'https://translate.google.com/translate_tts', params=payload).prepare()
    logger.info("URI:{0}".format(uri.url))
    player = Gst.parse_launch("souphttpsrc location={0} ! decodebin !  audioconvert ! alsasink".format(uri.url))
    player.set_state(Gst.State.PLAYING)
    logger.debug("GST State:{0}".format(player.current_state))

    # GST Signal handling
    self.bus = player.get_bus()
    self.bus.add_signal_watch()
    self.bus.connect("message", self.cb_on_message)
  
    # Init GObject loop to handle Gstreamer Bus Events 
    self.loop = GObject.MainLoop() 
    try:
      logger.debug("Announcement GST GObject Loop started")
      self.loop.run()
      logger.debug("Announcement GST GObject Loop stopped") 
    except: 
      self.loop.quit()
    player.set_state(Gst.State.NULL) 
    logger.debug("Announcement GST State:{0}".format(player.current_state))
  
  def cb_on_message(self, bus: Gst.Bus, message: Gst.Message):
    mtype = message.type
    logger.debug("Announcement GST GOobject Event:{0}".format(mtype))
    if mtype == Gst.MessageType.EOS: 
      # Handle End of Stream
      self.loop.quit()
    elif mtype == Gst.MessageType.ERROR:
      #TODO: Check real syntax
      logger.error("Announcement GST GObject Error:{0}".format(message.parse_error()))
      self.loop.quit()
    elif mtype == Gst.MessageType.WARNING:
      #TODO: Check real syntax
      logger.warning("Announcement GST GObject Warning:{0}".format(message.parse_warning()))
