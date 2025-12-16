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
import { t } from '@superset-ui/core';
import { css, styled } from '@apache-superset/core/ui';
import SubMenu, { SubMenuProps } from 'src/features/home/SubMenu';
import { useToasts } from 'src/components/MessageToasts/withToasts';
import { SupersetClient } from '@superset-ui/core';
import { UserWithPermissionsAndRoles } from 'src/types/bootstrapTypes';

const StyledContainer = styled.div`
  ${({ theme }) => css`
    padding: ${theme.sizeUnit * 5}px;
    margin-bottom: ${theme.sizeUnit * 10}px;
  `}
`;

const StyledRow = styled.div`
  display: flex;
  flex-wrap: wrap;
  margin-left: -15px;
  margin-right: -15px;
`;

const StyledCol = styled.div<{ md?: number; offset?: number }>`
  position: relative;
  width: 100%;
  padding-left: 15px;
  padding-right: 15px;
  
  ${({ md }) => md && css`
    flex: 0 0 ${(md / 12) * 100}%;
    max-width: ${(md / 12) * 100}%;
  `}
  
  ${({ offset }) => offset && css`
    margin-left: ${(offset / 12) * 100}%;
  `}
`;

const StyledPanel = styled.div`
  margin-bottom: 20px;
  background-color: #fff;
  border: 1px solid transparent;
  border-radius: 4px;
  box-shadow: 0 1px 1px rgba(0,0,0,.05);
  border-color: #ddd;
`;

const StyledPanelHeading = styled.div`
  padding: 10px 15px;
  border-bottom: 1px solid transparent;
  border-top-left-radius: 3px;
  border-top-right-radius: 3px;
  color: #fff;
  background-color: #5cb85c;
  border-color: #5cb85c;
  
  h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 500;
  }
`;

const StyledPanelBody = styled.div`
  padding: 15px;
  text-align: center;
`;

const StyledSuccessIcon = styled.i`
  font-size: 5rem;
  color: #5cb85c;
  margin: 20px 0;
`;

const StyledLabel = styled.span<{ variant?: string }>`
  display: inline;
  padding: .2em .6em .3em;
  font-size: 75%;
  font-weight: 700;
  line-height: 1;
  color: #fff;
  text-align: center;
  white-space: nowrap;
  vertical-align: baseline;
  border-radius: .25em;
  
  ${({ variant }) => {
    switch (variant) {
      case 'success':
        return css`background-color: #5cb85c;`;
      default:
        return css`background-color: #777;`;
    }
  }}
`;

const StyledButton = styled.button<{ variant?: string; size?: string }>`
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
  margin: 0 0.5rem;
  
  ${({ variant }) => {
    switch (variant) {
      case 'primary':
        return css`
          color: #fff;
          background-color: #337ab7;
          border-color: #2e6da4;
          &:hover {
            background-color: #286090;
            border-color: #204d74;
          }
        `;
      default:
        return css`
          color: #333;
          background-color: #fff;
          border-color: #ccc;
          &:hover {
            background-color: #e6e6e6;
            border-color: #adadad;
          }
        `;
    }
  }}
`;

const StyledDetailsList = styled.ul`
  list-style: none;
  padding: 0;
  text-align: left;
  
  li {
    margin-bottom: 8px;
    
    strong {
      margin-right: 8px;
    }
  }
