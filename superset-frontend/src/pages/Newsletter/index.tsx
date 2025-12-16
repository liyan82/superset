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
import { useState, useEffect, useCallback } from 'react';
import { SupersetClient, t } from '@superset-ui/core';
import { styled, css, useTheme } from '@apache-superset/core/ui';
import {
  Button,
  Select,
  FormLabel,
  Alert,
  Input,
} from '@superset-ui/core/components';
// eslint-disable-next-line no-restricted-imports
import { Modal } from 'antd';
import ProgressBar from '@superset-ui/core/components/ProgressBar';
import { Icons } from '@superset-ui/core/components/Icons';
import { Space } from '@superset-ui/core/components/Space';
import { Typography } from '@superset-ui/core/components/Typography';
import SubMenu, { SubMenuProps } from 'src/features/home/SubMenu';
import { useToasts } from 'src/components/MessageToasts/withToasts';
import { fetchPaginatedData } from 'src/utils/fetchOptions';

interface User {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  active: boolean;
}

interface SelectOption {
  label: string;
  value: number;
}

const StyledContainer = styled.div`
  ${({ theme }) => css`
    .form-section {
      background-color: ${theme.colors.grayscale.light5};
      padding: ${theme.sizeUnit * 6}px;
      margin-bottom: ${theme.sizeUnit * 4}px;
      border-radius: ${theme.borderRadius}px;
    }

    .form-row {
      margin-bottom: ${theme.sizeUnit * 6}px;
    }

    .form-actions {
      background-color: ${theme.colors.grayscale.light5};
      padding: ${theme.sizeUnit * 4}px ${theme.sizeUnit * 6}px;
      border-radius: ${theme.borderRadius}px;
      border-top: 1px solid ${theme.colors.grayscale.light2};
    }
  `}
`;

