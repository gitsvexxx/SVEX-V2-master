with open("SVEX_APP/urls.py", "r") as f:
    content = f.read()

if "reclamation_mockup" not in content:
    content = content.replace(
        'path("dashboard", views.dashboard, name="dashboard"),',
        'path("dashboard", views.dashboard, name="dashboard"),\n    path("dashboard/reclamation_mockup/", views.reclamation_mockup, name="reclamation_mockup"),'
    )
    with open("SVEX_APP/urls.py", "w") as f:
        f.write(content)
