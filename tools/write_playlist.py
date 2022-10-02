#!/usr/bin/env python3

"""Writes a playlist and default volume to RFID Card.

Playlist is a string starting with the playlist type followed by the playlist name.
The Playlist is the first argument for this script.

Example:

./write_playlist.py "m3u:ungeplante_abenteuer.m3u"

The length of this string is limited by the used RFID card.
Volume is by default int 25
Language is by default DE
track_nr is by default 0
track_progress is by default 0
"""
import logging
import sys
#from pirc522 import RFID #https://github.com/ondryaso/pi-rc522
from mopidy_figlio.rfid import RFID
import mifare
from functions import auth_block, auth_new_block, connect_card

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

def format_card(rdr, cardid, card, startblock: int=1):
    """Overwrites all block data with 0x00

    Returns True if successful otherwise False
    """
    logging.info("Overwrite all blocks in card with 0x00 "
                f"starting with block #{startblock:02}")
    if startblock == 0:
        logging.error("Cannot write to Manufacturer Block 0")
    data_block_index = card.data_blocks.index(startblock)
    sector_trailer=card.get_sector_trailer(startblock)
    # Authenticate to the first sector
    keya = card.get_key_a(startblock)
    if not auth_block(rdr, cardid, keya, sector_trailer):
        logging.error(f"could not intially authenticate block #{sector_trailer:02} to format card")
        return False
    while data_block_index < len(card.data_blocks):
        new_block = card.data_blocks[data_block_index]
        sector_trailer= auth_new_block(rdr, card, cardid, sector_trailer, new_block)
        if not sector_trailer:
            logging.error(f"could not authenticate block #{new_block:02} to format card")
            return False
        logging.debug(f"\tWrite {card.default_data_blocks}"
                      f"to block #{card.data_blocks[data_block_index]:02}")
        # pirc522 return True in case of any error :-(
        error = rdr.write(card.data_blocks[data_block_index], card.default_data_blocks)
        if error:
            logging.error(f"could not format block #{card.data_blocks[data_block_index]:02}")
            return False
        # Next data block
        data_block_index += 1
    return True

def write_text(rdr, cardid, card, text: str, startblock: int=8):
    """
    Write UTF8 encoded text to RFID card
    """
    logging.info(f"Writing text \"{text}\" to card "
                 f"starting with block #{startblock:02}")
    if startblock == 0:
        logging.error("Cannot write to Manufacturer Block 0")
    idx= 0
    text_encode= list(text.encode())
    data_block_index = card.data_blocks.index(startblock)
    sector_trailer=card.get_sector_trailer(startblock)
    # Authenticate to the first sector
    keya = card.get_key_a(startblock)
    if not auth_block(rdr, cardid, keya, sector_trailer):
        logging.error(f"could not intially authenticate"
                      f" block #{sector_trailer:02} to write text")
        return False
    while idx < len(text_encode):
        new_block = card.data_blocks[data_block_index]
        sector_trailer= auth_new_block(rdr, card, cardid, sector_trailer, new_block)
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

def write_volume(rdr, cardid, card, volume: int=25, block: int=2):
    """Write the Volume to the card

    Return True if successful written else False
    """
    logging.info(f"Writing volume: {volume:02} to block #{block:02}")
    keya = card.get_key_a(block)
    if not auth_block(rdr, cardid, keya, block):
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

def write_lang(rdr, cardid, card, lang: str='DE', block: int=2):
    """Write the Playlist language to the card.

    The language is a ISO 3166-1 Alpha-2 code
    Return True if successful written else False
    """
    logging.info(f"Writing language code {lang} to block #{block:02}")
    keya = card.get_key_a(block)
    if not auth_block(rdr, cardid, keya, block):
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

def write_track_nr(rdr, cardid, card, track_nr: int = 0, block: int=2):
    """Write the track number to the card.

    Return True if successful written else False
    """
    logging.info(f"Writing track number {track_nr} to block #{block:02}")
    keya = card.get_key_a(block)
    if not auth_block(rdr, cardid, keya, block):
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

def write_track_progress(rdr, cardid, card, track_progress: int = 0, block: int=2):
    """Write the track progress in ms to the card.

    Return True if successful written else False
    """
    logging.info(f"Writing track progress in ms to block #{block:02}")
    keya = card.get_key_a(block)
    if not auth_block(rdr, cardid, keya, block):
        logging.error(f"could not intially authenticate block #{block:02} to write time position")
        return False
    error, block_content = rdr.read(block)
    if error:
        logging.error(f"could not read block #{block:02} to write time position")
        return False
    #We use 4 bytes for the timeposition, max length = 4294967295ms
    # ~= 1193 minutes
    track_progress_hex= card.int2block(track_progress, 4)
    #block=4
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
################################## Main ######################################
card1k = mifare.Classic1k()
reader = RFID()
id_card = connect_card(reader)

if id_card:
    format_card(reader, id_card, card1k)
    write_text(reader, id_card, card1k,sys.argv[1])
    write_volume(reader, id_card, card1k, )
    write_lang(reader, id_card, card1k,'DE')
    write_track_nr(reader, id_card, card1k, 2)
    write_track_progress(reader, id_card, card1k, 35)
reader.cleanup()
