#!/usr/bin/env python3

# Write Playlist to RFID Card

#https://github.com/ondryaso/pi-rc522

from pirc522 import RFID
rdr = RFID()

import sys
sys.path.append("/home/pi/develop/rfid/MIFARE-Classic")
from MIFARE import Classic1k
card = Classic1k()

def connect_card(retries=3):
    """Opens the connection to a RFID card for reading or writing"""
    while retries > 0:
        (error, tag_type) = rdr.request()
        if not error:
            (error, cardid) = rdr.anticoll()
            if not error:
                if not rdr.select_tag(cardid):
                    return cardid
        retries -= 1
    print("No card found!")
    return []
    #uid

def auth_block(cardid, auth, block=0):
    assert len(cardid) == 5, f"Card uid has wrong length: {cardid}"
    assert len(auth) == 6, f"Authenticator has wrong length:{auth}"
    """Authenticate to a sector by a given block with authenticator a"""
    error = rdr.card_auth(rdr.auth_a, block, auth, cardid)
    if not error:
        print("Sucessful Auth")
        return True
    else:
        return False

def format_card(cardid, card, startblock=1):
    # Only the last 
    assert startblock > 0, "Cannot write to Manufacturer Block 0"
    data_block_index = card._data_blocks.index(startblock)
    sector_trailer=card.get_sector_trailer(startblock)
    print(f"index:{data_block_index} trailor {sector_trailer}")
    # Authenticate to the first sector
    if not auth_block(cardid, card._sector_trailers[sector_trailer]['keya'], sector_trailer):
        print(f"could not intially authenticate block {sector_trailer}")
        #rdr.stop_crypto()
        return False
    
    while data_block_index < len(card._data_blocks):
        if card.get_sector_trailer(card._data_blocks[data_block_index]) != sector_trailer:
                    sector_trailer = card.get_sector_trailer(card._data_blocks[data_block_index])
                    print(f"New Sector Trailer: {sector_trailer}")
                    if not auth_block(cardid, card._sector_trailers[sector_trailer]['keya'], sector_trailer):
                        print(f"could not authenticate block {sector_trailer}")
                        rdr.stop_crypto()
                        return False
        print(f"Write block {card._data_blocks[data_block_index]}")
        rdr.write(card._data_blocks[data_block_index], card.DEFAULT_BLOCK_DATA)
        # Next data block
        data_block_index += 1
        # check if we need to a authenticate a new sector
        # Same code is used in read_pl!
        # TODO externalize in a function
    #rdr.stop_crypto()    
    return True

def write_playlist(cardid, card, playlist, startblock=8):
    assert startblock > 0, "Cannot write to Manufacturer Block 0"
    #TODO repair this assert!
    #assert len(playlist) <= len(card._data_blocks) * card.block_length - startblock , f"Playlist must not be longer than {len(card._data_blocks * card.block_length)- startblock}"
    idx= 0
    playlist_encode= list(playlist.encode())
    data_block_index = card._data_blocks.index(startblock)
    sector_trailer=card.get_sector_trailer(startblock)
    print(f"index:{data_block_index} trailor {sector_trailer}")
    # Authenticate to the first sector
    if not auth_block(cardid, card._sector_trailers[sector_trailer]['keya'], sector_trailer):
        print(f"could not intially authenticate block {sector_trailer}")
        rdr.stop_crypto()
        return False
    while idx < len(playlist_encode):
        if card.get_sector_trailer(card._data_blocks[data_block_index]) != sector_trailer:
                    sector_trailer = card.get_sector_trailer(card._data_blocks[data_block_index])
                    print(f"New Sector Trailer: {sector_trailer}")
                    if not auth_block(cardid, card._sector_trailers[sector_trailer]['keya'], sector_trailer):
                        print(f"could not authenticate block {sector_trailer}")
                        rdr.stop_crypto()
                        return False
        block_to_write = playlist_encode[idx:idx+card.block_length]
        if len(block_to_write) < card.block_length:
            block_to_write.extend([0 for i in range(len(block_to_write),card.block_length)])
        print(f"Block to write: {block_to_write}")
        rdr.write(card._data_blocks[data_block_index], block_to_write)
        data_block_index += 1
        idx+=card.block_length

    #rdr.stop_crypto()
    return
    
cardid = connect_card()

if len(cardid) == 5:
    format_card(cardid, card)
    write_playlist(cardid,card,sys.argv[1])

#TODO need to find out where is the best place to do this
rdr.stop_crypto()
rdr.cleanup()