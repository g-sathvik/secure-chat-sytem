from pymongo import MongoClient
import hashlib

# class defined for all the database operations
class DB:
    # initialization of the class
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['chat']

    # checking the username exists in the database
    def is_account_exist(self, username):
        result = self.db.accounts.find_one({'username': username})
        if result:
            return True
        else:
            return False

    # For converting the password into hashed password
    def hashed_password(self, plaintext):
        return hashlib.sha256(plaintext.encode()).hexdigest()

    # For storing the messages of the user if he is not online
    # `message` is now an E2EE ciphertext bundle (bytes) — the DB never
    # sees plaintext, since it was encrypted to the recipient's public key
    # before it ever got here.
    def msg_storage(self, username, from_username, message):
        msg = {
            'username': username,
            'sender': from_username,
            'message': message
        }
        self.db.messages.insert_one(msg)

    # For fetching the messages
    def fetch_messages(self, username):
        result = self.db.messages.find({'username': username})
        return result

    # For deleting the messages
    def delete_msg(self, username):
        self.db.messages.delete_many({'username': username})

    # creating the new account for the user
    # now also stores the user's RSA public key so others can encrypt to them
    def register(self, username, password, public_key):
        password = self.hashed_password(password)
        account = {
            'username': username,
            'password': password,
            'public_key': public_key
        }
        self.db.accounts.insert_one(account)

    # finding the password of a given user
    def get_password(self, username):
        result = self.db.accounts.find_one({'username': username})
        return result["password"]

    # fetching a user's public key so a sender can encrypt a message to them
    def get_public_key(self, username):
        result = self.db.accounts.find_one({'username': username})
        return result["public_key"] if result and "public_key" in result else None

    # checking the user is online or not
    def is_account_online(self, username):
        result = self.db.online_peers.find_one({'username': username})
        if result:
            return True
        else:
            return False

    # storing the port and ip of a user logged now
    def user_login(self, username):
        # deleting the previous entries if he closed the aplication suddenly
        self.db.online_peers.delete_many({'username': username})
        peer = {
            "username": username,
        }
        self.db.online_peers.insert_one(peer)

    # removing the user record from online_users
    def user_logout(self, username):
        self.db.online_peers.delete_many({'username': username})
