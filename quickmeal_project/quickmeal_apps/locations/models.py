from __future__ import unicode_literals

from django.db import models

class TimeStamp(models.Model):
    """An Abstract class which takes care of these 2 time stamp fields in child classes"""

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Cities(TimeStamp):
    city = models.CharField(max_length=255)

    def __unicode__(self):
        return u"{}".format(self.city)


class Location(TimeStamp):
    location = models.CharField(max_length=255)
    city = models.ForeignKey(Cities, related_name='location_city')

    def __unicode__(self):
        return u"{}".format(self.location)