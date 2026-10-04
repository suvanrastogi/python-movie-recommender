import bcrypt

def hash_password(password: str) -> bytes:
    # Convert string to bytes
    password_bytes = password.encode('utf-8')
    
    # Generate a secure salt and hash the password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt)
    
    return hashed_password

def verify_password(plain_password: str, hashed_password: bytes) -> bool:
    # Convert string to bytes
    password_bytes = plain_password.encode('utf-8')
    
    # Check if the entered password matches the hash
    return bcrypt.checkpw(password_bytes, hashed_password)
