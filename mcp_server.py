"""
SVEX database MCP server.

This exposes a deliberately scoped interface to the Django database for an
authorized LLM/MCP client. It does not expose raw SQL, passwords, credentials,
KYC documents, or delete operations.

HTTP authentication:
  Authorization: Bearer <SVEX_MCP_READ_TOKEN>
or
  Authorization: Bearer <SVEX_MCP_WRITE_TOKEN>

Write operations are always two-step:
  1. propose_record_update(...)
  2. confirm_record_update(..., confirmation="CONFIRM")
"""

import contextlib
import hmac
import contextvars
import logging
import os
from decimal import Decimal, InvalidOperation

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SVEX_Project.settings")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.validators import validate_email
from django.db import close_old_connections, transaction
from django.db.models import Q
from django.utils import timezone
from starlette.responses import JSONResponse

from mcp.server import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from SVEX_APP.models import Client, ClientWallet, Deposit, Withdrawal


logging.basicConfig(level=os.environ.get("MCP_LOG_LEVEL", "INFO"))
logger = logging.getLogger("svex.mcp")

User = get_user_model()

READ_TOKEN = os.environ.get("SVEX_MCP_READ_TOKEN", "").strip()
WRITE_TOKEN = os.environ.get("SVEX_MCP_WRITE_TOKEN", "").strip()

if not READ_TOKEN and not WRITE_TOKEN:
    raise RuntimeError(
        "SVEX_MCP_READ_TOKEN or SVEX_MCP_WRITE_TOKEN must be configured."
    )

_auth_context = contextvars.ContextVar("svex_mcp_auth_context", default=None)


def current_principal():
    return _auth_context.get() or {"role": "unknown", "client_id": "unknown"}


def require_write_access():
    if current_principal().get("role") != "write":
        raise PermissionError(
            "Write access requires a valid SVEX_MCP_WRITE_TOKEN."
        )


def audit(action, target="", details="", status="ok"):
    principal = current_principal()
    safe_details = str(details).replace("\n", " ")[:1000]
    logger.info(
        "MCP_AUDIT action=%s status=%s role=%s client_id=%s target=%s details=%s",
        action,
        status,
        principal.get("role", "unknown"),
        principal.get("client_id", "unknown"),
        str(target)[:200],
        safe_details,
    )


@contextlib.contextmanager
def db_context():
    close_old_connections()
    try:
        yield
    finally:
        close_old_connections()


