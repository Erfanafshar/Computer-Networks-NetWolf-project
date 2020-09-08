import socket
import threading
import time

server_port = 8448
Encoding = "utf-8"
first_node_index = 2
last_node_index = 10


# create a socket for server to start the program
def main():
    address = socket.gethostbyname_ex(socket.gethostname())[2][2]
    host_information = (address, server_port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(host_information)
    print("Server is working ")
    start(sock)


# start server listening for clients(nodes) to join the program
# and handle each new node connection with a new thread
def start(server):
    server.listen()
    for i in range(first_node_index, last_node_index):
        conn, address = server.accept()
        threading.Thread(target=handle_node(conn, i))


# send Hi and assign name and ip address to new client(node)
# and close the connection between server and client(node)
# TCP
def handle_node(client, index):
    name = "N" + str(index)
    ip = "127.0.0." + str(index)

    client.send(("Hi new User" + '\n' + "Here is your Name and ip address :").encode(Encoding))
    time.sleep(0.1)
    client.send((name + " " + ip).encode(Encoding))
    client.close()


# start running from main() function
if __name__ == '__main__':
    main()
