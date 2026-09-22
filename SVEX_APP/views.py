import requests
from datetime import date
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import Group
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Avg, Count, Max, Min, OuterRef, Q, Subquery, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import resolve, reverse
from django.views.generic import View
from decimal import Decimal
import qrcode
import base64
from io import BytesIO
from .decorators import client_required, manager_required

from .forms import (
    ClientSupportTicketForm,
    CustomUserChangeForm,
    DepositFormNew,
    DepositWalletNewForm,
    EditCaseForm,
    EditClientWalletForm,
    EditKYCForm,
    EditProfileManagerForm,
    Edit_Client_from_manager_Form,
    KYCForm,
    LoginForm,
    NewSignUpForm,
    SignUpForm,
    UpdateClientForm,
    WebsiteForm,
    WithdrawalForm,
    WithdrawalFormNew,
    WithdrawalMessageFormNew,
)
from .models import (
    Case,
    Client,
    ClientWallet,
    Deposit,
    DepositWallet,
    KYC,
    User,
    UserCredentials,
    Website,
    Withdrawal,
    WithdrawalMessage,
)


############################################## Basic Views ####################################################################################################


#  Project HomePage
def home(request):
    return render(request, "SVEX_APP/home.html")


#  Client HomePage
@login_required(login_url='new_login')
@client_required
def client_home(request):
    base_url = "https://api.binance.com/api/v3/ticker/24hr"
    currency_info = {
        "BTCUSDT": {"image": "BTC.png", "class_name": "Bitcoin"},
        "ETHUSDT": {"image": "ETH.png", "class_name": "Ethereum"},
        "BCHUSDT": {"image": "BCH.png", "class_name": "Bitcoin Cash"},
        "BNBUSDT": {"image": "BNB.png", "class_name": "Binance Coin"},
        "SOLUSDT": {"image": "SOL.png", "class_name": "Solana"},
        "XRPUSDT": {"image": "XRP.png", "class_name": "Ripple"},
        "LTCUSDT": {"image": "LTC.png", "class_name": "Litecoin"},
        "ADAUSDT": {"image": "ADA.png", "class_name": "Cardano"},
        "LUNAUSDT": {"image": "LUNA.png", "class_name": "Terra"},
    }
    currency_data = []

    for symbol, info in currency_info.items():
        params = {"symbol": symbol}
        response = requests.get(base_url, params=params)

        if response.status_code == 200:
            data = response.json()
            last_price = float(data["lastPrice"])
            price_change_percent = float(data["priceChangePercent"])
            image_url = f"/static/images/home-page/{info['image']}"
            class_name = info["class_name"]
            price_change_percent_display = add_plus(price_change_percent)
            currency_data.append(
                {
                    "symbol": symbol,
                    "last_price": last_price,
                    "price_change_percent": price_change_percent,
                    "price_change_percent_display": price_change_percent_display,
                    "image_url": image_url,
                    "class_name": class_name,
                }
            )
        else:
            currency_data.append(
                {
                    "symbol": symbol,
                    "error": f"Error: {response.status_code}, {response.text}",
                }
            )

    user = request.user
    user_email = user.email if user.is_authenticated else None
    return render(
        request,
        "SVEX_APP/navbar/homepage.html",
        {"currency_data": currency_data, "user_email": user_email},
    )


# Manager HomePage
@login_required(login_url='new_login')
@manager_required
def manager_home(request):
    context = {}

    total_clients = Client.objects.count()
    active_clients_count = 0
    phone_provided_percentage = 0
    if total_clients != 0:
        phone_provided_percentage = (
                Client.objects.exclude(
                    phone__isnull=True).count() / total_clients * 100
        )

    address_provided_percentage = 0
    if total_clients != 0:
        address_provided_percentage = (
                Client.objects.exclude(
                    address__isnull=True).count() / total_clients * 100
        )

    credits_summary = Client.objects.aggregate(
        average_credits=Avg("client_credits"),
        max_credits=Max("client_credits"),
        min_credits=Min("client_credits"),
    )

    context.update(
        {
            "total_clients": total_clients,
            "active_clients_count": active_clients_count,
            "phone_provided_percentage": phone_provided_percentage,
            "address_provided_percentage": address_provided_percentage,
            "credits_summary": credits_summary,
        }
    )

    total_kyc_pending = KYC.objects.filter(
        verification_status="pending").count()
    total_kyc_confirmed = KYC.objects.filter(
        verification_status="confirmed").count()
    total_kyc_cancelled = KYC.objects.filter(
        verification_status="cancelled").count()
    total_clients_with_kyc = KYC.objects.exclude(
        verification_status="pending").count()
    if total_clients > 0:
        percentage_clients_with_kyc = (
                                              total_clients_with_kyc / total_clients) * 100
    else:
        percentage_clients_with_kyc = 0  # Set percentage to 0 if total_clients is 0

    context.update(
        {
            "total_kyc_pending": total_kyc_pending,
            "total_kyc_confirmed": total_kyc_confirmed,
            "total_kyc_cancelled": total_kyc_cancelled,
            "percentage_clients_with_kyc": percentage_clients_with_kyc,
        }
    )

    total_wallets = ClientWallet.objects.count()
    total_spotbtc_balance = ClientWallet.objects.aggregate(
        total_spotbtc_balance=Sum("spotbtc_balance")
    )["total_spotbtc_balance"]
    total_btc_balance = ClientWallet.objects.aggregate(
        total_btc_balance=Sum("btc_balance")
    )["total_btc_balance"]
    total_eth_balance = ClientWallet.objects.aggregate(
        total_eth_balance=Sum("eth_balance")
    )["total_eth_balance"]
    total_usdt_balance_erc20 = ClientWallet.objects.aggregate(
        total_usdt_balance_erc20=Sum("usdt_balance_erc20")
    )["total_usdt_balance_erc20"]
    total_usd_balance_trc20 = ClientWallet.objects.aggregate(
        total_usd_balance_trc20=Sum("usd_balance_trc20")
    )["total_usd_balance_trc20"]
    context.update(
        {
            "total_wallets": total_wallets,
            "total_spotbtc_balance": total_spotbtc_balance,
            "total_btc_balance": total_btc_balance,
            "total_eth_balance": total_eth_balance,
            "total_usdt_balance_erc20": total_usdt_balance_erc20,
            "total_usd_balance_trc20": total_usd_balance_trc20,
        }
    )

    total_cases = Case.objects.count()
    total_open_cases = Case.objects.filter(case_status="Open").count()
    total_in_progress_cases = Case.objects.filter(
        case_status="In Progress").count()
    total_resolved_cases = Case.objects.filter(
        case_status="Closed-Resolved").count()
    total_pending_cases = Case.objects.exclude(
        case_status="Closed-Resolved").count()
    context.update(
        {
            "total_cases": total_cases,
            "total_open_cases": total_open_cases,
            "total_in_progress_cases": total_in_progress_cases,
            "total_resolved_cases": total_resolved_cases,
            "total_pending_cases": total_pending_cases,
        }
    )

    website_info = Website.objects.first()
    context.update({"website_info": website_info})
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


    return render(request, "SVEX_APP/manager_home.html", context)


# Custom Login with redirection


def custom_login(request):
    msg = None

    form = LoginForm(request.POST or None)
    website = Website.objects.first()
    if request.method == "POST":
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if user.is_manager:
                    return redirect("manager_home")
                elif user.is_client:
                    return redirect("home")

                else:
                    msg = "Invalid Login Credentials"
            else:
                msg = "Incorrect username or password"
        else:
            msg = "Form Error"
    return render(request, "SVEX_APP/custom_login.html", {"form": form, "msg": msg, "website": website})


def new_login(request):
    msg = None
    form = LoginForm(request.POST or None)
    website = Website.objects.first()
    if request.method == "POST":
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if user.is_manager:
                    return redirect("manager_home")
                elif user.is_client:
                    return redirect("home")

                else:
                    msg = "Invalid Login Credentials"
            else:
                msg = "Incorrect username or password"
        else:
            msg = "Form Error"
    return render(request, "SVEX_APP/auth/login.html", {"form": form, "msg": msg, "website": website})


# Logout
def custom_logout(request):
    logout(request)
    return redirect("home")


############################# Manager Dashboard ##########################################################################


# Register user from Manager


@login_required(login_url='new_login')
@manager_required
def register(request):
    msg = None
    website = Website.objects.first()
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            raw_password = form.cleaned_data["password1"]

            UserCredentials.objects.create(
                username=username, password=raw_password)

            user = form.save()

            if form.cleaned_data["is_manager"]:
                manager_group = Group.objects.get(name="Managers")
                user.groups.add(manager_group)
            elif form.cleaned_data["is_client"]:
                client_group = Group.objects.get(name="Clients")
                user.groups.add(client_group)

            msg = "User created successfully"
            return redirect("register")
        else:
            msg = "Form is not valid"
    else:
        form = SignUpForm()
    return render(request, "SVEX_APP/register.html", {"form": form, "msg": msg, "website": website})


@login_required(login_url='new_login')
@manager_required
def import_users_csv(request):
    from .csv_importer import process_user_import_csv
    results = None
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        if csv_file:
            if not csv_file.name.endswith(".csv"):
                messages.error(request, "Please upload a valid .csv file.")
            else:
                results = process_user_import_csv(csv_file)
        else:
            messages.error(request, "Please select a CSV file to upload.")

    return render(request, "SVEX_APP/import_users_csv.html", {"results": results})


# Export Users Full Name, Email, Phone, and Autologin Link as CSV
@login_required(login_url='new_login')
@manager_required
def export_users_csv(request):
    import csv
    from .models import AutoLoginToken

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="svex_users_export.csv"'
    response.write("\ufeff")  # UTF-8 BOM for Microsoft Excel compatibility

    writer = csv.writer(response)
    writer.writerow(["Full Name", "Email", "Phone", "Autologin Link"])

    clients = list(Client.objects.select_related("user").all().order_by("id"))
    processed_user_ids = set()

    for client in clients:
        user = client.user
        if user:
            processed_user_ids.add(user.pk)

        # Full Name resolution
        parts = [p.strip() for p in [client.first_name, client.last_name] if p and p.strip()]
        if parts:
            full_name = " ".join(parts)
        elif user:
            user_full = user.get_full_name().strip()
            full_name = user_full if user_full else user.username
        else:
            full_name = ""

        # Email
        email = user.email if (user and user.email) else ""

        # Phone
        phone = client.phone if client.phone else ""

        # Autologin Link
        if user:
            token_obj, _ = AutoLoginToken.objects.get_or_create(user=user)
            autologin_path = reverse("autologin", kwargs={"token": token_obj.token})
            autologin_link = request.build_absolute_uri(autologin_path)
        else:
            autologin_link = ""

        writer.writerow([full_name, email, phone, autologin_link])

    # Also include any users who don't have a Client record
    orphaned_users = User.objects.exclude(id__in=processed_user_ids).order_by("id")
    for user in orphaned_users:
        user_full = user.get_full_name().strip()
        full_name = user_full if user_full else user.username
        email = user.email or ""
        phone = ""
        token_obj, _ = AutoLoginToken.objects.get_or_create(user=user)
        autologin_path = reverse("autologin", kwargs={"token": token_obj.token})
        autologin_link = request.build_absolute_uri(autologin_path)
        writer.writerow([full_name, email, phone, autologin_link])

    return response


# View Client
@login_required(login_url='new_login')
@manager_required
def client_list(request):
    from .models import AutoLoginToken
    clients = Client.objects.select_related("user").all()
    for client in clients:
        if client.user:
            token_obj, _ = AutoLoginToken.objects.get_or_create(user=client.user)
            client.autologin_url = request.build_absolute_uri(
                reverse("autologin", kwargs={"token": token_obj.token})
            )
        else:
            client.autologin_url = ""
    context = {"clients": clients}
    return render(request, "SVEX_APP/client_list.html", context)


