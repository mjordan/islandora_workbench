import sys
from cryptography.fernet import Fernet

credentials_file = sys.argv[1]
key = Fernet.generate_key()
fernet = Fernet(key)

with open(credentials_file, 'rb') as f:
    plain_text = f.read()

encrypted = fernet.encrypt(plain_text)

with open(credentials_file, 'wb') as f:
    f.write(encrypted)

print(f"\nThe encryption key for '{credentials_file}' is {key.decode()}\n")
