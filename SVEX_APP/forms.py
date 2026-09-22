from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import (
    User,
    Case,
    Client,
    UserCredentials,
    Website,
    KYC,
    ClientWallet,
    Withdrawal,
    DepositWallet,
    Deposit,
    WithdrawalMessage,
)
from django.contrib.auth import get_user_model


User = get_user_model()


class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )


class SignUpForm(UserCreationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    email = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password1",
            "password2",
            "is_manager",
            "is_client",
        )


class NewSignUpForm(UserCreationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    email = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}))

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")


# Support Ticked for Client
class ClientSupportTicketForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = ["case_category", "case_subject", "client_contact_details"]


# Edit Profile Client ###################################3


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "client__birthdate",
            "client__phone",
            "client__address",
            "client__zip_code",
        ]

    first_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100, required=False)
    email = forms.EmailField(required=False)
    client__birthdate = forms.DateField(required=False)
    client__phone = forms.CharField(max_length=15, required=False)
    client__address = forms.CharField(widget=forms.Textarea, required=False)
    client__zip_code = forms.CharField(max_length=10, required=False)


# Form for the client to update his data
class UpdateClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            "first_name",
            "last_name",
            "birthdate",
            "phone",
            "address",
            "zip_code",
        ]
        widgets = {
            "birthdate": forms.DateInput(attrs={"type": "date"}),
        }


class Edit_Client_from_manager_Form(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            "client_number",
            "first_name",
            "last_name",
            "birthdate",
            "client_credits",
            "phone",
            "address",
            "zip_code",
        ]
        widgets = {
            "birthdate": forms.DateInput(attrs={"type": "date"}),
        }


# KYC Form
class KYCForm(forms.ModelForm):
    class Meta:
        model = KYC
        fields = [
            "government_name",
            "first_name",
            "last_name",
            "country",
            "birthdate",
            "id_front",
            "id_back",
        ]


# Edit KYC
class EditKYCForm(forms.ModelForm):
    class Meta:
        model = KYC
        fields = "__all__"


# Edit client wallets
class EditClientWalletForm(forms.ModelForm):
    class Meta:
        model = ClientWallet
        fields = "__all__"


############################################### Website ###########################################################################


class WebsiteForm(forms.ModelForm):
    class Meta:
        model = Website
        fields = [
            "name",
            "support_email",
            "description",
            "address",
            "phone",
            "about_us",
            "telegram",
            "whatsapp",
        ]


############################################## Case(Tickets) #######################################################################


class EditCaseForm(forms.ModelForm):
    class Meta:
        model = Case
        fields = "__all__"


# Edit Profile for manager
class EditProfileManagerForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]


# withdrawl form


class WithdrawalForm(forms.ModelForm):
    class Meta:
        model = Withdrawal
        fields = ["crypto_currency", "amount", "wallet_withdraw", "comment"]

    def __init__(self, *args, **kwargs):
        super(WithdrawalForm, self).__init__(*args, **kwargs)
        self.fields["crypto_currency"].widget = forms.Select(
            choices=[
                ("btc", "Bitcoin"),
                ("eth", "Ethereum"),
                ("spotbtc", "Spot Bitcoin"),
                ("usdt_erc20", "USDT ERC20"),
                ("usd_trc20", "USDT TRC20"),
            ]
        )


class DepositWalletNewForm(forms.ModelForm):
    class Meta:
        model = DepositWallet
        fields = "__all__"


class WithdrawalFormNew(forms.ModelForm):
    class Meta:
        model = Withdrawal
        fields = "__all__"


class DepositFormNew(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = "__all__"


class WithdrawalMessageFormNew(forms.ModelForm):
    class Meta:
        model = WithdrawalMessage
        fields = "__all__"
