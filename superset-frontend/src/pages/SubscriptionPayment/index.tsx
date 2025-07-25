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

import { useCallback, useEffect, useState, useRef } from 'react';
import { useParams, useHistory } from 'react-router-dom';
import { css, t, styled, useTheme } from '@superset-ui/core';
import SubMenu, { SubMenuProps } from 'src/features/home/SubMenu';
import { useToasts } from 'src/components/MessageToasts/withToasts';
import { SupersetClient } from '@superset-ui/core';
import { UserWithPermissionsAndRoles } from 'src/types/bootstrapTypes';
import getBootstrapData from 'src/utils/getBootstrapData';

const StyledContainer = styled.div`
  ${({ theme }) => css`
    padding-top: 50px;
    padding-bottom: 50px;
    max-width: 960px;
    margin: 0 auto;
    background-color: #f5f7fa;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  `}
`;

const StyledRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  margin-left: -15px;
  margin-right: -15px;
`;

const StyledCol = styled.div<{ md?: number }>`
  position: relative;
  width: 100%;
  padding-left: 15px;
  padding-right: 15px;
  
  ${({ md }) => md && css`
    flex: 0 0 ${(md / 12) * 100}%;
    max-width: ${(md / 12) * 100}%;
  `}
`;

const StyledCard = styled.div`
  border: none;
  border-radius: 8px;
  box-shadow: 0 4px 25px rgba(0, 0, 0, 0.08);
  margin-bottom: 1.5rem;
  background-color: #fff;
`;

const StyledCardHeader = styled.div`
  background-color: #20a7c9;
  color: #ffffff;
  border-bottom: 1px solid #1a85a0;
  font-weight: 600;
  padding: 1.25rem;
  text-align: center;
  border-radius: 8px 8px 0 0;
  
  h4 {
    margin: 0;
    font-size: 1.25rem;
  }
`;

const StyledCardBody = styled.div`
  padding: 2.5rem;
`;

const StyledFormGroup = styled.div`
  margin-bottom: 1rem;
`;

const StyledLabel = styled.label`
  display: inline-block;
  margin-bottom: 0.5rem;
  font-weight: 500;
`;

const StyledFormControl = styled.input`
  display: block;
  width: 100%;
  padding: 0.75rem;
  font-size: 1rem;
  line-height: 1.5;
  color: #495057;
  background-color: #fff;
  background-image: none;
  border: 1px solid #ced4da;
  border-radius: 0.375rem;
  
  &:focus {
    border-color: #79cade;
    box-shadow: 0 0 0 0.2rem rgba(32,167,201,.25);
    outline: 0;
  }
  
  &:read-only {
    background-color: #e9ecef;
  }
`;

const StyledEmailInputWrapper = styled.div`
  position: relative;
  
  input {
    padding-right: 40px;
  }
`;

const StyledCopyIcon = styled.span`
  position: absolute;
  right: 15px;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  color: #6c757d;
  transition: color 0.2s ease-in-out;
  
  &:hover {
    color: #1a85a0;
  }
`;

const StyledButton = styled.button<{ variant?: string; size?: string; disabled?: boolean }>`
  display: inline-block;
  font-weight: 600;
  text-align: center;
  white-space: nowrap;
  vertical-align: middle;
  user-select: none;
  border: 1px solid transparent;
  padding: 14px;
  font-size: 18px;
  border-radius: 6px;
  background-image: linear-gradient(to right, #20a7c9, #1a85a0);
  border: none;
  color: white;
  transition: all 0.3s ease;
  cursor: pointer;
  width: 100%;
  margin-top: 1rem;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(32, 167, 201, 0.3);
  }
  
  &:disabled {
    opacity: 0.65;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }
`;

