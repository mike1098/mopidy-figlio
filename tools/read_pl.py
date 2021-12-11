#!/usr/bin/env python3

# Reads Playlist from RFID Card

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
            (error, uid) = rdr.anticoll()
            if not error:
                if not rdr.select_tag(uid):
                    return uid
        retries -= 1
    return []
    uid

def auth_block(uid, auth, block=0):
    """Authenticate to a sector by a given block with authenticator a"""
    error = rdr.card_auth(rdr.auth_a, block, auth, uid)
    if not error:
        print("Sucessful Auth")
        return True
    else:
        return False

def read_playlist(cardid, startblock=8):
    """Reads the playlist from the RFID card"""
    block_not_zero = True
    data_block_index = card._data_blocks.index(startblock)
    raw_content=[]
    sector_trailer=card.get_sector_trailer(startblock)
    if not auth_block(cardid, card._sector_trailers[sector_trailer]['keya'], sector_trailer):
        print(f"could not intially authenticate block {sector_trailer}")
        return ""
    while block_not_zero:
        error, block_content = rdr.read(card._data_blocks[data_block_index])
        if not error:
            print(f"read: {block_content}")
            raw_content.extend(block_content)
            if ''.join(map(chr,raw_content)).endswith('\x00'):
                print(f"Found 0x00 in content")
                block_not_zero = False
            else:
                data_block_index += 1
                if data_block_index > len(card._data_blocks):
                    print("reached end of card")
                    rdr.stop_crypto()
                    return "" 
                if card.get_sector_trailer(card._data_blocks[data_block_index]) != sector_trailer:
                    sector_trailer = card.get_sector_trailer(card._data_blocks[data_block_index])
                    print(f"New Sector Trailer: {sector_trailer}")
                    if not auth_block(cardid, card._sector_trailers[sector_trailer]['keya'], sector_trailer):
                        print(f"could not authenticate block {sector_trailer}")
                        rdr.stop_crypto()
                        return ""
        else:
            #TODO Find out where we handle card access
            rdr.stop_crypto()
            return ""
    #TODO Find out where we handle card access
    rdr.stop_crypto()
    # alternative faster: bytes([104, 101, 108, 108, 111, 32, 119, 111, 114, 108, 100]).decode()
    # neds to be checked if still supported in Python 3
    return ''.join(map(chr,raw_content)).rstrip('\0x00')



cardid = connect_card()
#print(cardid)
#if auth_block(cardid, [0xFF,0xFF,0xFF,0xFF,0xFF,0xFF], 8):
#    print("Authenticated to block 8")
#    print(rdr.read(8))

print("Card read UID: "+str(cardid[0])+","+str(cardid[1])+","+str(cardid[2])+","+str(cardid[3]))
text=read_playlist(cardid)
print(f"Text: {text}")


# Calls GPIO cleanup
rdr.cleanup()


