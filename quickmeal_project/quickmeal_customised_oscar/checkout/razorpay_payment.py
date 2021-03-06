from __future__ import unicode_literals
from decimal import Decimal as D
import logging

from django.views.generic import RedirectView, View
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.http import urlencode
from django.utils import six
from django.utils.translation import ugettext_lazy as _

import oscar
from oscar.apps.payment.exceptions import UnableToTakePayment
from oscar.core.exceptions import ModuleNotFoundError
from oscar.core.loading import get_class, get_model
from oscar.apps.shipping.methods import FixedPrice, NoShippingRequired

from urlparse import parse_qs, urlparse

from django.conf import settings
from django.template import loader,RequestContext
from django.shortcuts import render, render_to_response

import razorpay

# Load views dynamically
PaymentDetailsView = get_class('checkout.views', 'PaymentDetailsView')
CheckoutSessionMixin = get_class('checkout.session', 'CheckoutSessionMixin')

ShippingAddress = get_model('order', 'ShippingAddress')
Country = get_model('address', 'Country')
Basket = get_model('basket', 'Basket')
Repository = get_class('shipping.repository', 'Repository')
Selector = get_class('partner.strategy', 'Selector')
Source = get_model('payment', 'Source')
SourceType = get_model('payment', 'SourceType')
try:
    Applicator = get_class('offer.applicator', 'Applicator')
except ModuleNotFoundError:
    # fallback for django-oscar<=1.1
    Applicator = get_class('offer.utils', 'Applicator')

class SuccessResponseView(PaymentDetailsView):
    template_name = 'checkout/payment_details.html'
    template_name_preview = 'checkout/preview.html'
    preview = False

    @property
    def pre_conditions(self):
        return []

    def get(self, request, *args, **kwargs):
        """
        Fetch details about the successful transaction from PayPal.  We use
        these details to show a preview of the order with a 'submit' button to
        place it.
        """
        try:
            print request.GET
            # self.payer_id = request.GET['PayerID']
            # self.token = request.GET['token']
        except KeyError:
            # Manipulation - redirect to basket page with warning message
            logger.warning("Missing GET params on success response page")
            messages.error(
                self.request,
                _("Unable to determine PayPal transaction details"))
            return HttpResponseRedirect(reverse('basket:summary'))

        # Reload frozen basket which is specified in the URL
        kwargs['basket'] = self.load_frozen_basket(kwargs['basket_id'])
        if not kwargs['basket']:
            logger.warning(
                "Unable to load frozen basket with ID %s", kwargs['basket_id'])
            messages.error(
                self.request,
                _("No basket was found that corresponds to your "
                  "PayPal transaction"))
            return HttpResponseRedirect(reverse('basket:summary'))

        logger.info(
            "Basket #%s - showing preview with payer ID %s and token %s",
            kwargs['basket'].id, self.payer_id, self.token)

        return super(SuccessResponseView, self).get(request, *args, **kwargs)

    def load_frozen_basket(self, basket_id):
        # Lookup the frozen basket that this txn corresponds to
        try:
            basket = Basket.objects.get(id=basket_id, status=Basket.FROZEN)
        except Basket.DoesNotExist:
            basket = Basket.objects.get(id=basket_id)
            return None

        # Assign strategy to basket instance
        if Selector:
            basket.strategy = Selector().strategy(self.request)

        # Re-apply any offers
        Applicator().apply(request=self.request, basket=basket)

        return basket

    def get_context_data(self, **kwargs):
        ctx = super(SuccessResponseView, self).get_context_data(**kwargs)

        if not hasattr(self, 'payer_id'):
            return ctx
        return ctx

    def post(self, request, *args, **kwargs):
        """
        Place an order.

        We fetch the txn details again and then proceed with oscar's standard
        payment details view for placing the order.
        """
        error_msg = _(
            "A problem occurred communicating with CCAvenue "
            "- please try again later"
        )
        try:
            payment_id = request.body.split('&')[2].split('=')[1]
            amount = int(request.basket.total_incl_tax_excl_discounts)
            currency = request.basket.currency
            basket_id = request.basket.id

            razorpay_api_key = settings.RAZORPAY_KEY_ID
            razorpay_api_secret = settings.RAZORPAY_KEY_SECRET
            razor = razorpay.Client(auth=(razorpay_api_key, razorpay_api_secret))
            razorpay_data = razor.payment.fetch(payment_id)
            razorpay_amount = (float(razorpay_data['amount'])/100)
            razorpay_details = {'payment_id':payment_id, 'amount':razorpay_amount, 'currency':currency, 
                    'email':razorpay_data['email'], 'contact':razorpay_data['contact']}

            if payment_id:
                pass
            else:
                messages.error(self.request, error_msg)
                return HttpResponseRedirect(reverse('basket:summary'))

        except KeyError:
            # Probably suspicious manipulation if we get here
            messages.error(self.request, error_msg)
            return HttpResponseRedirect(reverse('basket:summary'))

        # Reload frozen basket which is specified in the URL
        # basket = self.load_frozen_basket(kwargs['basket_id'])
        basket = request.basket
        if not basket:
            messages.error(self.request, error_msg)
            return HttpResponseRedirect(reverse('basket:summary'))

        submission = self.build_submission(basket=basket, context={'payment_id': payment_id, 'email': razorpay_details['email'], 'payment_amount': razorpay_amount})
        return self.submit(**submission)

    def build_submission(self, **kwargs):
        email = kwargs['context']['email']
        payment_id = kwargs['context']['payment_id']
        payment_amount = kwargs['context']['payment_amount']
        kwargs.pop('context')
        
        submission = super(
            SuccessResponseView, self).build_submission(**kwargs)

        submission['order_kwargs']['email'] = email
        submission['payment_kwargs']['payment_id'] = payment_id
        submission['payment_kwargs']['payment_amount'] = payment_amount         
        return submission

    def handle_payment(self, order_number, total, **kwargs):
        """
        Complete payment with Razorpay.
        """
        try:
            pass
        except PayPalError:
            raise UnableToTakePayment()
        # if not confirm_txn.is_successful:
        #     raise UnableToTakePayment()

        # Record payment source and event
        source_type, is_created = SourceType.objects.get_or_create(
            name='Razorpay')
        source = Source(source_type=source_type,
                        currency=total.currency,
                        amount_allocated=kwargs['payment_amount'],
                        amount_debited=kwargs['payment_amount'])
        self.add_payment_source(source)
        self.add_payment_event('complete', kwargs['payment_amount'] ,
                               reference=kwargs['payment_id'])
