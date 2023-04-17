import socket
import os
import os.path as path
import sys
import ast
import select
from os import listdir
from os.path import isfile, join

#Index server ip and port
IP = '127.0.0.1'  # default IP address of the server
PORT = 12000  # change to a desired port number
BUFFER_SIZE = 1024  # change to a desired buffer size

#Regular peer ip and port
hostname=socket.gethostname()
myIP=socket.gethostbyname(hostname)
myPort=13500

#Regular peer IP just for them
peersNeeded={}
filesNeeded={}
otherIP=""

#Index server dictionaries encompassing all peers and files
allPeers={}
allFiles={}
allPeersIndex=0

# TODO Have peers close connections when done
# TODO Peers able to leave the network
# TODO Index server initial set up
# TODO End while loops
# TODO Peers switch to accepting connections to send files after receiving all of their own
# TODO Tell peer what to do when starting up

def start_server(ip, port):
    # create a TCP socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((ip, port))
    server_socket.listen(1)
    print(f'Server ready and listening on {ip}:{port}')

    try:
        while True:
            (conn_socket, addr) = server_socket.accept()
            # expecting an 8-byte byte string for file size followed by file name
            message, client_address = conn_socket.recvfrom(BUFFER_SIZE)
            file_name, file_size=get_file_info(message)
            print(f'Received: {file_name} with size = {file_size}')
            conn_socket.sendto(b'go ahead', addr)
            upload_file(conn_socket, file_name, file_size)
            conn_socket.close()
            break
    except KeyboardInterrupt as ki:
        pass
    finally:
        server_socket.close()

def get_file_info(data: bytes) -> (str, int):
    return data[8:].decode(), int.from_bytes(data[:8], byteorder='big')

def upload_file(conn_socket: socket, file_name: str, file_size: int):
    # create a new file to store the received data
    file_name += '.temp'
    # please do not change the above line!
    with open(file_name, 'wb') as file:
        retrieved_size = 0
        try:
            while retrieved_size < file_size:
                chunk, client_address = conn_socket.recvfrom(BUFFER_SIZE)
                file.write(chunk)
                retrieved_size += len(chunk)
                print(file.write(chunk))
        except OSError as oe:
            print(oe)
            os.remove(file_name)

def indexServer():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.bind(('', PORT))
    client_socket.listen(1)
    while True:
        (conn_socket, addr) = client_socket.accept()
        message, other_address = client_socket.recvfrom(BUFFER_SIZE)
        messArray = ast.literal_eval(message.decode())
        if message.decode()[:1]=="No":
            # If peer contacts index server to say that a peer is no longer in the system, check if there are other peers not connected to this peer, and if so send a new peer for it to connect to.
            client_socket.sendto("Send your peers dict", (addr, PORT))
            message2, other_address = client_socket.recvfrom(BUFFER_SIZE)
            messArray2 = ast.literal_eval(message2.decode())
            allPeers.pop(allPeers[messArray[0]])
            if len(messArray2)+1<len(allPeers):
                for y in allPeers:
                    if y not in messArray2 and y!=addr:
                        client_socket.sendto(str([y,str(allPeers[y])]), (addr, PORT))
                        break
                    else:
                        client_socket.sendto("No more peers to send", (addr, PORT))
        elif allPeers=={}:
            client_socket.sendto(str({IP: PORT}), (addr, PORT))
            allPeers[messArray[0]] = messArray[1]
            message2, other_address = client_socket.recvfrom(BUFFER_SIZE)
            if message2 == b"Continue":
                client_socket.sendto(str(allFiles), (addr, PORT))
        else:
            #Add new peer to allPeers dict, and send peer 5 peers to connect to as well as the dict of all files it needs.
            client_socket.sendto(str(indexChoosePeers(allPeersIndex)), (addr, PORT))
            allPeers[messArray[0]]=messArray[1]
            message2, other_address = client_socket.recvfrom(BUFFER_SIZE)
            if message2==b"Continue":
                client_socket.sendto(str(allFiles), (addr, PORT))
        #Tentative!
        break
    client_socket.close()

def indexChoosePeers(all):
    #Choose  up to 5 peers from allPeers to send to connected peer, in incrementing order (i.e. send a peer index 0 to 5's peers, then index 1 to 6's peers for the next peer to connect, and so on. If end of dict reached, start over.
    di={}
    num=0
    if len(allPeers)>=5:
        maxNum=5
    else:
        maxNum=len(allPeers)
        if (all+5)>len(allPeers):
            all=0
            allPeersIndex=0
    for x in allPeers:
        if num>=all:
            di[x]=allPeers[x]
            num+=1
            if num>=maxNum:
                break
    allPeersIndex=all+1
    return di

def contactPeers():
    #For each peer in peersNeeded dict, send filesNeeded and receive a file from them via upload file function
    actuallyNeeded={}
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while False in filesNeeded:
        for i in filesNeeded:
            if filesNeeded[i]==False:
                actuallyNeeded[i]=filesNeeded[i]
        for x in peersNeeded:
            client_socket.connect(('', peersNeeded[x]))
            client_socket.sendto(str(actuallyNeeded), (x, peersNeeded[x]))
            client_socket.setblocking(True)
            ready = select.select([client_socket], [], [], 6)
            if ready[0]:
                response, server_address = client_socket.recvfrom(BUFFER_SIZE)
                if response != "No files":
                    responseArray = ast.literal_eval(response.decode())
                    if responseArray[0] in actuallyNeeded:
                        client_socket.sendto("OK", (x, peersNeeded[x]))
                        upload_file(client_socket, responseArray[1], responseArray[0])
                        filesNeeded[responseArray[0]] = True
                        actuallyNeeded.pop(responseArray[0])
                    #else:
                    #   break
            else:
                client_socket.setblocking(False)
                contactIndexServer(True, peersNeeded, filesNeeded)
        client_socket.setblocking(False)

    client_socket.setblocking(False)
    #Once all files received, listen out for other peers to give files to.
    receiveFromPeers()



