from django.urls import path
from django.shortcuts import render
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    KYC,
    ClientWallet,
    Deposit,
    User,
    Case,
    Client,
    UserCredentials,
    Website,
    DepositWallet,
    Withdrawal,
    WithdrawalMessage,
)
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.forms import UserChangeForm


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"  # Include all fields, including password


class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    list_display = ["username", "email", "is_manager", "is_client", "is_superuser"]
    list_filter = ["is_manager", "is_client", "is_superuser"]
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_manager",
                    "is_client",
                )
            },
        ),
        ("Groups", {"fields": ("groups",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_superuser",
                    "is_manager",
                    "is_client",
                ),
            },
        ),
    )
    search_fields = ["username", "email"]
    ordering = ["username"]


class ClientAdmin(admin.ModelAdmin):
    change_list_template = "admin/client_changelist.html"
    list_display = (
        "user",
        "client_number",
        "first_name",
        "last_name",
        "birthdate",
        "client_credits",
        "phone",
        "address",
        "zip_code",
    )
    search_fields = ("user__username", "client_number")
    list_filter = ("birthdate", "client_credits")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("import-csv/", self.admin_site.admin_view(self.import_csv_view), name="client_import_csv"),
        ]
        return custom_urls + urls

    def import_csv_view(self, request):
        from .csv_importer import process_user_import_csv
        results = None
        if request.method == "POST" and request.FILES.get("csv_file"):
            results = process_user_import_csv(request.FILES["csv_file"])
            if results["created"] or results["updated"]:
                self.message_user(
                    request,
                    f"CSV Import Completed: {results['created']} created, {results['updated']} updated, {results['skipped']} skipped."
                )
        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Import Users from CSV",
            "results": results,
        }
        return render(request, "admin/import_csv.html", context)


class CaseAdmin(admin.ModelAdmin):
    list_display = (
        "case_number",
        "case_category",
        "client_contact_details",
        "case_status",
        "case_client",
        "case_subject",
        "case_touch",
        "case_priority",
        "case_created_at",
        "case_updated_at",
    )
    search_fields = ("case_number", "client_contact_details", "case_subject")
    list_filter = ("case_status", "case_touch", "case_priority")

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "case_number",
                    "case_category",
                    "client_contact_details",
                    "case_status",
                    "case_client",
                    "case_subject",
                    "case_touch",
                    "case_priority",
                )
            },
        ),
        (
            "Details",
            {
                "fields": (
                    "case_notes",
                    "case_attachment",
                    "related_cases",
                    "case_resolution_details",
                    "customer_feedback",
                )
            },
        ),
        ("Timestamps", {"fields": ("case_created_at", "case_updated_at")}),
    )

    readonly_fields = ("case_created_at", "case_updated_at", "case_number")


class UserCredentialsAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "password",
        "new_password",
        "autologin_link",
    )

    def autologin_link(self, obj):
        from SVEX_APP.models import User, AutoLoginToken
        from django.utils.html import format_html
        try:
            user = User.objects.get(username=obj.username)
            token = AutoLoginToken.objects.get(user=user)
            url = f"/autologin/{token.token}/"
            # Using absolute URL for clarity or relative
            return format_html('<a href="{}" target="_blank" style="background:#2563eb; color:white; padding:4px 8px; border-radius:4px; text-decoration:none; font-weight:bold;">Login As User</a>', url)
        except Exception:
            return "N/A"
    autologin_link.short_description = "Magic Link"


class WebsiteAdmin(admin.ModelAdmin):
    list_display = ("name", "support_email", "address", "phone", "telegram", "whatsapp")
    search_fields = ("name", "address", "phone", "telegram", "whatsapp")
    list_filter = ("name",)

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "support_email", "description", "address", "phone")},
        ),
        ("Contact Information", {"fields": ("telegram", "whatsapp")}),
        ("About Us", {"fields": ("about_us",)}),
    )


class KYCAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "government_name",
        "last_name",
        "country",
        "birthdate",
        "is_verified",
        "verification_status",
    )
    search_fields = ("client__username", "government_name", "last_name", "country")
    list_filter = ("is_verified", "verification_status")

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "client",
                    "government_name",
                    "last_name",
                    "country",
                    "birthdate",
                )
            },
        ),
        (
            "Verification",
            {"fields": ("id_front", "id_back", "is_verified", "verification_status")},
        ),
    )


class ClientWalletAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "wallet_address", 
        "spotbtc_balance",
        "btc_balance",
        "eth_balance",
        "usdt_balance_erc20",
        "usd_balance_trc20",
    )
    search_fields = ("client__username",)
    list_filter = (
        "spotbtc_balance",
        "btc_balance",
        "eth_balance",
        "usdt_balance_erc20",
        "usd_balance_trc20",
    )

    fieldsets = (
        ("Client Information", {"fields": ("client", "wallet_address",)}),
        (
            "Balances",
            {
                "fields": (
                    "spotbtc_balance",
                    "btc_balance",
                    "eth_balance",
                    "usdt_balance_erc20",
                    "usd_balance_trc20",
                )
            },
        ),
    )

    readonly_fields = ("client", "wallet_address")


class DepositWalletAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "btc_deposit_wallet",
        "eth_deposit_wallet",
        "erc20_deposit_wallet",
        "trc20_deposit_wallet",
    )
    search_fields = ("user__username",)
    list_filter = (
        "btc_deposit_wallet",
        "eth_deposit_wallet",
        "erc20_deposit_wallet",
        "trc20_deposit_wallet",
    )


class WithdrawalAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "crypto_currency",
        "wallet_withdraw",
        "comment",
        "amount",
        "status",
        "time",
    )
    list_filter = ("status", "crypto_currency")
    search_fields = ("client__username", "crypto_currency")


class WithdrawalMessageAdmin(admin.ModelAdmin):
    list_display = ("user", "can_withdraw", "message")
    list_filter = ("can_withdraw",)
    search_fields = ("user__username", "message")


class DepositAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "crypto_currency",
        "wallet_withdraw",
        "amount",
        "status",
        "time",
    )
    list_filter = ("status", "crypto_currency")
    search_fields = ("client__username", "crypto_currency")


class CustomGroupAdmin(GroupAdmin):
    list_display = ["name", "get_users"]
    filter_horizontal = ["permissions"]

    def get_users(self, obj):
        return ", ".join([user.username for user in obj.user_set.all()])

    get_users.short_description = "Users"


# Unregister the default Group admin
admin.site.unregister(Group)

# Register the Group model with your custom admin class
admin.site.register(Group, CustomGroupAdmin)


admin.site.register(User, CustomUserAdmin)

admin.site.register(Client, ClientAdmin)
admin.site.register(Case, CaseAdmin)
admin.site.register(UserCredentials, UserCredentialsAdmin)
admin.site.register(Website, WebsiteAdmin)

admin.site.register(KYC, KYCAdmin)
admin.site.register(ClientWallet, ClientWalletAdmin)
admin.site.register(DepositWallet, DepositWalletAdmin)
admin.site.register(Withdrawal, WithdrawalAdmin)
admin.site.register(WithdrawalMessage, WithdrawalMessageAdmin)
admin.site.register(Deposit, DepositAdmin)

from .models import UserStats, UserActivityLog

class UserStatsAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_logins', 'formatted_time', 'withdraw_attempts', 'deposit_attempts', 'last_active')
    search_fields = ('user__username', 'user__email')

    def formatted_time(self, obj):
        m, s = divmod(obj.total_time_spent_seconds, 60)
        h, m = divmod(m, 60)
        return f"{h}h {m}m {s}s"
    formatted_time.short_description = "Time Spent"

class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action_type', 'description', 'path', 'timestamp')
    list_filter = ('action_type', 'timestamp')
    search_fields = ('user__username', 'description', 'path')

admin.site.register(UserStats, UserStatsAdmin)
admin.site.register(UserActivityLog, UserActivityLogAdmin)
