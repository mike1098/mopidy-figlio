#!/usr/bin/env python3
""" Reads playlist, volume, language and Track from RFID Card.

Returns text
"""
import logging, sys
from pirc522 import RFID #https://github.com/ondryaso/pi-rc522
import mifare
from functions import auth_block, auth_new_block, connect_card

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

def read_pl(rdr, cardid, startblock=8):
    """Reads text from the RFID card.

    The TEXT must be UTF8 encoded and terminated with at least one 0x00 otherwise it
    returns none. If a sector could not be authenticated it returns None

    returns a byte object otherwise None
    """
    block_not_zero = True
    data_block_index = card.data_blocks.index(startblock)
    raw_content=[]
    sector_trailer=card.get_sector_trailer(startblock)
    keya = card.get_key_a(startblock)
    if not auth_block(rdr, cardid, keya, startblock):
        print(f"could not intially authenticate block {sector_trailer}")
        return None
    while block_not_zero:
        error, block_content = rdr.read(card.data_blocks[data_block_index])
        if not error:
            logging.debug(f"read block #:{card.data_blocks[data_block_index]:02}"
                  f" byte content: {block_content}")
            raw_content.extend(block_content)
            if 0x00 in raw_content:
                logging.debug("Found 0x00 in content -> end of text. Stop reading.")
                block_not_zero = False
            else:
                data_block_index += 1
                if data_block_index == len(card.data_blocks):
                    print("reached end of card")
                    return None
                new_block = card.data_blocks[data_block_index]
                sector_trailer= auth_new_block(rdr, card, cardid, sector_trailer, new_block)
                if not sector_trailer:
                    print(f"could not authenticate block {new_block} ")
                    return None
        else:
            return None
    return bytes(raw_content).decode()

def read_data(rdr, cardid, block=2):
    """
    Reads the volume, language and track from card

    returns a list with this items
    """
    keya = card.get_key_a(block)
    if not auth_block(rdr, cardid, keya, block):
        print(f"could not intially authenticate block {block}")
        return None
    error, block_content = rdr.read(block)
    if not error:
        logging.debug(f"read block #:{block:02}"
              f" byte content: {block_content}")
        #Return the volume and the track
        return block_content[0], block_content[2]     
    return None
reader = RFID()
card = mifare.Classic1k()
id_card = connect_card(reader)
if id_card:
    print(f'Card NUID: {card.block2int(id_card)}')
    pl=read_pl(reader, id_card)
    print(f"Playlist: {pl}")
    vol, tr = read_data(reader, id_card)
    print(f"Volume: {vol}\nTrack: {tr}")

else:
    print('No card found!')

# Calls GPIO cleanup and stop crypto
reader.cleanup()
