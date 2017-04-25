# TORchat Client

A client for [TORchat](https://github.com/FraMecca/torchat) written in Python3 and using curses.

## Usage

To run, start the daemon (see the TORchat readme) and then:

```
python3 client.py localhost 8000
```
*localhost can be replaced with any other host on which the TORchat daemon is running, 8000 is the standard port on which the TORchat daemon listens*

It will ask for a peer (an onion address) to connect with, and then it will support the following actions:
 * To write a message to the peer selected, simply write and press enter;
 * To send a command to the client/server and perform specific actions, head to the command table provided below. Commands are all preceded by a '/' sign.

| 	Command		| 	Action							|
| ------------- | ----------------------------------|
| 	**/peer**	| Change the current peer.  		|
| 	**/exit**	| Close the client and the server.  |
| 	**/quit**	| Close the client only.  			|

The peer commmand toggles a scrolling mode for the user panel. It is possible to change peer through the up/down arrow keys, or to insert a new onion address by pressing the spacebar. 
