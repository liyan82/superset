/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

import { useCallback, useEffect, useState } from 'react';
import { useHistory } from 'react-router-dom';
import { t } from '@superset-ui/core';
import { styled } from '@apache-superset/core/ui';
import { useToasts } from 'src/components/MessageToasts/withToasts';
import { SupersetClient } from '@superset-ui/core';
import { UserWithPermissionsAndRoles } from 'src/types/bootstrapTypes';
import { Modal } from 'antd';

// Unified styled component that replicates the exact styling from plans.html template
const StyledPlansPage = styled.div`
  /* Subscription plans specific styles */
  .subscription-plans {
    padding-top: 20px;
    padding-bottom: 40px;
  }
  
  .plan-row {
    display: flex;
    justify-content: center;
    flex-wrap: nowrap; /* Prevent wrapping */
    margin-left: -15px;
    margin-right: -15px;
    padding-top: 5px; /* Add space for hover effect */
  }
  
  .plan-col {
    display: flex; /* This makes columns of equal height in a flex row */
    padding-left: 15px;
    padding-right: 15px;
    margin-bottom: 30px;
    flex: 0 1 320px; /* Allow cards to shrink but not grow */
  }
  
  .plan-card {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    transition: all 0.3s ease;
    width: 100%; /* Take full width of the column */
    display: flex;
    flex-direction: column;
    background-color: #fff;
    
    &:hover {
      transform: translateY(-5px);
      box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    .panel-heading {
      background-color: #283E53; /* Dark blue from login page */
      color: white;
      border-top-left-radius: 8px;
      border-top-right-radius: 8px;
      padding: 10px 15px;
      border-bottom: 1px solid transparent;
      
      .panel-title {
        margin: 0;
        font-size: 16px;
        font-weight: 500;
      }
    }
    
    .panel-body {
      padding: 20px;
      flex-grow: 1;
      display: flex;
      flex-direction: column;
      text-align: center;
    }
    
    .plan-price {
      font-size: 2.5rem;
      font-weight: bold;
      margin: 10px 0;
      
      .plan-price-cycle {
        font-size: 1rem;
        color: #6c757d;
      }
    }
    
    .features-list {
      margin: 20px 0;
      flex-grow: 1;
      list-style: none;
      padding: 0;
      text-align: left;
      
      li {
        margin-bottom: 10px;
        
        i {
          margin-right: 8px;
        }
      }
    }
  }
  
  .btn-subscribe {
    background-color: #00af9e; /* Teal from screenshot */
    border-color: #00af9e;
    border-radius: 6px;
    padding: 10px;
    font-size: 16px;
    font-weight: 600;
    color: white;
    border: 1px solid #00af9e;
    cursor: pointer;
    transition: all 0.3s ease;
    width: 100%;
    display: block;
    text-align: center;
    text-decoration: none;
    
    &:hover {
      background-color: #008c7e;
      border-color: #008c7e;
      color: white;
      text-decoration: none;
    }
    
    &:disabled {
      background-color: #ccc;
      border-color: #ccc;
      cursor: not-allowed;
      color: #666;
    }
  }
  
  /* Flash messages */
  .flash-container {
    padding: 0;
    
    .flash-message {
      background-color: #f8f9fa;
      border: 1px solid #dee2e6;
      color: #212529;
      font-size: 1.1em;
      font-weight: 500;
      padding: 20px;
      border-radius: 8px;
      margin-bottom: 30px;
      text-align: center;
    }
  }
  
  /* Bootstrap styles */
  .alert-info {
    color: #31708f;
    background-color: #d9edf7;
    border-color: #bce8f1;
    padding: 15px;
    margin-bottom: 20px;
    border: 1px solid transparent;
    border-radius: 4px;
  }
  
  .btn {
    display: inline-block;
    padding: 6px 12px;
    margin-bottom: 0;
    font-size: 14px;
    font-weight: 400;
    line-height: 1.42857143;
    text-align: center;
    white-space: nowrap;
    vertical-align: middle;
    touch-action: manipulation;
    cursor: pointer;
    user-select: none;
    background-image: none;
    border: 1px solid transparent;
    border-radius: 4px;
    text-decoration: none;
    
    &:hover {
      text-decoration: none;
    }
  }
  
  .btn-primary {
    color: #fff;
    background-color: #337ab7;
    border-color: #2e6da4;
    
    &:hover {
      background-color: #286090;
      border-color: #204d74;
    }
  }
  
  .btn-block {
    display: block;
    width: 100%;
  }
  
  .btn-lg {
    padding: 10px 16px;
    font-size: 18px;
    line-height: 1.3333333;
    border-radius: 6px;
  }
  
  .list-unstyled {
    padding-left: 0;
    list-style: none;
  }
  
  .text-left {
    text-align: left;
  }
  
  .text-center {
    text-align: center;
  }
  
  .text-success {
    color: #5cb85c;
  }
  
  .text-info {
    color: #5bc0de;
  }
  
  .lead {
    margin-bottom: 20px;
    font-size: 16px;
    font-weight: 300;
    line-height: 1.4;
  }
  
  .container {
    padding-right: 15px;
    padding-left: 15px;
    margin-right: auto;
    margin-left: auto;
    max-width: 1170px;
  }
  
  .row {
    margin-left: -15px;
    margin-right: -15px;
  }
  
  .col-md-10 {
    position: relative;
    min-height: 1px;
    padding-left: 15px;
    padding-right: 15px;
    width: 83.33333333%;
    float: left;
  }
  
  .col-md-offset-1 {
    margin-left: 8.33333333%;
  }
  
  .col-md-12 {
    position: relative;
    min-height: 1px;
    padding-left: 15px;
    padding-right: 15px;
    width: 100%;
    float: left;
  }
`;

