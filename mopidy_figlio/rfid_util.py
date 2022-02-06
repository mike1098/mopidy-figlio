
"""
A class to read and write playlist, Track Number, time form mopidy
"""

import logging
import pirc522 #https://github.com/ondryaso/pi-rc522
import mifare

class RfidUtil:
    def __init__(self) -> None:
        self.reader = pirc522.RFID()
        self.card = mifare.Classic1k()
        self.cardid=None

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
        rdr=self.reader
        cardid=self.cardid
        key=self.card.get_key_a(block)
        """Authenticate to a sector by a given block with authenticator A.

        Returns true if authentication was successful, otherwise false.
        """
        assert len(cardid) == 5, f"Card uid has wrong length: {cardid}"
        assert len(key) == 6, f"Authenticator has wrong length:{key}"
        error = rdr.card_auth(rdr.auth_a, block, key, cardid)
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
        logging.debug(f"Block: {block} Old Trailer: {sector_trailer} New Trailer:{new_sector_trailer }")
        if sector_trailer != new_sector_trailer:
            sector_trailer = new_sector_trailer
            keya = card.get_key_a(sector_trailer)
            if not self.auth_block_a(sector_trailer):
                return None
        return sector_trailer