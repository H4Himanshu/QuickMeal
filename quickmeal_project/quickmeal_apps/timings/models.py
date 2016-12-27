from __future__ import unicode_literals

from django.db import models

class FoodTiming(models.Model):
    FOOD_CHOICES = (
        ('Breakfast', 'Breakfast'),
        ('Lunch', 'Lunch'),
        ('Dinner', 'Dinner'),        
    )
    food = models.CharField(max_length=10, choices=FOOD_CHOICES)
    start_time = models.TimeField(blank=True)
    end_time = models.TimeField(blank=True)

    def __unicode__(self):
        return u"{}".format(self.food)