interface SubscriptionPlan {
  id: string;
  product_id: string;
  name: string;
  description: string;
  price: number;
  billing_cycle: string;
  features: string[];
  is_active: boolean;
}

interface SubscriptionStatus {
  status: string;
  subscription: any;
  has_active_subscription: boolean;
}

interface SubscriptionPlansProps {
  user?: UserWithPermissionsAndRoles;
}

export default function SubscriptionPlans({ user }: SubscriptionPlansProps) {
  const history = useHistory();
  const { addDangerToast, addSuccessToast } = useToasts();
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [userStatus, setUserStatus] = useState<SubscriptionStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [subscribingToPlan, setSubscribingToPlan] = useState<string | null>(null);
  const [showReactivationModal, setShowReactivationModal] = useState(false);
  const [planToReactivate, setPlanToReactivate] = useState<string | null>(null);
  const [showPlanSwitchModal, setShowPlanSwitchModal] = useState(false);
  const [planToSwitch, setPlanToSwitch] = useState<string | null>(null);

  // Helper function to check if user is subscribing to the same plan they previously cancelled
  const isSameCancelledPlan = useCallback((planId: string) => {
    return userStatus?.subscription?.status === 'cancelled' && 
           userStatus.subscription?.plan?.product_id === planId;
  }, [userStatus]);

  // Helper function to check if user is subscribing to a different plan they previously cancelled
  const isDifferentCancelledPlan = useCallback((planId: string) => {
    return userStatus?.subscription?.status === 'cancelled' && 
           userStatus.subscription?.plan?.product_id !== planId;
  }, [userStatus]);

  const checkUserStatus = useCallback(async () => {
    try {
      const response = await SupersetClient.get({
        endpoint: '/subscription/api/status',
      });
      const status = response.json as SubscriptionStatus;
      setUserStatus(status);
      
      // If user has active subscription, redirect to manage page
      if (status.has_active_subscription) {
        history.push('/subscription/manage');
        return;
      }
      
      return status;
    } catch (error) {
      console.error('Error checking user status via API:', error);
      
      // Fallback: assume no active subscription for now
      const fallbackStatus = {
        status: "none",
        subscription: null,
        has_active_subscription: false
      };
      setUserStatus(fallbackStatus);
      return fallbackStatus;
    }
  }, [addDangerToast]);

  const fetchPlans = useCallback(async () => {
    try {
      // Try new API first
      const response = await SupersetClient.get({
        endpoint: '/subscription/api/plans',
      });
      
      const data = response.json;
      setPlans(data.plans || []);
      setError(null);
    } catch (error) {
      console.error('Error fetching plans via new API, trying legacy endpoint:', error);
      
      try {
        // Fallback to legacy endpoint (now JSON-only)
        const response = await SupersetClient.get({
          endpoint: '/subscription/plans',
        });
        
        const data = response.json;
        if (data.redirect) {
          // Use React Router navigation to stay in React app
          if (data.redirect.includes('/subscription/manage')) {
            history.push('/subscription/manage');
          } else if (data.redirect.includes('/subscription/plans')) {
            history.push('/subscription/plans');
          } else {
            window.location.href = data.redirect;
          }
          return;
        }
        
        // Handle the data from legacy endpoint
        setPlans(data.plans || []);
        setError(null);
        
        // Handle flash messages from backend
        if (data.message) {
          if (data.message_type === 'info') {
            addSuccessToast(data.message);
          } else if (data.message_type === 'warning') {
            addDangerToast(data.message);
          }
        }
      } catch (fallbackError) {
        console.error('Error fetching plans via fallback:', fallbackError);
        setError(t('Error loading subscription plans. Please try again later.'));
        addDangerToast(t('Error loading subscription plans. Please try again later.'));
      }
    }
  }, [addDangerToast, addSuccessToast]);

  const initializePage = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Check user status first
      let status;
      try {
        status = await checkUserStatus();
      } catch (error) {
        console.error('User status check failed, continuing anyway:', error);
        // Don't fail completely, just assume no active subscription
        status = { status: "none", subscription: null, has_active_subscription: false };
      }
      
      // If we get here, user doesn't have active subscription, so fetch plans
      if (status && !status.has_active_subscription) {
        try {
          await fetchPlans();
          
          // Show appropriate message based on status
          if (status.subscription?.status === 'cancelled') {
            addSuccessToast(
              t('Your subscription has been cancelled and will expire on %s. Please subscribe to a new plan below.', 
                status.subscription.end_date ? new Date(status.subscription.end_date).toLocaleDateString() : 'N/A'
              )
            );
          } else if (!status.subscription) {
            addSuccessToast(t('Choose a plan below to get started with your subscription.'));
          }
        } catch (error) {
          console.error('Failed to fetch plans:', error);
          setError(t('Error loading subscription plans. Please try refreshing the page.'));
        }
      }
    } catch (error) {
      console.error('Error initializing page:', error);
      setError(t('Error initializing page. Please refresh and try again.'));
    } finally {
      setLoading(false);
    }
  }, [checkUserStatus, fetchPlans, addSuccessToast]);

  useEffect(() => {
    initializePage();
  }, [initializePage]);

  const handleSubscribe = async (planId: string) => {
    if (subscribingToPlan) return; // Prevent double-clicking
    
    // Check if user is subscribing to the same plan they previously cancelled
    if (isSameCancelledPlan(planId)) {
      setPlanToReactivate(planId);
      setShowReactivationModal(true);
      return;
    }
    
    // Check if user is subscribing to a different plan they previously cancelled
    if (isDifferentCancelledPlan(planId)) {
      setPlanToSwitch(planId);
      setShowPlanSwitchModal(true);
      return;
    }
    
    setSubscribingToPlan(planId);
    try {
      // Call backend subscribe endpoint with JSON request
      const response = await SupersetClient.get({
        endpoint: `/subscription/subscribe/${planId}`,
        headers: {
          'Accept': 'application/json',
        },
      });
      
      const data = response.json as any;
      
      // Handle response from backend
      if (data.redirect) {
        // Show message if provided
        if (data.message) {
          if (data.message_type === 'info') {
            addSuccessToast(data.message);
          } else if (data.message_type === 'warning' || data.message_type === 'danger') {
            addDangerToast(data.message);
          }
        }
        
        // Navigate using React Router to stay in React app
        const redirectPath = data.redirect;
        if (redirectPath.includes('/subscription/manage')) {
          setTimeout(() => history.push('/subscription/manage'), data.message ? 1500 : 0);
        } else if (redirectPath.includes('/subscription/payment/')) {
          // Extract plan ID from redirect URL
          const match = redirectPath.match(/\/subscription\/payment\/(.+)/);
          const redirectPlanId = match ? match[1] : planId;
          setTimeout(() => history.push(`/subscription/payment/${redirectPlanId}`), data.message ? 1500 : 0);
        } else if (redirectPath.includes('/subscription/plans')) {
          setTimeout(() => history.push('/subscription/plans'), data.message ? 1500 : 0);
        } else {
          // Fallback to window.location for external or unknown redirects
          setTimeout(() => window.location.href = redirectPath, data.message ? 1500 : 0);
        }
      } else {
        // Fallback: direct navigation to payment page
        history.push(`/subscription/payment/${planId}`);
      }
    } catch (error) {
      console.error('Error initiating subscription:', error);
      addDangerToast(t('Error starting subscription process. Please try again.'));
      setSubscribingToPlan(null);
    }
  };

  const handleConfirmReactivation = async () => {
    if (!planToReactivate) return;
    
    setShowReactivationModal(false);
    setSubscribingToPlan(planToReactivate);
    
    try {
      // Call backend subscribe endpoint with JSON request
      const response = await SupersetClient.get({
        endpoint: `/subscription/subscribe/${planToReactivate}`,
        headers: {
          'Accept': 'application/json',
        },
      });
      
      const data = response.json as any;
      
      // Handle response from backend
      if (data.redirect) {
        // Show message if provided
        if (data.message) {
          if (data.message_type === 'info') {
            addSuccessToast(data.message);
          } else if (data.message_type === 'warning' || data.message_type === 'danger') {
            addDangerToast(data.message);
          }
        }
        
        // Navigate using React Router to stay in React app
        const redirectPath = data.redirect;
        if (redirectPath.includes('/subscription/manage')) {
          setTimeout(() => history.push('/subscription/manage'), data.message ? 1500 : 0);
        } else if (redirectPath.includes('/subscription/payment/')) {
          // Extract plan ID from redirect URL
          const match = redirectPath.match(/\/subscription\/payment\/(.+)/);
          const redirectPlanId = match ? match[1] : planToReactivate;
          setTimeout(() => history.push(`/subscription/payment/${redirectPlanId}`), data.message ? 1500 : 0);
        } else if (redirectPath.includes('/subscription/plans')) {
          setTimeout(() => history.push('/subscription/plans'), data.message ? 1500 : 0);
        } else {
          // Fallback to window.location for external or unknown redirects
          setTimeout(() => window.location.href = redirectPath, data.message ? 1500 : 0);
        }
      } else {
        // Fallback: direct navigation to payment page
        history.push(`/subscription/payment/${planToReactivate}`);
      }
    } catch (error) {
      console.error('Error reactivating subscription:', error);
      addDangerToast(t('Error reactivating subscription. Please try again.'));
    } finally {
      setSubscribingToPlan(null);
      setPlanToReactivate(null);
    }
  };

  const handleCancelReactivation = () => {
    setShowReactivationModal(false);
    setPlanToReactivate(null);
  };

  const handleConfirmPlanSwitch = async () => {
    if (!planToSwitch) return;
    
    setShowPlanSwitchModal(false);
    setSubscribingToPlan(planToSwitch);
    
    try {
      // Call new plan switch API directly (bypasses payment page)
      const response = await SupersetClient.post({
        endpoint: '/subscription/api/switch-plan',
        headers: {
          'Content-Type': 'application/json',
        },
        jsonPayload: {
          plan_id: planToSwitch,
        },
      });
      
      const data = response.json as any;
      
      if (data.success) {
        // Show success message
        addSuccessToast(data.message || t('Plan switched successfully!'));
        
        // Navigate to manage page after brief delay
        setTimeout(() => history.push('/subscription/manage'), 1500);
      } else {
        // Handle error response
        addDangerToast(data.error || t('Error switching subscription plan. Please try again.'));
      }
    } catch (error) {
      console.error('Error switching subscription plan:', error);
      const errorMessage = error instanceof Error ? error.message : t('Error switching subscription plan. Please try again.');
      addDangerToast(errorMessage);
    } finally {
      setSubscribingToPlan(null);
      setPlanToSwitch(null);
    }
  };

  const handleCancelPlanSwitch = () => {
    setShowPlanSwitchModal(false);
    setPlanToSwitch(null);
  };

  if (loading) {
    return (
      <StyledPlansPage>
        <div id="app-menu"></div>
        <div className="container subscription-plans">
          <div style={{ textAlign: 'center', padding: '50px' }}>
            {t('Loading subscription plans...')}
          </div>
        </div>
      </StyledPlansPage>
    );
  }

  if (error) {
    return (
      <StyledPlansPage>
        <div id="app-menu"></div>
        <div className="container subscription-plans">
          <div className="container flash-container">
            <div className="row">
              <div className="col-md-10 col-md-offset-1">
                <div className="flash-message" role="alert">
                  {error}
                </div>
              </div>
            </div>
          </div>
          <div style={{ textAlign: 'center', marginTop: '20px' }}>
            <button
              type="button"
              onClick={() => initializePage()}
              className="btn btn-primary"
            >
              {t('Retry')}
            </button>
          </div>
        </div>
      </StyledPlansPage>
    );
  }

  return (
    <StyledPlansPage>
      <div id="app-menu"></div>
      
      {/* Flash messages section - exactly like the original template */}
      <div className="container flash-container">
        {userStatus && userStatus.subscription?.status === 'cancelled' && (
          <div className="row">
            <div className="col-md-10 col-md-offset-1">
              <div className="flash-message" role="alert">
                {t('Your subscription has been cancelled and will expire on %s. Please subscribe to a new plan below.', 
                  userStatus.subscription.end_date ? new Date(userStatus.subscription.end_date).toLocaleDateString() : 'N/A'
                )}
              </div>
            </div>
          </div>
        )}
        {userStatus && !userStatus.subscription && (
          <div className="row">
            <div className="col-md-10 col-md-offset-1">
              <div className="flash-message" role="alert">
                {t('Choose a plan below to get started with your subscription.')}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="container subscription-plans">
        <div className="text-center">
          <h1>{t('Subscription Plans')}</h1>
          <p className="lead">{t('Choose the plan that\'s right for you and unlock powerful features.')}</p>
        </div>
        <br/>
        
        <div className="row plan-row">
          {plans.length > 0 ? (
            plans.map((plan) => (
              <div key={plan.id} className="plan-col">
                <div className="panel plan-card">
                  <div className="panel-heading">
                    <h3 className="panel-title text-center">{plan.name}</h3>
                  </div>
                  <div className="panel-body text-center">
                    <p>{plan.description}</p>
                    <div className="plan-price">
                      ${plan.price.toFixed(2)}
                      <span className="plan-price-cycle">/ {plan.billing_cycle}</span>
                    </div>
                    
                    <ul className="list-unstyled features-list text-left">
                      {plan.features && plan.features.length > 0 ? (
                        plan.features.map((feature, index) => (
                          <li key={index}>
                            <i className="fa fa-check text-success"></i> {feature}
                          </li>
                        ))
                      ) : (
                        <li>
                          <i className="fa fa-info-circle text-info"></i> {t('No specific features listed.')}
                        </li>
                      )}
                    </ul>
                    
                    <button
                      onClick={() => handleSubscribe(plan.product_id)}
                      disabled={subscribingToPlan === plan.product_id}
                      className="btn btn-block btn-lg btn-subscribe"
                    >
                      {subscribingToPlan === plan.product_id 
                        ? t('Processing...') 
                        : isSameCancelledPlan(plan.product_id) 
                          ? t('Reactivate Subscription')
                          : isDifferentCancelledPlan(plan.product_id)
                            ? t('Switch Plan')
                            : t('Subscribe')
                      }
                    </button>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="col-md-12">
              <div className="alert alert-info">
                {t('No subscription plans are currently available.')}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Reactivation confirmation modal */}
      <Modal
        title={t('Reactivate Subscription')}
        open={showReactivationModal}
        onOk={handleConfirmReactivation}
        onCancel={handleCancelReactivation}
        okText={t('Reactivate')}
        cancelText={t('Cancel')}
        okButtonProps={{
          loading: subscribingToPlan === planToReactivate,
        }}
      >
        <div style={{ marginBottom: '16px' }}>
          <p>
            {t('You previously had this subscription plan but cancelled it. It\'s still active until %s.', 
              userStatus?.subscription?.end_date ? new Date(userStatus.subscription.end_date).toLocaleDateString() : 'N/A'
            )}
          </p>
          <p>
            <strong>{t('Good news!')}</strong> {t('Instead of creating a new subscription, we can reactivate your existing one right away.')}
          </p>
          <p>
            {t('Would you like to reactivate your subscription to this plan?')}
          </p>
        </div>
      </Modal>

      {/* Plan switching confirmation modal */}
      <Modal
        title={t('Switch Subscription Plan')}
        open={showPlanSwitchModal}
        onOk={handleConfirmPlanSwitch}
        onCancel={handleCancelPlanSwitch}
        okText={t('Switch Plan')}
        cancelText={t('Cancel')}
        okButtonProps={{
          loading: subscribingToPlan === planToSwitch,
        }}
      >
        <div style={{ marginBottom: '16px' }}>
          <p>
            {t('You currently have a cancelled subscription that\'s still valid until %s.', 
              userStatus?.subscription?.end_date ? new Date(userStatus.subscription.end_date).toLocaleDateString() : 'N/A'
            )}
          </p>
          <p>
            <strong>{t('Great news!')}</strong> {t('You can switch to this new plan immediately and get access to all its features right away!')}
          </p>
          <p>
            {t('Your billing for the new plan will start on %s when your current subscription expires, so you won\'t pay double.', 
              userStatus?.subscription?.end_date ? new Date(userStatus.subscription.end_date).toLocaleDateString() : 'N/A'
            )}
          </p>
          <p>
            <strong>{t('Would you like to switch to this plan now?')}</strong>
          </p>
        </div>
      </Modal>
    </StyledPlansPage>
  );
} 