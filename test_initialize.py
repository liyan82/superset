#!/usr/bin/env python

"""
Test script to verify that the application can initialize properly
without circular dependency issues.
"""

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

# Import the models that were involved in the circular dependency
from superset.models.user_attributes import UserAttribute
from superset.models.dashboard import Dashboard
from superset.models.subscription import SubscriptionPlan, UserSubscription, Payment

def test_model_initialization():
    """Test that models can be imported and initialized without circular dependency issues."""
    print("Testing model initialization...")
    
    # Create a simple Flask app
    app = Flask(__name__)
    
    # Set up a SQLAlchemy session for testing
    engine = create_engine("sqlite:///:memory:")
    session_factory = sessionmaker(bind=engine)
    Session = scoped_session(session_factory)
    
    # Try to create instances of the models
    try:
        user_attr = UserAttribute()
        dashboard = Dashboard()
        subscription_plan = SubscriptionPlan()
        
        print("Models initialized successfully!")
        return True
    except Exception as e:
        print(f"Error initializing models: {e}")
        return False

if __name__ == "__main__":
    success = test_model_initialization()
    if success:
        print("Circular dependency issue fixed successfully!")
    else:
        print("Circular dependency issue still exists.")
