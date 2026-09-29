import csv
import io
import re
import secrets

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Client, ClientWallet, DepositWallet, UserCredentials, WithdrawalMessage

User = get_user_model()

IMPORT_BATCH_SIZE = 50
MAX_LOG_ITEMS = 200


def _append_log(results, key, message):
    """Keep the response small even for very large CSV imports."""
    if len(results[key]) < MAX_LOG_ITEMS:
        results[key].append(message)


def _decode_csv_file(csv_file):
    data = csv_file.read()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to decode file. Please upload a valid UTF-8 CSV file.")


def _detect_delimiter(text):
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    if ";" in first_line and first_line.count(";") > first_line.count(","):
        return ";"
    if "\t" in first_line and first_line.count("\t") > first_line.count(","):
        return "\t"
    return ","


def _get_columns(header):
    normalized = [
        (value or "").strip().lower().replace(" ", "_").replace("-", "_")
        for value in header
    ]

    aliases = {
        "name": {"full_name", "fullname", "name", "client_name", "client"},
        "email": {"email", "e_mail", "email_address", "mail"},
        "phone": {"phone", "phone_number", "telephone", "mobile", "cell", "tel"},
    }

    columns = {"name": None, "email": None, "phone": None}
    for index, column in enumerate(normalized):
        for key, names in aliases.items():
            if column in names:
                columns[key] = index

    # Backward-compatible fallback for simple "Name,Email,Phone" exports.
    if columns["email"] is None and len(header) >= 2:
        columns["name"] = 0
        columns["email"] = 1
        if len(header) >= 3:
            columns["phone"] = 2

    if columns["name"] is None and header:
        columns["name"] = 0 if columns["email"] != 0 else (1 if len(header) > 1 else None)

    if columns["phone"] is None and len(header) >= 3:
        taken = {columns["name"], columns["email"]}
        columns["phone"] = next((i for i in range(len(header)) if i not in taken), None)

    return columns


def _safe_username(base, used_usernames):
    base = re.sub(r"[^a-zA-Z0-9]", "", (base or "").strip())
    if not base:
        base = "user"

    candidate = base[:150]
    counter = 1
    while candidate.lower() in used_usernames:
        suffix = str(counter)
        candidate = f"{base[:150 - len(suffix)]}{suffix}"
        counter += 1

    used_usernames.add(candidate.lower())
    return candidate


def _unique_wallet_address(used_addresses):
    while True:
        address = "0x" + secrets.token_hex(20)
        if address not in used_addresses:
            used_addresses.add(address)
            return address