const StyledAlert = styled.div<{ variant?: string }>`
  padding: 0.75rem 1.25rem;
  margin-bottom: 1rem;
  border: 1px solid transparent;
  border-radius: 0.25rem;
  
  ${({ variant }) => {
    switch (variant) {
      case 'danger':
        return css`
          color: #721c24;
          background-color: #f8d7da;
          border-color: #f5c6cb;
        `;
      case 'info':
        return css`
          color: #0c5460;
          background-color: #d1ecf1;
          border-color: #bee5eb;
        `;
      default:
        return css`
          color: #155724;
          background-color: #d4edda;
          border-color: #c3e6cb;
        `;
    }
  }}
`;

const StyledSecurePaymentCard = styled(StyledCard)`
  background-color: #f3f8fa;
  border: 1px dashed #d2edf4;
  box-shadow: none;
  
  .fa-lock {
    color: #20a7c9;
    margin-right: 1rem;
    font-size: 2rem;
  }
  
  h6 {
    font-weight: 600;
    color: #156378;
    margin-bottom: 0.25rem;
  }
  
  p {
    color: #6c757d;
    font-size: 0.875rem;
    margin: 0;
  }
`;

const StyledListGroup = styled.ul`
  display: flex;
  flex-direction: column;
  padding-left: 0;
  margin-bottom: 0;
  border-radius: 0.375rem;
`;

const StyledListGroupItem = styled.li`
  position: relative;
  display: block;
  padding: 0.75rem 0;
  background-color: transparent;
  border: 0;
  border-bottom: 1px solid rgba(0,0,0,.125);
  
  &:last-child {
    border-bottom: 0;
  }
  
  &.fw-bold {
    font-weight: 700;
    border-top: 2px solid #e9f6f9;
    padding-top: 1rem;
    margin-top: 0.5rem;
    font-size: 1.25rem;
    color: #1a85a0;
  }
`;

const StyledFlexBetween = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const StyledCopyMessage = styled.div`
  color: #1a85a0;
  font-weight: 500;
  padding-top: 5px;
  font-size: 0.875rem;
  display: none;
  
  &.show {
    display: block;
  }
`;

interface Plan {
  id: string;
  product_id: string;
  name: string;
  description: string;
  price: number;
  billing_cycle: string;
  stripe_price_id: string;
}

interface SubscriptionPaymentProps {
  user?: UserWithPermissionsAndRoles;
}

declare global {
  interface Window {
    Stripe: any;
  }
}

