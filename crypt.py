from Crypto.Cipher import AES
from Crypto.Protocol.KDF import HKDF
import hashlib

class secure:
    def __init__(self):
        pass
    
    def key_generation(self, key):
        sha256 = hashlib.sha256()
        sha256.update(key)
        derived_key = sha256.digest()
        return derived_key
    
    def pad(self, plaintext_bytes):
        pad_length = AES.block_size - (len(plaintext_bytes) % AES.block_size)
        padding = bytes([pad_length]) * pad_length
        return plaintext_bytes + padding
    
    def unpad(self, decrypted_data):
        pad_length = decrypted_data[-1]
        return decrypted_data[:-pad_length]
    
    def encrypt(self, plaintext, key):
        key = self.key_generation(key)
        iv = b"RandomIV12345678"
        cipher = AES.new(key, AES.MODE_CBC, iv)
        plaintext_bytes = plaintext.encode()
        ciphertext = cipher.encrypt(self.pad(plaintext_bytes))
        return ciphertext

    def decrypt(self, ciphertext, key):
        key = self.key_generation(key)
        iv = b"RandomIV12345678"
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_data = cipher.decrypt(ciphertext)
        return self.unpad(decrypted_data).decode()

    def hashed_password(self,password):
        # Encode the password string to bytes
        password_bytes = password.encode('utf-8')
        # Create a SHA-256 hash object
        sha256 = hashlib.sha256()
        # Update the hash object with the password bytes
        sha256.update(password_bytes)
        # Get the hexadecimal representation of the hashed password
        hashed_password = sha256.hexdigest()
        return hashed_password

# # Example usage
# aes = AESCipher()
# plaintext = "Hello, world!"
# key = b"ThisIsAKey123456"  # Key in byte format
# iv = b"RandomIV12345678"   # Fixed IV
# encrypted_data = aes.encrypt(plaintext, key, iv)
# print("Encrypted:", encrypted_data)
# decrypted_data = aes.decrypt(encrypted_data, key, iv)
# print("Decrypted:", decrypted_data)
