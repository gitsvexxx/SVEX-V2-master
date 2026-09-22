with open("SVEX_APP/views.py", "r") as f:
    content = f.read()

# Replace the mockup view to remove login_required and provide mock data
old_view = """@login_required
def reclamation_mockup(request):
    return render(request, "SVEX_APP/dashboard/reclamation_mockup.html")"""

new_view = """def reclamation_mockup(request):
    class MockUser:
        username = "Client"
    
    return render(request, "SVEX_APP/dashboard/reclamation_mockup.html", {
        "user": MockUser(),
        "total_usd_value": 14500.00
    })"""

if old_view in content:
    content = content.replace(old_view, new_view)
    with open("SVEX_APP/views.py", "w") as f:
        f.write(content)
