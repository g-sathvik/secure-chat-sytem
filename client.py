import socket
import threading
import db_module
import crypt
from colorama import Fore, Style
import pyfiglet

text='Welcome to Secure Chat!'
banner_text = text.center(125)
banner_width=125
banner = f"{Fore.GREEN}{Style.BRIGHT}" + "=" * banner_width + "\n" + banner_text + f"\n{'=' * banner_width}{Style.RESET_ALL}"
print(banner)

print(Fore.GREEN + "Login If you have the account or register if you do not have an account" + Style.BRIGHT)
print("")
print(Fore.YELLOW + "1. Create Account" + Style.BRIGHT)
print(Fore.YELLOW +  "2. Login" + Style.BRIGHT)
print("")
print(Fore.GREEN + "Enter the choice for the using the Features" + Style.BRIGHT)
print(Fore.YELLOW + '1. Search For the Users' + Style.BRIGHT)
print(Fore.YELLOW + '2. Send text Message' + Style.BRIGHT)
print(Fore.YELLOW + '3. Fetch Missed Messages' + Style.BRIGHT)
print(Fore.YELLOW + '4. Logout' + Style.RESET_ALL)



HOST = input('Enter Host (default: 127.0.0.1): ').strip() or "127.0.0.1"
PORT = int(input('(default: 8080) PORT: ').strip() or 8080)

BUFFER_SIZE = 2048

class ChatClient:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
    
    def send_message(self, message):

        self.sock.sendall(message)
    
    def receive_message(self):
        data = self.sock.recv(BUFFER_SIZE)
        if not data:
            return None
        
        return data


def receive_loop(client,sec,username):
    while True:
        use=client.receive_message()
        
        #print(use)
        data = client.receive_message()
         
        msg_dec=sec.decrypt(data,username)
        data = '{}:{}'.format(use, msg_dec)
        print(data)

def main():
    database = db_module.DB()
    sec = crypt.secure()



    while True:
        choice = input('Enter the choice for Login/Register: ')
        if choice=='1':
            username=input('Enter the username: ')
            password=input('Enter the password: ')
            if database.is_account_exist(username):
                print("The username {} is already exists".format(username))
            else:
                database.register(username,password)
                message="The account with the username {} is created successfully".format(username)
                print(message)
        elif choice=='2':
            username=input('Enter the username: ')
            
            password=input('Enter the password: ')

            if not database.is_account_exist(username):
                message="The username {} is not exists".format(username)
                print(message)
            else:
                password_from_db = database.get_password(username)
                password = sec.hashed_password(password)
                if password_from_db == password:
                    if database.is_account_online(username):
                        print('The username {} is already online please logout'.format(username))
                    else:
                        database.user_login(username)

                        message="The username {} is logged in successfully".format(username)
                        print(message)
                        usernames=username
                        username = bytes(username, 'utf-8')
                        # 
                        break
                    
                else:
                    print('You have not entered the password correctly')
        else:
            continue

    client = ChatClient(HOST, PORT)
    receive_thread = threading.Thread(target=receive_loop, args=(client,sec,username), daemon=True)
    receive_thread.start()

    message = username
    

    client.send_message(message)    
    
    while True:
        choice = input('Enter the choice: ')
        if choice=='1':
            uname = input('Enter the username: ')
            if database.is_account_online(uname):
                message='{} is online'.format(uname)
                print(message)
            else:
                message='{} is not currently available'.format(uname)
                print(message)
        elif choice=='2':
            uname = input('Enter the username: ')
            uname = bytes(uname, 'utf-8')
            client.send_message(uname)

            message = input('Enter the message: ')
            message = sec.encrypt(message,uname)
            client.send_message(message)

        elif choice == '3':
            msg = database.fetch_messages(usernames)
            for i in msg:
                m=sec.decrypt(i['message'],username)
                data= '{}:{}'.format(i['sender'],m)
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
