import socket
import os
import os.path as path
import sys
import ast
import select
from os import listdir
from os.path import isfile, join
from threading import Thread

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
    print('upload')
    # create a new file to store the received data
    file_name += '.temp'
    # please do not change the above line!
    with open(file_name, 'wb') as file:
        retrieved_size = 0
        try:
            while retrieved_size < file_size:
                print('upload2')
                chunk, client_address = conn_socket.recvfrom(BUFFER_SIZE)
                file.write(chunk)
                retrieved_size += len(chunk)
                print(file.write(chunk))
        except OSError as oe:
            print(oe)
            os.remove(file_name)

def indexServer():
    #if client is None:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client_socket.bind((IP, PORT))
    client_socket.listen(5)
    #else:
    #   client_socket=client
    while True:
        print('index while')
        (conn_socket, addr) = client_socket.accept()
        print('accept')
        message, other_address = conn_socket.recvfrom(BUFFER_SIZE)
        messArray = ast.literal_eval(message.decode())
        if message.decode()[:1]==b"No":
            # If peer contacts index server to say that a peer is no longer in the system, check if there are other peers not connected to this peer, and if so send a new peer for it to connect to.
            conn_socket.sendto(b"Send your peers dict", (addr[0], PORT))
            message2, other_address = conn_socket.recvfrom(BUFFER_SIZE)
            messArray2 = ast.literal_eval(message2.decode())
            allPeers.pop(allPeers[messArray[0]])
            if len(messArray2)+1<len(allPeers):
                for y in allPeers:
                    if y not in messArray2 and y!=addr[0]:
                        conn_socket.sendto(str([y,str(allPeers[y])]).encode(), (addr[0], PORT))
                        break
                    else:
                        conn_socket.sendto(b"No more peers to send", (addr[0], PORT))
        elif allPeers=={}:
            #print(str({IP: PORT}).encode())
            #print(addr)
            conn_socket.sendto(str({IP: PORT}).encode(), (addr[0], PORT))
            allPeers[messArray[0]] = messArray[1]
            message2, other_address = conn_socket.recvfrom(BUFFER_SIZE)
            if message2 == b"Continue":
                conn_socket.sendto(str(allFiles).encode(), (addr[0], PORT))
            break
        else:
            #Add new peer to allPeers dict, and send peer 5 peers to connect to as well as the dict of all files it needs.
            conn_socket.sendto(str(indexChoosePeers(allPeersIndex)).encode(), (addr[0], PORT))
            allPeers[messArray[0]]=messArray[1]
            message2, other_address = conn_socket.recvfrom(BUFFER_SIZE)
            if message2==b"Continue":
                for p in allFiles:
                    allFiles[p]=False
                conn_socket.sendto(str(allFiles).encode(), (addr[0], PORT))
        #Tentative!
        #conn_socket.close()
        #break
    client_socket.close()
    f=allFiles
    for j in allFiles:
        allFiles[j]=True
    receiveFromPeers(allFiles, False, conn_socket, addr)

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

def contactPeers(files, peers, client_socket):
    if len(peers)==1 and list(peers.keys())[0]==IP:
        ip=''
        print('c1')
        filesNeeded=files
        peersNeeded=peers
        #For each peer in peersNeeded dict, send filesNeeded and receive a file from them via upload file function
        actuallyNeeded={}
        #client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(filesNeeded)
        while False in filesNeeded.values() or 'False' in filesNeeded.values():
            print('while')
            for i in filesNeeded:
                if filesNeeded[i]==False or filesNeeded[i]=='False':
                    actuallyNeeded[i]=filesNeeded[i]
            for x in peersNeeded:
                if ip != x:
                    #client_socket.connect((x, peersNeeded[x]))
                    #client_socket.connect((IP, PORT))
                    ip = x
                client_socket.sendto(str(actuallyNeeded).encode(), (x, int(peersNeeded[x])))
                #client_socket.sendto(str(actuallyNeeded).encode(), (IP, PORT))
                print('send actuallyNeeded')
                client_socket.setblocking(True)
                ready = select.select([client_socket], [], [], 6)
                if ready[0]:
                    response, server_address = client_socket.recvfrom(BUFFER_SIZE)
                    if response != b"No files":
                        print(response)
                        responseArray = ast.literal_eval(response.decode())
                        if responseArray[0] in actuallyNeeded:
                            client_socket.sendto(b"OK", (x, int(peersNeeded[x])))
                            upload_file(client_socket, responseArray[0], responseArray[1])
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
        for o in peersNeeded:
            client_socket.sendto(b'Finished!', (o, int(peers[o])))
        receiveFromPeers(filesNeeded, True, None, None)
    else:
        ip = ''
        print('c1')
        filesNeeded = files
        peersNeeded = peers
        # For each peer in peersNeeded dict, send filesNeeded and receive a file from them via upload file function
        actuallyNeeded = {}
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(filesNeeded)
        while False in filesNeeded.values() or 'False' in filesNeeded.values():
            print('while')
            for i in filesNeeded:
                if filesNeeded[i] == False or filesNeeded[i] == 'False':
                    actuallyNeeded[i] = filesNeeded[i]
            for x in peersNeeded:
                if ip != x:
                    print(x)
                    print(peersNeeded[x])
                    client_socket.connect((x, int(peersNeeded[x])))
                    ip = x
                client_socket.sendto(str(actuallyNeeded).encode(), (x, int(peersNeeded[x])))
                print('send actuallyNeeded')
                client_socket.setblocking(True)
                ready = select.select([client_socket], [], [], 6)
                if ready[0]:
                    response, server_address = client_socket.recvfrom(BUFFER_SIZE)
                    if response != b"No files":
                        print(response)
                        responseArray = ast.literal_eval(response.decode())
                        if responseArray[0] in actuallyNeeded:
                            client_socket.sendto(b"OK", (x, int(peersNeeded[x])))
                            upload_file(client_socket, responseArray[0], responseArray[1])
                            filesNeeded[responseArray[0]] = True
                            actuallyNeeded.pop(responseArray[0])
                        # else:
                        #   break
                else:
                    client_socket.setblocking(False)
                    contactIndexServer(True, peersNeeded, filesNeeded)
            client_socket.setblocking(False)

        client_socket.setblocking(False)
        # Once all files received, listen out for other peers to give files to.
        for o in peersNeeded:
            client_socket.sendto(b'Finished!', (o, int(peers[o])))
        receiveFromPeers(filesNeeded, True, None, None)