class BearerTokenMiddleware:
    """Simple bearer-token gate for this private database MCP endpoint."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        headers = {
            key.lower(): value
            for key, value in scope.get("headers", [])
        }
        auth_header = headers.get(b"authorization", b"").decode("latin-1")

        if not auth_header.lower().startswith("bearer "):
            response = JSONResponse(
                {"error": "Unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            return await response(scope, receive, send)

        token = auth_header[7:].strip()
        role = None
        client_id = "mcp-client"

        if WRITE_TOKEN and hmac.compare_digest(token, WRITE_TOKEN):
            role = "write"
        elif READ_TOKEN and hmac.compare_digest(token, READ_TOKEN):
            role = "read"

        if role is None:
            audit("authentication", status="denied")
            response = JSONResponse(
                {"error": "Invalid MCP token"},
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
            return await response(scope, receive, send)

        token_handle = _auth_context.set(
            {"role": role, "client_id": client_id}
        )
        try:
            return await self.app(scope, receive, send)
        finally:
            _auth_context.reset(token_handle)


server = MCPServer(
    "SVEX Database MCP",
    instructions=(
        "Authorized database tools for SVEX operations. "
        "Never expose passwords, stored credentials, KYC images/documents, "
        "or raw SQL. For writes, first create a proposal and then require "
        "the exact confirmation string CONFIRM before applying it."
    ),
)


def _limit(value, default=50, maximum=100):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, maximum))


def _serialize_user(user):
    return {
        "id": user.pk,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_active": user.is_active,
        "is_manager": user.is_manager,
        "is_client": user.is_client,
        "date_joined": user.date_joined.isoformat() if user.date_joined else None,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


def _serialize_client(client):
    if not client:
        return None
    return {
        "id": client.pk,
        "user_id": client.user_id,
        "client_number": client.client_number,
        "first_name": client.first_name,
        "last_name": client.last_name,
        "birthdate": client.birthdate.isoformat() if client.birthdate else None,
        "client_credits": str(client.client_credits),
        "phone": client.phone,
        "address": client.address,
        "zip_code": client.zip_code,
    }


def _serialize_wallet(wallet):
    if not wallet:
        return None
    return {
        "id": wallet.pk,
        "client_user_id": wallet.client_id,
        "wallet_address": wallet.wallet_address,
        "spotbtc_balance": str(wallet.spotbtc_balance),
        "btc_balance": str(wallet.btc_balance),
        "eth_balance": str(wallet.eth_balance),
        "usdt_balance_erc20": str(wallet.usdt_balance_erc20),
        "usd_balance_trc20": str(wallet.usd_balance_trc20),
    }


def _resolve_user(identifier):
    identifier = str(identifier).strip()
    if not identifier:
        raise ValueError("identifier is required")

    query = Q(username__iexact=identifier) | Q(email__iexact=identifier)
    if identifier.isdigit():
        query |= Q(pk=int(identifier))

    user = User._default_manager.filter(query).first()
    if not user:
        raise ValueError("User not found")
    return user


def _resolve_target(model, identifier, for_update=False):
    user = _resolve_user(identifier)
    client_qs = Client._default_manager
    wallet_qs = ClientWallet._default_manager

    if model == "user":
        qs = User._default_manager
        return qs.select_for_update().get(pk=user.pk) if for_update else qs.get(pk=user.pk)

    if model == "client":
        qs = client_qs
        try:
            return (
                qs.select_for_update().get(user_id=user.pk)
                if for_update
                else qs.get(user_id=user.pk)
            )
        except Client.DoesNotExist as exc:
            raise ValueError("Client record not found") from exc

    if model == "wallet":
        qs = wallet_qs
        try:
            return (
                qs.select_for_update().get(client_id=user.pk)
                if for_update
                else qs.get(client_id=user.pk)
            )
        except ClientWallet.DoesNotExist as exc:
            raise ValueError("Client wallet not found") from exc

    raise ValueError("model must be one of: user, client, wallet")


FIELD_TYPES = {
    "user": {
        "first_name": ("string", 150),
        "last_name": ("string", 150),
        "email": ("email", 254),
        "is_active": ("bool", None),
    },
    "client": {
        "first_name": ("string", 100),
        "last_name": ("string", 100),
        "phone": ("string", 15),
        "address": ("string", None),
        "zip_code": ("string", 10),
        "client_credits": ("decimal", None),
    },
    "wallet": {
        "wallet_address": ("string", 42),
        "spotbtc_balance": ("decimal", None),
        "btc_balance": ("decimal", None),
        "eth_balance": ("decimal", None),
        "usdt_balance_erc20": ("decimal", None),
        "usd_balance_trc20": ("decimal", None),
    },
}


def _coerce_field(model, field, value):
    field_type, max_length = FIELD_TYPES[model][field]

    if field_type == "decimal":
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError(f"{field} must be a valid number")
        if not number.is_finite() or number < 0:
            raise ValueError(f"{field} must be a non-negative number")
        if number.as_tuple().exponent < -8:
            raise ValueError(f"{field} supports at most 8 decimal places")
        if number >= Decimal("1000000000000"):
            raise ValueError(f"{field} is too large")
        return number

    if field_type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        raise ValueError(f"{field} must be boolean")

    text = str(value).strip()
    if max_length is not None and len(text) > max_length:
        raise ValueError(f"{field} exceeds the maximum length of {max_length}")
    if field_type == "email":
        validate_email(text)
    if model == "wallet" and field == "wallet_address" and not text:
        raise ValueError("wallet_address cannot be empty")
    return text


def _serializable_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _current_values(obj, fields):
    return {
        field: _serializable_value(getattr(obj, field))
        for field in fields
    }


@server.tool()
def search_users(query: str = "", limit: int = 50) -> dict:
    """Search client accounts by name, email, username, or client number."""
    with db_context():
        limit = _limit(limit, 50, 100)
        qs = (
            User._default_manager
            .filter(is_client=True, is_superuser=False)
            .order_by("-id")
        )
        query = str(query or "").strip()
        if query:
            qs = qs.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(client__client_number__icontains=query)
            )

        users = [_serialize_user(user) for user in qs[:limit]]
        audit("search_users", details=f"query_length={len(query)} count={len(users)}")
        return {"count": len(users), "users": users}


@server.tool()
def get_user(identifier: str) -> dict:
    """Read a user plus the associated client profile and wallet."""
    with db_context():
        user = _resolve_user(identifier)
        client = Client._default_manager.filter(user_id=user.pk).first()
        wallet = ClientWallet._default_manager.filter(client_id=user.pk).first()
        audit("get_user", target=user.pk)
        return {
            "user": _serialize_user(user),
            "client": _serialize_client(client),
            "wallet": _serialize_wallet(wallet),
        }


@server.tool()
def get_wallet(identifier: str) -> dict:
    """Read one client's wallet by user id, username, email, or client number."""
    with db_context():
        try:
            user = _resolve_user(identifier)
        except ValueError:
            client = Client._default_manager.filter(
                Q(client_number__iexact=str(identifier).strip())
            ).select_related("user").first()
            if not client:
                raise
            user = client.user

        wallet = ClientWallet._default_manager.filter(client_id=user.pk).first()
        if not wallet:
            raise ValueError("Client wallet not found")

        audit("get_wallet", target=user.pk)
        return {
            "user": {
                "id": user.pk,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "wallet": _serialize_wallet(wallet),
        }


@server.tool()
def list_wallets(query: str = "", limit: int = 100) -> dict:
    """List client wallets, optionally filtered by user or wallet data."""
    with db_context():
        limit = _limit(limit, 100, 100)
        qs = ClientWallet._default_manager.select_related("client").filter(
            client__is_client=True,
            client__is_superuser=False,
        ).order_by("-id")
        query = str(query or "").strip()
        if query:
            qs = qs.filter(
                Q(client__username__icontains=query)
                | Q(client__email__icontains=query)
                | Q(client__first_name__icontains=query)
                | Q(client__last_name__icontains=query)
                | Q(wallet_address__icontains=query)
            )

        wallets = []
        for wallet in qs[:limit]:
            wallets.append(
                {
                    "user_id": wallet.client_id,
                    "username": wallet.client.username,
                    "email": wallet.client.email,
                    "first_name": wallet.client.first_name,
                    "last_name": wallet.client.last_name,
                    "wallet": _serialize_wallet(wallet),
                }
            )

        audit("list_wallets", details=f"count={len(wallets)}")
        return {"count": len(wallets), "wallets": wallets}


@server.tool()
def list_transactions(identifier: str, limit: int = 100) -> dict:
    """Read recent deposits and withdrawals for one client. Read-only."""
    with db_context():
        user = _resolve_user(identifier)
        limit = _limit(limit, 100, 100)

        withdrawals = list(
            Withdrawal._default_manager
            .filter(client_id=user.pk)
            .order_by("-time")[:limit]
        )
        deposits = list(
            Deposit._default_manager
            .filter(client_id=user.pk)
            .order_by("-time")[:limit]
        )

        data = []
        for item in withdrawals:
            data.append(
                {
                    "type": "withdrawal",
                    "id": item.pk,
                    "crypto_currency": item.crypto_currency,
                    "amount": str(item.amount),
                    "status": item.status,
                    "time": item.time.isoformat() if item.time else None,
                    "wallet": item.wallet_withdraw,
                    "comment": item.comment,
                }
            )
        for item in deposits:
            data.append(
                {
                    "type": "deposit",
                    "id": item.pk,
                    "crypto_currency": item.crypto_currency,
                    "amount": str(item.amount),
                    "status": item.status,
                    "time": item.time.isoformat() if item.time else None,
                    "wallet": item.wallet_withdraw,
                }
            )

        data.sort(key=lambda item: item["time"] or "", reverse=True)
        audit("list_transactions", target=user.pk, details=f"count={len(data[:limit])}")
        return {"user_id": user.pk, "transactions": data[:limit]}


@server.tool()
def propose_record_update(
    model: str,
    identifier: str,
    updates: dict[str, object],
    reason: str = "",
) -> dict:
    """
    Create a signed, short-lived update proposal.

    Supported models: user, client, wallet.
    This does not write to the database. A separate confirmation call is
    required with confirmation="CONFIRM".
    """
    require_write_access()
    model = str(model).strip().lower()
    if model not in FIELD_TYPES:
        raise ValueError("model must be one of: user, client, wallet")
    if not updates:
        raise ValueError("updates cannot be empty")

    with db_context():
        target = _resolve_target(model, identifier)
        normalized = {}

        for field, raw_value in updates.items():
            if field not in FIELD_TYPES[model]:
                raise ValueError(
                    f"Field '{field}' is not writable through MCP for model '{model}'."
                )
            normalized[field] = _coerce_field(model, field, raw_value)

        before = _current_values(target, normalized.keys())
        payload = {
            "model": model,
            "pk": target.pk,
            "fields": {
                field: _serializable_value(value)
                for field, value in normalized.items()
            },
            "before": before,
            "reason": str(reason or "")[:200],
            "issued_at": timezone.now().isoformat(),
        }
        token = signing.dumps(
            payload,
            salt=f"svex-mcp-update-{model}",
            compress=True,
        )

        audit(
            "propose_update",
            target=f"{model}:{target.pk}",
            details=f"fields={','.join(normalized.keys())} reason={payload['reason']}",
        )

        return {
            "status": "proposal_created",
            "expires_in_seconds": 600,
            "confirmation_required": "CONFIRM",
            "confirmation_token": token,
            "model": model,
            "id": target.pk,
            "before": before,
            "proposed_updates": payload["fields"],
        }


@server.tool()
def confirm_record_update(
    confirmation_token: str,
    confirmation: str,
) -> dict:
    """Apply a previously proposed database update after explicit confirmation."""
    require_write_access()

    if str(confirmation).strip() != "CONFIRM":
        raise PermissionError(
            'The confirmation argument must be exactly "CONFIRM".'
        )

    payload = None
    model = None
    last_error = None
    for candidate_model in FIELD_TYPES:
        try:
            payload = signing.loads(
                confirmation_token,
                salt=f"svex-mcp-update-{candidate_model}",
                max_age=600,
            )
            model = candidate_model
            break
        except signing.BadSignature as exc:
            last_error = exc

    if payload is None:
        raise ValueError("Invalid or expired confirmation token") from last_error

    updates = payload.get("fields") or {}
    before = payload.get("before") or {}

    with db_context(), transaction.atomic():
        target = _resolve_target(model, str(payload["pk"]), for_update=True)

        current = _current_values(target, updates.keys())
        for field, expected in before.items():
            if current.get(field) != expected:
                audit(
                    "confirm_update",
                    target=f"{model}:{payload['pk']}",
                    status="conflict",
                    details=f"field={field}",
                )
                raise ValueError(
                    f"Update cancelled: {field} changed after the proposal was created."
                )

        typed_updates = {
            field: _coerce_field(model, field, value)
            for field, value in updates.items()
        }

        for field, value in typed_updates.items():
            setattr(target, field, value)

        target.save(update_fields=list(typed_updates.keys()))

        # Keep the User and Client name fields synchronized because the
        # client-facing dashboard reads the User name.
        if model == "client":
            user_updates = {}
            if "first_name" in typed_updates:
                user_updates["first_name"] = typed_updates["first_name"]
            if "last_name" in typed_updates:
                user_updates["last_name"] = typed_updates["last_name"]
            if user_updates:
                user = User._default_manager.select_for_update().get(pk=target.user_id)
                for field, value in user_updates.items():
                    setattr(user, field, value)
                user.save(update_fields=list(user_updates.keys()))

        audit(
            "confirm_update",
            target=f"{model}:{payload['pk']}",
            details=f"fields={','.join(typed_updates.keys())} reason={payload.get('reason', '')}",
        )

        return {
            "status": "updated",
            "model": model,
            "id": target.pk,
            "updated_fields": list(typed_updates.keys()),
            "values": {
                field: _serializable_value(getattr(target, field))
                for field in typed_updates
            },
        }


security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
mcp_app = server.streamable_http_app(
    transport_security=security,
    json_response=True,
)
app = BearerTokenMiddleware(mcp_app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("SVEX_MCP_PORT", "8001")),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
