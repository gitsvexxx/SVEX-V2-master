with open("SVEX_APP/views.py", "r") as f:
    content = f.read()

new_views = """def reclamation_mockup_v2(request):
    class MockUser:
        username = "Client"
    return render(request, "SVEX_APP/dashboard/reclamation_mockup_v2.html", {"user": MockUser(), "total_usd_value": 14500.00})

def reclamation_mockup_v3(request):
    class MockUser:
        username = "Client"
    return render(request, "SVEX_APP/dashboard/reclamation_mockup_v3.html", {"user": MockUser(), "total_usd_value": 14500.00})
"""

if "reclamation_mockup_v2" not in content:
    content += "\n" + new_views
    with open("SVEX_APP/views.py", "w") as f:
        f.write(content)
