from oscar.apps.promotions.views import HomeView as CoreHomeView
from quickmeal_apps.locations.models import Cities, Location


from django.http import HttpResponse
import pdb, json

class HomeView(CoreHomeView):
    def get_context_data(self, **kwargs):
        if self.request.is_ajax():
            return self.ajax(self.request)

        ctx = super(HomeView, self).get_context_data(**kwargs)

        ctx['location_cities'] = Cities.objects.all()
        return ctx

    def ajax(self, request):
        # if "city_id" in self.request.GET.dict().keys():
        #     data = Location.objects.filter(city_id=self.request.GET.dict()["city_id"])
        data = {}
        data["response"] = 'Success'
        return HttpResponse(json.dumps(data), content_type = "application/json")