# Edit client
@login_required(login_url='new_login')
@manager_required
def edit_client_manager(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = Edit_Client_from_manager_Form(request.POST or None, instance=client)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Client details updated successfully.")
            return redirect("client_list")
        else:
            messages.error(request, "Form has errors. Please correct them.")

    return render(
        request, "SVEX_APP/edit_client_manager.html", {
            "form": form, "client": client}
    )


# Edit website details
@login_required(login_url='new_login')
@manager_required
def edit_website(request):
    website = Website.objects.first()
    if website:
        form = WebsiteForm(request.POST or None, instance=website)
        if request.method == "POST":
            if form.is_valid():
                form.save()
                return redirect("manager_home")
    else:
        form = WebsiteForm(request.POST or None)
        if request.method == "POST":
            if form.is_valid():
                form.save()
                return redirect("manager_home")

    return render(request, "SVEX_APP/edit_website.html", {"form": form})


# My Profile
@login_required(login_url='new_login')
@manager_required
def my_profile_manager(request):
    user = request.user
    return render(request, "SVEX_APP/my_profile_manager.html", {"user": user})


@login_required(login_url='new_login')
@manager_required
def edit_profile_manager(request):
    user = request.user
    if request.method == "POST":
        form = EditProfileManagerForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect("my_profile_manager")
    else:
        form = EditProfileManagerForm(instance=user)
    return render(request, "SVEX_APP/edit_profile_manager.html", {"form": form})


############################## KYC--Manager #################################################


@login_required(login_url='new_login')
@manager_required
def view_kyc(request):
    kyc_entries = KYC.objects.all()
    return render(request, "SVEX_APP/view_kyc.html", {"kyc_entries": kyc_entries})


# Edit KYC
@login_required(login_url='new_login')
@manager_required
def edit_kyc(request, kyc_id):
    kyc_entry = get_object_or_404(KYC, pk=kyc_id)
    if request.method == "POST":
        form = EditKYCForm(request.POST, request.FILES, instance=kyc_entry)
        if form.is_valid():
            form.save()
            return redirect("view_kyc")
    else:
        form = EditKYCForm(instance=kyc_entry)
    return render(
        request, "SVEX_APP/edit_kyc_page.html", {
            "form": form, "kyc_entry": kyc_entry}
    )


# Client Wallets --- Manager #################################################33


# View client wallets from manager
@login_required(login_url='new_login')
@manager_required
def view_client_wallet(request):
    client_wallets = ClientWallet.objects.all()
    return render(
        request, "SVEX_APP/view_client_wallet.html", {
            "client_wallets": client_wallets}
    )


# Edit the wallets
@login_required(login_url='new_login')
@manager_required
def edit_client_wallet(request, client_wallet_id):
    client_wallet = ClientWallet.objects.get(pk=client_wallet_id)

    if request.method == "POST":
        form = EditClientWalletForm(request.POST, instance=client_wallet)
        if form.is_valid():
            form.save()
            return redirect("view_client_wallet")
    else:
        form = EditClientWalletForm(instance=client_wallet)

    return render(
        request,
        "SVEX_APP/edit_client_wallet_page.html",
        {"form": form, "client_wallet": client_wallet},
    )


@login_required(login_url='new_login')
@manager_required
def deposit_wallet_view(request):
    deposit_wallets = DepositWallet.objects.all()
    return render(
        request,
        "SVEX_APP/deposit_wallet_manager.html",
        {"deposit_wallets": deposit_wallets},
    )


@login_required(login_url='new_login')
@manager_required
def update_deposit_wallet(request, pk):
    deposit_wallet = get_object_or_404(DepositWallet, pk=pk)
    if request.method == "POST":
        form = DepositWalletNewForm(request.POST, instance=deposit_wallet)
        if form.is_valid():
            form.save()
            return redirect("deposit_wallet")
    else:
        form = DepositWalletNewForm(instance=deposit_wallet)
    return render(request, "SVEX_APP/update_deposit_wallet.html", {"form": form})



@login_required(login_url='new_login')
@manager_required
def create_deposit_wallet(request):
    if request.method == "POST":
        form = DepositWalletNewForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("deposit_wallet")
    else:
        form = DepositWalletNewForm()

    return render(request, "SVEX_APP/create_deposit_wallet.html", {"form": form})


@login_required(login_url='new_login')
@manager_required
def delete_deposit_wallet(request, pk):
    deposit_wallet = get_object_or_404(DepositWallet, pk=pk)
    if request.method == "POST":
        deposit_wallet.delete()
        return redirect("deposit_wallet")
    return redirect("deposit_wallet")

@login_required(login_url='new_login')
@manager_required
def withdrawal_list(request):
    withdrawals = Withdrawal.objects.all()
    return render(
        request, "SVEX_APP/withdrawal_list.html", {"withdrawals": withdrawals}
    )



@login_required(login_url='new_login')
@manager_required
def edit_withdrawal(request, pk):
    withdrawal = get_object_or_404(Withdrawal, pk=pk)
    old_status = withdrawal.status
    old_amount = withdrawal.amount
    if request.method == "POST":
        form = WithdrawalFormNew(request.POST, instance=withdrawal)
        if form.is_valid():
            new_status = form.cleaned_data.get('status')
            new_amount = form.cleaned_data.get('amount')
            crypto_currency = withdrawal.crypto_currency
            
            client_wallet = ClientWallet.objects.get(client=withdrawal.client)
            
            # If it was canceled but now is pending/confirmed, deduct the new amount
            if old_status == 'canceled' and new_status != 'canceled':
                if crypto_currency == 'btc': client_wallet.btc_balance -= new_amount
                elif crypto_currency == 'spotbtc': client_wallet.spotbtc_balance -= new_amount
                elif crypto_currency == 'eth': client_wallet.eth_balance -= new_amount
                elif crypto_currency == 'usdt_erc20': client_wallet.usdt_balance_erc20 -= new_amount
                elif crypto_currency == 'usd_trc20': client_wallet.usd_balance_trc20 -= new_amount
            # If it was not canceled but now is canceled, refund the old amount
            elif old_status != 'canceled' and new_status == 'canceled':
                if crypto_currency == 'btc': client_wallet.btc_balance += old_amount
                elif crypto_currency == 'spotbtc': client_wallet.spotbtc_balance += old_amount
                elif crypto_currency == 'eth': client_wallet.eth_balance += old_amount
                elif crypto_currency == 'usdt_erc20': client_wallet.usdt_balance_erc20 += old_amount
                elif crypto_currency == 'usd_trc20': client_wallet.usd_balance_trc20 += old_amount
            # If it remained active but amount changed, adjust the difference
            elif old_status != 'canceled' and new_status != 'canceled' and old_amount != new_amount:
                diff = new_amount - old_amount
                if crypto_currency == 'btc': client_wallet.btc_balance -= diff
                elif crypto_currency == 'spotbtc': client_wallet.spotbtc_balance -= diff
                elif crypto_currency == 'eth': client_wallet.eth_balance -= diff
                elif crypto_currency == 'usdt_erc20': client_wallet.usdt_balance_erc20 -= diff
                elif crypto_currency == 'usd_trc20': client_wallet.usd_balance_trc20 -= diff
                
            client_wallet.save()
            form.save()
            return redirect("withdrawal_list")
    else:
        form = WithdrawalFormNew(instance=withdrawal)
    return render(request, "SVEX_APP/update_withdrawal.html", {"form": form})

@login_required(login_url='new_login')
@manager_required
def create_withdrawal_manager(request):
    if request.method == "POST":
        form = WithdrawalFormNew(request.POST)
        if form.is_valid():
            withdrawal = form.save(commit=False)
            if withdrawal.status != 'canceled':
                client_wallet = ClientWallet.objects.get(client=withdrawal.client)
                crypto_currency = withdrawal.crypto_currency
                amount = withdrawal.amount
                if crypto_currency == 'btc': client_wallet.btc_balance -= amount
                elif crypto_currency == 'spotbtc': client_wallet.spotbtc_balance -= amount
                elif crypto_currency == 'eth': client_wallet.eth_balance -= amount
                elif crypto_currency == 'usdt_erc20': client_wallet.usdt_balance_erc20 -= amount
                elif crypto_currency == 'usd_trc20': client_wallet.usd_balance_trc20 -= amount
                client_wallet.save()
            withdrawal.save()
            return redirect('withdrawal_list')
    else:
        form = WithdrawalFormNew()  
    return render(request, "SVEX_APP/create_withdrawal.html", {"form": form})

@login_required(login_url='new_login')
@manager_required
def delete_withdrawal(request, pk):
    withdrawal = get_object_or_404(Withdrawal, pk=pk)
    if request.method == "POST":
        if withdrawal.status != 'canceled':
            client_wallet = ClientWallet.objects.get(client=withdrawal.client)
            crypto_currency = withdrawal.crypto_currency
            amount = withdrawal.amount
            if crypto_currency == 'btc': client_wallet.btc_balance += amount
            elif crypto_currency == 'spotbtc': client_wallet.spotbtc_balance += amount
            elif crypto_currency == 'eth': client_wallet.eth_balance += amount
            elif crypto_currency == 'usdt_erc20': client_wallet.usdt_balance_erc20 += amount
            elif crypto_currency == 'usd_trc20': client_wallet.usd_balance_trc20 += amount
            client_wallet.save()
        withdrawal.delete()
        return redirect("withdrawal_list")
    return render(request, "SVEX_APP/delete_withdrawal.html", {"withdrawal": withdrawal})

def deposit_list(request):
    deposits = Deposit.objects.all()
    return render(request, "SVEX_APP/deposit_list.html", {"deposits": deposits})



@login_required(login_url='new_login')
@manager_required
def edit_deposit(request, pk):
    deposit = get_object_or_404(Deposit, pk=pk)
    old_status = deposit.status
    old_amount = deposit.amount
    if request.method == "POST":
        form = DepositFormNew(request.POST, instance=deposit)
        if form.is_valid():
            new_status = form.cleaned_data.get('status')
            new_amount = form.cleaned_data.get('amount')
            crypto_currency = deposit.crypto_currency
            
            client_wallet = ClientWallet.objects.get(client=deposit.client)
            
            if old_status == 'canceled' and new_status != 'canceled':
                if crypto_currency == 'btc': client_wallet.btc_balance += new_amount
                elif crypto_currency == 'spotbtc': client_wallet.spotbtc_balance += new_amount
                elif crypto_currency == 'eth': client_wallet.eth_balance += new_amount
                elif crypto_currency == 'usdt_erc20': client_wallet.usdt_balance_erc20 += new_amount
                elif crypto_currency == 'usd_trc20': client_wallet.usd_balance_trc20 += new_amount
            elif old_status != 'canceled' and new_status == 'canceled':
                if crypto_currency == 'btc': client_wallet.btc_balance -= old_amount
                elif crypto_currency == 'spotbtc': client_wallet.spotbtc_balance -= old_amount
                elif crypto_currency == 'eth': client_wallet.eth_balance -= old_amount
                elif crypto_currency == 'usdt_erc20': client_wallet.usdt_balance_erc20 -= old_amount
                elif crypto_currency == 'usd_trc20': client_wallet.usd_balance_trc20 -= old_amount
            elif old_status != 'canceled' and new_status != 'canceled' and old_amount != new_amount:
                diff = new_amount - old_amount
                if crypto_currency == 'btc': client_wallet.btc_balance += diff
                elif crypto_currency == 'spotbtc': client_wallet.spotbtc_balance += diff
                elif crypto_currency == 'eth': client_wallet.eth_balance += diff
                elif crypto_currency == 'usdt_erc20': client_wallet.usdt_balance_erc20 += diff
                elif crypto_currency == 'usd_trc20': client_wallet.usd_balance_trc20 += diff
                
            client_wallet.save()
            form.save()
            return redirect("deposit_list")
    else:
        form = DepositFormNew(instance=deposit)
    return render(request, "SVEX_APP/edit_deposit.html", {"form": form})

@login_required(login_url='new_login')
@manager_required
def create_deposit(request):
    if request.method == "POST":
        form = DepositFormNew(request.POST)
        if form.is_valid():
            deposit = form.save(commit=False)
            if deposit.status != 'canceled':
                client_wallet = ClientWallet.objects.get(client=deposit.client)
                crypto_currency = deposit.crypto_currency
                amount = deposit.amount
                if crypto_currency == 'btc': client_wallet.btc_balance += amount
                elif crypto_currency == 'spotbtc': client_wallet.spotbtc_balance += amount
                elif crypto_currency == 'eth': client_wallet.eth_balance += amount
                elif crypto_currency == 'usdt_erc20': client_wallet.usdt_balance_erc20 += amount
                elif crypto_currency == 'usd_trc20': client_wallet.usd_balance_trc20 += amount
                client_wallet.save()
            deposit.save()
            return redirect('deposit_list')
    else:
        form = DepositFormNew()  
    return render(request, "SVEX_APP/create_deposit.html", {"form": form})

@login_required(login_url='new_login')
@manager_required
def delete_deposit(request, pk):
    deposit = get_object_or_404(Deposit, pk=pk)
    if request.method == "POST":
        if deposit.status != 'canceled':
            client_wallet = ClientWallet.objects.get(client=deposit.client)
            crypto_currency = deposit.crypto_currency
            amount = deposit.amount
            if crypto_currency == 'btc': client_wallet.btc_balance -= amount
            elif crypto_currency == 'spotbtc': client_wallet.spotbtc_balance -= amount
            elif crypto_currency == 'eth': client_wallet.eth_balance -= amount
            elif crypto_currency == 'usdt_erc20': client_wallet.usdt_balance_erc20 -= amount
            elif crypto_currency == 'usd_trc20': client_wallet.usd_balance_trc20 -= amount
            client_wallet.save()
        deposit.delete()
        return redirect("deposit_list")
    return render(request, "SVEX_APP/delete_deposit.html", {"deposit": deposit})

def withdrawal_message_list(request):
    withdrawal_messages = WithdrawalMessage.objects.all()
    return render(
        request,
        "SVEX_APP/withdrawal_message_list.html",
        {"withdrawal_messages": withdrawal_messages},
    )


@login_required(login_url='new_login')
@manager_required
def edit_withdrawal_message(request, pk):
    withdrawal_message = get_object_or_404(WithdrawalMessage, pk=pk)
    if request.method == "POST":
        form = WithdrawalMessageFormNew(
            request.POST, instance=withdrawal_message)
        if form.is_valid():
            form.save()
            return redirect("withdrawal_message_list")
    else:
        form = WithdrawalMessageFormNew(instance=withdrawal_message)
    return render(request, "SVEX_APP/update_withdrawal_message.html", {"form": form})


######################################### Client Side #######################################################################


# Client Sign up


def register_new(request):
    msg = None
    website = Website.objects.first()
    if request.method == "POST":
        form = NewSignUpForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            raw_password = form.cleaned_data["password1"]
            UserCredentials.objects.create(
                username=username, password=raw_password)
            user = form.save()
            client_group = Group.objects.get(name="Clients")
            user.groups.add(client_group)

            msg = "User created successfully"
            return redirect("new_login")
        else:
            msg = "Invalid Credentials"
    else:
        form = NewSignUpForm()
    return render(request, "SVEX_APP/auth/register.html", {"form": form, "msg": msg, "website": website})


def forgot_password(request):
    return render(request, "SVEX_APP/auth/forgot-password.html")

@login_required(login_url='new_login')
def change_email_address(request):
    user = request.user

    if request.method == "POST":
        form = CustomUserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile was successfully updated!")
            return redirect("client_profile")
    else:
        form = CustomUserChangeForm(instance=user)

    return render(request, "SVEX_APP/edit_profile_client.html", {"form": form})


# Client Profile

@login_required(login_url='new_login')
def client_profile(request):
    user = request.user
    client = Client.objects.get(user=user)
    context = {"client": client}
    return render(request, "SVEX_APP/client_profile.html", context)

@login_required(login_url='new_login')
def my_account(request):
    user = request.user
    return render(request, "SVEX_APP/my_account.html", {"user": user})

class EditClientProfileView(View):
    def get(self, request):
        client = Client.objects.get(user=request.user)
        form = UpdateClientForm(instance=client)
        return render(request, "SVEX_APP/update_client_profile.html", {"form": form})

    def post(self, request):
        client = Client.objects.get(user=request.user)
        form = UpdateClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile was successfully updated!")
            return redirect("client_profile")
        else:
            messages.error(
                request, "Failed to update your profile. Please check the form data."
            )
            return render(
                request, "SVEX_APP/update_client_profile.html", {"form": form}
            )


# kyc view
@login_required(login_url='new_login')
def kyc_submit(request):
    user = request.user

    try:
        kyc_entry = KYC.objects.get(client=user)
        form = KYCForm(instance=kyc_entry)

        return render(request, "SVEX_APP/kyc_verification.html", {"form": form})

    except KYC.DoesNotExist:
        if request.method == "POST":
            form = KYCForm(request.POST, request.FILES)
            if form.is_valid():
                kyc_instance = form.save(commit=False)
                kyc_instance.client = user
                kyc_instance.save()
                return redirect("kyc_status")

        else:
            form = KYCForm()

        return render(request, "SVEX_APP/kyc_verification.html", {"form": form})


@login_required(login_url='new_login')
def kyc_status(request):
    user = request.user
    kyc = KYC.objects.filter(client=user).first()

    if not kyc:
        return redirect("kyc_verification")

    context = {
        "kyc": kyc,
    }
    return render(request, "SVEX_APP/kyc_status.html", context)


# Client Wallets
@login_required(login_url='new_login')
def wallet_balance(request):
    user = request.user

    if hasattr(user, "client"):
        try:
            client_wallet = ClientWallet.objects.get(client=user)
        except ClientWallet.DoesNotExist:
            client_wallet = ClientWallet.objects.create(client=user)

        context = {
            "spotbtc_balance": client_wallet.spotbtc_balance,
            "btc_balance": client_wallet.btc_balance,
            "eth_balance": client_wallet.eth_balance,
            "usdt_balance_erc20": client_wallet.usdt_balance_erc20,
            "usd_balance_trc20": client_wallet.usd_balance_trc20,
        }

        return render(request, "SVEX_APP/my_wallets.html", context)
    else:
        return HttpResponse("You need to create a client profile first.")


@login_required(login_url='new_login')
def deposit_wallet(request):
    try:
        deposit_wallet_instance = DepositWallet.objects.get(user=request.user)
        context = {"deposit_wallet": deposit_wallet_instance}
    except DepositWallet.DoesNotExist:
        context = {}

    return render(request, "SVEX_APP/deposit_wallet.html", context)

@login_required(login_url='new_login')
def withdraw(request):
    user = request.user
    client_wallet = ClientWallet.objects.get(client=user)
    website = Website.objects.first()
    withdrawal_denied_message = None

    withdrawal_message = WithdrawalMessage.objects.filter(user=user).first()
    if withdrawal_message and not withdrawal_message.can_withdraw:
        withdrawal_denied_message = withdrawal_message.message

    if request.method == "POST":
        form = WithdrawalForm(request.POST)
        if form.is_valid():
            crypto_currency = form.cleaned_data["crypto_currency"]
            amount = form.cleaned_data["amount"]
            wallet_withdraw = form.cleaned_data["wallet_withdraw"]

            if withdrawal_message and not withdrawal_message.can_withdraw:
                return render(
                    request,
                    "SVEX_APP/wallets/withdraw.html",
                    {"message": withdrawal_message.message, "website": website},
                )

            if crypto_currency == "btc" and amount <= client_wallet.btc_balance:
                withdrawal = form.save(commit=False)
                withdrawal.client = user
                withdrawal.save()
                client_wallet.btc_balance -= amount
                client_wallet.save()
                return redirect("wallets_withdraw")

            elif crypto_currency == "eth" and amount <= client_wallet.eth_balance:
                withdrawal = form.save(commit=False)
                withdrawal.client = user
                withdrawal.save()
                client_wallet.eth_balance -= amount
                client_wallet.save()
                return redirect("wallets_withdraw")

            elif (
                    crypto_currency == "usdt_erc20"
                    and amount <= client_wallet.usdt_balance_erc20
            ):
                withdrawal = form.save(commit=False)
                withdrawal.client = user
                withdrawal.save()
                client_wallet.usdt_balance_erc20 -= amount
                client_wallet.save()
                return redirect("wallets_withdraw")

            elif (
                    crypto_currency == "usd_trc20"
                    and amount <= client_wallet.usd_balance_trc20
            ):
                withdrawal = form.save(commit=False)
                withdrawal.client = user
                withdrawal.save()
                client_wallet.usd_balance_trc20 -= amount
                client_wallet.save()
                return redirect("wallets_withdraw")

            else:
                form.add_error(None, "Insufficient balance")
    else:
        form = WithdrawalForm()

    context = {
        "message": withdrawal_message.message if withdrawal_message else None,
        "withdrawal_denied_message": withdrawal_denied_message,
        "form": form,
        "wallet": client_wallet,
        "website": website,
    }
    return render(request, "SVEX_APP/wallets/withdraw.html", context)

@login_required(login_url='new_login')
def withdrawal_success(request):
    user = request.user
    withdrawal_message = WithdrawalMessage.objects.get(user=user)
    return render(
        request,
        "SVEX_APP/withdrawal_success.html",
        {"withdrawal_message": withdrawal_message},
    )

@login_required(login_url='new_login')
def transaction_history(request):
    user = request.user
    withdrawals = Withdrawal.objects.filter(client=user)
    deposits = Deposit.objects.filter(client=user)
    return render(
        request,
        "SVEX_APP/transaction_history.html",
        {"withdrawals": withdrawals, "deposits": deposits},
    )


################################ Support Ticket #######################################################################################


@login_required(login_url='new_login')
@client_required
def create_support_ticket(request):
    if request.method == "POST":
        form = ClientSupportTicketForm(request.POST)
        if form.is_valid():
            support_ticket = form.save(commit=False)
            support_ticket.case_client = request.user
            support_ticket.save()
            messages.success(request, "Ticket created successfully.")
            return redirect("dashboard_support_tickets")
        else:
            messages.error(
                request, "Please make sure all fields are filled correctly.")
            return redirect("dashboard_support_tickets")
    else:
        form = ClientSupportTicketForm()
    return render(
        request, "SVEX_APP/dashboard/dashboard_support_tickets.html", {
            "form": form}
    )


@login_required(login_url='new_login')
@client_required
def ticket_created_successfully(request):
    success_message = (
        "Your support ticket has been created successfully. We will address it shortly."
    )

    return render(
        request,
        "SVEX_APP/ticket_created_successfully.html",
        {"success_message": success_message},
    )

@login_required(login_url='new_login')
def dashboard(request):
    client_wallet = ClientWallet.objects.get(client=request.user)
    website = Website.objects.first()
    
    # Get prices from Binance API
    from .binance_api import get_crypto_prices
    from decimal import Decimal
    prices = get_crypto_prices(timeout=4)
    btc_price = prices.get('btc_price', Decimal('0.0'))
    eth_price = prices.get('eth_price', Decimal('0.0'))
    usdt_price = prices.get('usdt_price', Decimal('1.0'))
    
    btc_usd_value = client_wallet.btc_balance * btc_price
    spotbtc_usd_value = client_wallet.spotbtc_balance * Decimal('1.0')
    eth_usd_value = client_wallet.eth_balance * eth_price
    usdt_erc20_usd_value = client_wallet.usdt_balance_erc20 * usdt_price
    usd_trc20_usd_value = client_wallet.usd_balance_trc20 * usdt_price
    total_usd_value = btc_usd_value + spotbtc_usd_value + eth_usd_value + usdt_erc20_usd_value + usd_trc20_usd_value

    context = {
        "user": request.user,
        "wallet": client_wallet,
        "website": website,
        "btc_price": btc_price,
        "btc_usd_value": btc_usd_value,
        "total_usd_value": total_usd_value,
    }
    return render(request, "SVEX_APP/dashboard/dashboard.html", context)

@login_required(login_url='new_login')
def dashboard_settings(request):
    current_path = resolve(request.path_info).url_name
    show_back_button = not current_path.endswith("dashboard")
    client_wallet = ClientWallet.objects.get(client=request.user)
    website = Website.objects.first()
    return render(
        request,
        "SVEX_APP/dashboard/dashboard_settings.html",
        {
            "show_back_button": show_back_button,
            "user": request.user,
            "wallet": client_wallet,
            "website": website,
        },
    )

@login_required(login_url='new_login')
def dashboard_support_tickets(request):
    client_wallet = ClientWallet.objects.get(client=request.user)
    website = Website.objects.first()
    context = {
        "user_email": request.user.email if request.user.is_authenticated else None,
        "wallet": client_wallet,
        "website": website,
    }
    return render(request, "SVEX_APP/dashboard/dashboard_support_tickets.html", context)

@login_required(login_url='new_login')
def get_tickets(request):
    query_param = request.GET.get("q")
    user_tickets = Case.objects.filter(case_client=request.user).order_by("id")

    if query_param:
        user_tickets = user_tickets.filter(
            Q(id__icontains=query_param)
            | Q(case_category__icontains=query_param)
            | Q(case_notes__icontains=query_param)
            | Q(case_status__icontains=query_param)
            | Q(case_subject__icontains=query_param)
        )

    items_per_page = int(request.GET.get("items_per_page", 10))
    paginator = Paginator(user_tickets, items_per_page)
    page_number = request.GET.get("page")

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    user_tickets_slice = page_obj.object_list

    tickets_data = [
        {
            "id": ticket.id,
            "subject": ticket.case_subject,
            "category": ticket.case_category,
            "status": ticket.case_status,
            "status_class": ticket.case_status.lower().replace(" ", ""),
            "notes": ticket.case_notes,
            "created_at": ticket.case_created_at,
        }
        for ticket in user_tickets_slice
    ]

    return JsonResponse(
        {
            "tickets": tickets_data,
            "total_pages": paginator.num_pages,
            "current_page": page_obj.number,
            "total_entries": paginator.count,
            "items_per_page": items_per_page,
        }
    )

@login_required(login_url='new_login')
def get_withdraws(request):
    query_param = request.GET.get("q")
    user_withdraws = Withdrawal.objects.filter(client=request.user)
    if query_param:
        user_withdraws = user_withdraws.filter(
            Q(id__icontains=query_param)
            | Q(crypto_currency__icontains=query_param)
            | Q(wallet_withdraw__icontains=query_param)
            | Q(comment__icontains=query_param)
            | Q(amount__icontains=query_param)
            | Q(status__icontains=query_param)
        )

    items_per_page = int(request.GET.get("items_per_page", 10))
    paginator = Paginator(user_withdraws, items_per_page)
    page_number = request.GET.get("page")

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    user_withdraws = page_obj.object_list

    withdraw_data = [
        {
            "id": withdraw.id,
            "crypto": withdraw.crypto_currency,
            "wallet_withdraw": withdraw.wallet_withdraw,
            "status": withdraw.status.upper(),
            "status_class": withdraw.status.lower().replace(" ", ""),
            "amount": withdraw.amount,
            "comment": withdraw.comment,
            "created_at": (
                withdraw.time.strftime(
                    "%Y %b %d %H %M") if withdraw.time else None
            ),
        }
        for withdraw in user_withdraws
    ]

    return JsonResponse(
        {
            "withdraws": withdraw_data,
            "total_pages": paginator.num_pages,
            "current_page": page_obj.number,
            "total_entries": paginator.count,
            "items_per_page": items_per_page,
        }
    )

@login_required(login_url='new_login')
def dashboard_orders(request):
    client_wallet = ClientWallet.objects.get(client=request.user)
    website = Website.objects.first()
    return render(
        request,
        "SVEX_APP/dashboard/dashboard_orders.html",
        {"user_email": request.user.email if request.user.is_authenticated else None, "wallet": client_wallet, "website": website},
    )


@login_required(login_url='new_login')
def dashboard_history(request):
    client_wallet = ClientWallet.objects.get(client=request.user)
    website = Website.objects.first()
    user_deposits = Deposit.objects.filter(client=request.user)
    user_withdrawals = Withdrawal.objects.filter(client=request.user)
    
    transactions = []
    for d in user_deposits:
        transactions.append({
            'type': 'deposit',
            'amount': d.amount,
            'crypto_currency': d.crypto_currency.upper(),
            'status': d.status,
            'time': d.time,
            'address': d.wallet_withdraw,
        })
    for w in user_withdrawals:
        transactions.append({
            'type': 'withdrawal',
            'amount': w.amount,
            'crypto_currency': w.crypto_currency.upper(),
            'status': w.status,
            'time': w.time,
            'address': w.wallet_withdraw,
            'comment': w.comment if hasattr(w, 'comment') else ''
        })
        
    # Sort by time descending
    transactions.sort(key=lambda x: x['time'], reverse=True)

    return render(
        request,
        "SVEX_APP/dashboard/dashboard_funds_history.html",
        {
            "user_email": request.user.email if request.user.is_authenticated else None,
            "wallet": client_wallet,
            "website": website,
            "transactions": transactions,
        },
    )

@login_required(login_url='new_login')
def dashboard_kyc(request):
    user = request.user
    client_wallet = ClientWallet.objects.get(client=user)
    website = Website.objects.first()

    try:
        kyc_entry = KYC.objects.get(client=user)
        context = {
            "user_email": request.user.email if request.user.is_authenticated else None,
            "wallet": client_wallet,
            "message": "You have already submitted your KYC information, if you want to update it, please contact us.",
            "kyc_status": kyc_entry.verification_status,
            "website": website,
        }
        return render(request, "SVEX_APP/dashboard/dashboard_kyc.html", context)
    except KYC.DoesNotExist:
        if request.method == "POST":
            form = KYCForm(request.POST, request.FILES)
            if form.is_valid():
                kyc_instance = form.save(commit=False)
                kyc_instance.client = user
                kyc_instance.save()
                return redirect("dashboard")
            else:
                print(f"Form errors: {form.errors}")
        else:
            form = KYCForm()

        context = {
            "user_email": request.user.email if request.user.is_authenticated else None,
            "wallet": client_wallet,
            "form": form,
            "current_date": date.today(),
            "website": website,
        }
        return render(request, "SVEX_APP/dashboard/dashboard_kyc.html", context)

@login_required(login_url='new_login')
def exchange(request):
    website = Website.objects.first()
    client_wallet = ClientWallet.objects.get(client=request.user)
    user_email = request.user.email if request.user.is_authenticated else None

    return render(
        request,
        "SVEX_APP/navbar/exchange.html",
        {"user_email": user_email, "website": website, "wallet": client_wallet},
    )


def faq(request):
    website = Website.objects.first()
    user_email = request.user.email if request.user.is_authenticated else None

    context = {
        "user_email": user_email,
        "website": website,
    }
    return render(request, "SVEX_APP/navbar/faq.html", context)


def add_plus(value):
    return f"+{value}" if value >= 0 else value


def home_page(request):
    base_url = "https://api.binance.com/api/v3/ticker/24hr"
    currency_info = {
        "BTCUSDT": {"image": "BTC.png", "class_name": "Bitcoin"},
        "ETHUSDT": {"image": "ETH.png", "class_name": "Ethereum"},
        "BCHUSDT": {"image": "BCH.png", "class_name": "Bitcoin Cash"},
        "BNBUSDT": {"image": "BNB.png", "class_name": "Binance Coin"},
        "SOLUSDT": {"image": "SOL.png", "class_name": "Solana"},
        "XRPUSDT": {"image": "XRP.png", "class_name": "Ripple"},
        "LTCUSDT": {"image": "LTC.png", "class_name": "Litecoin"},
        "ADAUSDT": {"image": "ADA.png", "class_name": "Cardano"},
        "LUNAUSDT": {"image": "LUNA.png", "class_name": "Terra"},
    }
    currency_data = []

    for symbol, info in currency_info.items():
        params = {"symbol": symbol}
        response = requests.get(base_url, params=params)

        if response.status_code == 200:
            data = response.json()
            last_price = float(data["lastPrice"])
            price_change_percent = float(data["priceChangePercent"])
            image_url = f"/static/images/home-page/{info['image']}"
            class_name = info["class_name"]
            price_change_percent_display = add_plus(price_change_percent)
            currency_data.append(
                {
                    "symbol": symbol,
                    "last_price": last_price,
                    "price_change_percent": price_change_percent,
                    "price_change_percent_display": price_change_percent_display,
                    "image_url": image_url,
                    "class_name": class_name,
                }
            )
        else:
            currency_data.append(
                {
                    "symbol": symbol,
                    "error": f"Error: {response.status_code}, {response.text}",
                }
            )

    # client_wallet = ClientWallet.objects.get(client=request.user)
    website = Website.objects.first()
    user_email = request.user.email if request.user.is_authenticated else None

    return render(
        request,
        "SVEX_APP/navbar/homepage.html",
        {
            "currency_data": currency_data,
            "user_email": user_email,
            # "wallet": client_wallet,
            "website": website,
        },
    )


@login_required(login_url='new_login')
def wallets_index(request):
    client_wallet = ClientWallet.objects.get(client=request.user)
    website = Website.objects.first()
    
    # Get prices from Binance API
    from .binance_api import get_crypto_prices
    prices = get_crypto_prices(timeout=4)
    btc_price = prices['btc_price']
    eth_price = prices['eth_price']
    
    btc_usd_value = client_wallet.btc_balance * btc_price
    spotbtc_usd_value = client_wallet.spotbtc_balance * Decimal('1.0')
    eth_usd_value = client_wallet.eth_balance * eth_price
    usdt_price = prices.get('usdt_price', Decimal('1.0'))
    usdt_erc20_usd_value = client_wallet.usdt_balance_erc20 * usdt_price
    usd_trc20_usd_value = client_wallet.usd_balance_trc20 * usdt_price
    total_usd_value = btc_usd_value + spotbtc_usd_value + eth_usd_value + usdt_erc20_usd_value + usd_trc20_usd_value
    
    context = {
        "user_email": request.user.email if request.user.is_authenticated else None,
        "wallet": client_wallet,
        "website": website,
        "btc_price": btc_price,
        "eth_price": eth_price,
        "btc_usd_value": btc_usd_value,
        "spotbtc_usd_value": spotbtc_usd_value,
        "eth_usd_value": eth_usd_value,
        "usdt_price": usdt_price,
        "usdt_erc20_usd_value": usdt_erc20_usd_value,
        "usd_trc20_usd_value": usd_trc20_usd_value,
        "total_usd_value": total_usd_value,
    }
    
    return render(request, "SVEX_APP/wallets/index.html", context)

@login_required(login_url='new_login')
def wallets_transfer(request):
    client_wallet = ClientWallet.objects.get(client=request.user)
    website = Website.objects.first()
    
    # Get prices from Binance API
    from .binance_api import get_crypto_prices
    from decimal import Decimal
    prices = get_crypto_prices(timeout=4)
    btc_price = prices.get('btc_price', Decimal('0.0'))
    eth_price = prices.get('eth_price', Decimal('0.0'))
    usdt_price = prices.get('usdt_price', Decimal('1.0'))
    
    return render(
        request,
        "SVEX_APP/wallets/transfer.html",
        {
            "user_email": request.user.email if request.user.is_authenticated else None,
            "wallet": client_wallet,
            "website": website,
            "btc_price": btc_price,
            "eth_price": eth_price,
            "usdt_price": usdt_price,
        },
    )

@login_required(login_url='new_login')
def wallets_withdraw(request):
    user = request.user
    client_wallet, _ = ClientWallet.objects.get_or_create(client=user)
    website = Website.objects.first()
    withdrawal_denied_message = None
    success_message = None
    custom_message = None

    # Get prices from Binance API
    from .binance_api import get_crypto_prices
    prices = get_crypto_prices(timeout=4)
    btc_price = prices['btc_price']
    eth_price = prices['eth_price']
    usdt_price = prices.get('usdt_price', Decimal('1.0'))

    withdrawal_message = WithdrawalMessage.objects.filter(user=user).first()
    if withdrawal_message and not withdrawal_message.can_withdraw:
        withdrawal_denied_message = withdrawal_message.message
        return render(
            request,
            "SVEX_APP/wallets/withdraw.html",
            {
                "withdrawal_denied_message": withdrawal_denied_message,
                "website": website,
                "btc_price": btc_price,
                "eth_price": eth_price,
                "wallet": client_wallet,
            },
        )

    if request.method == "POST":
        form = WithdrawalForm(request.POST)
        if form.is_valid():
            success_message = "Your withdrawal request has been submitted successfully. We will process it shortly."
            crypto_currency = form.cleaned_data["crypto_currency"]
            amount = form.cleaned_data["amount"]
            wallet_withdraw = form.cleaned_data["wallet_withdraw"]

            if crypto_currency == "btc" and amount <= client_wallet.btc_balance:
                withdrawal = form.save(commit=False)
                withdrawal.client = user
                withdrawal.save()
                client_wallet.btc_balance -= amount
                client_wallet.save()

            elif crypto_currency == "spotbtc" and amount <= client_wallet.spotbtc_balance:
                withdrawal = form.save(commit=False)
                withdrawal.client = user
                withdrawal.save()
                client_wallet.spotbtc_balance -= amount
                client_wallet.save()

            elif crypto_currency == "eth" and amount <= client_wallet.eth_balance:
                withdrawal = form.save(commit=False)
                withdrawal.client = user
                withdrawal.save()
                client_wallet.eth_balance -= amount
                client_wallet.save()

            elif (
                    crypto_currency == "usdt_erc20"
                    and amount <= client_wallet.usdt_balance_erc20
            ):
                print("Here in the usdt_erc20")
                withdrawal = form.save(commit=False)
                withdrawal.client = user
                withdrawal.save()
                client_wallet.usdt_balance_erc20 -= amount
                client_wallet.save()

            elif (
                    crypto_currency == "usd_trc20"
                    and amount <= client_wallet.usd_balance_trc20
            ):
                print("Here in the usd_trc20")
                withdrawal = form.save(commit=False)
                withdrawal.client = user
                withdrawal.save()
                client_wallet.usd_balance_trc20 -= amount
                client_wallet.save()

            else:
                custom_message = "Insufficient balance"
                success_message = None
    else:
        form = WithdrawalForm()

    context = {
        "success_message": success_message if success_message else None,
        "custom_message": custom_message if custom_message else None,
        "withdrawal_denied_message": withdrawal_denied_message,
        "form": form,
        "user_email": request.user.email if request.user.is_authenticated else None,
        "wallet": client_wallet,
        "website": website,
        "btc_price": btc_price,
        "eth_price": eth_price,
        "btc_balance_usd": client_wallet.btc_balance * btc_price,
        "spotbtc_balance_usd": client_wallet.spotbtc_balance * Decimal('1.0'),
        "eth_balance_usd": client_wallet.eth_balance * eth_price,
        "usdt_price": usdt_price,
        "usdt_erc20_balance_usd": client_wallet.usdt_balance_erc20 * usdt_price,
        "usd_trc20_balance_usd": client_wallet.usd_balance_trc20 * usdt_price,
    }
    return render(request, "SVEX_APP/wallets/withdraw.html", context)


@login_required(login_url='new_login')
def wallets_deposit(request):
    user = request.user
    client_wallet = ClientWallet.objects.get(client=user)
    website = Website.objects.first()
    success_message = None
    custom_message = None

    qr_code_base64 = None
    if client_wallet.wallet_address:
        qr = qrcode.make(client_wallet.wallet_address)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    if request.method == "POST":
        form = DepositFormNew(request.POST)
        if form.is_valid():
            crypto_currency = form.cleaned_data["crypto_currency"]
            amount = form.cleaned_data["amount"]

            form.instance.client = user
            form.instance.status = Deposit.PENDING
            try:
                deposit = form.save()
                if crypto_currency == "btc":
                    client_wallet.btc_balance += amount
                elif crypto_currency == "eth":
                    client_wallet.eth_balance += amount
                elif crypto_currency == "usdt_erc20":
                    client_wallet.usdt_balance_erc20 += amount
                elif crypto_currency == "usd_trc20":
                    client_wallet.usd_balance_trc20 += amount
                else:
                    custom_message = "Invalid cryptocurrency selected"
                    deposit.delete()
                client_wallet.save()

                success_message = (
                    "Your deposit request has been submitted successfully."
                )
                messages.success(request, success_message)
                return redirect("deposit_success_url")
            except Exception as e:
                custom_message = f"An error occurred: {str(e)}"
        else:
            custom_message = "Invalid form submission"
    else:
        form = DepositFormNew()

    context = {
        "success_message": success_message,
        "custom_message": custom_message,
        "form": form,
        "user_email": user.email if user.is_authenticated else None,
        "wallet": client_wallet,
        "website": website,
        "wallet_qr": qr_code_base64,
    }

    return render(request, "SVEX_APP/wallets/deposit.html", context)


@login_required(login_url='new_login')
@manager_required
def open_ticket_list(request):
    open_tickets = Case.objects.filter(case_status="Open")
    return render(
        request, "SVEX_APP/open_ticket_list.html", {
            "open_tickets": open_tickets}
    )


@login_required(login_url='new_login')
@manager_required
def all_tickets(request):
    all_cases = Case.objects.all()
    return render(request, "SVEX_APP/all_tickets.html", {"all_cases": all_cases})


def test(request):
    return render(request, "SVEX_APP/dashboard/layout.html")


@login_required(login_url='new_login')
@manager_required
def closed_tickets(request):
    closed_statuses = [
        "Closed-Resolved",
        "Closed-NotResolved",
        "Closed-Spam",
        "Closed-Lost",
    ]
    closed_cases = Case.objects.filter(case_status__in=closed_statuses)
    return render(
        request, "SVEX_APP/closed_tickets.html", {"closed_cases": closed_cases}
    )


def test_2(request):
    return render(request, "SVEX_APP/wallets/layout.html")


@login_required(login_url='new_login')
@manager_required
def tickets_in_progress(request):
    in_progress_cases = Case.objects.filter(
        case_status__in=["In Progress", "Responded", "Escalated", "On Hold"]
    )
    return render(
        request,
        "SVEX_APP/ticket_in_progress.html",
        {"in_progress_cases": in_progress_cases},
    )


def test_3(request):
    return render(request, "SVEX_APP/auth/layout.html")


# Edit Tickets
@login_required(login_url='new_login')
@manager_required
def edit_case(request, case_id):
    case = get_object_or_404(Case, pk=case_id)
    if request.method == "POST":
        form = EditCaseForm(request.POST, instance=case)
        if form.is_valid():
            form.save()
            return redirect("all_tickets")
    else:
        form = EditCaseForm(instance=case)
    return render(request, "SVEX_APP/edit_case_manager.html", {"form": form})


def buy_crypto(request):
    website = Website.objects.first()
    context = {
        "user": request.user,
        "website": website,
    }
    return render(request, "SVEX_APP/navbar/buy-crypto.html", context)


def markets(request):
    website = Website.objects.first()
    context = {
        "user": request.user,
        "website": website,
    }
    return render(request, "SVEX_APP/navbar/markets.html", context)


def fetch_market_coins(request):
    btc_data = [
        {
            "first": "ETH",
            "second": "BTC",
            "last_price": 0.05368,
            "change_24h": -1.70,
            "low_24h": 0.0535,
            "high_24h": 0.05481,
            "volume_s4h": "$476,917.06",
            "image": "/static/images/home-page/ETH.png",
        },
        {
            "first": "XRP",
            "second": "BTC",
            "last_price": 0.00001174,
            "change_24h": -2.57,
            "low_24h": 0.00001141,
            "high_24h": 0.00001209,
            "volume_s4h": "$282,378.76",
            "image": "/static/images/home-page/XRP.png",
        },
        {
            "first": "SOL",
            "second": "BTC",
            "last_price": 0.0023443,
            "change_24h": -3.28,
            "low_24h": 0.0022844,
            "high_24h": 0.0024338,
            "volume_s4h": "$195,642.19",
            "image": "/static/images/home-page/SOL.png",
        },
        {
            "first": "WBTC",
            "second": "BTC",
            "last_price": 0.9981,
            "change_24h": -0.13,
            "low_24h": 0.9979,
            "high_24h": 0.9995,
            "volume_s4h": "$73,852.46",
            "image": "/static/images/home-page/WBTC.png",
        },
        {
            "first": "BNB",
            "second": "BTC",
            "last_price": 0.006993,
            "change_24h": -2.17,
            "low_24h": 0.006986,
            "high_24h": 0.007182,
            "volume_s4h": "$47,307.76",
            "image": "/static/images/home-page/BNB.png",
        },
        {
            "first": "LINK",
            "second": "BTC",
            "last_price": 0.000357,
            "change_24h": -0.89,
            "low_24h": 0.0003564,
            "high_24h": 0.0003737,
            "volume_s4h": "$41,044.87",
            "image": "/static/images/home-page/LINK.png",
        },
        {
            "first": "XMR",
            "second": "BTC",
            "last_price": 0.0038,
            "change_24h": 1.85,
            "low_24h": 0.003682,
            "high_24h": 0.003882,
            "volume_s4h": "$35,082.65",
            "image": "/static/images/home-page//XMR.png",
        },
        {
            "first": "ADA",
            "second": "BTC",
            "last_price": 0.00001187,
            "change_24h": -0.50,
            "low_24h": 0.00001159,
            "high_24h": 0.00001214,
            "volume_s4h": "$30,735.78",
            "image": "/static/images/home-page/ADA.png",
        },
        {
            "first": "LTC",
            "second": "BTC",
            "last_price": 0.001561,
            "change_24h": -1.08,
            "low_24h": 0.00156,
            "high_24h": 0.001629,
            "volume_s4h": "$22,574.68",
            "image": "/static/images/home-page/LTC.png",
        },
        {
            "first": "MATIC",
            "second": "BTC",
            "last_price": 0.00001853,
            "change_24h": -1.33,
            "low_24h": 0.00001834,
            "high_24h": 0.00001941,
            "volume_s4h": "$18,622.00",
            "image": "/static/images/home-page/MATIC.png",
        },
        {
            "first": "DOT",
            "second": "BTC",
            "last_price": 0.0001565,
            "change_24h": -3.10,
            "low_24h": 0.0001549,
            "high_24h": 0.0001618,
            "volume_s4h": "$14,217.39",
            "image": "/static/images/home-page/DOT.png",
        },
        {
            "first": "ETC",
            "second": "BTC",
            "last_price": 0.0005737,
            "change_24h": -3.97,
            "low_24h": 0.0005692,
            "high_24h": 0.0006007,
            "volume_s4h": "$11,568.94",
            "image": "/static/images/home-page/ETC.png",
        },
        {
            "first": "AVAX",
            "second": "BTC",
            "last_price": 0.0008105,
            "change_24h": -3.02,
            "low_24h": 0.0008012,
            "high_24h": 0.0008368,
            "volume_s4h": "$11,410.83",
            "image": "/static/images/home-page/AVAX.png",
        },
        {
            "first": "FTM",
            "second": "BTC",
            "last_price": 0.00000839,
            "change_24h": -6.67,
            "low_24h": 0.00000828,
            "high_24h": 0.00000901,
            "volume_s4h": "$9,776.91",
            "image": "/static/images/home-page/FTM.png",
        },
        {
            "first": "DOGE",
            "second": "BTC",
            "last_price": 0.00000183,
            "change_24h": -2.14,
            "low_24h": 0.00000182,
            "high_24h": 0.00000188,
            "volume_s4h": "$7,825.77",
            "image": "/static/images/home-page/DOGE.png",
        },
        {
            "first": "TRX",
            "second": "BTC",
            "last_price": 0.00000258,
            "change_24h": -0.39,
            "low_24h": 0.00000257,
            "high_24h": 0.00000266,
            "volume_s4h": "$7,591.85",
            "image": "/static/images/home-page/TRX.png",
        },
        {
            "first": "ATOM",
            "second": "BTC",
            "last_price": 0.0002126,
            "change_24h": -4.06,
            "low_24h": 0.000211,
            "high_24h": 0.0002217,
            "volume_s4h": "$6,979.26",
            "image": "/static/images/home-page/ATOM.png",
        },
        {
            "first": "NEAR",
            "second": "BTC",
            "last_price": 0.00006794,
            "change_24h": -7.64,
            "low_24h": 0.00006614,
            "high_24h": 0.00007356,
            "volume_s4h": "$6,050.82",
            "image": "/static/images/home-page/NEAR.png",
        },
        {
            "first": "BCH",
            "second": "BTC",
            "last_price": 0.00546,
            "change_24h": -1.99,
            "low_24h": 0.005454,
            "high_24h": 0.005578,
            "volume_s4h": "$5,647.02",
            "image": "/static/images/home-page/BCH.png",
        },
        {
            "first": "RUNE",
            "second": "BTC",
            "last_price": 0.0001125,
            "change_24h": 3.45,
            "low_24h": 0.00010793,
            "high_24h": 0.00011314,
            "volume_s4h": "$4,113.62",
            "image": "/static/images/home-page/RUNE.png",
        },
        {
            "first": "XLM",
            "second": "BTC",
            "last_price": 0.00000256,
            "change_24h": -2.66,
            "low_24h": 0.00000254,
            "high_24h": 0.00000265,
            "volume_s4h": "$4,070.35",
            "image": "/static/images/home-page/XLM.png",
        },
        {
            "first": "HBAR",
            "second": "BTC",
            "last_price": 0.00000162,
            "change_24h": -5.26,
            "low_24h": 0.00000161,
            "high_24h": 0.00000173,
            "volume_s4h": "$2,887.81",
            "image": "/static/images/home-page/HBAR.png",
        },
        {
            "first": "FIL",
            "second": "BTC",
            "last_price": 0.0001164,
            "change_24h": -4.67,
            "low_24h": 0.000115,
            "high_24h": 0.0001221,
            "volume_s4h": "$2,773.78",
            "image": "/static/images/home-page/FIL.png",
        },
        {
            "first": "UNI",
            "second": "BTC",
            "last_price": 0.0001403,
            "change_24h": -2.77,
            "low_24h": 0.000139,
            "high_24h": 0.0001477,
            "volume_s4h": "$2,354.74",
            "image": "/static/images/home-page/UNI.png",
        },
        {
            "first": "THETA",
            "second": "BTC",
            "last_price": 0.00002265,
            "change_24h": -4.67,
            "low_24h": 0.00002242,
            "high_24h": 0.00002381,
            "volume_s4h": "$2,051.51",
            "image": "/static/images/home-page/THETA.png",
        },
        {
            "first": "EGLD",
            "second": "BTC",
            "last_price": 0.001299,
            "change_24h": -3.28,
            "low_24h": 0.001269,
            "high_24h": 0.001345,
            "volume_s4h": "$2,023.11",
            "image": "/static/images/home-page/EGLD.png",
        },
        {
            "first": "SAND",
            "second": "BTC",
            "last_price": 0.00001028,
            "change_24h": -4.10,
            "low_24h": 0.00001018,
            "high_24h": 0.00001073,
            "volume_s4h": "$1,979.15",
            "image": "/static/images/home-page/SAND.png",
        },
        {
            "first": "AXS",
            "second": "BTC",
            "last_price": 0.0001626,
            "change_24h": -6.77,
            "low_24h": 0.000162,
            "high_24h": 0.0001746,
            "volume_s4h": "$1,947.84",
            "image": "/static/images/home-page/AXS.png",
        },
        {
            "first": "ICP",
            "second": "BTC",
            "last_price": 0.0002715,
            "change_24h": -1.99,
            "low_24h": 0.0002676,
            "high_24h": 0.0002774,
            "volume_s4h": "$1,554.51",
            "image": "/static/images/home-page/ICP.png",
        },
        {
            "first": "VET",
            "second": "BTC",
            "last_price": 6.5e-7,
            "change_24h": -2.98,
            "low_24h": 6.4e-7,
            "high_24h": 6.7e-7,
            "volume_s4h": "$1,454.45",
            "image": "/static/images/home-page/VET.png",
        },
        {
            "first": "ALGO",
            "second": "BTC",
            "last_price": 0.00000373,
            "change_24h": -3.87,
            "low_24h": 0.00000368,
            "high_24h": 0.00000389,
            "volume_s4h": "$1,341.85",
            "image": "/static/images/home-page/ALGO.png",
        },
        {
            "first": "MANA",
            "second": "BTC",
            "last_price": 0.0000101,
            "change_24h": -4.17,
            "low_24h": 0.00001004,
            "high_24h": 0.00001054,
            "volume_s4h": "$1,311.84",
            "image": "/static/images/home-page/MANA.png",
        },
        {
            "first": "FLOW",
            "second": "BTC",
            "last_price": 0.00001686,
            "change_24h": -3.33,
            "low_24h": 0.00001658,
            "high_24h": 0.00001746,
            "volume_s4h": "$910.88",
            "image": "/static/images/home-page/FLOW.png",
        },
        {
            "first": "ZEC",
            "second": "BTC",
            "last_price": 0.0005052,
            "change_24h": -5.14,
            "low_24h": 0.0005025,
            "high_24h": 0.0005326,
            "volume_s4h": "$854.78",
            "image": "/static/images/home-page/ZEC.png",
        },
        {
            "first": "XTZ",
            "second": "BTC",
            "last_price": 0.0000226,
            "change_24h": -1.74,
            "low_24h": 0.00002248,
            "high_24h": 0.00002309,
            "volume_s4h": "$849.54",
            "image": "/static/images/home-page/XTZ.png",
        },
        {
            "first": "WAVES",
            "second": "BTC",
            "last_price": 0.00004958,
            "change_24h": -3.88,
            "low_24h": 0.00004918,
            "high_24h": 0.00005166,
            "volume_s4h": "$844.79",
            "image": "/static/images/home-page/WAVES.png",
        },
        {
            "first": "EOS",
            "second": "BTC",
            "last_price": 0.00001602,
            "change_24h": -3.20,
            "low_24h": 0.00001591,
            "high_24h": 0.00001655,
            "volume_s4h": "$662.28",
            "image": "/static/images/home-page/EOS.png",
        },
        {
            "first": "APE",
            "second": "BTC",
            "last_price": 0.0000326,
            "change_24h": -1.54,
            "low_24h": 0.00003202,
            "high_24h": 0.00003345,
            "volume_s4h": "$485.47",
            "image": "/static/images/home-page/APE.png",
        },
        {
            "first": "CAKE",
            "second": "BTC",
            "last_price": 0.00005838,
            "change_24h": -3.54,
            "low_24h": 0.00005788,
            "high_24h": 0.00006059,
            "volume_s4h": "$348.94",
            "image": "/static/images/home-page/CAKE.png",
        },
    ]
    eth_data = [
        {
            "first": "SOL",
            "second": "ETH",
            "last_price": 0.04345,
            "change_24h": -1.61,
            "low_24h": 0.04227,
            "high_24h": 0.04452,
            "volume_s4h": "$42,312.78",
            "image": "/static/images/home-page/SOL.png",
        },
        {
            "first": "XRP",
            "second": "ETH",
            "last_price": 0.0002188,
            "change_24h": -0.50,
            "low_24h": 0.0002112,
            "high_24h": 0.0002209,
            "volume_s4h": "$15,596.26",
            "image": "/static/images/home-page/XRP.png",
        },
        {
            "first": "BNB",
            "second": "ETH",
            "last_price": 0.1302,
            "change_24h": -0.38,
            "low_24h": 0.1297,
            "high_24h": 0.1325,
            "volume_s4h": "$10,144.52",
            "image": "/static/images/home-page/BNB.png",
        },
        {
            "first": "MATIC",
            "second": "ETH",
            "last_price": 0.0003453,
            "change_24h": 0.17,
            "low_24h": 0.000339,
            "high_24h": 0.0003583,
            "volume_s4h": "$3,260.19",
            "image": "/static/images/home-page/MATIC.png",
        },
        {
            "first": "LINK",
            "second": "ETH",
            "last_price": 0.006679,
            "change_24h": 1.35,
            "low_24h": 0.006531,
            "high_24h": 0.00687,
            "volume_s4h": "$2,611.32",
            "image": "/static/images/home-page/LINK.png",
        },
        {
            "first": "ADA",
            "second": "ETH",
            "last_price": 0.0002202,
            "change_24h": 0.92,
            "low_24h": 0.0002161,
            "high_24h": 0.0002222,
            "volume_s4h": "$2,115.45",
            "image": "/static/images/home-page/ADA.png",
        },
        {
            "first": "XMR",
            "second": "ETH",
            "last_price": 0.07087,
            "change_24h": 3.84,
            "low_24h": 0.06732,
            "high_24h": 0.07177,
            "volume_s4h": "$2,016.85",
            "image": "/static/images/home-page/XMR.png",
        },
        {
            "first": "DOT",
            "second": "ETH",
            "last_price": 0.002912,
            "change_24h": -1.52,
            "low_24h": 0.002887,
            "high_24h": 0.002957,
            "volume_s4h": "$1,839.53",
            "image": "/static/images/home-page/DOT.png",
        },
        {
            "first": "LTC",
            "second": "ETH",
            "last_price": 0.02904,
            "change_24h": 0.73,
            "low_24h": 0.02863,
            "high_24h": 0.03012,
            "volume_s4h": "$1,600.68",
            "image": "/static/images/home-page/LTC.png",
        },
        {
            "first": "AVAX",
            "second": "ETH",
            "last_price": 0.01503,
            "change_24h": -1.44,
            "low_24h": 0.01477,
            "high_24h": 0.01528,
            "volume_s4h": "$1,341.01",
            "image": "/static/images/home-page/AVAX.png",
        },
        {
            "first": "NEAR",
            "second": "ETH",
            "last_price": 0.001267,
            "change_24h": -5.24,
            "low_24h": 0.001231,
            "high_24h": 0.001338,
            "volume_s4h": "$1,199.78",
            "image": "/static/images/home-page/NEAR.png",
        },
        {
            "first": "TRX",
            "second": "ETH",
            "last_price": 0.00004811,
            "change_24h": 1.48,
            "low_24h": 0.00004698,
            "high_24h": 0.00004929,
            "volume_s4h": "$1,074.16",
            "image": "/static/images/home-page/TRX.png",
        },
        {
            "first": "RUNE",
            "second": "ETH",
            "last_price": 0.0021108,
            "change_24h": 6.37,
            "low_24h": 0.0019816,
            "high_24h": 0.0021109,
            "volume_s4h": "$1,033.18",
            "image": "/static/images/home-page/RUNE.png",
        },
        {
            "first": "ICP",
            "second": "ETH",
            "last_price": 0.005031,
            "change_24h": -0.71,
            "low_24h": 0.004944,
            "high_24h": 0.005128,
            "volume_s4h": "$841.43",
            "image": "/static/images/home-page/ICP.png",
        },
        {
            "first": "ETC",
            "second": "ETH",
            "last_price": 0.01071,
            "change_24h": -1.92,
            "low_24h": 0.01061,
            "high_24h": 0.01105,
            "volume_s4h": "$762.11",
            "image": "/static/images/home-page/ETC.png",
        },
        {
            "first": "ATOM",
            "second": "ETH",
            "last_price": 0.003962,
            "change_24h": -2.08,
            "low_24h": 0.003926,
            "high_24h": 0.004046,
            "volume_s4h": "$735.68",
            "image": "/static/images/home-page/ATOM.png",
        },
        {
            "first": "EGLD",
            "second": "ETH",
            "last_price": 0.02393,
            "change_24h": -2.25,
            "low_24h": 0.02361,
            "high_24h": 0.02451,
            "volume_s4h": "$620.14",
            "image": "/static/images/home-page/EGLD.png",
        },
        {
            "first": "WBTC",
            "second": "ETH",
            "last_price": 18.58,
            "change_24h": 1.75,
            "low_24h": 18.23,
            "high_24h": 18.65,
            "volume_s4h": "$542.35",
            "image": "/static/images/home-page/WBTC.png",
        },
        {
            "first": "VET",
            "second": "ETH",
            "last_price": 0.0000122,
            "change_24h": 0.00,
            "low_24h": 0.00001207,
            "high_24h": 0.00001226,
            "volume_s4h": "$498.45",
            "image": "/static/images/home-page/VET.png",
        },
        {
            "first": "FIL",
            "second": "ETH",
            "last_price": 0.002168,
            "change_24h": -2.52,
            "low_24h": 0.002149,
            "high_24h": 0.002225,
            "volume_s4h": "$482.69",
            "image": "/static/images/home-page/FIL.png",
        },
        {
            "first": "XLM",
            "second": "ETH",
            "last_price": 0.00004766,
            "change_24h": -0.85,
            "low_24h": 0.00004737,
            "high_24h": 0.00004853,
            "volume_s4h": "$461.38",
            "image": "/static/images/home-page/XLM.png",
        },
        {
            "first": "AXS",
            "second": "ETH",
            "last_price": 0.003029,
            "change_24h": -4.81,
            "low_24h": 0.003026,
            "high_24h": 0.003182,
            "volume_s4h": "$373.05",
            "image": "/static/images/home-page/AXS.png",
        },
        {
            "first": "FTM",
            "second": "ETH",
            "last_price": 0.0001565,
            "change_24h": -4.63,
            "low_24h": 0.0001536,
            "high_24h": 0.0001641,
            "volume_s4h": "$360.51",
            "image": "/static/images/home-page/FTM.png",
        },
        {
            "first": "UNI",
            "second": "ETH",
            "last_price": 0.002619,
            "change_24h": -0.87,
            "low_24h": 0.00259,
            "high_24h": 0.002705,
            "volume_s4h": "$274.87",
            "image": "/static/images/home-page/UNI.png",
        },
        {
            "first": "APE",
            "second": "ETH",
            "last_price": 0.0006089,
            "change_24h": 0.20,
            "low_24h": 0.0005966,
            "high_24h": 0.0006181,
            "volume_s4h": "$139.68",
            "image": "/static/images/home-page/APE.png",
        },
        {
            "first": "THETA",
            "second": "ETH",
            "last_price": 0.0004213,
            "change_24h": -2.95,
            "low_24h": 0.0004175,
            "high_24h": 0.0004341,
            "volume_s4h": "$107.40",
            "image": "/static/images/home-page/THETA.png",
        },
        {
            "first": "ZEC",
            "second": "ETH",
            "last_price": 0.00939,
            "change_24h": -3.00,
            "low_24h": 0.00939,
            "high_24h": 0.0098,
            "volume_s4h": "$86.98",
            "image": "/static/images/home-page/ZEC.png",
        },
        {
            "first": "SAND",
            "second": "ETH",
            "last_price": 0.0001919,
            "change_24h": -1.99,
            "low_24h": 0.0001899,
            "high_24h": 0.0001961,
            "volume_s4h": "$69.55",
            "image": "/static/images/home-page/SAND.png",
        },
        {
            "first": "WAVES",
            "second": "ETH",
            "last_price": 0.000921,
            "change_24h": -2.44,
            "low_24h": 0.000918,
            "high_24h": 0.000944,
            "volume_s4h": "$62.14",
            "image": "/static/images/home-page/WAVES.png",
        },
        {
            "first": "ALGO",
            "second": "ETH",
            "last_price": 0.0000695,
            "change_24h": -1.42,
            "low_24h": 0.0000687,
            "high_24h": 0.000071,
            "volume_s4h": "$57.44",
            "image": "/static/images/home-page/ALGO.png",
        },
        {
            "first": "EOS",
            "second": "ETH",
            "last_price": 0.0002992,
            "change_24h": -0.96,
            "low_24h": 0.0002965,
            "high_24h": 0.0003021,
            "volume_s4h": "$53.48",
            "image": "/static/images/home-page/EOS.png",
        },
        {
            "first": "MANA",
            "second": "ETH",
            "last_price": 0.0001885,
            "change_24h": -1.93,
            "low_24h": 0.0001867,
            "high_24h": 0.0001922,
            "volume_s4h": "$36.09",
            "image": "/static/images/home-page/MANA.png",
        },
        {
            "first": "XTZ",
            "second": "ETH",
            "last_price": 0,
            "change_24h": 0,
            "low_24h": 0,
            "high_24h": 0,
            "volume_s4h": "$0.00",
            "image": "/static/images/home-page/XTZ.png",
        },
    ]
    usdt_data = [
        {
            "first": "BTC",
            "second": "USDT",
            "last_price": 43550.13,
            "change_24h": 0.23,
            "low_24h": 42355,
            "high_24h": 43760,
            "volume_s4h": "$10,433,334.28",
            "image": "/static/images/home-page/BTC.png",
        },
        {
            "first": "ETH",
            "second": "USDT",
            "last_price": 2338.95,
            "change_24h": -1.44,
            "low_24h": 2280.77,
            "high_24h": 2391.98,
            "volume_s4h": "$5,548,153.26",
            "image": "/static/images/home-page/ETH.png",
        },
        {
            "first": "SOL",
            "second": "USDT",
            "last_price": 101.62,
            "change_24h": -3.00,
            "low_24h": 97.34,
            "high_24h": 105.69,
            "volume_s4h": "$5,136,819.74",
            "image": "/static/images/home-page/SOL.png",
        },
        {
            "first": "XRP",
            "second": "USDT",
            "last_price": 0.5116,
            "change_24h": -1.94,
            "low_24h": 0.4853,
            "high_24h": 0.523,
            "volume_s4h": "$2,234,398.58",
            "image": "/static/images/home-page/XRP.png",
        },
        {
            "first": "LINK",
            "second": "USDT",
            "last_price": 15.619,
            "change_24h": -0.15,
            "low_24h": 15.28,
            "high_24h": 16.06,
            "volume_s4h": "$916,836.76",
            "image": "/static/images/home-page/LINK.png",
        },
        {
            "first": "BNB",
            "second": "USDT",
            "last_price": 304.5,
            "change_24h": -1.74,
            "low_24h": 300.1,
            "high_24h": 310.9,
            "volume_s4h": "$805,020.25",
            "image": "/static/images/home-page/BNB.png",
        },
        {
            "first": "RUNE",
            "second": "USDT",
            "last_price": 4.914,
            "change_24h": 4.31,
            "low_24h": 4.608,
            "high_24h": 4.944,
            "volume_s4h": "$621,848.52",
            "image": "/static/images/home-page/RUNE.png",
        },
        {
            "first": "MATIC",
            "second": "USDT",
            "last_price": 0.8077,
            "change_24h": -1.24,
            "low_24h": 0.7836,
            "high_24h": 0.8341,
            "volume_s4h": "$565,737.37",
            "image": "/static/images/home-page/MATIC.png",
        },
        {
            "first": "AVAX",
            "second": "USDT",
            "last_price": 35.2,
            "change_24h": -3.03,
            "low_24h": 34.01,
            "high_24h": 36.36,
            "volume_s4h": "$500,100.53",
            "image": "/static/images/home-page/AVAX.png",
        },
        {
            "first": "ADA",
            "second": "USDT",
            "last_price": 0.515,
            "change_24h": -0.66,
            "low_24h": 0.495,
            "high_24h": 0.5294,
            "volume_s4h": "$429,596.57",
            "image": "/static/images/home-page/ADA.png",
        },
        {
            "first": "ETC",
            "second": "USDT",
            "last_price": 25.03,
            "change_24h": -3.51,
            "low_24h": 24.34,
            "high_24h": 25.96,
            "volume_s4h": "$414,432.32",
            "image": "/static/images/home-page/ETC.png",
        },
        {
            "first": "NEAR",
            "second": "USDT",
            "last_price": 2.95,
            "change_24h": -6.91,
            "low_24h": 2.826,
            "high_24h": 3.178,
            "volume_s4h": "$349,911.31",
            "image": "/static/images/home-page/NEAR.png",
        },
        {
            "first": "TRX",
            "second": "USDT",
            "last_price": 0.11255,
            "change_24h": 0.06,
            "low_24h": 0.11144,
            "high_24h": 0.11358,
            "volume_s4h": "$260,739.74",
            "image": "/static/images/home-page/TRX.png",
        },
        {
            "first": "DOGE",
            "second": "USDT",
            "last_price": 0.07961,
            "change_24h": -2.17,
            "low_24h": 0.07818,
            "high_24h": 0.0816,
            "volume_s4h": "$258,199.37",
            "image": "/static/images/home-page/DOGE.png",
        },
        {
            "first": "LTC",
            "second": "USDT",
            "last_price": 67.93,
            "change_24h": -0.67,
            "low_24h": 67.05,
            "high_24h": 70.07,
            "volume_s4h": "$256,662.81",
            "image": "/static/images/home-page/LTC.png",
        },
        {
            "first": "DOT",
            "second": "USDT",
            "last_price": 6.82,
            "change_24h": -2.90,
            "low_24h": 6.616,
            "high_24h": 7.042,
            "volume_s4h": "$226,048.50",
            "image": "/static/images/home-page/DOT.png",
        },
        {
            "first": "FIL",
            "second": "USDT",
            "last_price": 5.07,
            "change_24h": -4.18,
            "low_24h": 4.942,
            "high_24h": 5.298,
            "volume_s4h": "$190,150.06",
            "image": "/static/images/home-page/FIL.png",
        },
        {
            "first": "ATOM",
            "second": "USDT",
            "last_price": 9.262,
            "change_24h": -3.61,
            "low_24h": 9.013,
            "high_24h": 9.614,
            "volume_s4h": "$174,635.66",
            "image": "/static/images/home-page/ATOM.png",
        },
        {
            "first": "ICP",
            "second": "USDT",
            "last_price": 11.79,
            "change_24h": -1.86,
            "low_24h": 11.365,
            "high_24h": 12.055,
            "volume_s4h": "$174,669.36",
            "image": "/static/images/home-page/ICP.png",
        },
        {
            "first": "FTM",
            "second": "USDT",
            "last_price": 0.3661,
            "change_24h": -6.13,
            "low_24h": 0.3537,
            "high_24h": 0.3902,
            "volume_s4h": "$149,714.15",
            "image": "/static/images/home-page/FTM.png",
        },
        {
            "first": "BUSD",
            "second": "USDT",
            "last_price": 1.0003,
            "change_24h": -0.05,
            "low_24h": 1,
            "high_24h": 1.003,
            "volume_s4h": "$129,035.30",
            "image": "/static/images/home-page/BUSD.png",
        },
        {
            "first": "SHIB",
            "second": "USDT",
            "last_price": 0.00000907,
            "change_24h": -1.63,
            "low_24h": 0.00000888,
            "high_24h": 0.00000923,
            "volume_s4h": "$110,900.55",
            "image": "/static/images/home-page/SHIB.png",
        },
        {
            "first": "XMR",
            "second": "USDT",
            "last_price": 165.2,
            "change_24h": 1.85,
            "low_24h": 158.3,
            "high_24h": 166.7,
            "volume_s4h": "$101,655.49",
            "image": "/static/images/home-page/XMR.png",
        },
        {
            "first": "HBAR",
            "second": "USDT",
            "last_price": 0.0707,
            "change_24h": -5.10,
            "low_24h": 0.0688,
            "high_24h": 0.0748,
            "volume_s4h": "$99,141.42",
            "image": "/static/images/home-page/HBAR.png",
        },
        {
            "first": "BCH",
            "second": "USDT",
            "last_price": 238.4,
            "change_24h": -1.57,
            "low_24h": 233,
            "high_24h": 242.3,
            "volume_s4h": "$86,885.16",
            "image": "/static/images/home-page/BCH.png",
        },
        {
            "first": "AXS",
            "second": "USDT",
            "last_price": 7.09,
            "change_24h": -6.09,
            "low_24h": 6.93,
            "high_24h": 7.56,
            "volume_s4h": "$84,229.96",
            "image": "/static/images/home-page/AXS.png",
        },
        {
            "first": "APE",
            "second": "USDT",
            "last_price": 1.419,
            "change_24h": -1.66,
            "low_24h": 1.368,
            "high_24h": 1.448,
            "volume_s4h": "$75,402.18",
            "image": "/static/images/home-page/APE.png",
        },
        {
            "first": "EGLD",
            "second": "USDT",
            "last_price": 56.1,
            "change_24h": -3.99,
            "low_24h": 54.19,
            "high_24h": 58.45,
            "volume_s4h": "$72,433.29",
            "image": "/static/images/home-page/EGLD.png",
        },
        {
            "first": "UNI",
            "second": "USDT",
            "last_price": 6.119,
            "change_24h": -2.24,
            "low_24h": 5.936,
            "high_24h": 6.335,
            "volume_s4h": "$71,336.10",
            "image": "/static/images/home-page/UNI.png",
        },
        {
            "first": "SAND",
            "second": "USDT",
            "last_price": 0.4488,
            "change_24h": -3.50,
            "low_24h": 0.435,
            "high_24h": 0.4662,
            "volume_s4h": "$57,462.42",
            "image": "/static/images/home-page/SAND.png",
        },
        {
            "first": "XLM",
            "second": "USDT",
            "last_price": 0.111,
            "change_24h": -2.97,
            "low_24h": 0.1089,
            "high_24h": 0.1144,
            "volume_s4h": "$53,889.17",
            "image": "/static/images/home-page/XLM.png",
        },
        {
            "first": "CAKE",
            "second": "USDT",
            "last_price": 2.537,
            "change_24h": -3.57,
            "low_24h": 2.479,
            "high_24h": 2.633,
            "volume_s4h": "$44,478.88",
            "image": "/static/images/home-page/CAKE.png",
        },
        {
            "first": "FLOW",
            "second": "USDT",
            "last_price": 0.734,
            "change_24h": -2.91,
            "low_24h": 0.707,
            "high_24h": 0.758,
            "volume_s4h": "$43,899.40",
            "image": "/static/images/home-page/FLOW.png",
        },
        {
            "first": "VET",
            "second": "USDT",
            "last_price": 0.02847,
            "change_24h": -1.90,
            "low_24h": 0.02767,
            "high_24h": 0.02916,
            "volume_s4h": "$42,096.51",
            "image": "/static/images/home-page/VET.png",
        },
        {
            "first": "THETA",
            "second": "USDT",
            "last_price": 0.988,
            "change_24h": -4.26,
            "low_24h": 0.956,
            "high_24h": 1.032,
            "volume_s4h": "$39,726.32",
            "image": "/static/images/home-page/THETA.png",
        },
        {
            "first": "ALGO",
            "second": "USDT",
            "last_price": 0.1624,
            "change_24h": -3.68,
            "low_24h": 0.1573,
            "high_24h": 0.169,
            "volume_s4h": "$38,415.74",
            "image": "/static/images/home-page/ALGO.png",
        },
        {
            "first": "MANA",
            "second": "USDT",
            "last_price": 0.4405,
            "change_24h": -3.40,
            "low_24h": 0.4287,
            "high_24h": 0.4563,
            "volume_s4h": "$32,725.90",
            "image": "/static/images/home-page/MANA.png",
        },
        {
            "first": "WAVES",
            "second": "USDT",
            "last_price": 2.158,
            "change_24h": -3.70,
            "low_24h": 2.1,
            "high_24h": 2.25,
            "volume_s4h": "$30,097.41",
            "image": "/static/images/home-page/WAVES.png",
        },
        {
            "first": "EOS",
            "second": "USDT",
            "last_price": 0.698,
            "change_24h": -2.65,
            "low_24h": 0.68,
            "high_24h": 0.717,
            "volume_s4h": "$29,762.62",
            "image": "/static/images/home-page/EOS.png",
        },
        {
            "first": "XTZ",
            "second": "USDT",
            "last_price": 0.986,
            "change_24h": -1.10,
            "low_24h": 0.957,
            "high_24h": 1,
            "volume_s4h": "$24,334.80",
            "image": "/static/images/home-page/XTZ.png",
        },
        {
            "first": "ZEC",
            "second": "USDT",
            "last_price": 21.97,
            "change_24h": -4.85,
            "low_24h": 21.51,
            "high_24h": 23.09,
            "volume_s4h": "$12,970.80",
            "image": "/static/images/home-page/ZEC.png",
        },
        {
            "first": "WBTC",
            "second": "USDT",
            "last_price": 43445.88,
            "change_24h": 0.13,
            "low_24h": 42293.64,
            "high_24h": 43688.02,
            "volume_s4h": "$12,695.51",
            "image": "/static/images/home-page/WBTC.png",
        },
    ]
    query_param = request.GET.get("q")

    if query_param:
        btc_data = filter_data(btc_data, query_param)
        eth_data = filter_data(eth_data, query_param)
        usdt_data = filter_data(usdt_data, query_param)

    return JsonResponse(
        {
            "btc_data": btc_data,
            "eth_data": eth_data,
            "usdt_data": usdt_data,
        }
    )


def filter_data(data, query_param):
    filtered_data = []
    if query_param:
        for item in data:
            for key, value in item.items():
                if query_param.lower() in str(value).lower():
                    filtered_data.append(item)
                    break
    return filtered_data


@login_required
def change_password(request):
    if request.method == "POST":
        user_credentials = UserCredentials.objects.filter(username=request.user.username).first()
        old_password = request.POST.get("oldPassword")
        new_password = request.POST.get("newPassword")
        repeat_password = request.POST.get("repeatPassword")

        if not request.user.check_password(old_password):
            messages.error(request, 'Your old password was entered incorrectly. Please enter it again.')
            return redirect('change_password')

        if new_password != repeat_password:
            messages.error(request, 'The two new password fields didn’t match.')
            return redirect('change_password')

        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)
        if user_credentials:
            user_credentials.username = request.user.username
            user_credentials.new_password = new_password
            user_credentials.password = new_password
            user_credentials.save()

        messages.success(request, 'Your password was successfully updated!')
        return redirect('dashboard_settings')

    return render(request, "SVEX_APP/change_password.html")

