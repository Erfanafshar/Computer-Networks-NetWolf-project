import socket
import threading
import select
import time
import os
import sys
import ipaddress

server_port = 8448
discovery_udp_port = 8445
request_udp_port_1 = 8443
request_udp_port_2 = 8441

BUFFER_SIZE = 2048
Encoding = "utf-8"
cluster_copy = []
user_input = ""
nodes = []
threshold = 2
concurrent_sending = 0


def main():
    global name
    global address
    global cluster
    global sock2
    global sock3
    global sock4

    # connecting this node to server to get name and ip
    # TCP
    server_address = socket.gethostbyname_ex(socket.gethostname())[2][2]
    server_information = (server_address, server_port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_information)
    print(sock.recv(1024).decode(Encoding))
    name, address = sock.recv(1024).decode(Encoding).split(" ")
    sock.close()

    cluster = [[name, address]]
    ipaddress.ip_address(address)

    print(name)
    print(address)
    print()

    set_cluster()

    # creat socket to use in discovery stage of the program
    # and start discovery thread after that
    # UDP
    sock2 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock2.bind((address, discovery_udp_port))
    discovery_thread = threading.Thread(target=discovery_seq)
    discovery_thread.start()

    # creat socket to use in request stage of the program
    # and start request thread after that
    # UDP
    sock3 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock3.bind((address, request_udp_port_1))
    sock4 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock4.bind((address, request_udp_port_2))
    request_thread = threading.Thread(target=request_seq)
    request_thread.start()


# DISCOVERY ## S #
# read the file contain the nodes are in cluster of this node
# and add them to cluster list for discovery stage
def set_cluster():
    file = open("files\\" + name + ".txt", "r")
    while True:
        line = file.readline()
        if not line:
            break
        cluster.append(line.replace("\n", "").split(" "))


# DISCOVERY ## M #
# this function never terminate
# and calls discovery function at each step
def discovery_seq():
    global cluster
    while True:
        discovery()
        global cluster_copy
        # print(cluster_copy)       ## this line can show clusters at each step of discovery
        time.sleep(2)
        cluster = cluster_copy.copy()


# DISCOVERY ## M #
# create two threads and do not stop until their termination
# and join to the main branch
# one thread is for sending cluster to other nodes
# other one is for receiving cluster of other nodes
def discovery():
    t1 = threading.Thread(target=send_discovery)
    t2 = threading.Thread(target=receive_discovery)
    t1.start()
    t2.start()
    t1.join()
    t2.join()


# DISCOVERY ## M #
# send this node cluster to other members of the cluster
# so other nodes can merge this cluster with their clusters
# UDP
def send_discovery():
    for i in range(len(cluster)):
        addr = cluster[i][1]
        if addr == address:
            continue
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(str(cluster).encode(Encoding), (addr, discovery_udp_port))
        sock.close()


# DISCOVERY ## M #
# this node receive other nodes cluster and merge that cluster
# to itself cluster with calling merge_cluster function
# so this node cluster will upgrade
# UDP
def receive_discovery():
    read_sockets, _, _ = select.select([sock2], [], [], 2)
    if len(read_sockets) == 0:
        # print("r")       ## important for error checking
        merge_cluster("")
        return

    cls, addr = sock2.recvfrom(1024)
    cls = cls.decode(Encoding)
    merge_cluster(cls)


