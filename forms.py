from django import forms
from validations import validate_lon_geographical_coordinates, validate_lat_geographical_coordinates

class RoutingForm(forms.Form):
    origin_latitude = forms.DecimalField(label='Origin Latitide',validators=[validate_lat_geographical_coordinates])
    origin_longitude = forms.DecimalField(label='Origin Longitude',validators=[validate_lon_geographical_coordinates])
    destination_latitude = forms.DecimalField(label='Destination Latitide',validators=[validate_lat_geographical_coordinates])
    destination_longitude = forms.DecimalField(label='Destination Longitude',validators=[validate_lon_geographical_coordinates])


