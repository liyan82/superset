from flask_appbuilder import ModelView
from flask_appbuilder.models.sqla.interface import SQLAInterface

from superset.models.subscription import Payment, SubscriptionPlan, UserSubscription


class SubscriptionPlanAdmin(ModelView):
    datamodel = SQLAInterface(SubscriptionPlan)
    list_columns = ["name", "price", "billing_cycle", "is_active"]
    add_columns = ["name", "description", "price", "billing_cycle", "features",
                   "is_active"]
    edit_columns = ["name", "description", "price", "billing_cycle", "features",
                    "is_active"]
    show_columns = ["name", "description", "price", "billing_cycle", "features",
                    "is_active", "created_on"]


class UserSubscriptionAdmin(ModelView):
    datamodel = SQLAInterface(UserSubscription)
    list_columns = ["user", "plan", "status", "start_date", "end_date"]
    add_columns = ["user", "plan", "status", "start_date", "end_date", "is_auto_renew"]
    edit_columns = ["status", "end_date", "is_auto_renew"]
    show_columns = ["user", "plan", "status", "start_date", "end_date", "is_auto_renew"]


class PaymentAdmin(ModelView):
    datamodel = SQLAInterface(Payment)
    list_columns = ["user", "amount", "payment_date", "payment_method", "status"]
    show_columns = ["user", "subscription", "amount", "currency", "payment_date",
                    "payment_method", "transaction_id", "status"]
    # Typically, payments shouldn't be editable
    base_permissions = ["can_list", "can_show"]
