import socket
import threading
import db_module
from colorama import Fore, Style
import pyfiglet




banner = pyfiglet.figlet_format('Border defender')
banner_colored = f"{Fore.RED}{banner}{Style.RESET_ALL}"
print(banner_colored)

HOST = input('Enter Host (default: 127.0.0.1): ').strip() or "127.0.0.1"
PORT = int(input('(default: 8080) PORT: ').strip() or 8080)
MAX_CLIENTS = int(input('Maximum clients (default: 10): ').strip() or 10)
BUFFER_SIZE = 2048

class ChatServer:
    def __init__(self, host, port, database):
        self.all_users = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.sock.listen(MAX_CLIENTS)
        print("Server started at {}:{}".format(host, port))
        self.database = db_module.DB()
        
    def run(self):
        while True:
            conn, addr = self.sock.accept()
            tr = threading.Thread(target=self.client_handler, args=(conn,))
            tr.daemon = True
            tr.start()
            
    def client_handler(self, conn):
        name = conn.recv(BUFFER_SIZE)
        #name = binascii.a2b_uu(name).decode()
        print(name, 'joined')      
        self.all_users.append((conn, name))
        
        while True:
            to_user_name = conn.recv(BUFFER_SIZE)
            if to_user_name == b'Quit':
                break
            #to_user_name = binascii.a2b_uu(to_user_name).decode()
            print('from',to_user_name)
            message = conn.recv(BUFFER_SIZE)
            print('msg:',message)
            if not message:
                break
           
            else:
                from_user_name = name
                self.send_to_user(from_user_name, to_user_name, from_user_name)
                self.send_to_user(from_user_name, to_user_name, message)
            
                
        hello_string = "{} has left the chat ".format(name)
        self.database.user_logout(name)
        print(hello_string)
        self.delete_user(conn)
        
    def delete_user(self, del_user):
        for i in range(len(self.all_users)):
            if self.all_users[i][0] == del_user:
                del self.all_users[i]
                break

    def send_to_all(self, from_user, message):
        if len(self.all_users) > 1:
            for user in self.all_users:
                if user[0] != from_user[0]:
                    msg = "{}: {}".format(from_user[1], message)
                    user[0].sendall(binascii.b2a_uu(msg.encode()))

    def send_to_user(self, from_user_name, to_user_name, message):
        for user in self.all_users:
            if user[1] == to_user_name:
                user[0].sendall(message)
                print('sent message')
                return
               
        usr=to_user_name.decode('utf-8')

        if self.database.is_account_exist(usr) :
            if from_user_name != message:
                frs=from_user_name.decode('utf-8')
                self.database.msg_storage(usr, frs, message)
        else:
            print("User '{}' not found.".format(to_user_name))

                    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, tb):
        print("Server is shutting down.")

database = db_module.DB()  # Assuming DB() is the class constructor
with ChatServer(HOST, PORT, database) as chat:
    chat.run()
