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
    logging.info(f"reading playlist from card "
                 f"starting with block #{startblock:02}")
    block_not_zero = True
    data_block_index = card.data_blocks.index(startblock)
    raw_content=[]
    sector_trailer=card.get_sector_trailer(startblock)
    keya = card.get_key_a(startblock)
    if not auth_block(rdr, cardid, keya, startblock):
        logging.error(f"could not intially authenticate block #{startblock:02}")
        return None
    while block_not_zero:
        error, block_content = rdr.read(card.data_blocks[data_block_index])
        if not error:
            logging.debug(f"read block #{card.data_blocks[data_block_index]:02}"
                  f" byte content: {block_content}")
            raw_content.extend(block_content)
            if 0x00 in raw_content:
                logging.debug(f"Found 0x00 in content at block #{card.data_blocks[data_block_index]:02}"
                              "-> end of text. Stop reading.")
                block_not_zero = False
            else:
                data_block_index += 1
                if data_block_index == len(card.data_blocks):
                    logging.error("Reached end of card while reading!")
                    return False
                new_block = card.data_blocks[data_block_index]
                sector_trailer= auth_new_block(rdr, card, cardid, sector_trailer, new_block)
                if not sector_trailer:
                    logging.error(f"could not authenticate block #{new_block:02}")
                    return None
        else:
            logging.error(f"Could not read block #{card.data_blocks[data_block_index]}")
            return None
    return bytes(raw_content).decode()

def read_data(rdr, cardid, block=2):
    """
    Reads the volume, language code track nr and progress from card

    returns a list with this items
    """
    logging.info(f"reading volume, language code, track nr. and track progress,  from card "
                 f"starting with block #{startblock:02}")
    keya = card.get_key_a(block)
    if not auth_block(rdr, cardid, keya, block):
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
    

############################### MAIN ###############################################
reader = RFID()
card = mifare.Classic1k()
id_card = connect_card(reader)
if id_card:
    print(f'Card NUID: {card.block2int(id_card)}')
    pl=read_pl(reader, id_card)
    print(f"Playlist: {pl}")
    vol, lang, tr, progress = read_data(reader, id_card)
    print(f"Volume: {vol}\nTrack: {tr}\nLanguage: {lang}\nProgress (ms):{progress}")

else:
    print('No card found!\n')
# Calls GPIO cleanup and stop crypto
reader.cleanup()
