import datetime

from flask_appbuilder import BaseView, expose, has_access
from flask_appbuilder.views import ModelView
from flask import redirect, url_for, request, flash, g
from flask_babel import lazy_gettext as _

from superset.models.subscription import SubscriptionPlan, UserSubscription, Payment


class SubscriptionView(BaseView):
    route_base = "/subscription"
    default_view = "plans"  # Set the default view to the plans method
    
    @expose('/plans')
    def plans(self):
        """Show available subscription plans"""
        plans = self.appbuilder.session.query(SubscriptionPlan).filter_by(
            is_active=True).all()
        return self.render_template('subscription/plans.html',
                                    plans=plans,
                                    user=g.user)

    @expose('/subscribe/<int:plan_id>', methods=['GET', 'POST'])
    @has_access
    def subscribe(self, plan_id):
        """Process new subscription"""
        plan = self.appbuilder.session.query(SubscriptionPlan).get(plan_id)
        if not plan:
            flash(_("Invalid subscription plan"), "danger")
            return redirect(url_for('.plans'))

        if request.method == 'POST':
            # Process payment form data
            payment_method = request.form.get('payment_method')

            # Integrate with payment processor (simplified)
            success, transaction_id = self.process_payment(plan, payment_method)

            if success:
                # Create subscription
                end_date = datetime.datetime.now() + self.calc_subscription_period(plan)
                subscription = UserSubscription(
                    user_id=g.user.id,
                    plan_id=plan.id,
                    status='active',
                    start_date=datetime.datetime.now(),
                    end_date=end_date,
                    is_auto_renew=True
                )

                # Create payment record
                payment = Payment(
                    user_id=g.user.id,
                    amount=plan.price,
                    payment_method=payment_method,
                    transaction_id=transaction_id,
                    status='success'
                )

                # Update user status
                g.user.is_paid_user = True

                # Save to database
                self.appbuilder.session.add(subscription)
                self.appbuilder.session.add(payment)
                self.appbuilder.session.commit()

                flash(_("Subscription activated successfully!"), "success")
                return redirect(url_for('IndexView.index'))
            else:
                flash(_("Payment processing failed"), "danger")

        # GET request - show payment form
        return self.render_template('subscription/payment.html',
                                    plan=plan,
                                    user=g.user)

    @expose('/manage')
    @has_access
    def manage(self):
        """Manage existing subscription"""
        subscription = g.user.current_subscription
        return self.render_template('subscription/manage.html',
                                    subscription=subscription,
                                    user=g.user)

    @expose('/cancel', methods=['POST'])
    @has_access
    def cancel(self):
        """Cancel subscription"""
        subscription = g.user.current_subscription
        if subscription:
            subscription.status = 'cancelled'
            subscription.is_auto_renew = False
            self.appbuilder.session.commit()
            flash(_("Your subscription has been cancelled"), "success")
        return redirect(url_for('.manage'))

    # Helper methods
    def process_payment(self, plan, payment_method):
        """
        Integrate with payment processor (Stripe, PayPal, etc.)
        Returns (success, transaction_id)
        """
        # Implement actual payment processing here
        # This is where you'd integrate with Stripe, PayPal, etc.
        return True, f"TRANS-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    def calc_subscription_period(self, plan):
        """Calculate subscription end date based on billing cycle"""
        if plan.billing_cycle == 'monthly':
            return datetime.timedelta(days=30)
        elif plan.billing_cycle == 'quarterly':
            return datetime.timedelta(days=90)
        elif plan.billing_cycle == 'yearly':
            return datetime.timedelta(days=365)
        return datetime.timedelta(days=30)  # Default to monthly
