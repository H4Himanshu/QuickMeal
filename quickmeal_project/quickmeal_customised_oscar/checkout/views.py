from oscar.apps.checkout import views
from oscar.apps.payment import models

from quickmeal_project import settings

class PaymentDetailsView(views.PaymentDetailsView):
    def get_context_data(self, **kwargs):
        ctx = super(PaymentDetailsView, self).get_context_data(**kwargs)
        ctx['RAZORPAY_KEY_ID'] = settings.RAZORPAY_KEY_ID
        ctx['RAZORPAY_KEY_SECRET'] = settings.RAZORPAY_KEY_SECRET

        ctx['order_total_paise'] = (ctx['order_total'].excl_tax * 100)
        return ctx
