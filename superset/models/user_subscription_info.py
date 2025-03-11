
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from flask_appbuilder import Model

class UserSubscriptionInfo(Model):
    """
    Model for user subscription information.
    This is a proxy model that connects to the ab_user table
    to manage subscription fields.
    """
    __tablename__ = 'user_subscription_info'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('ab_user.id'), nullable=False)
    is_paid_user = Column(Boolean, default=False)
    trial_used = Column(Boolean, default=False)
    stripe_customer_id = Column(String(255))
    
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"UserSubscriptionInfo(user_id={self.user_id}, is_paid_user={self.is_paid_user})"
