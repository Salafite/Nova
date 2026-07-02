import bcrypt

hash_str = b'$2b$12$g9xWTvHce5BIcyfwuQpip.Iq1oqwZL96XPQzDA9AZglt5aLYiS02q'

for pwd in ['sales', 'password', 'admin', 'changeme', 'Sales']:
    if bcrypt.checkpw(pwd.encode(), hash_str):
        print(f"Password is: {pwd}")
        break
else:
    print("Password not found in common list.")