export default function SubscriptionPayment({ user }: SubscriptionPaymentProps) {
  const { planId } = useParams<{ planId: string }>();
  const history = useHistory();
  const bootstrapData = getBootstrapData();
  const currentUser = user || bootstrapData?.user;
  const theme = useTheme();
  const { addDangerToast, addSuccessToast } = useToasts();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [stripeLoaded, setStripeLoaded] = useState(false);
  const [paymentProcessing, setPaymentProcessing] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  
  // Stripe-related state
  const stripeRef = useRef<any>(null);
  const elementsRef = useRef<any>(null);
  const paymentElementRef = useRef<any>(null);
  const [clientSecret, setClientSecret] = useState<string>('');
  const [customerId, setCustomerId] = useState<string>('');
  const [subscriptionId, setSubscriptionId] = useState<string>('');
  const [paymentId, setPaymentId] = useState<string>('');

  // Load Stripe script with error handling
  useEffect(() => {
    // Check if Stripe is already loaded
    if (window.Stripe) {
      setStripeLoaded(true);
      return;
    }
    
    const script = document.createElement('script');
    script.src = 'https://js.stripe.com/v3/';
    script.async = true;
    script.onload = () => setStripeLoaded(true);
    script.onerror = () => {
      console.error('Failed to load Stripe script');
      setError(t('Failed to load payment system. Please refresh the page.'));
    };
    document.body.appendChild(script);
    
    return () => {
      // Only remove if we added it
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, []);

  const fetchPlan = useCallback(async () => {
    if (!planId) {
      setError(t('Plan ID is required'));
      setLoading(false);
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      // First check if user has active subscription
      const statusResponse = await SupersetClient.get({
        endpoint: '/subscription/api/status',
      });
      
      const statusData = statusResponse.json as any;
      if (statusData.has_active_subscription) {
        addDangerToast(t('You already have an active subscription. Please cancel it before subscribing to a new plan.'));
        history.push('/subscription/manage');
        return;
      }
      
      // Fetch plan details using SupersetClient for consistency
      const planResponse = await SupersetClient.get({
        endpoint: `/subscription/api/stripe-plan/${planId}`,
      });
      
      const planData = planResponse.json as any;
      setPlan({
        id: planData.id,
        product_id: planData.id,
        name: planData.product || planData.name,
        description: planData.description || '',
        price: parseFloat(planData.price),
        billing_cycle: planData.billing_cycle || 'month',
        stripe_price_id: planData.stripe_price_id || planData.id,
      });
      
    } catch (error) {
      console.error('Error fetching plan:', error);
      setError(t('Invalid subscription plan or plan not found.'));
      addDangerToast(t('Invalid subscription plan. Redirecting to plans page.'));
      setTimeout(() => {
        history.push('/subscription/plans');
      }, 2000);
    } finally {
      setLoading(false);
    }
  }, [planId, addDangerToast, addSuccessToast]);

  const initializeStripe = useCallback(async () => {
    if (!stripeLoaded || !plan || !window.Stripe) return;
    
    try {
      // Get Stripe configuration from the new API endpoint
      const configResponse = await SupersetClient.get({
        endpoint: '/subscription/api/stripe-config',
      });
      
      const configData = configResponse.json as any;
      if (!configData.publishable_key) {
        throw new Error('No Stripe publishable key received from server');
      }
      
      // Initialize Stripe with the configuration from API
      stripeRef.current = window.Stripe(configData.publishable_key, {
        apiVersion: configData.api_version || '2025-01-27.acacia; custom_checkout_beta=v1;',
      });
      
      console.log('Stripe initialized with version:', window.Stripe.version);
      
      // Create payment intent (identical to original logic)
      await createPaymentIntent();
      
    } catch (error) {
      console.error('Error initializing Stripe:', error);
      setError(t('Error initializing payment system. Please try again.'));
    }
  }, [stripeLoaded, plan, planId]);

  const createPaymentIntent = useCallback(async () => {
    if (!plan) return;
    
    try {
      // Create payment intent using SupersetClient for CSRF handling
      const response = await SupersetClient.post({
        endpoint: '/subscription/create-payment-intent',
        jsonPayload: {
          orderAmount: plan.price.toString(),
          product_id: plan.product_id,
        },
      });
      
      const data = response.json as any;
      
      if (data.redirect_url) {
        // Use React Router navigation to stay in React app where possible
        if (data.redirect_url.includes('/subscription/manage')) {
          history.push('/subscription/manage');
        } else if (data.redirect_url.includes('/subscription/plans')) {
          history.push('/subscription/plans');
        } else {
          window.location.href = data.redirect_url;
        }
        return;
      }
      
      // Validate required fields
      if (!data.clientSecret) {
        throw new Error('No client secret received from server');
      }
      
      // Store the client secret and IDs (identical to original)
      setClientSecret(data.clientSecret);
      setCustomerId(data.customer_id || '');
      setSubscriptionId(data.subscription_id || '');
      setPaymentId(data.payment_id || '');
      
      // Create elements instance (identical to original)
      const loader = 'auto';
      elementsRef.current = stripeRef.current.elements({ clientSecret: data.clientSecret, loader });
      
      // Create and mount Payment Element (identical to original)
      paymentElementRef.current = elementsRef.current.create('payment');
      paymentElementRef.current.mount('#payment-element-container');
      
      // Create and mount linkAuthentication Element (identical to original)
      const linkAuthenticationElement = elementsRef.current.create("linkAuthentication");
      linkAuthenticationElement.mount("#link-authentication-element");
      
    } catch (error) {
      console.error('Error creating payment intent:', error);
      setError(error instanceof Error ? error.message : t('Failed to initialize payment. Please try again.'));
    }
  }, [plan]);

  useEffect(() => {
    fetchPlan();
  }, [fetchPlan]);

  useEffect(() => {
    if (plan && stripeLoaded) {
      initializeStripe();
    }
  }, [plan, stripeLoaded, initializeStripe]);

  const handleCopyEmail = useCallback(() => {
    if (currentUser?.email) {
      navigator.clipboard.writeText(currentUser.email).then(() => {
        setCopySuccess(true);
        setTimeout(() => setCopySuccess(false), 2500);
      }).catch(err => {
        console.error('Could not copy text: ', err);
      });
    }
  }, [currentUser?.email]);

  const handlePaymentSubmit = useCallback(async (event: React.FormEvent) => {
    event.preventDefault();
    
    if (paymentProcessing || !stripeRef.current || !elementsRef.current) return;
    
    setPaymentProcessing(true);
    setPaymentError(null);
    
    try {
      // Confirm payment with IDENTICAL logic to original
      const { error: stripeError, paymentIntent } = await stripeRef.current.confirmPayment({
        elements: elementsRef.current,
        redirect: 'if_required',
      });
      
      if (stripeError) {
        setPaymentError(stripeError.message);
      } else if (paymentIntent && paymentIntent.status === 'succeeded') {
        await handleSuccessfulPayment(paymentIntent);
      }
    } catch (error) {
      console.error('Payment error:', error);
      setPaymentError(error instanceof Error ? error.message : t('An unknown error occurred'));
    } finally {
      setPaymentProcessing(false);
    }
  }, [paymentProcessing, customerId, subscriptionId, paymentId, planId]);

  const handleSuccessfulPayment = useCallback(async (paymentIntent: any) => {
    console.log('Payment intent:', JSON.stringify(paymentIntent));
    
    try {
      // Notify server of successful payment using SupersetClient
      const response = await SupersetClient.post({
        endpoint: '/subscription/payment-complete',
        jsonPayload: {
          payment_intent_id: paymentIntent.id,
          plan_id: planId,
          customer_id: customerId,
          subscription_id: subscriptionId,
          payment_id: paymentId,
        },
      });
      
      const data = response.json as any;
      
      if (data.success) {
        // Show success message and redirect
        addSuccessToast(t('Payment successful! Redirecting to success page...'));
        setTimeout(() => {
          history.push('/subscription/subscription-success');
        }, 1000);
      } else {
        throw new Error(data.error || 'Failed to record payment');
      }
    } catch (error) {
      console.error('Error in payment completion:', error);
      setPaymentError(error instanceof Error ? error.message : t('Payment successful, but failed to update subscription status'));
    }
  }, [customerId, subscriptionId, paymentId, planId, addSuccessToast]);

  const subMenuButtons: SubMenuProps['buttons'] = [];

  if (loading) {
    return (
      <StyledContainer>
        <SubMenu name={t('Checkout')} buttons={subMenuButtons} />
        <div style={{ textAlign: 'center', padding: '50px' }}>
          {t('Loading payment information...')}
        </div>
      </StyledContainer>
    );
  }

  if (error) {
    return (
      <StyledContainer>
        <SubMenu name={t('Checkout')} buttons={subMenuButtons} />
        <StyledAlert variant="danger">
          {error}
        </StyledAlert>
      </StyledContainer>
    );
  }

  if (!plan) {
    return (
      <StyledContainer>
        <SubMenu name={t('Checkout')} buttons={subMenuButtons} />
        <StyledAlert variant="danger">
          {t('Plan not found. Redirecting to plans page...')}
        </StyledAlert>
      </StyledContainer>
    );
  }

  return (
    <StyledContainer>
      <SubMenu name={t('Checkout')} buttons={subMenuButtons} />
      
      <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1>{t('Checkout')}</h1>
        <p style={{ fontSize: '1.125rem', color: '#6c757d' }}>
          {t('Complete your secure payment for the %s plan.', plan.name)}
        </p>
      </div>

      <StyledRow>
        <StyledCol md={7}>
          <StyledCard>
            <StyledCardHeader>
              <h4>{t('Payment Details')}</h4>
            </StyledCardHeader>
            <StyledCardBody>
              <form id="payment-form" onSubmit={handlePaymentSubmit}>
                {/* Hidden inputs for compatibility - not needed in React but keeping for consistency */}
                <input type="hidden" id="plan-price" value={plan.price} />
                <input type="hidden" id="plan-id" value={planId} />
                <input type="hidden" id="stripe-publishable-key" value="" />
                <input type="hidden" id="csrf-token" value="" />

                {/* Email display */}
                <StyledFormGroup>
                  <StyledLabel htmlFor="email">{t('Email Address')}</StyledLabel>
                  <StyledEmailInputWrapper>
                    <StyledFormControl
                      type="email"
                      id="email"
                      value={currentUser?.email || ''}
                      readOnly
                    />
                    <StyledCopyIcon onClick={handleCopyEmail} title={t('Copy email to clipboard')}>
                      <i className="fa fa-clipboard" aria-hidden="true"></i>
                    </StyledCopyIcon>
                  </StyledEmailInputWrapper>
                  <StyledCopyMessage className={copySuccess ? 'show' : ''}>
                    {t('Email copied to clipboard!')}
                  </StyledCopyMessage>
                </StyledFormGroup>

                <p style={{ color: '#6c757d', fontSize: '0.875rem', marginBottom: '1rem' }}>
                  {t('Enter your payment details below. The transaction is handled by Stripe.')}
                </p>

                <div id="link-authentication-element" style={{ marginBottom: '1rem' }}>
                  {/* Stripe Link Authentication Element will be mounted here */}
                </div>
                
                <div id="payment-element-container" style={{ marginBottom: '1rem' }}>
                  {/* Stripe Payment Element will be mounted here */}
                </div>

                {paymentError && (
                  <StyledAlert variant="danger">
                    {paymentError}
                  </StyledAlert>
                )}

                <StyledButton
                  type="submit"
                  disabled={paymentProcessing || !clientSecret}
                >
                  {paymentProcessing ? (
                    <>
                      <i className="fa fa-spinner fa-spin" style={{ marginRight: '0.5rem' }}></i>
                      {t('Processing...')}
                    </>
                  ) : (
                    t('Pay $%s', plan.price.toFixed(2))
                  )}
                </StyledButton>
              </form>
            </StyledCardBody>
          </StyledCard>
        </StyledCol>

        <StyledCol md={5}>
          <StyledCard>
            <StyledCardHeader>
              <h4>{t('Order Summary')}</h4>
            </StyledCardHeader>
            <StyledCardBody>
              <StyledListGroup>
                <StyledListGroupItem>
                  <StyledFlexBetween>
                    <div>
                      <h6 style={{ margin: 0 }}>{plan.name}</h6>
                      <small style={{ color: '#6c757d' }}>{plan.description}</small>
                    </div>
                    <span style={{ color: '#6c757d' }}>${plan.price.toFixed(2)}</span>
                  </StyledFlexBetween>
                </StyledListGroupItem>
                <StyledListGroupItem className="fw-bold">
                  <StyledFlexBetween>
                    <span>{t('Total (USD)')}</span>
                    <strong>${plan.price.toFixed(2)}</strong>
                  </StyledFlexBetween>
                </StyledListGroupItem>
              </StyledListGroup>
            </StyledCardBody>
          </StyledCard>

          <StyledSecurePaymentCard>
            <StyledCardBody style={{ textAlign: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <i className="fa fa-lock fa-2x" aria-hidden="true"></i>
                <div>
                  <h6>{t('Secure Payment via Stripe')}</h6>
                  <p>
                    {t('Your payment is processed securely. We do not store your card details.')}
                  </p>
                </div>
              </div>
            </StyledCardBody>
          </StyledSecurePaymentCard>
        </StyledCol>
      </StyledRow>
    </StyledContainer>
  );
} 