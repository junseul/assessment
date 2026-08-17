from django import forms


def digits_only(value):
    return ''.join(ch for ch in (value or '') if ch.isdigit())


class VerifyForm(forms.Form):
    name = forms.CharField(label='이름', max_length=100)
    birthdate = forms.DateField(label='생년월일', widget=forms.DateInput(attrs={'type': 'date'}))
    phone = forms.CharField(
        label='연락처',
        max_length=20,
        widget=forms.TextInput(attrs={'type': 'tel'}),
    )

    def clean_name(self):
        return self.cleaned_data['name'].strip()

    def clean_phone(self):
        return self.cleaned_data['phone'].strip()