# DISCOVERY ## S #
# merge two cluster of nodes and return the union of their
# clusters in cluster_copy attribute
def merge_cluster(cls):
    global cluster
    substr = cls.split(",")
    segs = []
    for seg in substr:
        segs.append(seg.replace("[", "").replace("]", "").replace("'", "").replace(" ", "").replace("\n", ""))

    clus2 = []
    for i in range(len(segs) // 2):
        clus2.append([segs[2 * i], segs[2 * i + 1]])

    new_cluster = clus2 + cluster
    global cluster_copy
    [cluster_copy.append(x) for x in new_cluster if x not in cluster_copy]


# REQUEST ## M #
# this function never terminate
# and calls request_func function at each step
def request_seq():
    while True:
        request_func()


# REQUEST ## M #
# create two threads and do not stop until their termination
# and join to the main branch
# one thread is for sending request from this node to other nodes
# other one is for responding to other nodes
# which has sent request for some file
def request_func():
    t3 = threading.Thread(target=send_request)
    t4 = threading.Thread(target=receive_request)
    t3.start()
    t4.start()
    t3.join()
    t4.join()


# REQUEST ## M #
# this function has four main part
# first part detect that if is it necessary to send this input to other nodes
# second part send request for this file to all other nodes in cluster
# third part is a loop to receive responds has been sent to this node
# forth part may detect that there is no respond for this file or
# introduce the the sender node and start receiving file
# UDP
def send_request():
    # first part
    available_nodes = []
    times = []
    inp = get_input()
    if len(inp) == 0:
        return
    if search_folder(inp):
        print("you already have this file")
        return
    file_name = inp

    # second part
    for i in range(len(cluster)):
        addr = cluster[i][1]
        if addr == address:
            continue
        times.append([addr, time.perf_counter()])
        sock3.sendto(file_name.encode(Encoding), (addr, request_udp_port_1))
        print("request for ", file_name, " send to ", addr)
    if len(times) == 0:
        print("no request sent !")
    else:

        # third part
        ex_delay = 0.0
        stt = time.perf_counter()
        while time.perf_counter() - stt < 2:
            read_sockets, _, _ = select.select([sock4], [], [], 0.4)
            if len(read_sockets) == 0:
                continue

            prt, addr = sock4.recvfrom(1024)
            prt = prt.decode(Encoding)

            # for load balance
            if prt == "TH":
                print(addr[0] + " can't send file now")
                continue
            tcp_port, ex_delay = prt.split('*')
            end_time = time.perf_counter()

            # ex_delay is extra delay to prevent injustice
            delay = calculate_delay(times, addr[0], end_time) + float(ex_delay)
            available_nodes.append([addr[0], tcp_port, delay])

        # forth part
        if len(available_nodes) == 0:
            print("no response for this file")
            print()
            return
        best_node = choose_best_node(available_nodes)
        time.sleep(float(ex_delay))
        print("best node ip is ", best_node[0], " tcp port is ", best_node[1], " delay is ",
              best_node[2])
        nodes.append(best_node[0])
        transfer_thread_receive = threading.Thread(target=receive_file, args=(available_nodes, best_node, file_name))
        transfer_thread_receive.start()


# REQUEST ## M #
# this function has three part
# first part detect that if there is any input for this node to read the requested file name
# second part detect that can this node send the requested file to the requester or not
# third part send the tcp port of sender to receiver to
# and starting send_file thread to send file to receiver node
# UDP
def receive_request():
    # first part
    read_sockets, _, _ = select.select([sock3], [], [], 2)
    if len(read_sockets) == 0:
        # print("no req")
        return

    cls, addr = sock3.recvfrom(1024)
    cls = cls.decode(Encoding)
    file_name = cls
    print("request received for : ", file_name)

    # second part
    # check number of concurrent file sending on this node
    if concurrent_sending >= threshold:
        print("can't send that file to you now ")
        sock4.sendto("TH".encode(Encoding), (addr[0], request_udp_port_2))
        return
    if search_folder(file_name):

        # third part
        # calculate extra delay
        x = nodes.count(addr[0])
        delay = 0
        if x < 4:
            delay = 2 - x * 0.5

        tcp_port = str(get_free_tcp_port())
        sending_str = tcp_port + "*" + str(delay)
        sock4.sendto(sending_str.encode(Encoding), (addr[0], request_udp_port_2))
        print(file_name, " founded in my folder")
        transfer_thread_send = threading.Thread(target=send_file, args=(int(tcp_port), file_name))
        transfer_thread_send.start()
    else:
        print(file_name, " did not find in my folder")
        print()
        return


# TRANSFER ## M #
# this function has three part
# first part sending '0' to sender that shouldn't send file
# second part sending '1' to sender that should send file
# third part receive the file from the sender
# and store that in a file with same name in the node folder
# TCP
def receive_file(available_nodes, best_node, file_name):
    # first part
    for node in available_nodes:
        if node[0] != best_node[0]:
            sock_tmp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_tmp.bind((address, get_free_tcp_port()))
            sock_tmp.connect((node[0], int(node[1])))
            sock_tmp.send('0'.encode(Encoding))
            sock_tmp.close()

    # second part
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((address, get_free_tcp_port()))
    sock.connect((best_node[0], int(best_node[1])))
    sock.send('1'.encode(Encoding))
    print("start receiving file from ip : ", best_node[0])

    # third part
    with open("files/" + name + "/" + file_name, "wb") as f:
        while True:
            bytes_write = sock.recv(BUFFER_SIZE)
            if not bytes_write:
                break
            f.write(bytes_write)
        print("file received")
        print()
    sock.close()


# TRANSFER ## M #
# this function has three part
# first part listen on the confirmed tcp port and establish connection with receiver
# second part check the received number from receiver and detect sending file to receiver or not
# third part send the file to the receiver
# and store that in a file with same name in the node folder
# TCP
def send_file(tcp_port, file_name):
    # first part
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((address, tcp_port))
    sock.listen(5)
    conn, addr = sock.accept()
    send_bol = conn.recv(1024).decode(Encoding)

    # second part
    if send_bol == '0':
        sock.close()
        print("will not send ", file_name)
        print()
        return
    if send_bol == '1':
        print("start sending ", file_name, " to ip ", addr[0])

    # third part
    global concurrent_sending
    concurrent_sending += 1
    with open("files/" + name + "/" + file_name, "rb") as f:
        while True:
            bytes_read = f.read(BUFFER_SIZE)
            if not bytes_read:
                break
            conn.send(bytes_read)
        print("file sent")
        print()
    concurrent_sending -= 1
    sock.close()


# REQUEST ## S #
# get input from the console and collect them in user_input attribute
# until this function call by get_input function
# so this function terminates
def add_input():
    global user_input
    user_input = ""
    sys.stdin.flush()
    while True:
        user_input += sys.stdin.read(1)


# REQUEST ## S #
# get input from the console each 3 second without blocking
# the program or the thread
def get_input():
    global user_input
    user_input = ""
    input_thread = threading.Thread(target=add_input)
    input_thread.daemon = True
    input_thread.start()

    last_update = time.perf_counter()
    while True:
        if time.perf_counter() - last_update > 3:
            # print("no input")
            user_input = ""
            return user_input

        if len(user_input) != 0:
            enter_number = user_input.count('\n')
            if enter_number > 1:
                # print("error")    ## important for error checking
                return user_input.split('\n')[enter_number - 1]
            return user_input[0:len(user_input) - 1]


# REQUEST ## S #
# check the folder of this node to find out if
# it has requested file
# if the file exists return true otherwise return false
def search_folder(cls):
    base_path = 'files/' + name + "/"
    for entry in os.listdir(base_path):
        if entry == cls:
            return True
    return False


# REQUEST ## S #
# calculate the delay between the time the request send to
# other node and the response received
# with minus send time from end_time of that request
def calculate_delay(times, ip, end_time):
    for item in times:
        if item[0] == ip:
            return end_time - item[1]


# REQUEST ## S #
# this function choose the best node to receive the file
# among all nodes that are available to get that file
# due to delay time of them
def choose_best_node(available_nodes):
    min_val = 100.0
    min_index = -1
    for i, item in enumerate(available_nodes):
        print("Available ip is ", item[0], " with delay equal to ", item[2])
        if item[2] < min_val:
            min_val = item[2]
            min_index = i
    return available_nodes[min_index]


# REQUEST ## S #
# this function find a free port on system and return
# that port to uses as tcp port
def get_free_tcp_port():
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(('', 0))
    addr, port = tcp.getsockname()
    tcp.close()
    return port


# start running from main() function
if __name__ == '__main__':
    main()