def receiveFromPeers():
    #Listen out for a peer to contact you, then choose a file you have to give them and send it via send_file.
    arr=[]
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.bind(('', PORT))
    client_socket.listen(1)
    while True:
        (conn_socket, addr) = client_socket.accept()
        message, other_address = client_socket.recvfrom(BUFFER_SIZE)
        messArray = ast.literal_eval(message.decode())
        for y in messArray:
            if y in filesNeeded:
                if filesNeeded[y]==True:
                    arr.append(filesNeeded[y])
                    arr.append(os.path.getsize(filesNeeded[y]))
                    client_socket.sendto(str(arr), (addr, PORT))
                    message2, other_address=client_socket.recvfrom(BUFFER_SIZE)
                    if message2==b"OK":
                        send_file(filesNeeded[y],(addr, PORT),addr, PORT)
        #Tentative!
        break
    client_socket.close()



def requestFiles(peers):
    # First, see how many files you need
    numNeeded = 0
    for i in filesNeeded:
        if filesNeeded[i] == False:
            numNeeded += 1

    # Divide number of needed files by number of peers to see how many peers are needed
    filesPerPeer = numNeeded // len(peers)
    remainder = numNeeded % len(peers)

    # Iterate through need files dictionary and peers array to get files
    for x in peers:
        numFiles = filesPerPeer
        for y in filesNeeded:
            if filesNeeded[y] == False:
                for z in x.files:
                    if z == y and x.files[z] == True:
                        x.sendFile(z)
                        numFiles -= 1
                        break
            if numFiles <= 0:
                break

    # Repeat above but for remainder of needed files
    for a in range(remainder):
        numFiles = remainder
        for b in filesNeeded:
            if filesNeeded[b] == False:
                for c in filesNeeded[remainder].files:
                    if c == b and filesNeeded[remainder].files[c] == True:
                        filesNeeded[remainder].sendFile(c)
                        numFiles -= 1
                        break
            if numFiles <= 0:
                break

def receiveFile(files, fileName):
    files[fileName] = True

    pass

def sendFile():
    # Connect to otherPeer
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    pass

def get_file_size(file_name: str) -> int:
    size = 0
    try:
        size = path.getsize(file_name)
    except FileNotFoundError as fnfe:
        print(fnfe)
        sys.exit(1)
    return size


def send_file(filename: str, address: (str, int), ip, port):
    # get the file size in bytes
    file_size = get_file_size(filename)
    # convert file_size to an 8-byte byte string using big endian
    size = file_size.to_bytes(8, byteorder='big')
    # create a TCP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((ip, port))
        # send the file size in the first 8-bytes followed by the bytes
        # for the file name to server at (ip, port)
        client_socket.sendto(size + filename.encode(), (ip, port))
        response, server_address=client_socket.recvfrom(BUFFER_SIZE)
        if response!=b'go ahead':
            raise OSError('Bad server response - was not go ahead!')
        # open the file to be transferred
        with open(filename, 'rb') as file:
            # read the file in chunks and send each chunk to the server
            is_done = False
            while not is_done:
                chunk = file.read(BUFFER_SIZE)
                client_socket.sendto(chunk, (ip, port))
                print(chunk)
                if len(chunk)<=0:
                    is_done=True
                    print('Done!')
    except OSError as e:
        print(f'An error occurred while sending the file:\n\t{e}')
    finally:
        client_socket.close()

def contactIndexServer(noPeer, peersNeeded, filesNeeded):
    #Connect to Index Server
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #client_socket.setblocking(False)
    client_socket.connect(('', PORT))

    #If we're not contacting server because we found a peer no longer in the network, then continue, otherwise go to else
    if not noPeer:
        #Receive dictionary of up to 5 peers from the server, then a dictionary of all files needed
        client_socket.sendto(str([myIP, str(myPort)]), (IP, PORT))
        response, server_address = client_socket.recvfrom(BUFFER_SIZE)
        if response!=b'Error':
            peersNeeded=ast.literal_eval(response.decode())
            client_socket.sendto("Continue", (IP, PORT))
            response2, server_address = client_socket.recvfrom(BUFFER_SIZE)
            if response2!=b'Error':
                filesNeeded=ast.literal_eval(response2.decode())
    else:
        #Tell index server a peer at the specified address is no longer connected, and receive a new peer, if one exists
        client_socket.sendto("No peer at "+otherIP, (IP, PORT))
        response, server_address = client_socket.recvfrom(BUFFER_SIZE)
        responseArr = ast.literal_eval(response.decode())
        if response==b"Send your peers dict":
            client_socket.sendto(str(peersNeeded), (IP, PORT))
            response2, server_address = client_socket.recvfrom(BUFFER_SIZE)
            if response2 != b'Error':
                peersNeeded[responseArr[0]]=responseArr[1]

    contactPeers()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    kind=input("Index server? y/n: ")
    if kind=='y':
        mypath="C:/Users/Derick/Pictures/Captures"
        files = [f for f in listdir(mypath) if isfile(join(mypath, f))]
        for x in files:
            allFiles[mypath+'/'+x]='False'
        indexServer()
    else:
        contactIndexServer(False, peersNeeded, filesNeeded)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
