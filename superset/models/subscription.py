from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, \
    Text
from sqlalchemy.orm import relationship
from flask_appbuilder.security.sqla.models import User
from flask_appbuilder import Model
import datetime


# Plan definitions
class SubscriptionPlan(Model):
    __tablename__ = 'subscription_plans'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    price = Column(Float, nullable=False)
    billing_cycle = Column(String(20),
                           nullable=False)  # 'monthly', 'quarterly', 'yearly'
    features = Column(Text)  # JSON string of features
    is_active = Column(Boolean, default=True)
    created_on = Column(DateTime, default=datetime.datetime.now)

    subscriptions = relationship('UserSubscription', back_populates='plan')

    def __repr__(self):
        return self.name


# User subscriptions
class UserSubscription(Model):
    __tablename__ = 'user_subscriptions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('ab_user.id'), nullable=False)
    plan_id = Column(Integer, ForeignKey('subscription_plans.id'), nullable=False)
    status = Column(String(20),
                    nullable=False)  # 'active', 'trial', 'expired', 'cancelled'
    start_date = Column(DateTime, nullable=False, default=datetime.datetime.now)
    end_date = Column(DateTime)
    is_auto_renew = Column(Boolean, default=True)
    external_subscription_id = Column(String(255), nullable=True)

    # Relationships
    user = relationship('User', backref='subscriptions')
    plan = relationship('SubscriptionPlan', back_populates='subscriptions')
    payments = relationship('Payment', back_populates='subscription')

    def is_valid(self):
        now = datetime.datetime.now()
        return (self.status == 'active' or self.status == 'trial') and \
            (self.end_date is None or now <= self.end_date)


# Payment history
class Payment(Model):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True)
    subscription_id = Column(Integer, ForeignKey('user_subscriptions.id'))
    user_id = Column(Integer, ForeignKey('ab_user.id'), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default='USD')
    payment_date = Column(DateTime, default=datetime.datetime.now)
    payment_method = Column(String(50))  # 'credit_card', 'paypal', etc.
    transaction_id = Column(String(255))  # External payment processor ID
    status = Column(String(20))  # 'success', 'failed', 'pending', 'refunded'

    # Relationships
    subscription = relationship('UserSubscription', back_populates='payments')
    user = relationship('User', backref='payments')


# Payment methods for recurring billing
class PaymentMethod(Model):
    __tablename__ = 'payment_methods'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('ab_user.id'), nullable=False)
    method_type = Column(String(50), nullable=False)  # 'credit_card', 'paypal', etc.
    token = Column(String(255))  # Token from payment processor
    is_default = Column(Boolean, default=False)
    last_digits = Column(String(4))  # For display purposes
    expiry_date = Column(String(7))  # MM/YYYY
    created_on = Column(DateTime, default=datetime.datetime.now)

    # Relationships
    user = relationship('User', backref='payment_methods')