def beginSending(conn_socket, addr, arr, files):
    filesNeeded=files
    while True:
        print('receive')
        message, other_address = conn_socket.recvfrom(BUFFER_SIZE)
        print("Message", message)
        if message != b'Finished!':
            messArray = ast.literal_eval(message.decode())
            for y in messArray:
                print('for')
                if y in filesNeeded:
                    if filesNeeded[y] == True:
                        arr.append(y)
                        arr.append(path.getsize(y))
                        conn_socket.sendto(str(arr).encode(), (addr[0], PORT))
                        message2, other_address = conn_socket.recvfrom(BUFFER_SIZE)
                        if message2 == b"OK":
                            send_file(conn_socket, y, (addr[0], PORT), addr[0], PORT, filesNeeded)
                            break
        else:
            break
    print('break')
    conn_socket.close()
    receiveFromPeers(filesNeeded, True, None, None)

def receiveFromPeers(files, bind, client, address):
    print('hello')
    filesNeeded=files
    print(f"filesNeeded: {filesNeeded}")
    #Listen out for a peer to contact you, then choose a file you have to give them and send it via send_file.
    arr=[]
    if bind:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_socket.bind((myIP, myPort))
        client_socket.listen(5)
        print('listen')
    else:
        client_socket=client
    while True:
        print('while')
        if bind:
            print('bind')
            (conn_socket, addr) = client_socket.accept()
            print('new thread')
            #Thread(target=beginSending(conn_socket, addr, arr, filesNeeded))
            #beginSending(conn_socket, addr, arr, filesNeeded)

        else:
            conn_socket=client_socket
            addr = address
            #beginSending(conn_socket, addr, arr, filesNeeded)
            '''
            print('bind2')
            client.bind((IP, PORT))
            client.listen(1)
            (conn_socket, addr)=client.accept()
            conn_socket.recvfrom(BUFFER_SIZE)
            print('new thread2')
            Thread(target=beginSending(conn_socket, address, arr, filesNeeded))
            '''


        #'''
        print('receive')
        message, other_address = conn_socket.recvfrom(BUFFER_SIZE)
        print("Message",message)
        if message!=b'Finished!':
            messArray = ast.literal_eval(message.decode())
            for y in messArray:
                print('for')
                if y in filesNeeded:
                    if filesNeeded[y]==True:
                        arr.append(y)
                        arr.append(path.getsize(y))
                        conn_socket.sendto(str(arr).encode(), (addr[0], PORT))
                        message2, other_address=conn_socket.recvfrom(BUFFER_SIZE)
                        if message2==b"OK":
                            send_file(conn_socket,y,(addr[0], PORT),addr[0], PORT, filesNeeded)
                            break
        else:
            break
        #conn_socket.close()
        #client_socket.close()
        #receiveFromPeers2(filesNeeded, True, None, None)
        print('break')
        if allFiles=={}:
            receiveFromPeers(filesNeeded, True, None, None)
        else:
            indexServer()
        #'''
        #if allFiles=={}:
        #    client_socket.close()
        #    conn_socket.close()
            #receiveFromPeers(filesNeeded,True,None,None)
        #else:
        #    print('indexServer')
        #    client_socket.close()
        #    conn_socket.close()
        #    indexServer()

        #Tentative!
        #conn_socket.close()
        #break
    #client_socket.close()

