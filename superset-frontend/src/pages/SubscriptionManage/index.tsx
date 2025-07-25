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
import { css, t, styled } from '@superset-ui/core';
import SubMenu, { SubMenuProps } from 'src/features/home/SubMenu';
import { useToasts } from 'src/components/MessageToasts/withToasts';
import { SupersetClient } from '@superset-ui/core';
import { Modal } from 'antd';
import { UserWithPermissionsAndRoles } from 'src/types/bootstrapTypes';
import getBootstrapData from 'src/utils/getBootstrapData';

const StyledPageWrapper = styled.div`
  min-height: 100vh;
  min-height: 100dvh;
  background-color: #f5f7fa;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  position: relative;
  
  &::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #f5f7fa;
    z-index: -1;
  }
`;

const StyledContainer = styled.div`
  padding: 25px;
  margin-bottom: 50px;
  max-width: 1200px;
  margin: 0 auto;
  position: relative;
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

const StyledPanelHeading = styled.div<{ variant?: string }>`
  padding: 10px 15px;
  border-bottom: 1px solid transparent;
  border-top-left-radius: 3px;
  border-top-right-radius: 3px;
  color: #fff;
  border-color: #ddd;
  
  ${({ variant }) => {
    if (variant === 'primary') {
      return css`
        background-color: #337ab7;
        border-color: #337ab7;
      `;
    }
    if (variant === 'info') {
      return css`
        background-color: #5bc0de;
        border-color: #5bc0de;
      `;
    }
    return css`
      background-color: #f5f5f5;
      border-color: #ddd;
      color: #333;
    `;
  }}
  
  h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 500;
  }