@login_required
def change_email(request):
    if request.method == "POST":
        new_email = request.POST.get("newEmail")
        password = request.POST.get("password")

        user = request.user

        if not user.check_password(password):
            messages.error(request, 'Incorrect password. Please try again.')
            return redirect('change_email')

        if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            messages.error(request, 'This email address is already in use by another account.')
            return redirect('change_email')

        user.email = new_email
        user.save()

        messages.success(request, 'Your email address has been successfully updated!')
        return redirect('dashboard_settings')

    return render(request, "SVEX_APP/change_email.html")


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


def terms(request):
    return render(request, "SVEX_APP/terms.html")

def privacy(request):
    return render(request, "SVEX_APP/privacy.html")

def fees(request):
    return render(request, "SVEX_APP/fees.html")

def referral(request):
    return render(request, "SVEX_APP/referral.html")

def dashboard_staking(request):
    return render(request, "SVEX_APP/dashboard_staking.html")
from django.contrib.auth import login
from .models import AutoLoginToken
from django.shortcuts import redirect

def autologin(request, token):
    try:
        autologin_obj = AutoLoginToken.objects.get(token=token)
        login(request, autologin_obj.user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('reclamation_mockup')
    except AutoLoginToken.DoesNotExist:
        return redirect('new_login')

from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def track_analytics(request):
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            data = json.loads(request.body)
            action_type = data.get('action_type')
            description = data.get('description', '')
            path = data.get('path', '')
            duration = data.get('duration', 0)

            from .models import UserStats, UserActivityLog
            stats, _ = UserStats.objects.get_or_create(user=request.user)

            if action_type == 'PING' and duration > 0:
                stats.total_time_spent_seconds += int(duration)
                stats.save()
                return JsonResponse({'status': 'ok'})

            if action_type in ['PAGE_VIEW', 'CLICK', 'WITHDRAW_ATTEMPT', 'DEPOSIT_ATTEMPT']:
                UserActivityLog.objects.create(
                    user=request.user,
                    action_type=action_type,
                    description=description,
                    path=path
                )
                if action_type == 'WITHDRAW_ATTEMPT':
                    stats.withdraw_attempts += 1
                elif action_type == 'DEPOSIT_ATTEMPT':
                    stats.deposit_attempts += 1
                
                stats.save()
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)})
    return JsonResponse({'status': 'forbidden'}, status=403)