`;

interface SubscriptionDetails {
  subscription: {
    id: number;
    status: string;
    start_date: string;
    end_date: string;
    is_auto_renew: boolean;
    external_subscription_id: string;
    plan: {
      id: number;
      name: string;
      description: string;
      price: number;
      billing_cycle: string;
    };
  };
}

interface SubscriptionSuccessProps {
  user?: UserWithPermissionsAndRoles;
}

export default function SubscriptionSuccess({ user }: SubscriptionSuccessProps) {
  const { addDangerToast } = useToasts();
  const [subscription, setSubscription] = useState<SubscriptionDetails | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchSubscriptionDetails = useCallback(async () => {
    try {
      setLoading(true);
      
      const response = await SupersetClient.get({
        endpoint: '/subscription/api/details',
      });
      
      const data = response.json as SubscriptionDetails;
      setSubscription(data);
      
      // If no subscription found, redirect to plans
      if (!data.subscription) {
        window.location.href = '/subscription/plans';
        return;
      }
      
    } catch (error) {
      console.error('Error fetching subscription details:', error);
      addDangerToast(t('Error loading subscription details.'));
      // Redirect to plans on error
      setTimeout(() => {
        window.location.href = '/subscription/plans';
      }, 2000);
    } finally {
      setLoading(false);
    }
  }, [addDangerToast]);

  useEffect(() => {
    fetchSubscriptionDetails();
  }, [fetchSubscriptionDetails]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const handleReturnToDashboard = () => {
    window.location.href = '/';
  };

  const handleManageSubscription = () => {
    window.location.href = '/subscription/manage';
  };

  const subMenuButtons: SubMenuProps['buttons'] = [];

  if (loading) {
    return (
      <StyledContainer>
        <SubMenu name={t('Subscription Success')} buttons={subMenuButtons} />
        <div style={{ textAlign: 'center', padding: '50px' }}>
          {t('Loading subscription details...')}
        </div>
      </StyledContainer>
    );
  }

  if (!subscription?.subscription) {
    return (
      <StyledContainer>
        <SubMenu name={t('Subscription Success')} buttons={subMenuButtons} />
        <div style={{ textAlign: 'center', padding: '50px' }}>
          {t('No subscription found. Redirecting...')}
        </div>
      </StyledContainer>
    );
  }

  const sub = subscription.subscription;

  return (
    <StyledContainer>
      <SubMenu name={t('Subscription Success')} buttons={subMenuButtons} />
      
      <StyledRow>
        <StyledCol md={8} offset={2}>
          <StyledPanel>
            <StyledPanelHeading>
              <h3>{t('Subscription Successful!')}</h3>
            </StyledPanelHeading>
            <StyledPanelBody>
              <StyledSuccessIcon className="fa fa-check-circle" />
              
              <h3>{t('Thank you for your subscription!')}</h3>
              <p style={{ fontSize: '1.125rem', marginBottom: '2rem' }}>
                {t('Your %s subscription has been successfully activated.', sub.plan.name)}
              </p>
              
              <hr style={{ margin: '2rem 0' }} />
              
              <StyledRow>
                <StyledCol md={6}>
                  <h4>{t('Subscription Details')}</h4>
                  <StyledDetailsList>
                    <li><strong>{t('Plan:')}</strong> {sub.plan.name}</li>
                    <li><strong>{t('Price:')}</strong> ${sub.plan.price.toFixed(2)} / {sub.plan.billing_cycle}</li>
                    <li><strong>{t('Status:')}</strong> <StyledLabel variant="success">{t('Active')}</StyledLabel></li>
                    <li><strong>{t('Start Date:')}</strong> {formatDate(sub.start_date)}</li>
                    <li><strong>{t('Renewal Date:')}</strong> {formatDate(sub.end_date)}</li>
                    {sub.external_subscription_id && (
                      <li><strong>{t('Payment Method:')}</strong> Stripe</li>
                    )}
                  </StyledDetailsList>
                </StyledCol>
                <StyledCol md={6}>
                  <h4>{t('What\'s Next?')}</h4>
                  <p>{t('You now have full access to all premium features associated with your subscription plan.')}</p>
                  <p>{t('You can manage your subscription at any time from your account settings.')}</p>
                  {sub.external_subscription_id && (
                    <p style={{ fontSize: '0.875rem', color: '#6c757d' }}>
                      {t('Your subscription will automatically renew unless you cancel it before the renewal date.')}
                    </p>
                  )}
                </StyledCol>
              </StyledRow>
              
              <div style={{ marginTop: '2rem' }}>
                <StyledButton variant="primary" onClick={handleReturnToDashboard}>
                  {t('Return to Dashboard')}
                </StyledButton>
                <StyledButton onClick={handleManageSubscription}>
                  {t('Manage Subscription')}
                </StyledButton>
              </div>
            </StyledPanelBody>
          </StyledPanel>
        </StyledCol>
      </StyledRow>
    </StyledContainer>
  );
} 