def receiveFromPeers2(files, bind, client, address):
    print('hello2')
    filesNeeded=files
    print(f"filesNeeded: {filesNeeded}")
    #Listen out for a peer to contact you, then choose a file you have to give them and send it via send_file.
    arr=[]
    if bind:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_socket.bind((IP, PORT))
        client_socket.listen(1)
    else:
        client_socket=client
    while True:
        print('while')
        if bind:
            print('bind')
            (conn_socket, addr) = client_socket.accept()
            print('new thread')
            Thread(target=beginSending(conn_socket, addr, arr, filesNeeded))

        else:
            #conn_socket=client_socket
            #addr = address
            #beginSending(conn_socket, addr, arr, filesNeeded)
            print('bind2')
            client.bind((IP, PORT))
            client.listen(1)
            (conn_socket, addr)=client.accept()
            conn_socket.recvfrom(BUFFER_SIZE)
            print('new thread2')
            Thread(target=beginSending(conn_socket, address, arr, filesNeeded))

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


def send_file(client_socket, filename: str, address: (str, int), ip, port, files):
    filesNeeded=files
    print("send")
    # get the file size in bytes
    file_size = get_file_size(filename)
    # convert file_size to an 8-byte byte string using big endian
    size = file_size.to_bytes(8, byteorder='big')
    # create a TCP socket
    #client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        #client_socket.connect((ip, port))
        # send the file size in the first 8-bytes followed by the bytes
        # for the file name to server at (ip, port)
        #client_socket.sendto(size + filename.encode(), (ip, port))
        #response, server_address=client_socket.recvfrom(BUFFER_SIZE)
        #if response!=b'go ahead':
        #    raise OSError('Bad server response - was not go ahead!')
        # open the file to be transferred
        with open(filename, 'rb') as file:
            # read the file in chunks and send each chunk to the server
            is_done = False
            while not is_done:
                print('send2')
                chunk = file.read(BUFFER_SIZE)
                client_socket.sendto(chunk, (ip, port))
                print(chunk)
                if len(chunk)<=0:
                    is_done=True
                    print('Done!')
    except OSError as e:
        print(f'An error occurred while sending the file:\n\t{e}')
    #finally:
        #client_socket.close()
    receiveFromPeers(filesNeeded, False, client_socket, address)
    #beginSending(client_socket,address,[],filesNeeded)

def contactIndexServer(noPeer, peersNeeded, filesNeeded):
    #Connect to Index Server
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #client_socket.setblocking(False)
    client_socket.connect((IP, PORT))

    #If we're not contacting server because we found a peer no longer in the network, then continue, otherwise go to else
    if not noPeer:
        #Receive dictionary of up to 5 peers from the server, then a dictionary of all files needed
        client_socket.sendto(str([myIP, str(myPort)]).encode(), (IP, PORT))
        response, server_address = client_socket.recvfrom(BUFFER_SIZE)
        if response!=b'Error':
            peersNeeded=ast.literal_eval(response.decode())
            client_socket.sendto(b"Continue", (IP, PORT))
            response2, server_address = client_socket.recvfrom(BUFFER_SIZE)
            if response2!=b'Error':
                filesNeeded=ast.literal_eval(response2.decode())
                for x in filesNeeded:
                    bool(filesNeeded[x])
                print(filesNeeded)
    else:
        #Tell index server a peer at the specified address is no longer connected, and receive a new peer, if one exists
        client_socket.sendto(str("No peer at "+(otherIP)).encode(), (IP, PORT))
        response, server_address = client_socket.recvfrom(BUFFER_SIZE)
        responseArr = ast.literal_eval(response.decode())
        if response==b"Send your peers dict":
            client_socket.sendto(str(peersNeeded).encode(), (IP, PORT))
            response2, server_address = client_socket.recvfrom(BUFFER_SIZE)
            if response2 != b'Error':
                peersNeeded[responseArr[0]]=bool(responseArr[1])

    contactPeers(filesNeeded, peersNeeded, client_socket)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    kind=input("Index server? y/n: ")
    if kind=='y':
        if len(sys.argv) < 2:
            print(f'SYNOPSIS: {sys.argv[0]} <filename> [IP address]')
            sys.exit(1)
        #mypath="C:/Users/Derick/Pictures/Captures"
        mypath =sys.argv[1]
        files = [f for f in listdir(mypath) if isfile(join(mypath, f))]
        for x in files:
            allFiles[mypath+'/'+x]='False'
        if len(sys.argv) == 3:
            IP = sys.argv[2]
        print(allFiles)
        myIP=IP
        myPort=PORT
        indexServer()
    else:
        contactIndexServer(False, peersNeeded, filesNeeded)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
