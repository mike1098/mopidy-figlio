#!/usr/bin/env python3

"""Writes a playlist and default volume to RFID Card.

Playlist is a string starting with the playlist type followed by the playlist name.
The Playlist is the first argument for this script.

Example:

./write_playlist.py "m3u:ungeplante_abenteuer.m3u"

The length of this string is limited by the used RFID card.
Volume is by default int 25
"""
import logging, sys
from pirc522 import RFID #https://github.com/ondryaso/pi-rc522
import mifare
from functions import auth_block, auth_new_block, connect_card

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

def format_card(rdr, cardid, card, startblock=1):
    """Overwrites all block data with 0x00

    Returns true if successful otherwise false
    """
    assert startblock > 0, "Cannot write to Manufacturer Block 0"
    data_block_index = card.data_blocks.index(startblock)
    sector_trailer=card.get_sector_trailer(startblock)
    # Authenticate to the first sector
    keya = card.get_key_a(startblock)
    if not auth_block(rdr, cardid, keya, sector_trailer):
        print(f"could not intially authenticate block {sector_trailer}")
        return False
    while data_block_index < len(card.data_blocks):
        new_block = card.data_blocks[data_block_index]
        sector_trailer= auth_new_block(rdr, card, cardid, sector_trailer, new_block)
        if not sector_trailer:
            print(f"could not authenticate block {new_block} ")
            return None
        logging.debug(f"Write {card.default_data_blocks} to block # {card.data_blocks[data_block_index]}")
        rdr.write(card.data_blocks[data_block_index], card.default_data_blocks)
        # Next data block
        data_block_index += 1
    return True

def write_text(rdr, cardid, card, text, startblock=8):
    """
    Write UTF8 encoded text to RFID card
    """
    assert startblock > 0, "Cannot write to Manufacturer Block 0"
    idx= 0
    text_encode= list(text.encode())
    data_block_index = card.data_blocks.index(startblock)
    sector_trailer=card.get_sector_trailer(startblock)
    print(f"index:{data_block_index} trailor {sector_trailer}")
    # Authenticate to the first sector
    keya = card.get_key_a(startblock)
    if not auth_block(rdr, cardid, keya, sector_trailer):
        print(f"could not intially authenticate block {sector_trailer}")
        return False
    while idx < len(text_encode):
        new_block = card.data_blocks[data_block_index]
        sector_trailer= auth_new_block(rdr, card, cardid, sector_trailer, new_block)
        if not sector_trailer:
            print(f"could not authenticate block {new_block} ")
            return False
        block_content = text_encode[idx:idx+card.block_length]
        # If the last block is less than 16 bytes we fill the remaining bytes with 0x00
        if len(block_content) < card.block_length:
            block_content.extend([0x00 for i in range(len(block_content),card.block_length)])
        logging.debug(f"write block #:{card.data_blocks[data_block_index]:02}"
              f" byte content: {block_content}")
        rdr.write(card.data_blocks[data_block_index], block_content)
        data_block_index += 1
        idx+=card.block_length
    return True

def write_volume(rdr, cardid, card, volume: int=25, block: int=2):
    """Write the Volume to the card

    """
    keya = card.get_key_a(block)
    if not auth_block(rdr, cardid, keya, block):
        print(f"could not intially authenticate block {block}")
        return False
    _, block_content = rdr.read(block)
    block_content[0] = volume
    #We fill the rest of this block with 0x00
    #Need to check if this is OK with the track ID or if track IF needs to be 1
    #block_content.extend([0x00 for i in range(len(block_content),card.block_length)])
    logging.info(f"write volume to block #{block:02}"
              f" byte content: {block_content}")
    rdr.write(block, block_content)
    return True

def write_lang(rdr, cardid, card, lang: str='DE', block: int=2):
    """Write the Playlist language to the card.

    The language is a ISO 3166-1 Alpha-2 code

    """
    keya = card.get_key_a(block)
    if not auth_block(rdr, cardid, keya, block):
        logging.debug(f"could not intially authenticate block {block}")
        return False
    _, block_content = rdr.read(block)
    lang_encode= lang.encode()
    block_content[1:3] = lang_encode
    #block_content[2] = lang_encode[1]
    logging.debug(f"write language block #{block:02}"
              f" byte content: {block_content}")
    rdr.write(block, block_content)
    return True

def write_tlid(rdr, cardid, card, tlid: int = 0, block: int=2):
    """Write the track id to the card.
    
    """
    keya = card.get_key_a(block)
    if not auth_block(rdr, cardid, keya, block):
        logging.debug(f"could not intially authenticate block {block}")
        return False
    _, block_content = rdr.read(block)
    #We use 2 bytes for the tlid, max length = 65535
    tlid_hex= card.int2block(tlid, 2)
    print(tlid_hex)
    if tlid_hex:
        block_content[3:5]= tlid_hex
        #block_content[4]= tlid_hex[1]
        logging.debug(f"write language block #{block:02}"
              f" byte content: {block_content}")
        return True
    logging.debug(f"tlid {tlid} not written")
    return False

card1k = mifare.Classic1k()
reader = RFID()
id_card = connect_card(reader)

if id_card:
    format_card(reader, id_card, card1k)
    write_text(reader, id_card, card1k,sys.argv[1])
    write_volume(reader, id_card, card1k)
    write_lang(reader, id_card, card1k)
    write_tlid(reader, id_card, card1k, 65536)
reader.cleanup()
