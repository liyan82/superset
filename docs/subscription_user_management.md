# Subscription User Management

This document describes the implementation of subscription-related fields in the user management module.

## Overview

The subscription functionality extends the Superset user model with fields that track subscription status:

- `is_paid_user`: Boolean flag indicating if the user has a paid subscription
- `trial_used`: Boolean flag indicating if the user has used their trial period
- `stripe_customer_id`: String field storing the Stripe customer ID for billing

## Implementation Details

### User Model Extension

The user model is extended via a mixin class (`UserSubscriptionMixin`) that adds the subscription fields to the existing Flask-AppBuilder user model.

### Custom User View

A custom `SubscriptionUserModelView` extends the standard Flask-AppBuilder `UserModelView` to include the subscription fields in the add, edit, show, and list views. This view is registered to replace the default user views during application initialization.

### Templates

Custom templates enhance the user interface for subscription fields, visually separating them in the add/edit forms.

## Usage

### Creating/Editing Users with Subscription Information

When creating or editing users, administrators will see the additional subscription fields at the bottom of the form. These fields allow tracking:

1. Whether the user has a paid subscription
2. Whether they've used their trial period
3. Their Stripe customer ID for billing integration

### Integration with Stripe

The `stripe_customer_id` field enables integration with Stripe for payment processing. When a user is marked as a paid user, the system expects a Stripe customer ID to be provided for billing purposes.

## Security Considerations

Access to subscription management is restricted to administrators through the standard Superset security model. The `SubscriptionSecurityManager` can enforce access controls based on subscription status.

## Future Enhancements

Potential enhancements could include:

1. Direct Stripe integration for creating/retrieving customer records
2. Subscription expiration date tracking
3. Automatic trial period management
4. Subscription level/tier tracking
5. Usage statistics and quota enforcement
