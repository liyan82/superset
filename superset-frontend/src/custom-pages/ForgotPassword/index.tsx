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

import { useState } from 'react';
import { SupersetClient, t, css } from '@superset-ui/core';
import { Button } from '@superset-ui/core/components/Button';
import { Form } from '@superset-ui/core/components/Form';
import { Input } from '@superset-ui/core/components/Input';
import { Typography } from '@superset-ui/core/components/Typography';
import {
  addSuccessToast,
  addDangerToast,
} from 'src/components/MessageToasts/actions';
import { useDispatch } from 'react-redux';
import {
  LoginContainer,
  LoginLogo,
  StyledCard,
  StyledLabel,
  PageContainer,
  LinkSection,
} from '../shared/LoginStyles';

interface ForgotPasswordForm {
  email: string;
}

export default function ForgotPasswordPage() {
  const [form] = Form.useForm<ForgotPasswordForm>();
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const dispatch = useDispatch();

  const onFinish = async (values: ForgotPasswordForm) => {
    setLoading(true);
    try {
      await SupersetClient.post({
        endpoint: '/api/v1/auth/forgot-password',
        jsonPayload: values,
      });
      setSubmitted(true);
      dispatch(
        addSuccessToast(
          t(
            "If an account with that email exists, we've sent you a password reset link.",
          ),
        ),
      );
    } catch (error) {
      dispatch(addDangerToast(t('Something went wrong. Please try again.')));
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <LoginContainer>
        <div css={PageContainer}>
          <LoginLogo>
            <a href="/">
              <img src="/static/assets/images/patent-1024.png" alt="Logo" />
            </a>
            <p className="tagline">Unlock Insights from US Patent Data</p>
          </LoginLogo>
          <StyledCard title={t('Check Your Email')} data-test="email-sent-form">
            <div
              css={css`
                text-align: center;
              `}
            >
              <Typography.Paragraph>
                {t(
                  "If an account with that email exists, we've sent you a password reset link.",
                )}
              </Typography.Paragraph>
              <Typography.Paragraph type="secondary">
                {t(
                  'Please check your email and follow the instructions to reset your password.',
                )}
              </Typography.Paragraph>
              <div css={LinkSection}>
                <a href="/login">{t('Back to Sign In')}</a>
              </div>
            </div>
          </StyledCard>
        </div>
      </LoginContainer>
    );
  }

  return (
    <LoginContainer>
      <div css={PageContainer}>
        <LoginLogo>
          <a href="/">
            <img src="/static/assets/images/patent-1024.png" alt="Logo" />
          </a>
          <p className="tagline">Unlock Insights from US Patent Data</p>
        </LoginLogo>
        <StyledCard
          title={t('Reset Your Password')}
          data-test="forgot-password-form"
        >
          <Typography.Paragraph
            type="secondary"
            css={css`
              text-align: center;
              margin-bottom: 24px;
            `}
          >
            {t(
              "Enter your email address and we'll send you a link to reset your password.",
            )}
          </Typography.Paragraph>
          <Form
            layout="vertical"
            requiredMark={false}
            form={form}
            onFinish={onFinish}
          >
            <Form.Item<ForgotPasswordForm>
              label={<StyledLabel>{t('Email Address')}</StyledLabel>}
              name="email"
              rules={[
                {
                  required: true,
                  message: t('Please enter your email address'),
                },
                {
                  type: 'email',
                  message: t('Please enter a valid email address'),
                },
              ]}
            >
              <Input
                className="form-control"
                data-test="email-input"
                placeholder={t('Email Address')}
                type="email"
              />
            </Form.Item>
            <Form.Item>
              <Button
                block
                type="primary"
                htmlType="submit"
                loading={loading}
                data-test="send-reset-button"
                className="btn-primary"
              >
                {t('Send Reset Link')}
              </Button>
            </Form.Item>
          </Form>
          <div css={LinkSection}>
            <a href="/login">{t('Back to Sign In')}</a>
          </div>
        </StyledCard>
      </div>
    </LoginContainer>
  );
}