`;

const StyledPanelBody = styled.div`
  padding: 15px;
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
      case 'warning':
        return css`background-color: #f0ad4e;`;
      case 'danger':
        return css`background-color: #d9534f;`;
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
  
  ${({ variant }) => {
    switch (variant) {
      case 'danger':
        return css`
          color: #fff;
          background-color: #d9534f;
          border-color: #d43f3a;
          &:hover {
            background-color: #c9302c;
            border-color: #ac2925;
          }
        `;
      case 'warning':
        return css`
          color: #fff;
          background-color: #f0ad4e;
          border-color: #eea236;
          &:hover {
            background-color: #ec971f;
            border-color: #d58512;
          }
        `;
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
  
  &:disabled {
    opacity: 0.65;
    cursor: not-allowed;
  }
`;

const StyledTable = styled.table`
  width: 100%;
  max-width: 100%;
  margin-bottom: 20px;
  background-color: transparent;
  border-collapse: collapse;
  border-spacing: 0;
  
  th, td {
    padding: 8px;
    line-height: 1.42857143;
    vertical-align: top;
    border-top: 1px solid #ddd;
  }
  
  th {
    font-weight: 500;
    text-align: left;
    background-color: #f5f5f5;
    border-bottom: 2px solid #ddd;
  }
  
  tbody tr:nth-child(odd) {
    background-color: #f9f9f9;
  }
`;

const StyledAlert = styled.div<{ variant?: string }>`
  padding: 15px;
  margin-bottom: 20px;
  border: 1px solid transparent;
  border-radius: 4px;
  
  ${({ variant }) => {
    switch (variant) {
      case 'warning':
        return css`
          color: #8a6d3b;
          background-color: #fcf8e3;
          border-color: #faebcc;
        `;
      case 'info':
        return css`
          color: #31708f;
          background-color: #d9edf7;
          border-color: #bce8f1;
        `;
      default:
        return css`
          color: #3c763d;
          background-color: #dff0d8;
          border-color: #d6e9c6;
        `;
    }
  }}
`;

interface Payment {
  id: number;
  amount: number;
  status: string;
  payment_date: string;
  payment_method: string;
  transaction_id: string;
}

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
      product_id: string;
      description: string;
      price: number;
      billing_cycle: string;
      features: string[];
    };
  };
  payments: Payment[];
  user: {
    id: number;
    email: string;
    username: string;
  };
  is_admin: boolean;
}

interface SubscriptionManageProps {
  user?: UserWithPermissionsAndRoles;
}

export default function SubscriptionManage({ user }: SubscriptionManageProps) {
  const history = useHistory();
  const { addDangerToast, addSuccessToast } = useToasts();
  const bootstrapData = getBootstrapData();
  const currentUser = user || bootstrapData?.user;
  const [details, setDetails] = useState<SubscriptionDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelling, setCancelling] = useState(false);

  const fetchDetails = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await SupersetClient.get({
        endpoint: '/subscription/api/details',
      });
      
      const data = response.json as SubscriptionDetails;
      setDetails(data);
      
      // If no subscription, redirect to plans page
      if (!data.subscription) {
        addSuccessToast(t('You don\'t have an active subscription. Choose a plan below to subscribe.'));
        history.push('/subscription/plans');
        return;
      }
      
    } catch (error) {
      console.error('Error fetching subscription details:', error);
      setError(t('Error loading subscription details. Please try again.'));
      addDangerToast(t('Error loading subscription details. Please try again.'));
    } finally {
      setLoading(false);
    }
  }, [addDangerToast, addSuccessToast]);

  useEffect(() => {
    fetchDetails();
  }, [fetchDetails]);

  const handleCancelSubscription = async () => {
    console.log('handleCancelSubscription called!');
    console.log('details:', details);
    
    if (!details?.subscription) {
      console.log('No subscription found, returning early');
      return;
    }
    
    setCancelling(true);
    try {
      console.log('Making API call to cancel subscription...');
      console.log('subscription_id:', details.subscription.id);
      
      const response = await SupersetClient.post({
        endpoint: '/subscription/api/cancel',
        jsonPayload: {
          subscription_id: details.subscription.id,
        },
      });
      
      console.log('API Response:', response);
      const result = response.json as any;
      
      if (result.success) {
        addSuccessToast(result.message || t('Your subscription has been cancelled'));
        setShowCancelModal(false);
        // Refresh the details to show updated status
        await fetchDetails();
      } else {
        throw new Error(result.error || 'Failed to cancel subscription');
      }
    } catch (error) {
      console.error('Error cancelling subscription:', error);
      addDangerToast(error instanceof Error ? error.message : t('Error cancelling subscription. Please try again.'));
    } finally {
      setCancelling(false);
    }
  };

  const handleResumePayment = () => {
    if (!details?.subscription?.plan?.product_id) return;
    history.push(`/subscription/payment/${details.subscription.plan.product_id}`);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString(undefined, {
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
      timeZoneName: 'short'
    });
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'active':
        return <StyledLabel variant="success">Active</StyledLabel>;
      case 'cancelled':
        return <StyledLabel variant="warning">Cancelled</StyledLabel>;
      case 'expired':
        return <StyledLabel variant="danger">Expired</StyledLabel>;
      case 'incomplete':
        return <StyledLabel variant="warning">Incomplete</StyledLabel>;
      default:
        return <StyledLabel>{status}</StyledLabel>;
    }
  };

  const getPaymentStatusLabel = (status: string) => {
    switch (status) {
      case 'success':
        return <StyledLabel variant="success">Success</StyledLabel>;
      case 'failed':
        return <StyledLabel variant="danger">Failed</StyledLabel>;
      default:
        return <StyledLabel>{status}</StyledLabel>;
    }
  };

  const subMenuButtons: SubMenuProps['buttons'] = [];

  if (loading) {
    return (
      <StyledPageWrapper>
        <StyledContainer>
          <SubMenu name={t('Manage Subscription')} buttons={subMenuButtons} />
          <div style={{ textAlign: 'center', padding: '50px' }}>
            {t('Loading subscription details...')}
          </div>
        </StyledContainer>
      </StyledPageWrapper>
    );
  }

  if (error) {
    return (
      <StyledPageWrapper>
        <StyledContainer>
          <SubMenu name={t('Manage Subscription')} buttons={subMenuButtons} />
        <StyledAlert variant="warning">
          <h4>{t('Error Loading Subscription')}</h4>
          <p>{error}</p>
          <StyledButton variant="primary" onClick={fetchDetails}>
            {t('Retry')}
          </StyledButton>
        </StyledAlert>
        </StyledContainer>
      </StyledPageWrapper>
    );
  }

  if (!details?.subscription) {
    return (
      <StyledPageWrapper>
        <StyledContainer>
          <SubMenu name={t('Manage Subscription')} buttons={subMenuButtons} />
        <StyledAlert variant="warning">
          <h4>{t('No Active Subscription')}</h4>
          <p>{t('You don\'t have an active subscription at the moment.')}</p>
          <a href="/subscription/plans">
            <StyledButton variant="primary">{t('View Available Plans')}</StyledButton>
          </a>
        </StyledAlert>
        </StyledContainer>
      </StyledPageWrapper>
    );
  }

  const subscription = details.subscription;

  return (
    <StyledPageWrapper>
      <StyledContainer>
        <SubMenu name={t('Manage Your Subscription')} buttons={subMenuButtons} />
      
      <StyledRow>
        <StyledCol md={8}>
          <StyledPanel>
            <StyledPanelHeading variant="primary">
              <h3>{t('Current Subscription')}</h3>
            </StyledPanelHeading>
            <StyledPanelBody>
              <StyledRow>
                <StyledCol md={6}>
                  <h4>{subscription.plan.name}</h4>
                  <p>{subscription.plan.description}</p>
                  
                  <h5>
                    {t('Status: ')}
                    {getStatusLabel(subscription.status)}
                  </h5>
                </StyledCol>
                <StyledCol md={6}>
                  <h5>{t('Subscription Details:')}</h5>
                  <ul style={{ listStyle: 'none', padding: 0 }}>
                    <li><strong>{t('Started:')}</strong> {formatDate(subscription.start_date)}</li>
                    <li><strong>{t('Ends:')}</strong> {formatDate(subscription.end_date)}</li>
                    <li>
                      <strong>{t('Auto-renew:')}</strong>
                      {subscription.is_auto_renew ? (
                        <span style={{ color: '#5cb85c' }}> {t('Yes')}</span>
                      ) : (
                        <span style={{ color: '#d9534f' }}> {t('No')}</span>
                      )}
                    </li>
                  </ul>
                </StyledCol>
              </StyledRow>
              
              {subscription.status === 'active' && (
                <div style={{ borderTop: '1px solid #ddd', marginTop: '15px', paddingTop: '15px' }}>
                  <StyledButton variant="danger" onClick={() => setShowCancelModal(true)}>
                    {t('Cancel Subscription')}
                  </StyledButton>
                </div>
              )}
              
              {subscription.status === 'incomplete' && (
                <div style={{ borderTop: '1px solid #ddd', marginTop: '15px', paddingTop: '15px' }}>
                  <StyledButton variant="warning" onClick={handleResumePayment}>
                    {t('Resume Payment')}
                  </StyledButton>
                </div>
              )}
              
              {(subscription.status === 'cancelled' || subscription.status === 'expired') && (
                <div style={{ borderTop: '1px solid #ddd', marginTop: '15px', paddingTop: '15px' }}>
                  <a href="/subscription/plans">
                    <StyledButton variant="primary">{t('View Available Plans')}</StyledButton>
                  </a>
                </div>
              )}
            </StyledPanelBody>
          </StyledPanel>
          
          <StyledPanel>
            <StyledPanelHeading variant="info">
              <h3>{t('Payment History')}</h3>
            </StyledPanelHeading>
            <StyledPanelBody>
              {details.payments && details.payments.length > 0 ? (
                <StyledTable>
                  <thead>
                    <tr>
                      <th>{t('Date')}</th>
                      <th>{t('Amount')}</th>
                      <th>{t('Status')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {details.payments.map((payment) => (
                      <tr key={payment.id}>
                        <td>{payment.payment_date ? formatDateTime(payment.payment_date) : 'N/A'}</td>
                        <td>${payment.amount.toFixed(2)}</td>
                        <td>{getPaymentStatusLabel(payment.status)}</td>
                      </tr>
                    ))}
                  </tbody>
                </StyledTable>
              ) : (
                <StyledAlert variant="info">
                  {t('No payment history available.')}
                </StyledAlert>
              )}
            </StyledPanelBody>
          </StyledPanel>
        </StyledCol>
        
        <StyledCol md={4}>
          <StyledPanel>
            <StyledPanelHeading>
              <h3>{t('Need Help?')}</h3>
            </StyledPanelHeading>
            <StyledPanelBody>
              <p>{t('If you have any questions about your subscription or need assistance, please contact our support team:')}</p>
              <ul style={{ listStyle: 'none', padding: 0 }}>
                <li><i className="fa fa-envelope"></i> <a href="mailto:david@patent1024.com">david@patent1024.com</a></li>
                <li><i className="fa fa-phone"></i> (678) 888-2116</li>
              </ul>
            </StyledPanelBody>
          </StyledPanel>
        </StyledCol>
      </StyledRow>

      {/* Cancellation Confirmation Modal */}
      <Modal
        title={t('Confirm Cancellation')}
        open={showCancelModal}
        onCancel={() => setShowCancelModal(false)}
        footer={[
          <StyledButton 
            key="keep"
            onClick={() => {
              console.log('Keep Subscription button clicked!');
              setShowCancelModal(false);
            }}
          >
            {t('Keep Subscription')}
          </StyledButton>,
          <StyledButton 
            key="cancel"
            variant="danger" 
            onClick={() => {
              console.log('Cancel button clicked!');
              handleCancelSubscription();
            }}
            disabled={cancelling}
          >
            {cancelling ? t('Cancelling...') : t('Yes, Cancel My Subscription')}
          </StyledButton>,
        ]}
      >
        <p>{t('Are you sure you want to cancel your subscription?')}</p>
        <p>
          {t('If you cancel, you can still use the service until your current subscription period ends on ')}
          <strong>{formatDate(subscription.end_date)}</strong>.
        </p>
      </Modal>
      </StyledContainer>
    </StyledPageWrapper>
  );
} 