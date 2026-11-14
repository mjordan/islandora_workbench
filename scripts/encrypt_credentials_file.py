import sys
from pathlib import Path
from cryptography.fernet import Fernet

credentials_file = sys.argv[1]

try:
    key = Fernet.generate_key()
    fernet = Fernet(key)

    fc = open(credentials_file, "rb")
    plain_text = fc.read()

    encrypted = fernet.encrypt(plain_text)

    fe = open(credentials_file, "wb")
    fe.write(encrypted)

    key_file = Path(credentials_file).stem
    key_file = f"{key_file}_key.txt"

    key_string = key.decode()

    fk = open(key_file, "wb")
    fk.write(key)

    print(f"'{credentials_file}' can be decrypted using the key {key_string}, which has been saved to the file '{key_file}'.")
except Exception as e:
    print("Unable to encrypt credentials: ", e)