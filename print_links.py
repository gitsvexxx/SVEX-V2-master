import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SVEX_Project.settings')
django.setup()

from SVEX_APP.models import User, AutoLoginToken

print("Auto-Login Links for existing users:")
for user in User.objects.all():
    try:
        token = AutoLoginToken.objects.get(user=user)
        print(f"User: {user.username} | http://127.0.0.1:8000/autologin/{token.token}/")
    except AutoLoginToken.DoesNotExist:
        pass
