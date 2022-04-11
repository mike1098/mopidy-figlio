"""
Figlio extension for Mopidy

A mopidy extension to read a playlist from RFID card and start playing at same track and position where left of.
Announce the playlist name with text to speach.
Provide a menu driven by text to speach commands to write a playlist to a RFID card 
"""

import logging
from mopidy import core
import pykka
from .rfid_util import RfidUtil
# For RFID reader and control buttons we need GPIOs
# If other device as Raspi is used needs to be adjusted
#import RPi.GPIO as GPIO
#from mfrc522 import SimpleMFRC522
from gpiozero import Button


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
    self.config = config["figlio"]
    self.playlists = []

  def on_start(self):
    logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend started !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    Gst.init(None)
    self.reload_playlists()
    #define the card reader
    self.rfidutil=RfidUtil()
    #Define button to play/pause
    self.button_play = Button(17,pull_up=False)
    self.button_play.when_pressed = self.cb_pause_play
    #Define Button skip/seek forward
    self.button_fwd = Button(27,pull_up=False)
    self.button_fwd.when_pressed = self.cb_skip_forward
    #Define Button skip/seek backward
    self.button_back = Button(22,pull_up=False)
    self.button_back.when_pressed = self.cb_skip_backward
    #Define Button volume up
    self.button_vol_up = Button(23,pull_up=False)
    self.button_vol_up.when_pressed = self.cb_vol_up
    #Define Button volume dowwn
    self.button_vol_down = Button(24,pull_up=False)
    self.button_vol_down.when_pressed = self.cb_vol_down
    #photo sensor; If high or active, card is inserted.
    self.sensor = Button(25,pull_up=False)
    self.sensor.when_pressed = self.cb_card_inserted
    self.sensor.when_released = self.cb_card_removed

  def on_stop(self):
    logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend stopped !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    #Because of GPIO we need to cleanup here
    self.rfidutil.reader.cleanup()

  def on_failure(self):
    logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend failed !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    #Because of GPIO we need to cleanup here
    self.rfidutil.reader.cleanup()

  def playback_state_changed(self, old_state, new_state):
        logger.info("Playback State changed from: {0} to: {1}".format(old_state, new_state))
        if old_state == "stopped":
            seek = self.core.playback.seek(self.seek_time).get()
            logger.info("Seek command result: {0}".format(seek))
            self.seek_time = 0
  
  def cb_card_inserted(self,channel):
    """
    This is the callback function which is called as soon as a RFID card is inserted or removed in the slot.
    Card insertation could be detected by photo sensor or physical contact switch.
    From the card the playlist URI, the position in the track list and the time position is read.
    Playlist Example: m3u:rockantenne.m3u

    TODOS: a lot
    """
    
    '''
    # We stop plying as soon as card is removed
    if GPIO.input(channel) == GPIO.LOW:
      self.core.playback.stop()
      #self.core.playback.set_state("paused")
      logger.info("Core Playback State:{0}".format(self.core.playback.get_state().get()))
      return
    '''
    id = None
    rf_tlid = None
    rf_seek = None
    id = self.rfidutil.connect_card()
    playlist_uri = self.rfidutil.read_pl()
    volume,lang,rf_tlid,rf_seek = self.rfidutil.read_data()
    logger.info("Card ID: {0} Playlist: {1}".format(id, playlist_uri))
    logger.info(f"Changing volume to {volume}")
    self.core.mixer.set_volume(volume)
    self.seek_time = int(rf_seek)
    logger.info("Playlist URI: {0} tlid: {1} seek: {2}".format(playlist_uri, rf_tlid, rf_seek))
    playlist = self.core.playlists.lookup(playlist_uri).get()
    #Playlist name is only derived from playlist filename
    #Add support of extended M3U Tag #PLAYLIST to mopidy core
    if not playlist:
        logger.info("Plylist not found  ")
        self.announce(f"Die Playliste {playlist_uri} habe ich nicht gefunden")
        return
    logger.info("Playing: {0} Last Modifed:{1} URI:{2}".format(playlist.name, playlist.last_modified, playlist.uri))
    self.announce("Ich spiele für Dich " + playlist.name)
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
    first_tlid = self.core.tracklist.get_tl_tracks().get()[0].tlid
    logger.info("TLIDs: {0}".format(self.core.tracklist.get_tl_tracks().get()))
    play = self.core.playback.play(tlid=int(rf_tlid)+first_tlid)
    logger.info("Play command result:{0}".format(play.get()))
    logger.info("Tracklist version: {0} Length: {1} Index:{2}".format(self.core.tracklist.get_version().get(), self.core.tracklist.get_length().get(), self.core.tracklist.index(tlid=4).get()))
    logger.info("Next Track TLID:{0}".format(self.core.tracklist.get_eot_tlid().get()))

  def cb_card_removed(self):
        logger.info("Card Removed")
        self.core.playback.stop().get()
        logger.info("Sent Stop command")
        logger.info("Playback State: {0}".format(self.core.playback.get_state().get()))
        self.rfidutil.reader.stop_crypto()

  def cb_stop(self):
        self.core.playback.stop().get()
        logger.info("Sent Stop command")
        logger.info("Playback State: {0}".format(self.core.playback.get_state().get()))
    
  def cb_play(self):
    play = self.core.playback.play().get()
    logger.info("Sent Play command: {0}".format(play))
    logger.info("Playback State: {0}".format(self.core.playback.get_state().get()))
    
  def cb_pause_play(self):
    logger.info("Pause/Play pressed")
    if self.core.playback.get_state().get() == core.PlaybackState.PLAYING:
      self.core.playback.pause()
      self.rfidutil.write_volume(self.core.mixer.get_volume().get())
      self.rfidutil.write_track_progress(self.core.playback.get_time_position().get())
      track_nr = self.core.playback.get_current_tl_track().get().tlid - self.core.tracklist.get_tl_tracks().get()[0].tlid
      self.rfidutil.write_track_nr(track_nr)
    else:
      self.core.playback.play()
      logger.info("Playback State: {0}".format(self.core.playback.get_state().get()))

  def cb_skip_forward(self):
      logger.info("Skip forward pressed")
      self.core.playback.next()

  def cb_skip_backward(self):
      logger.info("Skip backward pressed")
      self.core.playback.previous()
  
  def cb_vol_up(self):
      logger.info("Volume UP")
      step = int(self.config.get("step", 5))
      volume = self.core.mixer.get_volume().get()
      volume += step
      volume = min(volume, 100)
      self.core.mixer.set_volume(volume)
  
  def cb_vol_down(self):
      logger.info("Volume DOWN")
      step = int(self.config.get("step", 5))
      volume = self.core.mixer.get_volume().get()
      volume -= step
      volume = max(volume, 0)
      self.core.mixer.set_volume(volume)

  def reload_playlists(self):
    self.playlists = []
    for playlist in self.core.playlists.as_list().get():
      self.playlists.append(playlist)
      logger.debug("Load Playlist:{0}".format(playlist))
      self.selected_playlist = 0
      logger.debug("Found {0} playlists to load.".format(len(self.playlists)))

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
