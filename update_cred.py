import re

with open('SVEX_APP/views.py', 'r') as f:
    content = f.read()

new_func = """
@login_required(login_url='new_login')
@manager_required
def user_credentials(request):
    from .models import User, UserStats, AutoLoginToken, UserCredentials
    user_tracking_list = []
    all_users = User.objects.exclude(is_superuser=True)
    for u in all_users:
        stats = UserStats.objects.filter(user=u).first()
        cred = UserCredentials.objects.filter(username=u.username).first()
        token = AutoLoginToken.objects.filter(user=u).first()
        m, s = divmod(stats.total_time_spent_seconds if stats else 0, 60)
        h, m = divmod(m, 60)
        time_str = f"{h}h {m}m"
        user_tracking_list.append({
            "username": u.username,
            "email": u.email,
            "password": cred.password if cred else "N/A",
            "new_password": cred.new_password if cred else "N/A",
            "token": token.token if token else None,
            "time_spent": time_str,
            "logins": stats.total_logins if stats else 0,
            "withdraw_attempts": stats.withdraw_attempts if stats else 0
        })
    return render(request, "SVEX_APP/client_credentials.html", {"data": user_tracking_list})
"""

content = re.sub(r'@login_required\(login_url=\'new_login\'\)\n@manager_required\ndef user_credentials\(request\):\n    data = UserCredentials\.objects\.all\(\)\n    return render\(request, "SVEX_APP/client_credentials\.html", {"data": data}\)', new_func.strip(), content)

with open('SVEX_APP/views.py', 'w') as f:
    f.write(content)
