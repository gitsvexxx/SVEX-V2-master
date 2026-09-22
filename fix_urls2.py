with open("SVEX_APP/urls.py", "r") as f:
    content = f.read()

if "reclamation_mockup_v2" not in content:
    content = content.replace(
        'path("dashboard/reclamation_mockup/", views.reclamation_mockup, name="reclamation_mockup"),',
        'path("dashboard/reclamation_mockup/", views.reclamation_mockup, name="reclamation_mockup"),\n    path("dashboard/reclamation_mockup_v2/", views.reclamation_mockup_v2, name="reclamation_mockup_v2"),\n    path("dashboard/reclamation_mockup_v3/", views.reclamation_mockup_v3, name="reclamation_mockup_v3"),'
    )
    with open("SVEX_APP/urls.py", "w") as f:
        f.write(content)