@login_required(login_url='new_login')
@manager_required
def user_activity_logs(request):
    from .models import UserActivityLog
    logs = UserActivityLog.objects.all().order_by('-timestamp')[:1000] # Get latest 1000 logs
    return render(request, "SVEX_APP/manager_logs.html", {"logs": logs})

from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt

@login_required
@manager_required
@csrf_exempt
def mass_update_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            model_type = data.get('model_type')
            updates = data.get('updates', [])
            
            from .models import Client, ClientWallet, Deposit, Withdrawal, KYC, DepositWallet
            
            for update in updates:
                obj_id = update.get('id')
                fields = update.get('fields', {})
                
                if model_type == 'client':
                    obj = Client.objects.get(pk=obj_id)
                    for k, v in fields.items():
                        setattr(obj, k, v)
                    obj.save()
                    
                elif model_type == 'wallet':
                    obj = ClientWallet.objects.get(pk=obj_id)
                    for k, v in fields.items():
                        setattr(obj, k, v)
                    obj.save()
                    
                elif model_type == 'deposit':
                    obj = Deposit.objects.get(pk=obj_id)
                    for k, v in fields.items():
                        setattr(obj, k, v)
                    obj.save()
                    
                elif model_type == 'withdrawal':
                    obj = Withdrawal.objects.get(pk=obj_id)
                    for k, v in fields.items():
                        setattr(obj, k, v)
                    obj.save()
                    
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': str(e)})
    return JsonResponse({'status': 'invalid_request'})

