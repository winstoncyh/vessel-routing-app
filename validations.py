from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_lat_geographical_coordinates(value):
    if abs(value)>90:
        raise ValidationError(
            _('%(value)s is not a valid geographical coordinate'),
            params={'value': value},
        )

def validate_lon_geographical_coordinates(value):
    if abs(value)>180:
        raise ValidationError(
            _('%(value)s is not a valid geographical coordinate'),
            params={'value': value},
        )