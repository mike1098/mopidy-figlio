"""
A Module to support RFID card read and write
"""


import logging
import sys
import pirc522 #https://github.com/ondryaso/pi-rc522
import mifare

class RfidUtil:
    """
    A class to read and write playlist, Track Number, time from mopidy
    """
    def __init__(self) -> None:
        self.reader = pirc522.RFID()
        self.card = mifare.Classic1k()
        self.cardid=None
        logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    def connect_card(self,retries=3):
        """Opens the connection to a RFID card for reading or writing.

        Returns the NUID/UID as a list
        """
        rdr=self.reader
        while retries > 0:
            (error, _) = rdr.request()
            if not error:
                (error, uid) = rdr.anticoll()
                if not error:
                    if not rdr.select_tag(uid):
                        self.cardid=uid
                        return uid
            retries -= 1
        self.cardid=None
        return None

    def auth_block_a(self,block=0):
        """Authenticate to a sector by a given block with authenticator A.

        Returns true if authentication was successful, otherwise false.
        """
        rdr=self.reader
        cardid=self.cardid
        keya=self.card.get_key_a(block)
        error = rdr.card_auth(rdr.auth_a, block, keya, cardid)
        if not error:
            logging.debug(f"Sucessful Auth block {block}")
            return True
        return False

    def auth_new_block_a(self, sector_trailer, block):
        """
        Check if the new block has a new sector trailer and authenticate if needed.

        Returns true if authentication was successful, otherwise false.
        """
        card=self.card
        new_sector_trailer = card.get_sector_trailer(block)
        logging.debug(f"Block: {block} Old Trailer: {sector_trailer} "
                       f"New Trailer:{new_sector_trailer }")
        if sector_trailer != new_sector_trailer:
            sector_trailer = new_sector_trailer
            if not self.auth_block_a(sector_trailer):
                return None
        return sector_trailer

    def read_pl(self, startblock=8):
        """Reads text beinning of startblock from RFID card.

        The TEXT must be UTF8 encoded and terminated with at least one 0x00 otherwise it
        returns none. If a sector could not be authenticated it returns None

        returns a byte object otherwise None
        """
        card=self.card
        rdr=self.reader
        logging.info(f"reading playlist from card "
                     f"starting with block #{startblock:02}")
        block_not_zero = True
        data_block_index = card.data_blocks.index(startblock)
        raw_content=[]
        sector_trailer=card.get_sector_trailer(startblock)
        if not self.auth_block_a(startblock):
            logging.error(f"could not intially authenticate block #{startblock:02}")
            return None
        while block_not_zero:
            error, block_content = rdr.read(card.data_blocks[data_block_index])
            if not error:
                logging.debug(f"read block #{card.data_blocks[data_block_index]:02}"
                      f" byte content: {block_content}")
                raw_content.extend(block_content)
                if 0x00 in raw_content:
                    logging.debug(f"Found 0x00 in content at block #"
                                  f"{card.data_blocks[data_block_index]:02}"
                                  "-> end of text. Stop reading.")
                    block_not_zero = False
                else:
                    data_block_index += 1
                    if data_block_index == len(card.data_blocks):
                        logging.error("Reached end of card while reading!")
                        return False
                    new_block = card.data_blocks[data_block_index]
                    sector_trailer= self.auth_new_block_a(sector_trailer, new_block)
                    if not sector_trailer:
                        logging.error(f"could not authenticate block #{new_block:02}")
                        return None
            else:
                logging.error(f"Could not read block #{card.data_blocks[data_block_index]}")
                return None
        return bytes(raw_content).decode().rstrip('\0x00')

    def read_data(self,block=2):
        """
        Reads the volume, language code track nr and progress from card

        returns a list with this items
        """
        card=self.card
        rdr=self.reader
        logging.info(f"reading volume, language code, track nr. and track progress,  from card "
                     f"starting with block #{block:02}")
        if not self.auth_block_a(block):
            logging.error(f"could not intially authenticate block #{block:02}")
            return None
        # pirc522 return True in case of any error :-(
        error, block_content = rdr.read(block)
        if error:
            logging.error(f"Could not read block #{block:02}")
            return None
        logging.debug(f"read block #:{block:02}"
                      f" byte content: {block_content}")
        vol = block_content[0]
        lang=''.join(map(chr,block_content[1:3]))
        track_nr = card.block2int(block_content[3:5])
        track_progress = card.block2int(block_content[5:9])
        return vol, lang, track_nr, track_progress

    def write_volume(self, volume: int=25, block: int=2):
        """Write the Volume to the card

        Return True if successful written else False
        """
        rdr=self.reader
        logging.info(f"Writing volume: {volume:02} to block #{block:02}")
        if not self.auth_block_a(block):
            logging.error(f"could not intially authenticate block #{block:02} to write volume")
            return False
        error, block_content = rdr.read(block)
        if error:
            logging.error(f"could not read block #{block:02} to write volume")
            return False
        block_content[0] = volume
        logging.debug(f"Write Volume: {volume} Volume in hex: {volume}")
        logging.debug(f"\twrite block #{block:02}"
                  f" byte content: {block_content}")
        # pirc522 return True in case of any error :-(
        error = rdr.write(block, block_content)
        if error:
            logging.error(f"could not write volume to block #{block:02}")
            return False
        return True

    def write_lang(self,lang: str='DE', block: int=2):
        """Write the Playlist language to the card.

        The language is a ISO 3166-1 Alpha-2 code
        Return True if successful written else False
        """
        rdr=self.reader
        logging.info(f"Writing language code {lang} to block #{block:02}")
        if not self.auth_block_a(block):
            logging.error(f"could not intially authenticate block #{block:02} to write language")
            return False
        error, block_content = rdr.read(block)
        if error:
            logging.error(f"could not read block #{block:02} to write language")
            return False
        lang_encode= lang.encode()
        logging.debug(f"Write language {lang} encoded {lang_encode}")
        block_content[1:3] = lang_encode
        logging.debug(f"\twrite language block #{block:02}"
                  f" byte content: {block_content}")
        # pirc522 return True in case of any error :-(
        error = rdr.write(block, block_content)
        if error:
            logging.error(f"could not write language to  block #{block:02}")
            return False
        return True

    def write_track_nr(self, track_nr: int = 0, block: int=2):
        """Write the track number to the card.

        Return True if successful written else False
        """
        card=self.card
        rdr=self.reader
        logging.info(f"Writing track number {track_nr} to block #{block:02}")
        if not self.auth_block_a(block):
            logging.error(f"could not intially authenticate block #{block:02} to write track_nr")
            return False
        error, block_content = rdr.read(block)
        if error:
            logging.error(f"could not read block #{block:02} to write track_nr")
            return False
        #We use 2 bytes for the track_nr, max length = 65535
        track_nr_hex= card.int2block(track_nr, 2)
        logging.debug(f"Write track_nr: {track_nr} track_nr in hex: {track_nr_hex}")
        if track_nr_hex:
            block_content[3:5]= track_nr_hex
            logging.debug(f"\twrite block #{block:02}"
                  f" byte content: {block_content}")
            # pirc522 return True in case of any error :-(
            error = rdr.write(block, block_content)
            if error:
                logging.error(f"could not write track_nr to block #{block:02}")
                return False
            return True
        logging.error(f"track_nr: {track_nr} not written")
        return False

    def write_track_progress(self, track_progress: int = 0, block: int=2):
        """Write the track progress in ms to the card.

        Return True if successful written else False
        """
        card=self.card
        rdr=self.reader
        logging.info(f"Writing track progress in ms to block #{block:02}")
        if not self.auth_block_a(block):
            logging.error(f"could not intially authenticate "
                          f"block #{block:02} to write time position")
            return False
        error, block_content = rdr.read(block)
        if error:
            logging.error(f"could not read block #{block:02} to write time position")
            return False
        #We use 4 bytes for the timeposition, max length = 4294967295ms
        # ~= 1193 minutes
        track_progress_hex= card.int2block(track_progress, 4)
        if track_progress_hex:
            logging.debug(f"Write Time Position: {track_progress}"
                          f" Time Pos in hex: {track_progress_hex}")
            block_content[5:9]= track_progress_hex
            logging.debug(f"\twrite block #{block:02}"
                  f" byte content: {block_content}")
            # pirc522 return True in case of any error :-(
            error= rdr.write(block, block_content)
            if error:
                logging.error(f"could not write time position to block #{block:02}")
            return True
        logging.error(f"Time position {track_progress} not written")
        return False

    def write_pl(self, text: str, startblock: int=8):
        """
        Write UTF8 encoded text to RFID card
        """
        card=self.card
        rdr=self.reader
        logging.info(f"Writing text \"{text}\" to card "
                     f"starting with block #{startblock:02}")
        if startblock == 0:
            logging.error("Cannot write to Manufacturer Block 0")
        idx= 0
        text_encode= list(text.encode())
        data_block_index = card.data_blocks.index(startblock)
        sector_trailer=card.get_sector_trailer(startblock)
        # Authenticate to the first sector
        if not self.auth_block_a(sector_trailer):
            logging.error(f"could not intially authenticate"
                          f" block #{sector_trailer:02} to write text")
            return False
        while idx < len(text_encode):
            new_block = card.data_blocks[data_block_index]
            sector_trailer= self.auth_new_block_a(sector_trailer, new_block)
            if not sector_trailer:
                logging.error(f"could not authenticate block #{new_block:02} ")
                return False
            block_content = text_encode[idx:idx+card.block_length]
            # If the last block is less than 16 bytes we fill the remaining bytes with 0x00
            if len(block_content) < card.block_length:
                block_content.extend([0x00 for i in range(len(block_content),card.block_length)])
            logging.debug(f"\twrite block #:{card.data_blocks[data_block_index]:02}"
                          f" byte content: {block_content}")
            # pirc522 return True in case of any error :-(
            error= rdr.write(card.data_blocks[data_block_index], block_content)
            if error:
                logging.error(f"could not write block #{card.data_blocks[data_block_index]:02}"
                              f" to write text")
                return False
            data_block_index += 1
            idx+=card.block_length
        return True
