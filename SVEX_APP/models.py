from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.models import Group
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid


# Create your models here.


class CustomUserManager(BaseUserManager):
    def create_user(
        self,
        username,
        email,
        password=None,
        is_client=True,
        is_manager=False,
        **extra_fields,
    ):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)

        user = self.model(
            username=username,
            email=email,
            is_client=is_client,
            is_manager=is_manager,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)

        if is_client:
            client_group, _ = Group.objects.get_or_create(name="Clients")
            user.groups.add(client_group)
        elif is_manager:
            manager_group, _ = Group.objects.get_or_create(name="Managers")
            user.groups.add(manager_group)

        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        admin_group, _ = Group.objects.get_or_create(name="Admin")
        extra_fields.setdefault("is_manager", True)
        extra_fields.setdefault("is_client", False)
        user = self.create_user(username, email, password, **extra_fields)
        user.groups.add(admin_group)
        return user


class User(AbstractUser, PermissionsMixin):
    email = models.EmailField(unique=True)

    is_manager = models.BooleanField("Manager", default=False)
    is_client = models.BooleanField("Client", default=True)
    # is_active = models.BooleanField('Active', default=True)
    # is_verified = models.BooleanField( default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if not self.date_joined:
            self.date_joined = timezone.now()
        super().save(*args, **kwargs)

    def display_name_with_role(self):
        roles = [
            role
            for role in ["Manager", "Client"]
            if getattr(self, f"is_{role.lower()}")
        ]
        role_str = ", ".join(roles) if roles else "No Role"
        return f"{self.get_full_name()} - {role_str}"


class UserCredentials(models.Model):

    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    new_password = models.CharField(max_length=255, blank=True, null=True)


class Client(models.Model):
    objects = None
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    client_number = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    birthdate = models.DateField(null=True, blank=True)
    client_credits = models.DecimalField(
        max_digits=10, decimal_places=2, default=10
    )
    phone = models.CharField(max_length=15)
    address = models.TextField()
    zip_code = models.CharField(max_length=10)

    def __str__(self):
        return self.client_number

    def save(self, *args, **kwargs):
        if not self.client_number:
            last_client = Client.objects.order_by("-client_number").first()
            if last_client:
                last_client_number = int(last_client.client_number)
                self.client_number = str(last_client_number + 1)
            else:
                self.client_number = "100000"

        super(Client, self).save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_client(sender, instance, created, **kwargs):
    if created and instance.is_client:
        Client.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_client(sender, instance, **kwargs):
    if instance.is_client:
        instance.client.save()


class KYC(models.Model):
    objects = None
    STATUS_CHOICES = [
        ("confirmed", "Confirmed"),
        ("pending", "Pending"),
        ("cancelled", "Cancelled"),
    ]

    client = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    government_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100)
    birthdate = models.DateField()
    id_front = models.ImageField(upload_to="kyc/")
    id_back = models.ImageField(upload_to="kyc/")
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )

    def __str__(self):
        return f"KYC for {self.government_name} {self.last_name}"


# client wallet


class ClientWallet(models.Model):
    DoesNotExist = None
    objects = None

    wallet_address = models.CharField(max_length=42, unique=True, blank=True, null=True)

    client = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True)
    spotbtc_balance = models.DecimalField(
        max_digits=20, decimal_places=8, default=0)
    btc_balance = models.DecimalField(
        max_digits=20, decimal_places=8, default=0)
    eth_balance = models.DecimalField(
        max_digits=20, decimal_places=8, default=0)
    usdt_balance_erc20 = models.DecimalField(
        max_digits=20, decimal_places=8, default=0)
    usd_balance_trc20 = models.DecimalField(
        max_digits=20, decimal_places=8, default=0)

    
    def save(self, *args, **kwargs):
        if not self.wallet_address:
            self.wallet_address = self.generate_wallet_address()
        super().save(*args, **kwargs)
    
    def generate_wallet_address(self):
        import secrets
        address = '0x' + secrets.token_hex(20)
        while ClientWallet.objects.filter(wallet_address=address).exists():
            address = '0x' + secrets.token_hex(20)
        return address

    
    def __str__(self):
        if self.client:
            return f"{self.client.username}'s Wallet"
        return "Unassigned Wallet"



