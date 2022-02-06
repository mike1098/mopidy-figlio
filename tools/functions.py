"""
Repository of functions for examples
"""

import logging, sys

def connect_card(rdr,retries=3):
    """Opens the connection to a RFID card for reading or writing.

    Returns the NUID/UID as a list
    """
    while retries > 0:
        (error, _) = rdr.request()
        if not error:
            (error, uid) = rdr.anticoll()
            if not error:
                if not rdr.select_tag(uid):
                    return uid
        retries -= 1
    return None

def auth_block(rdr, cardid, key, block=0):
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

def auth_new_block(rdr, card, cardid, sector_trailer, block):
    """
    Check if the new block has a new sector trailer and authenticate if needed.

    Returns true if authentication was successful, otherwise false.
    """
    new_sector_trailer = card.get_sector_trailer(block)
    logging.debug(f"Block: {block} Old Trailer: {sector_trailer} New Trailer:{new_sector_trailer }")
    if sector_trailer != new_sector_trailer:
        sector_trailer = new_sector_trailer
        keya = card.get_key_a(sector_trailer)
        if not auth_block(rdr, cardid, keya, sector_trailer):
            return None
    return sector_trailer
