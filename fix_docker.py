from pathlib import Path

dockerfile_path = Path(__file__).resolve().parent / 'Dockerfile'

with dockerfile_path.open('r') as f:
    content = f.read()

# Replace CMD with a shell script that runs collectstatic, migrate, and then starts gunicorn
new_cmd = """
# Run migrations and collectstatic, then start gunicorn
CMD python manage.py collectstatic --noinput && python manage.py migrate && gunicorn SVEX_Project.wsgi:application --bind 0.0.0.0:8000 --workers 5 --timeout 120 --worker-class sync --access-logfile - --error-logfile -
"""

import re
content = re.sub(r'CMD \["gunicorn".*', new_cmd.strip(), content)

with dockerfile_path.open('w') as f:
    f.write(content)