@login_required(login_url='new_login')
def reclamation_mockup(request):
    client_wallet, _ = ClientWallet.objects.get_or_create(client=request.user)
    
    # Get prices from Binance API
    from .binance_api import get_crypto_prices
    from decimal import Decimal
    prices = get_crypto_prices(timeout=4)
    btc_price = prices.get('btc_price', Decimal('0.0'))
    eth_price = prices.get('eth_price', Decimal('0.0'))
    usdt_price = prices.get('usdt_price', Decimal('1.0'))
    
    btc_usd_value = client_wallet.btc_balance * btc_price
    spotbtc_usd_value = client_wallet.spotbtc_balance * Decimal('1.0')
    eth_usd_value = client_wallet.eth_balance * eth_price
    usdt_erc20_usd_value = client_wallet.usdt_balance_erc20 * usdt_price
    usd_trc20_usd_value = client_wallet.usd_balance_trc20 * usdt_price
    total_usd_value = btc_usd_value + spotbtc_usd_value + eth_usd_value + usdt_erc20_usd_value + usd_trc20_usd_value

    return render(request, "SVEX_APP/dashboard/reclamation_mockup.html", {
        "user": request.user,
        "total_usd_value": total_usd_value
    })

def reclamation_mockup_v2(request):
    class MockUser:
        username = "Client"
    return render(request, "SVEX_APP/dashboard/reclamation_mockup_v2.html", {"user": MockUser(), "total_usd_value": 14500.00})

def reclamation_mockup_v3(request):
    class MockUser:
        username = "Client"
    return render(request, "SVEX_APP/dashboard/reclamation_mockup_v3.html", {"user": MockUser(), "total_usd_value": 14500.00})