def _process_batch(batch, results):
    if not batch:
        return

    user_manager = User._default_manager
    client_manager = Client._default_manager
    wallet_manager = ClientWallet._default_manager
    deposit_wallet_manager = DepositWallet._default_manager
    withdrawal_message_manager = WithdrawalMessage._default_manager
    credentials_manager = UserCredentials._default_manager

    # One query per related set instead of a query/transaction for every row.
    emails = {row["email"] for row in batch if row["email"]}
    email_filter = Q()
    for email in emails:
        email_filter |= Q(email__iexact=email)

    existing_users = {
        user.email.lower(): user
        for user in user_manager.filter(email_filter)
    } if emails else {}

    existing_user_ids = [user.pk for user in existing_users.values()]
    existing_clients = {
        client.user_id: client
        for client in client_manager.filter(user_id__in=existing_user_ids)
    } if existing_user_ids else {}

    # Reserve usernames in memory for the entire batch.
    bases = {
        re.sub(r"[^a-zA-Z0-9]", "", row["email"].split("@")[0]) or
        re.sub(r"[^a-zA-Z0-9]", "", row["first_name"].lower()) or "user"
        for row in batch
        if row["email"]
    }
    username_filter = Q()
    for base in bases:
        username_filter |= Q(username__istartswith=base[:150])
    used_usernames = {
        username.lower()
        for username in user_manager.filter(username_filter).values_list("username", flat=True)
    } if bases else set()

    with transaction.atomic():
        # One account operation per email in a batch. Duplicate CSV rows for the
        # same email are treated as repeated updates instead of attempting a
        # duplicate UNIQUE email insert.
        unique_rows = {}
        duplicate_rows = []
        for row in batch:
            if row["email"] in unique_rows:
                duplicate_rows.append(row)
            else:
                unique_rows[row["email"]] = row

        unique_batch = list(unique_rows.values())
        new_rows = [row for row in unique_batch if row["email"] not in existing_users]
        new_users = []
        new_credentials = []
        new_user_rows = []

        for row in new_rows:
            username = _safe_username(
                row["email"].split("@")[0] or row["first_name"].lower(),
                used_usernames,
            )
            raw_password = secrets.token_urlsafe(10)
            user = User(
                username=username,
                email=row["email"],
                password=make_password(raw_password),
                first_name=row["first_name"],
                last_name=row["last_name"],
                is_client=True,
                is_manager=False,
                is_active=True,
                date_joined=timezone.now(),
            )
            new_users.append(user)
            new_credentials.append(
                UserCredentials(username=username, password=raw_password)
            )
            new_user_rows.append((row, user, username))

        if new_users:
            user_manager.bulk_create(new_users, batch_size=IMPORT_BATCH_SIZE)

            # bulk_create does not fire post_save signals, so create the same
            # related records explicitly in efficient batches.
            client_group, _ = Group.objects.get_or_create(name="Clients")
            client_group.user_set.add(*new_users)

            last_client = client_manager.select_for_update().order_by("-id").first()
            next_client_number = 100000
            if last_client and str(last_client.client_number).isdigit():
                next_client_number = int(last_client.client_number) + 1

            # Existing address list avoids unique collisions in this process.
            used_addresses = set(
                wallet_manager.exclude(wallet_address__isnull=True)
                .exclude(wallet_address="")
                .values_list("wallet_address", flat=True)
            )

            new_clients = []
            new_wallets = []
            new_deposit_wallets = []
            new_withdrawal_messages = []

            for row, user, username in new_user_rows:
                new_clients.append(
                    Client(
                        user=user,
                        client_number=str(next_client_number),
                        first_name=row["first_name"] or "",
                        last_name=row["last_name"] or "",
                        phone=row["phone"][:15],
                        address="",
                        zip_code="",
                    )
                )
                next_client_number += 1

                new_wallets.append(
                    ClientWallet(
                        client=user,
                        wallet_address=_unique_wallet_address(used_addresses),
                    )
                )
                new_deposit_wallets.append(DepositWallet(user=user))
                new_withdrawal_messages.append(
                    WithdrawalMessage(user=user)
                )

            client_manager.bulk_create(new_clients, batch_size=IMPORT_BATCH_SIZE)
            wallet_manager.bulk_create(new_wallets, batch_size=IMPORT_BATCH_SIZE)
            deposit_wallet_manager.bulk_create(
                new_deposit_wallets, batch_size=IMPORT_BATCH_SIZE
            )
            withdrawal_message_manager.bulk_create(
                new_withdrawal_messages, batch_size=IMPORT_BATCH_SIZE
            )
            credentials_manager.bulk_create(
                new_credentials, batch_size=IMPORT_BATCH_SIZE
            )

        # Refresh the just-created users from the maps for duplicate emails
        # inside the same CSV batch and update existing accounts in place.
        for row in batch:
            if row["email"] not in existing_users:
                # Locate the bulk-created user by email without another query.
                created_user = next(
                    user for source_row, user, _ in new_user_rows
                    if source_row["email"] == row["email"]
                )
                existing_users[row["email"]] = created_user
                existing_clients[created_user.pk] = next(
                    client for client in new_clients if client.user_id == created_user.pk
                )

        new_email_set = {row["email"] for row, _, _ in new_user_rows}
        users_to_update = []
        clients_to_update = []
        clients_to_create = []

        repair_next_client_number = 100000
        last_client_for_repair = client_manager.select_for_update().order_by("-id").first()
        if last_client_for_repair and str(last_client_for_repair.client_number).isdigit():
            repair_next_client_number = int(last_client_for_repair.client_number) + 1

        for row in unique_batch:
            if not row["email"]:
                results["skipped"] += 1
                _append_log(results, "errors", f"Row {row['row_num']}: Skipped - missing email")
                continue

            user = existing_users.get(row["email"])
            if not user:
                results["skipped"] += 1
                _append_log(results, "errors", f"Row {row['row_num']}: Could not resolve user")
                continue

            was_new = row["email"] in new_email_set

            if row["first_name"] and user.first_name != row["first_name"]:
                user.first_name = row["first_name"]
            if row["last_name"] and user.last_name != row["last_name"]:
                user.last_name = row["last_name"]

            if not was_new:
                users_to_update.append(user)

            client = existing_clients.get(user.pk)
            if client:
                if row["first_name"]:
                    client.first_name = row["first_name"]
                if row["last_name"]:
                    client.last_name = row["last_name"]
                if row["phone"]:
                    client.phone = row["phone"][:15]
                if not was_new:
                    clients_to_update.append(client)
            elif not was_new:
                # Repair legacy users that never received a Client row.
                clients_to_create.append(
                    Client(
                        user=user,
                        client_number=str(repair_next_client_number),
                        first_name=row["first_name"] or "",
                        last_name=row["last_name"] or "",
                        phone=(row["phone"] or "")[:15],
                        address="",
                        zip_code="",
                    )
                )
                repair_next_client_number += 1

            if was_new:
                results["created"] += 1
                _append_log(
                    results,
                    "details",
                    f"Created user: {row['email']}",
                )
            else:
                results["updated"] += 1
                _append_log(
                    results,
                    "details",
                    f"Updated user: {row['email']} ({row['full_name']})",
                )

        if users_to_update:
            user_manager.bulk_update(
                users_to_update,
                ["first_name", "last_name"],
                batch_size=IMPORT_BATCH_SIZE,
            )
        if clients_to_update:
            client_manager.bulk_update(
                clients_to_update,
                ["first_name", "last_name", "phone"],
                batch_size=IMPORT_BATCH_SIZE,
            )
        if clients_to_create:
            client_manager.bulk_create(
                clients_to_create, batch_size=IMPORT_BATCH_SIZE
            )

        for row in duplicate_rows:
            _append_log(
                results,
                "details",
                f"Repeated CSV row for existing email: {row['email']} (processed without duplicate account creation)",
            )


