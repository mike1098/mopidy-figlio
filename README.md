# mopidy-figlio
An extension to mopidy which:
- Reads the playlist, currrent track, track position and volume form a RFID card as soon as the card is inserted or mopidy starts and card is already inserted.
- While playing, writes every n seconds the current track, track position and volume to the RFID card. Validates that current playlist in mopidy is still the one written on the card.
- Stops as soon as the RFID card is removed.


## The current lab setup:
![Current Lab Setuo](./pics/Lab_setup.jpg)
