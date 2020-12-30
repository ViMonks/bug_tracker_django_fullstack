from django.contrib.auth import forms, get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.forms import fields, TextInput

from allauth.account.forms import SignupForm

User = get_user_model()


class UserChangeForm(forms.UserChangeForm):
    class Meta(forms.UserChangeForm.Meta):
        model = User


class UserCreationForm(forms.UserCreationForm):

    error_message = forms.UserCreationForm.error_messages.update(
        {"duplicate_username": _("This username has already been taken.")}
    )

    class Meta(forms.UserCreationForm.Meta):
        model = User

    def clean_username(self):
        username = self.cleaned_data["username"]

        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            return username

        raise ValidationError(self.error_messages["duplicate_username"])


class MySignupForm(SignupForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'] = fields.CharField(label='Name', widget=TextInput(attrs={'placeholder': 'Your full name'}))
        original_fields = self.fields
        new_order = {}
        for key in ['email', 'username', 'name', 'password1', 'password2']:
                if key in original_fields:
                    new_order[key] = original_fields[key]
        self.fields = new_order

    def save(self, request):
        user = super(MySignupForm, self).save(request)
        user.name = self.cleaned_data.pop('name')
        user.save()
        return user
