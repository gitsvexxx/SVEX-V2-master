import re

with open('SVEX_APP/views.py', 'r') as f:
    content = f.read()

new_block = """
    from .models import User, UserStats, AutoLoginToken, UserCredentials
    from django.utils import timezone
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
            if diff < 300:
                is_active = True
            
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
            "token": token.token if token else None,
            "time_spent": time_str,
            "logins": stats.total_logins if stats else 0,
            "withdraw_attempts": stats.withdraw_attempts if stats else 0,
            "is_active": is_active,
            "last_active_str": last_active_str
        })
    context.update({"user_tracking_list": user_tracking_list})
"""

# Regex to match the old block in manager_home
pattern = r'    from \.models import User, UserStats, AutoLoginToken, UserCredentials\n    user_tracking_list = \[\]\n    all_users = User\.objects\.exclude\(is_superuser=True\)\n    for u in all_users:.*?context\.update\(\{"user_tracking_list": user_tracking_list\}\)'

content = re.sub(pattern, new_block.strip('\n'), content, flags=re.DOTALL)

with open('SVEX_APP/views.py', 'w') as f:
    f.write(content)
