from oscar.core.loading import get_model
from django import template

from quickmeal_apps.timings.models import FoodTiming

from datetime import datetime
import pdb

register = template.Library()

@register.filter(name='buyable')
def buyable(value):
    current_time = datetime.time(datetime.now())
    attr_value_list = [item.value for item in value.attribute_values.all()]
    for item in attr_value_list:
        availability = FoodTiming.objects.get(food=item)
        if current_time > availability.start_time and current_time < availability.end_time:
            return True
        else:
            return False 