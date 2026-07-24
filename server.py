import socket
import threading
import struct
import db_module
from colorama import Fore, Style
import pyfiglet

banner = pyfiglet.figlet_format('Border defender')
banner_colored = f"{Fore.RED}{banner}{Style.RESET_ALL}"
print(banner_colored)

HOST = input('Enter Host (default: 127.0.0.1): ').strip() or "127.0.0.1"
PORT = int(input('(default: 8080) PORT: ').strip() or 8080)
MAX_CLIENTS = int(input('Maximum clients (default: 10): ').strip() or 10)


class ChatServer:
    def __init__(self, host, port, database):
        self.all_users = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow address reuse in case you restart the server quickly
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(MAX_CLIENTS)
        print("Server started at {}:{}".format(host, port))
        self.database = database

    def _recvall(self, conn, n):
        """Helper to receive exactly n bytes."""
        data = bytearray()
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return bytes(data)

    def receive_message(self, conn):
        """Reads the 4-byte length header, then the exact message."""
        raw_msglen = self._recvall(conn, 4)
        if not raw_msglen:
            return None
        msglen = struct.unpack('>I', raw_msglen)[0]
        return self._recvall(conn, msglen)

    def send_message(self, conn, message):
        """Prefixes the message with a 4-byte length header before sending."""
        length_prefix = struct.pack('>I', len(message))
        conn.sendall(length_prefix + message)

    def run(self):
        while True:
            conn, addr = self.sock.accept()
            tr = threading.Thread(target=self.client_handler, args=(conn,))
            tr.daemon = True
            tr.start()

    def client_handler(self, conn):
        # Replaced conn.recv with receive_message to handle the framing header
        name = self.receive_message(conn)
        if not name:
            return

        print('{} joined'.format(name.decode('utf-8', errors='replace')))
        self.all_users.append((conn, name))

        while True:
            to_user_name = self.receive_message(conn)
            if not to_user_name or to_user_name == b'Quit':
                break

            print('from', to_user_name.decode('utf-8', errors='replace'))

            message = self.receive_message(conn)
            if not message:
                break

            print('msg received (encrypted bundle)')

            from_user_name = name
            # Forward the sender's name so the recipient client knows who it's from
            self.send_to_user(from_user_name, to_user_name, from_user_name)
            # Forward the actual encrypted message bundle
            self.send_to_user(from_user_name, to_user_name, message)

        hello_string = "{} has left the chat".format(name.decode('utf-8', errors='replace'))
        self.database.user_logout(name.decode('utf-8', errors='replace'))
        print(hello_string)
        self.delete_user(conn)
        conn.close()

    def delete_user(self, del_user):
        for i in range(len(self.all_users)):
            if self.all_users[i][0] == del_user:
                del self.all_users[i]
                break

    def send_to_all(self, from_user, message):
        if len(self.all_users) > 1:
            for user in self.all_users:
                if user[0] != from_user[0]:
                    msg = "{}: {}".format(from_user[1].decode('utf-8', errors='replace'), message)
                    self.send_message(user[0], msg.encode('utf-8'))

    def send_to_user(self, from_user_name, to_user_name, message):
        for user in self.all_users:
            if user[1] == to_user_name:
                self.send_message(user[0], message)
                print('sent message')
                return

        usr = to_user_name.decode('utf-8')
        if self.database.is_account_exist(usr):
            if from_user_name != message:
                frs = from_user_name.decode('utf-8')
                self.database.msg_storage(usr, frs, message)
        else:
            print("User '{}' not found.".format(usr))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, tb):
        print("Server is shutting down.")
        self.sock.close()


database = db_module.DB()
with ChatServer(HOST, PORT, database) as chat:
    chat.run()