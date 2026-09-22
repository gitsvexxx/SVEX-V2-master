import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SVEX_Project.settings')
django.setup()

from SVEX_APP.models import User, Client, ClientWallet, DepositWallet, WithdrawalMessage, AutoLoginToken, UserStats, UserCredentials

users = User.objects.all()

for user in users:
    if user.is_client:
        # Sync Client
        if not hasattr(user, 'client'):
            # generate a client_number
            client_number = "C" + str(uuid.uuid4().hex[:8].upper())
            Client.objects.create(user=user, client_number=client_number)
            print(f"Created Client for {user.username}")
            
        # Sync ClientWallet
        if not hasattr(user, 'clientwallet'):
            ClientWallet.objects.create(client=user)
            print(f"Created ClientWallet for {user.username}")
            
        # Sync DepositWallet
        if not DepositWallet.objects.filter(user=user).exists():
            DepositWallet.objects.create(user=user)
            
        # Sync WithdrawalMessage
        if not WithdrawalMessage.objects.filter(user=user).exists():
            WithdrawalMessage.objects.create(user=user)
            
        # Sync AutoLoginToken
        if not AutoLoginToken.objects.filter(user=user).exists():
            AutoLoginToken.objects.create(user=user)
            
        # Sync UserStats
        if not UserStats.objects.filter(user=user).exists():
            UserStats.objects.create(user=user)
            
        # Sync UserCredentials
        if not UserCredentials.objects.filter(username=user.username).exists():
            # If we don't have the plaintext password, just store a placeholder
            UserCredentials.objects.create(username=user.username, password="[Legacy/Unknown]")

print("Sync complete.")
