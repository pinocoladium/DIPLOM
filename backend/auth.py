from django.contrib.auth.backends import BaseBackend

import bcrypt

from backend.models import Client

def hash_password(password: str):
    return (bcrypt.hashpw(password.encode(), bcrypt.gensalt())).decode()

def check_password(password: str, hashed_password: str):
    return bcrypt.checkpw(password.encode(), hashed_password.encode())

class MyAuthenticationBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        client = Client.objects.get(email=email)
        hashed_password = client.password
        valid = check_password(password, hashed_password)
        if valid and hashed_password:
           return client
        return None
    
    def get_client(self, client_id):
        try:
            return Client.objects.get(pk=client_id)
        except Client.DoesNotExist:
            return None

    