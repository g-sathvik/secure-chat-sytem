import crypt


def test_encryption():
    sec = crypt.secure()

    # 1. Generate keys for a fake user
    private_key_obj, public_pem = sec.generate_keypair()

    # 2. Try to encrypt a message
    original_message = "Hello, this is a secret test!"
    print("Original:", original_message)

    try:
        # Encrypt with the public key
        bundle = sec.encrypt(original_message, public_pem)
        print(f"Encrypted bundle size: {len(bundle)} bytes")

        # Decrypt with the private key
        decrypted = sec.decrypt(bundle, private_key_obj)
        print("Decrypted:", decrypted)

        if original_message == decrypted:
            print("\n✅ SUCCESS: crypt.py works perfectly!")
        else:
            print("\n❌ FAILED: Decrypted text doesn't match.")

    except Exception as e:
        print(f"\n❌ ERROR in crypt.py: {e}")


if __name__ == "__main__":
    test_encryption()