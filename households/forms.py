from django import forms
from django.contrib.auth import get_user_model

from .models import MemberProfile

User = get_user_model()


class MemberCreationForm(forms.Form):
    username = forms.CharField(max_length=150)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    allowed_from_time = forms.TimeField(help_text="Start of allowed window")
    allowed_to_time = forms.TimeField(help_text="End of allowed window")
    active = forms.BooleanField(required=False, initial=True)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match")
        return cleaned

    def save(self, household):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password1"],
            role=User.Roles.MEMBER,
        )
        MemberProfile.objects.create(
            user=user,
            household=household,
            allowed_from_time=self.cleaned_data["allowed_from_time"],
            allowed_to_time=self.cleaned_data["allowed_to_time"],
            active=self.cleaned_data.get("active", False),
        )
        return user


class MemberProfileForm(forms.ModelForm):
    class Meta:
        model = MemberProfile
        fields = ["allowed_from_time", "allowed_to_time", "active"]
