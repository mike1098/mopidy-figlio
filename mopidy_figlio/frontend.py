import logging
from mopidy import core
from mopidy.core import CoreListener
import pykka
from gpiozero import Button
from time import sleep

logger = logging.getLogger(__name__) #mopidy_figlio.frontend

class FiglioFrontend(pykka.ThreadingActor, core.CoreListener):
    def __init__(self, config, core):
        super().__init__()
        self.core = core
        self.config = config["figlio"]
    
    def on_start(self):
        logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend started !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        #Define button to play/pause
        self.button = Button(17,pull_up=False)
        self.button.when_released = self.cb_pause_play
        #photo sensor; If high or active, card is inserted.
        self.sensor = Button(25,pull_up=False)
        self.sensor.when_pressed = self.cb_card_inserted
        self.sensor.when_released = self.cb_stop
        logger.info("Playback State: {0}".format(self.core.playback.get_state().get()))

    def on_stop(self):
        logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend stopped !!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    def on_failure(self):
        logger.info('!!!!!!!!!!!!!!!!! Figlio Frontend failed !!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    def cb_stop(self):
        stop = self.core.playback.stop().get()
        logger.info("Sent Stop command: {0}".format(stop))
        logger.info("Playback State: {0}".format(self.core.playback.get_state().get()))
    
    def cb_play(self):
        play = self.core.playback.play().get()
        logger.info("Sent Play command: {0}".format(play))
        logger.info("Playback State: {0}".format(self.core.playback.get_state().get()))
    
    def cb_pause_play(self):
        logger.info("Pause/Play pressed")
        if self.core.playback.get_state().get() == core.PlaybackState.PLAYING:
            self.core.playback.pause()
        else:
            self.core.playback.play()
        logger.info("Playback State: {0}".format(self.core.playback.get_state().get()))

    def  track_playback_started(self,tl_track):
        seek = self.core.playback.seek(160000).get()
        logger.info("Seek command result: {0}".format(seek))

    def cb_card_inserted(self):
        logger.info("Card inserted")
        track_uris = ['file:///home/pi/Music/Blues/004%20doggin%27%20the%20blues.mp3', 'file:///home/pi/Music/Blues/003%20friendless%20blues.mp3']
        self.core.tracklist.add(uris=track_uris)
        play = self.core.playback.play().get()

        #logger.info("Seek command result: {0}".format(seek))
        sleep(1)
        logger.info("Playback State: {0}".format(self.core.playback.get_state().get()))

    def cb_card_removed():
        pass
