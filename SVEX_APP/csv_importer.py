import csv
import io
import re
import secrets
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Client, UserCredentials

User = get_user_model()


def process_user_import_csv(csv_file):
    """
    Parses an uploaded CSV file containing full name, email, and phone.
    Creates new Client users or updates existing ones.
    Returns a dictionary with import statistics and details.
    """
    results = {
        "total": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
        "details": [],
    }

    try:
        data = csv_file.read()
        decoded_file = None
        for encoding in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
            try:
                decoded_file = data.decode(encoding)
                break
            except (UnicodeDecodeError, AttributeError):
                continue

        if not decoded_file:
            results["errors"].append("Unable to decode file. Please upload a valid UTF-8 CSV file.")
            return results
    except Exception as e:
        results["errors"].append(f"File read error: {str(e)}")
        return results

    lines = decoded_file.splitlines()
    if not lines:
        results["errors"].append("The CSV file is empty.")
        return results

    # Detect delimiter
    first_line = lines[0]
    delimiter = ","
    if ";" in first_line and first_line.count(";") > first_line.count(","):
        delimiter = ";"
    elif "\t" in first_line and first_line.count("\t") > first_line.count(","):
        delimiter = "\t"

    reader = csv.reader(lines, delimiter=delimiter)
    try:
        header = next(reader)
    except StopIteration:
        results["errors"].append("Empty CSV file.")
        return results

    # Normalize header names
    header_clean = [h.strip().lower().replace(" ", "_").replace("-", "_") for h in header]

    col_name = None
    col_email = None
    col_phone = None

    for idx, col in enumerate(header_clean):
        if col in ["full_name", "fullname", "name", "client_name", "client"]:
            col_name = idx
        elif col in ["email", "e_mail", "email_address", "mail"]:
            col_email = idx
        elif col in ["phone", "phone_number", "telephone", "mobile", "cell", "tel"]:
            col_phone = idx

    # If headers weren't explicitly matched, fall back to heuristics
    if col_email is None:
        for idx, col in enumerate(header):
            if "@" in col:
                col_email = idx
                break

    if col_email is None:
        # Default order assumption: full_name, email, phone
        if len(header) >= 2:
            col_name = 0
            col_email = 1
            if len(header) >= 3:
                col_phone = 2
        elif len(header) == 1:
            col_email = 0

    if col_name is None and len(header) > 0:
        col_name = 0 if col_email != 0 else (1 if len(header) > 1 else None)

    if col_phone is None and len(header) > 2:
        taken = {col_name, col_email}
        for i in range(len(header)):
            if i not in taken:
                col_phone = i
                break

    row_num = 1
    for row in reader:
        row_num += 1
        if not row or not any(field.strip() for field in row):
            continue

        results["total"] += 1

        full_name = row[col_name].strip() if col_name is not None and col_name < len(row) else ""
        email = row[col_email].strip() if col_email is not None and col_email < len(row) else ""
        phone = row[col_phone].strip() if col_phone is not None and col_phone < len(row) else ""

        if not email or "@" not in email:
            results["skipped"] += 1
            results["errors"].append(f"Row {row_num}: Skipped - missing or invalid email ('{email}')")
            continue

        email = email.lower()

        # Split full name into first and last name
        name_parts = full_name.split(None, 1)
        first_name = name_parts[0] if len(name_parts) > 0 else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        try:
            with transaction.atomic():
                user = User.objects.filter(email__iexact=email).first()
                if user:
                    # Update existing user info
                    if first_name:
                        user.first_name = first_name
                    if last_name:
                        user.last_name = last_name
                    user.save()

                    client, _ = Client.objects.get_or_create(user=user)
                    if first_name:
                        client.first_name = first_name
                    if last_name:
                        client.last_name = last_name
                    if phone:
                        client.phone = phone
                    client.save()

                    results["updated"] += 1
                    results["details"].append(f"Updated user: {email} ({full_name})")
                else:
                    # Generate a unique username
                    base_username = re.sub(r"[^a-zA-Z0-9]", "", email.split("@")[0])
                    if not base_username:
                        base_username = re.sub(r"[^a-zA-Z0-9]", "", first_name.lower()) or "user"

                    username = base_username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1

                    raw_password = secrets.token_urlsafe(10)

                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=raw_password,
                        first_name=first_name,
                        last_name=last_name,
                        is_client=True,
                        is_manager=False,
                    )

                    client, _ = Client.objects.get_or_create(user=user)
                    client.first_name = first_name
                    client.last_name = last_name
                    client.phone = phone
                    client.save()

                    # Record credentials for backoffice
                    UserCredentials.objects.create(username=username, password=raw_password)

                    results["created"] += 1
                    results["details"].append(f"Created user: {email} (Username: {username})")
        except Exception as err:
            results["skipped"] += 1
            results["errors"].append(f"Row {row_num} ({email}): Error - {str(err)}")

    return results