def process_user_import_row(full_name="", email="", phone=""):
    """Process exactly one CSV-style client row and return its import result."""
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["Full Name", "Email", "Phone"])
    writer.writerow([
        str(full_name or "").strip(),
        str(email or "").strip(),
        str(phone or "").strip(),
    ])
    csv_buffer.seek(0)
    return process_user_import_csv(
        io.BytesIO(csv_buffer.getvalue().encode("utf-8"))
    )


def process_user_import_csv(csv_file):
    """
    Import clients in small database batches.

    The previous implementation performed multiple queries, saves and nested
    transactions for every row. Large imports could therefore keep a Gunicorn
    worker busy long enough to be killed. This version batches the work and
    keeps the response logs bounded, so hundreds/thousands of rows do not
    create an oversized HTML response.
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
        decoded = _decode_csv_file(csv_file)
    except Exception as exc:
        results["errors"].append(str(exc))
        return results

    if not decoded.strip():
        results["errors"].append("The CSV file is empty.")
        return results

    try:
        reader = csv.reader(
            io.StringIO(decoded, newline=""),
            delimiter=_detect_delimiter(decoded),
        )
        header = next(reader)
    except StopIteration:
        results["errors"].append("Empty CSV file.")
        return results
    except Exception as exc:
        results["errors"].append(f"CSV parsing error: {exc}")
        return results

    columns = _get_columns(header)
    if columns["email"] is None:
        results["errors"].append("Could not find an Email column in the CSV.")
        return results

    batch = []
    row_num = 1

    try:
        for row in reader:
            row_num += 1
            if not row or not any((field or "").strip() for field in row):
                continue

            results["total"] += 1

            full_name = (
                row[columns["name"]].strip()
                if columns["name"] is not None and columns["name"] < len(row)
                else ""
            )
            email = (
                row[columns["email"]].strip().lower()
                if columns["email"] is not None and columns["email"] < len(row)
                else ""
            )
            phone = (
                row[columns["phone"]].strip()
                if columns["phone"] is not None and columns["phone"] < len(row)
                else ""
            )

            if not email or "@" not in email:
                results["skipped"] += 1
                _append_log(
                    results,
                    "errors",
                    f"Row {row_num}: Skipped - missing or invalid email ('{email}')",
                )
                continue

            name_parts = full_name.split(None, 1)
            batch.append(
                {
                    "row_num": row_num,
                    "full_name": full_name,
                    "email": email,
                    "phone": phone,
                    "first_name": name_parts[0] if name_parts else "",
                    "last_name": name_parts[1] if len(name_parts) > 1 else "",
                }
            )

            if len(batch) >= IMPORT_BATCH_SIZE:
                _process_batch(batch, results)
                batch = []

        if batch:
            _process_batch(batch, results)
    except Exception as exc:
        results["errors"].append(f"Import stopped at row {row_num}: {exc}")

    if results["total"] > MAX_LOG_ITEMS:
        results["logs_limited"] = True
    else:
        results["logs_limited"] = False

    return results