@receiver(post_save, sender=User)
def create_client_wallet(sender, instance, created, **kwargs):
    if created:
        ClientWallet.objects.create(client=instance)


@receiver(post_save, sender=User)
def save_client_wallet(sender, instance, **kwargs):
    if instance.is_client:
        if hasattr(instance, "clientwallet"):
            instance.clientwallet.save()
        else:
            ClientWallet.objects.create(client=instance)


class DepositWallet(models.Model):
    objects = None
    DoesNotExist = None
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    btc_deposit_wallet = models.CharField(max_length=100, default="wallet")
    eth_deposit_wallet = models.CharField(max_length=100, default="wallet")
    erc20_deposit_wallet = models.CharField(max_length=100, default="wallet")
    trc20_deposit_wallet = models.CharField(max_length=100, default="wallet")

    def __str__(self):
        return f"{self.user.username}'s Deposit Wallet"


@receiver(post_save, sender=User)
def create_deposit_wallet(sender, instance, created, **kwargs):
    if created:
        DepositWallet.objects.create(user=instance)


class Withdrawal(models.Model):
    objects = None
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELED = "canceled"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (CONFIRMED, "Confirmed"),
        (CANCELED, "Canceled"),
    ]

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    crypto_currency = models.CharField(max_length=10)
    wallet_withdraw = models.CharField(max_length=100, null=False)
    comment = models.CharField(max_length=200, null=True, blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=PENDING)
    time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.client.username} did a withdraw of {self.amount} {self.crypto_currency}"


class Deposit(models.Model):
    objects = None
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELED = "canceled"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (CONFIRMED, "Confirmed"),
        (CANCELED, "Canceled"),
    ]

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    crypto_currency = models.CharField(max_length=10)
    wallet_withdraw = models.CharField(max_length=20, null=False)
    amount = models.DecimalField(max_digits=20, decimal_places=8)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=PENDING)
    time = models.DateTimeField(auto_now_add=True)


class WithdrawalMessage(models.Model):
    objects = None
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    can_withdraw = models.BooleanField(default=False)
    message = models.CharField(
        max_length=200, default="Please Contact Support.")

    def __str__(self):
        return f"Withdrawal permissions for {self.user.username}"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_withdrawal_message(sender, instance, created, **kwargs):
    if created:
        WithdrawalMessage.objects.create(user=instance)



