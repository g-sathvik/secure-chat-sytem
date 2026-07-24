import hashlib
import os

from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes

RSA_KEY_SIZE = 2048
ENC_KEY_LEN = RSA_KEY_SIZE // 8   # 256 bytes for a 2048-bit RSA key
NONCE_LEN = 12                   # AES-GCM standard nonce size
TAG_LEN = 16                     # AES-GCM auth tag size
KEYS_DIR = "keys"


class secure:
    """
    Password hashing + true end-to-end encryption.

    E2EE design:
      - Every user has an RSA keypair. The private key is generated once,
        encrypted with the user's password, and saved ONLY on their own
        machine. The public key is published to the server/DB.
      - To send a message, the sender generates a random one-time AES key,
        encrypts the plaintext with it (AES-GCM), then encrypts that AES
        key with the recipient's RSA public key. Only the recipient's
        private key can unwrap the AES key and read the message.
      - This holds even for offline messages stored in Mongo: they are
        stored as this same ciphertext bundle, so the server/DB operator
        can never read message contents.
    """

    def __init__(self):
        pass

    # ---------------- password hashing (used for login only) ----------------

    def hashed_password(self, password):
        sha256 = hashlib.sha256()
        sha256.update(password.encode("utf-8"))
        return sha256.hexdigest()

    # ---------------- RSA keypair management ----------------

    def generate_keypair(self):
        """Generate a fresh RSA keypair. Returns (private_key_obj, public_pem_str)."""
        key = RSA.generate(RSA_KEY_SIZE)
        public_pem = key.publickey().export_key().decode("utf-8")
        return key, public_pem

    def _private_key_path(self, username):
        os.makedirs(KEYS_DIR, exist_ok=True)
        return os.path.join(KEYS_DIR, "{}_private.pem".format(username))

    def save_private_key(self, key, username, passphrase):
        """Persist the private key locally, encrypted with the user's password."""
        path = self._private_key_path(username)
        encrypted_pem = key.export_key(
            passphrase=passphrase,
            pkcs=8,
            protection="scryptAndAES128-GCM",
        )
        with open(path, "wb") as f:
            f.write(encrypted_pem)
        return path

    def load_private_key(self, username, passphrase):
        """Load + decrypt the user's own private key. Raises if password is wrong."""
        path = self._private_key_path(username)
        with open(path, "rb") as f:
            data = f.read()
        return RSA.import_key(data, passphrase=passphrase)

    def has_private_key(self, username):
        return os.path.exists(self._private_key_path(username))

    # ---------------- hybrid RSA + AES-GCM message encryption ----------------

    def encrypt(self, plaintext, recipient_public_pem):
        """
        Encrypt `plaintext` so ONLY the holder of the recipient's private key
        can decrypt it. `recipient_public_pem` is the recipient's public key
        (PEM string, as fetched from the DB).
        Returns raw bytes ready to send over the socket / store in Mongo.
        """
        recipient_key = RSA.import_key(recipient_public_pem)

        # Fresh one-time AES key for this message only
        session_key = get_random_bytes(16)

        rsa_cipher = PKCS1_OAEP.new(recipient_key)
        enc_session_key = rsa_cipher.encrypt(session_key)

        # Force exactly a 12-byte nonce so it matches NONCE_LEN
        aes_cipher = AES.new(session_key, AES.MODE_GCM, nonce=get_random_bytes(NONCE_LEN))
        ciphertext, tag = aes_cipher.encrypt_and_digest(plaintext.encode("utf-8"))

        # bundle layout: [enc_session_key][nonce][tag][ciphertext]
        return enc_session_key + aes_cipher.nonce + tag + ciphertext

    def decrypt(self, bundle, private_key):
        """
        Decrypt a bundle produced by `encrypt`.
        `private_key` may be an RSA key object (from load_private_key) or
        raw PEM bytes/str.
        """
        if isinstance(private_key, (bytes, str)):
            private_key = RSA.import_key(private_key)

        enc_session_key = bundle[:ENC_KEY_LEN]
        nonce = bundle[ENC_KEY_LEN: ENC_KEY_LEN + NONCE_LEN]
        tag = bundle[ENC_KEY_LEN + NONCE_LEN: ENC_KEY_LEN + NONCE_LEN + TAG_LEN]
        ciphertext = bundle[ENC_KEY_LEN + NONCE_LEN + TAG_LEN:]

        rsa_cipher = PKCS1_OAEP.new(private_key)
        session_key = rsa_cipher.decrypt(enc_session_key)

        aes_cipher = AES.new(session_key, AES.MODE_GCM, nonce=nonce)
        plaintext = aes_cipher.decrypt_and_verify(ciphertext, tag)
        return plaintext.decode("utf-8")