export default function Newsletter() {
  const theme = useTheme();
  const { addDangerToast, addSuccessToast } = useToasts();
  const [subject, setSubject] = useState('');
  const [recipients, setRecipients] = useState<SelectOption[]>([]);
  const [emailBody, setEmailBody] = useState('');
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState({
    users: true,
    sending: false,
  });
  const [sendingProgress, setSendingProgress] = useState<{
    visible: boolean;
    sessionId: string | null;
    total: number;
    sent: number;
    failed: number;
    percentage: number;
    status: 'in_progress' | 'completed' | 'failed';
    failedEmails: Array<{ email: string; reason: string }>;
  }>({
    visible: false,
    sessionId: null,
    total: 0,
    sent: 0,
    failed: 0,
    percentage: 0,
    status: 'in_progress',
    failedEmails: [],
  });
  const [errors, setErrors] = useState<{
    subject?: string;
    recipients?: string;
    emailBody?: string;
  }>({});

  const fetchUsers = useCallback(() => {
    fetchPaginatedData({
      endpoint: '/api/v1/security/users/',
      setData: setUsers,
      setLoadingState: setLoading,
      loadingKey: 'users',
      addDangerToast,
      errorMessage: t('Error while fetching users'),
    });
  }, [addDangerToast]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const userOptions = users
    .filter(user => user.active && user.email)
    .map(user => ({
      label: `${user.first_name} ${user.last_name} (${user.email})`,
      value: user.id,
    }));

  const validateForm = () => {
    const newErrors: typeof errors = {};

    if (!subject.trim()) {
      newErrors.subject = t('Subject is required');
    }

    if (recipients.length === 0) {
      newErrors.recipients = t('At least one recipient is required');
    }

    if (!emailBody.trim()) {
      newErrors.emailBody = t('Email body is required');
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const pollProgress = useCallback(
    async (sessionId: string) => {
      try {
        const response = await SupersetClient.get({
          endpoint: `/api/v1/newsletter/progress/${sessionId}`,
        });

        const progressData = response.json;
        setSendingProgress(prev => ({
          ...prev,
          total: progressData.total,
          sent: progressData.sent,
          failed: progressData.failed,
          percentage: progressData.percentage,
          status: progressData.status,
          failedEmails: progressData.failed_emails || [],
        }));

        if (progressData.status === 'completed') {
          if (progressData.sent > 0 && progressData.failed === 0) {
            // All succeeded
            addSuccessToast(
              t(
                'Newsletter sent successfully to all %s recipients!',
                progressData.sent,
              ),
            );
          } else if (progressData.sent > 0 && progressData.failed > 0) {
            // Partial success
            addSuccessToast(
              t(
                'Newsletter partially sent. Success: %s, Failed: %s',
                progressData.sent,
                progressData.failed,
              ),
            );
          } else if (progressData.sent === 0 && progressData.failed > 0) {
            // All failed
            addDangerToast(
              t(
                'Newsletter sending failed for all %s recipients. Check SMTP configuration.',
                progressData.failed,
              ),
            );
          }

          setLoading(prev => ({ ...prev, sending: false }));

          // Only clear form if at least some emails were sent successfully
          if (progressData.sent > 0) {
            setSubject('');
            setRecipients([]);
            setEmailBody('');
            setErrors({});
          }
        } else if (progressData.status === 'failed') {
          addDangerToast(t('Newsletter sending failed.'));
          setLoading(prev => ({ ...prev, sending: false }));
        } else {
          // Continue polling
          setTimeout(() => pollProgress(sessionId), 1000);
        }
      } catch (error) {
        // eslint-disable-next-line no-console
        console.error('Error polling progress:', error);
        addDangerToast(t('Error checking sending progress'));
        setLoading(prev => ({ ...prev, sending: false }));
        setSendingProgress(prev => ({ ...prev, visible: false }));
      }
    },
    [addDangerToast, addSuccessToast],
  );

  const handleSendNewsletter = async () => {
    if (!validateForm()) {
      return;
    }

    setLoading(prev => ({ ...prev, sending: true }));
    setSendingProgress({
      visible: true,
      sessionId: null,
      total: recipients.length,
      sent: 0,
      failed: 0,
      percentage: 0,
      status: 'in_progress',
      failedEmails: [],
    });

    try {
      const response = await SupersetClient.post({
        endpoint: '/api/v1/newsletter/send',
        body: JSON.stringify({
          subject,
          recipient_ids: recipients.map(r => r.value),
          html_body: emailBody,
        }),
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const { session_id } = response.json;
      setSendingProgress(prev => ({ ...prev, sessionId: session_id }));

      // Start polling progress
      pollProgress(session_id);
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error('Error sending newsletter:', error);
      addDangerToast(t('Failed to send newsletter. Please try again.'));
      setLoading(prev => ({ ...prev, sending: false }));
      setSendingProgress(prev => ({ ...prev, visible: false }));
    }
  };

  const subMenuButtons: SubMenuProps['buttons'] = [
    {
      name: t('Send Newsletter'),
      buttonStyle: 'primary',
      onClick: loading.users ? undefined : handleSendNewsletter,
      loading: loading.sending,
      icon: <Icons.MailOutlined iconSize="m" />,
      'data-test': 'send-newsletter-button',
    },
  ];

  return (
    <StyledContainer>
      <SubMenu name={t('Newsletter')} buttons={subMenuButtons} />

      <div className="form-section">
        <Typography.Title
          level={4}
          style={{ marginBottom: theme.sizeUnit * 4 }}
        >
          {t('Compose Newsletter')}
        </Typography.Title>
        <Typography.Paragraph
          type="secondary"
          style={{ marginBottom: theme.sizeUnit * 6 }}
        >
          {t('Send HTML newsletters to selected users in your organization.')}
        </Typography.Paragraph>

        <div className="form-row">
          <FormLabel required>{t('Subject')}</FormLabel>
          <Input
            placeholder={t('Enter newsletter subject')}
            value={subject}
            onChange={e => setSubject(e.target.value)}
            status={errors.subject ? 'error' : undefined}
            style={{ marginTop: theme.sizeUnit * 2 }}
          />
          {errors.subject && (
            <Alert
              type="error"
              message={errors.subject}
              showIcon
              style={{ marginTop: theme.sizeUnit * 2 }}
            />
          )}
        </div>

        <div className="form-row">
          <FormLabel required>{t('Recipients')}</FormLabel>
          <Select
            mode="multiple"
            placeholder={t('Select users to send newsletter to')}
            value={recipients.map(r => r.value)}
            onChange={selectedValues => {
              if (Array.isArray(selectedValues)) {
                const selectedOptions = selectedValues.map(value => {
                  const numValue =
                    typeof value === 'object' && 'value' in value
                      ? (value.value as number)
                      : (value as number);
                  const user = userOptions.find(opt => opt.value === numValue);
                  return user || { label: 'Unknown', value: numValue };
                });
                setRecipients(selectedOptions);
              }
            }}
            options={userOptions}
            loading={loading.users}
            showSearch
            filterOption={(input, option) =>
              (typeof option?.label === 'string' &&
                option.label.toLowerCase().includes(input.toLowerCase())) ||
              false
            }
            css={css`
              margin-top: ${theme.sizeUnit * 2}px;
              width: 100%;
            `}
            maxTagCount="responsive"
          />
          {errors.recipients && (
            <Alert
              type="error"
              message={errors.recipients}
              showIcon
              style={{ marginTop: theme.sizeUnit * 2 }}
            />
          )}
          <Typography.Text
            type="secondary"
            style={{ marginTop: theme.sizeUnit, display: 'block' }}
          >
            {t('Selected: %s users', recipients.length)}
          </Typography.Text>
        </div>

        <div className="form-row">
          <FormLabel required>{t('Email Content (HTML)')}</FormLabel>
          <Typography.Text
            type="secondary"
            style={{ marginBottom: theme.sizeUnit * 2, display: 'block' }}
          >
            {t(
              'Write your newsletter content in HTML format. Available variables: {user_first_name}, {user_last_name}, {user_username}, {user_email}, {unsubscribe_link}',
            )}
          </Typography.Text>
          <Input.TextArea
            placeholder={t('Enter your HTML newsletter content here...')}
            value={emailBody}
            onChange={e => setEmailBody(e.target.value)}
            rows={20}
            status={errors.emailBody ? 'error' : undefined}
            style={{
              marginTop: theme.sizeUnit * 2,
              fontFamily: 'monospace',
              fontSize: '13px',
              backgroundColor: theme.colors.grayscale.light4,
            }}
          />
          {errors.emailBody && (
            <Alert
              type="error"
              message={errors.emailBody}
              showIcon
              style={{ marginTop: theme.sizeUnit * 2 }}
            />
          )}
        </div>
      </div>

      <div className="form-actions">
        <Space>
          <Button
            type="primary"
            onClick={handleSendNewsletter}
            loading={loading.sending}
            disabled={loading.users}
            icon={<Icons.MailOutlined />}
          >
            {loading.sending ? t('Sending...') : t('Send Newsletter')}
          </Button>
          <Button
            onClick={() => {
              setSubject('');
              setRecipients([]);
              setEmailBody('');
              setErrors({});
            }}
            disabled={loading.sending}
            icon={<Icons.CloseOutlined />}
          >
            {t('Clear form')}
          </Button>
        </Space>
      </div>

      {/* Progress Modal */}
      <Modal
        title={t('Sending Newsletter')}
        open={sendingProgress.visible}
        footer={[
          <Button
            key="close"
            onClick={() =>
              setSendingProgress(prev => ({ ...prev, visible: false }))
            }
            disabled={sendingProgress.status === 'in_progress'}
          >
            {sendingProgress.status === 'completed' ? t('Close') : t('Cancel')}
          </Button>,
        ]}
        closable={sendingProgress.status !== 'in_progress'}
        maskClosable={false}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Typography.Text>
            {t('Sending newsletter to %s recipients...', sendingProgress.total)}
          </Typography.Text>

          <ProgressBar
            percent={Math.round(sendingProgress.percentage)}
            striped={sendingProgress.status !== 'completed'}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography.Text type="success">
              {t('Sent: %s', sendingProgress.sent)}
            </Typography.Text>
            <Typography.Text
              type={sendingProgress.failed > 0 ? 'danger' : 'secondary'}
            >
              {t('Failed: %s', sendingProgress.failed)}
            </Typography.Text>
          </div>

          {sendingProgress.failedEmails.length > 0 && (
            <div>
              <Typography.Text strong>
                {t('Failed recipients:')}
              </Typography.Text>
              <div
                style={{
                  maxHeight: '200px',
                  overflow: 'auto',
                  marginTop: '8px',
                }}
              >
                {sendingProgress.failedEmails.map((failed, index) => (
                  <div key={index} style={{ marginBottom: '4px' }}>
                    <Typography.Text type="danger" style={{ fontSize: '12px' }}>
                      {failed.email}: {failed.reason}
                    </Typography.Text>
                  </div>
                ))}
              </div>
            </div>
          )}

          {sendingProgress.status === 'completed' && (
            <Alert
              type={
                sendingProgress.sent > 0 && sendingProgress.failed === 0
                  ? 'success'
                  : sendingProgress.sent > 0 && sendingProgress.failed > 0
                    ? 'warning'
                    : 'error'
              }
              message={
                sendingProgress.sent > 0 && sendingProgress.failed === 0
                  ? t('Newsletter sent successfully to all recipients!')
                  : sendingProgress.sent > 0 && sendingProgress.failed > 0
                    ? t('Newsletter partially sent. Some recipients failed.')
                    : t('Newsletter sending failed for all recipients.')
              }
              showIcon
            />
          )}
        </Space>
      </Modal>
    </StyledContainer>
  );
}