class Case(models.Model):
    objects = None
    CASE_STATUS_CHOICES = [
        ("Open", "Open"),
        ("In Progress", "In Progress"),
        ("Responded", "Responded"),
        ("Escalated", "Escalated"),
        ("On Hold", "On Hold"),
        ("Closed-Resolved", "Closed-Resolved"),
        ("Closed-NotResolved", "Closed-NotResolved"),
        ("Closed-Spam", "Closed-Spam"),
        ("Closed-Lost", "Closed-Lost"),
    ]

    CASE_PRIORITY_CHOICES = [
        ("Very High", "Very High"),
        ("High", "High"),
        ("Medium", "Medium"),
        ("Low", "Low"),
        ("Very Low", "Very Low"),
    ]

    CASE_TOUCH_CHOICES = [
        ("First Touch", "First Touch"),
        ("Second Touch", "Second Touch"),
        ("Processing", "Processing"),
        ("Other", "Other"),
    ]

    CASE_CATEGORY_CHOICES = [
        ("Bug", "Bug Report"),
        ("Feature", "Feature Request"),
        ("Complaint", "Customer Complaint"),
        ("Refund", "Refund Request"),
        ("Account", "Account Issue"),
        ("Security", "Security Concern"),
        ("Transaction", "Transaction Issue"),
        ("Wallet", "Wallet Management Issue"),
        ("Exchange", "Exchange Rate Discrepancy"),
        ("KYC", "Know Your Customer (KYC) Issue"),
        ("AML", "Anti-Money Laundering (AML) Issue"),
        ("Withdrawal", "Withdrawal Problem"),
        ("Deposit", "Deposit Issue"),
        ("Trading", "Trading Issue"),
        ("API", "API Integration Issue"),
        ("Chart", "Charting/Graphical Issue"),
        ("Order", "Order Execution Issue"),
        ("Liquidity", "Liquidity Problem"),
        ("Margin", "Margin Trading Issue"),
        ("Funds", "Funds Availability Issue"),
        ("Verification", "Account Verification Issue"),
        ("Scam", "Suspected Scam/Phishing Report"),
        ("Tax", "Tax Reporting Issue"),
        ("Regulatory", "Regulatory Compliance Issue"),
        ("Privacy", "Privacy Concern"),
        ("Support", "Customer Support Request"),
        ("Education", "Education/Training Request"),
        ("Feedback", "General Feedback"),
        ("Other", "Other"),
    ]

    case_number = models.CharField(max_length=100, unique=True)
    case_category = models.CharField(
        max_length=20, choices=CASE_CATEGORY_CHOICES, blank=True
    )
    client_contact_details = models.CharField(max_length=255)
    case_status = models.CharField(
        max_length=20, choices=CASE_STATUS_CHOICES, default="Open"
    )
    case_client = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    case_subject = models.CharField(max_length=255)

    case_touch = models.CharField(
        max_length=20, choices=CASE_TOUCH_CHOICES, blank=True)
    case_priority = models.CharField(
        max_length=20, choices=CASE_PRIORITY_CHOICES, default="Medium"
    )

    case_notes = models.TextField(default="Waiting for response.")

    case_created_at = models.DateTimeField(auto_now_add=True)
    case_updated_at = models.DateTimeField(auto_now=True)
    case_attachment = models.FileField(
        upload_to="case_attachments/", null=True, blank=True
    )
    related_cases = models.ManyToManyField("self", blank=True)
    case_resolution_details = models.TextField(null=True, blank=True)
    customer_feedback = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Case #{self.case_number}"

    def save(self, *args, **kwargs):
        if not self.case_number:
            last_case = Case.objects.order_by("-case_number").first()
            if last_case:
                last_case_number = int(last_case.case_number)
                self.case_number = str(last_case_number + 1)
            else:
                self.case_number = "10000000"

        if not self.case_created_at:
            self.case_created_at = timezone.now()

        self.case_updated_at = timezone.now()

        super(Case, self).save(*args, **kwargs)


@receiver(post_save, sender=Case)
def create_case_number(sender, instance, created, **kwargs):
    if created:
        instance.save()


###################################################### Website ##############################################################


class Website(models.Model):
    objects = None
    name = models.CharField(max_length=100)
    support_email = models.EmailField()
    description = models.TextField()
    address = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    about_us = models.TextField()
    telegram = models.CharField(max_length=100, blank=True, null=True)
    whatsapp = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name

class AutoLoginToken(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="autologin_token")
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AutoLoginToken for {self.user.username}"

@receiver(post_save, sender=User)
def create_autologin_token(sender, instance, created, **kwargs):
    if created:
        AutoLoginToken.objects.create(user=instance)

class UserStats(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='stats')
    total_logins = models.IntegerField(default=0)
    total_time_spent_seconds = models.IntegerField(default=0)
    withdraw_attempts = models.IntegerField(default=0)
    deposit_attempts = models.IntegerField(default=0)
    last_active = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stats for {self.user.username}"

class UserActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity_logs')
    action_type = models.CharField(max_length=50) # e.g. PAGE_VIEW, CLICK, LOGIN
    description = models.CharField(max_length=255) # e.g. "Visited /dashboard", "Clicked Withdraw"
    path = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action_type} - {self.timestamp}"

@receiver(post_save, sender=User)
def create_user_stats(sender, instance, created, **kwargs):
    if created:
        UserStats.objects.get_or_create(user=instance)

from django.contrib.auth.signals import user_logged_in

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    stats, _ = UserStats.objects.get_or_create(user=user)
    stats.total_logins += 1
    stats.save()
    UserActivityLog.objects.create(
        user=user,
        action_type='LOGIN',
        description='User logged in',
        path=request.path
    )
