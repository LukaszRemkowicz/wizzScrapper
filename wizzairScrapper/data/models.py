from django.db import models


COUNTRIES = (
    ('Katowice', "KTW"),
    ('Tenerife', 'TFS'),
)


class WizzOffers(models.Model):
    url = models.CharField(max_length=2000, null=True, unique=True)
    destination = models.CharField(max_length=50, choices=COUNTRIES)
    created = models.DateTimeField(auto_created=True, auto_now_add=True)
