# Peer2PeerProject

The main, other, and other2.py files are the networking code for sending and receiving files. Run any of them and enter the input prompts to set up index serer and
regular peers. Make sure to run the index server first!

If the raspberry pi is a peer receiving the files, make sure to run other.py on the pi as a regular peer.

The Files folder contains the files that would be sent.

To set up the kiosk display, open the Raspberry pi and go to 127.0.0.1:5000 on Chromium. Next, make sure to have both webserver.py and index.html, and run webserver.py
after all files have been sent. The webserver code will then send the files within the static folder to the html file to be displayed. Once the webserver.py code is
running, refresh the Chromium page and everything should work, with the html files refreshing the page every 5 seconds with a new file.

The above assumes Python, Flask, and Javascript are installed on the Raspberry Pi. If not, then install them, then wherever in the file directory your webserver.py code
would be create a file named 'templates' and put index.html in there. Also create a file named 'static', as this is where the files would be sent. After this set up
you should be able to run all the code following the above instructions without issue.

All other png and pub files are for viewing only.
