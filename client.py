import socket
import threading
import db_module
import crypt
from colorama import Fore, Style
import pyfiglet

text = 'Welcome to Secure Chat!'
banner_text = text.center(125)
banner_width = 125
banner = f"{Fore.GREEN}{Style.BRIGHT}" + "=" * banner_width + "\n" + banner_text + f"\n{'=' * banner_width}{Style.RESET_ALL}"
print(banner)

print(Fore.GREEN + "Login If you have the account or register if you do not have an account" + Style.BRIGHT)
print("")
print(Fore.YELLOW + "1. Create Account" + Style.BRIGHT)
print(Fore.YELLOW + "2. Login" + Style.BRIGHT)
print("")
print(Fore.GREEN + "Enter the choice for the using the Features" + Style.BRIGHT)
print(Fore.YELLOW + '1. Search For the Users' + Style.BRIGHT)
print(Fore.YELLOW + '2. Send text Message' + Style.BRIGHT)
print(Fore.YELLOW + '3. Fetch Missed Messages' + Style.BRIGHT)
print(Fore.YELLOW + '4. Logout' + Style.RESET_ALL)


HOST = input('Enter Host (default: 127.0.0.1): ').strip() or "127.0.0.1"
PORT = int(input('(default: 8080) PORT: ').strip() or 8080)

# Bumped up from 2048: E2EE bundles carry a 256-byte RSA-wrapped key +
# 12-byte nonce + 16-byte tag on top of the ciphertext itself.
BUFFER_SIZE = 4096

import struct


class ChatClient:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))

    def send_message(self, message):
        # 1. Pack the length of the message into a 4-byte integer
        # '>I' means Big-Endian Unsigned Integer
        length_prefix = struct.pack('>I', len(message))

        # 2. Send the length header, followed immediately by the actual message
        self.sock.sendall(length_prefix + message)

    def receive_message(self):
        # 1. Read exactly 4 bytes to get the message length
        raw_msglen = self._recvall(4)
        if not raw_msglen:
            return None

        # 2. Unpack the 4 bytes back into an integer
        msglen = struct.unpack('>I', raw_msglen)[0]

        # 3. Read exactly 'msglen' bytes from the socket
        return self._recvall(msglen)

    def _recvall(self, n):
        # Helper function to ensure we receive exactly 'n' bytes, no more, no less
        data = bytearray()
        while len(data) < n:
            packet = self.sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return bytes(data)


def receive_loop(client, sec, private_key):
    while True:
        sender = client.receive_message()
        if sender is None:
            break

        bundle = client.receive_message()
        if bundle is None:
            break

        try:
            msg_dec = sec.decrypt(bundle, private_key)
        except Exception as e:
            # THIS IS CRITICAL: Print the exact error PyCryptodome gives us
            msg_dec = "[unable to decrypt message: {}]".format(e)

        sender_name = sender.decode('utf-8', errors='replace')
        data = '{}:{}'.format(sender_name, msg_dec)
        print(data)


def main():
    database = db_module.DB()
    sec = crypt.secure()

    my_private_key = None

    while True:
        choice = input('Enter the choice for Login/Register: ')
        if choice == '1':
            username = input('Enter the username: ')
            password = input('Enter the password: ')
            if database.is_account_exist(username):
                print("The username {} is already exists".format(username))
            else:
                # Generate this user's RSA keypair. The private key is
                # encrypted with their password and saved locally — it
                # never goes to the server or the database.
                key, public_pem = sec.generate_keypair()
                sec.save_private_key(key, username, password)
                database.register(username, password, public_pem)
                message = "The account with the username {} is created successfully".format(username)
                print(message)
                print("Your encryption keys have been generated. Keep your password safe — "
                      "it protects your private key, and it can't be recovered without it.")
        elif choice == '2':
            username = input('Enter the username: ')

            password = input('Enter the password: ')

            if not database.is_account_exist(username):
                message = "The username {} is not exists".format(username)
                print(message)
            else:
                password_from_db = database.get_password(username)
                hashed = sec.hashed_password(password)
                if password_from_db == hashed:
                    if database.is_account_online(username):
                        print('The username {} is already online please logout'.format(username))
                    else:
                        if not sec.has_private_key(username):
                            print("No local private key found for {}. If this is a new machine, "
                                  "you'll need to have your key migrated — messages can't be "
                                  "decrypted without it.".format(username))
                            continue
                        try:
                            my_private_key = sec.load_private_key(username, password)
                        except (ValueError, KeyError) as e:
                            print("Could not unlock your private key: {}".format(e))
                            continue

                        database.user_login(username)

                        message = "The username {} is logged in successfully".format(username)
                        print(message)
                        usernames = username
                        username = bytes(username, 'utf-8')
                        break

                else:
                    print('You have not entered the password correctly')
        else:
            continue

    client = ChatClient(HOST, PORT)
    receive_thread = threading.Thread(target=receive_loop, args=(client, sec, my_private_key), daemon=True)
    receive_thread.start()

    message = username

    client.send_message(message)

    while True:
        choice = input('Enter the choice: ')
        if choice == '1':
            uname = input('Enter the username: ')
            if database.is_account_online(uname):
                message = '{} is online'.format(uname)
                print(message)
            else:
                message = '{} is not currently available'.format(uname)
                print(message)
        elif choice == '2':
            uname_str = input('Enter the username: ')
            recipient_pub_key = database.get_public_key(uname_str)
            if not recipient_pub_key:
                print("No public key found for '{}' — can't send an encrypted message.".format(uname_str))
                continue

            uname = uname_str.encode('utf-8')
            client.send_message(uname)

            message = input('Enter the message: ')
            # Encrypted here, client-side, to the recipient's public key.
            # The server and database only ever see this ciphertext bundle.
            bundle = sec.encrypt(message, recipient_pub_key)
            client.send_message(bundle)

        elif choice == '3':
            msg = database.fetch_messages(usernames)
            for i in msg:
                try:
                    m = sec.decrypt(i['message'], my_private_key)
                except Exception:
                    m = "[unable to decrypt message]"
                data = '{}:{}'.format(i['sender'], m)
                print(data)
            database.delete_msg(usernames)

        elif choice == '4':
            database.user_logout(usernames)
            client.send_message(b'Quit')
            break
        else:
            print('Enter the correct choice !')


if __name__ == "__main__":
    main()
