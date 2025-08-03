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

import { useState, useEffect } from 'react';
import { SupersetClient, t, css, useTheme } from '@superset-ui/core';
import { Button } from '@superset-ui/core/components/Button';
import { Form } from '@superset-ui/core/components/Form';
import { Input } from '@superset-ui/core/components/Input';
import { Typography } from '@superset-ui/core/components/Typography';
import ProgressBar from '@superset-ui/core/components/ProgressBar';
import { useLocation, useHistory } from 'react-router-dom';
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

interface ResetPasswordForm {
  password: string;
  confirmPassword: string;
}

interface PasswordStrength {
  score: number;
  text: string;
  color: string;
}

export default function ResetPasswordPage() {
  const [form] = Form.useForm<ResetPasswordForm>();
  const dispatch = useDispatch();
  const theme = useTheme();
  const [loading, setLoading] = useState(false);
  const [validatingToken, setValidatingToken] = useState(true);
  const [tokenValid, setTokenValid] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState<PasswordStrength>({
    score: 0,
    text: '',
    color: '',
  });
  const location = useLocation();
  const history = useHistory();
  const token = new URLSearchParams(location.search).get('token');

  useEffect(() => {
    if (!token) {
      dispatch(
        addDangerToast(t('The password reset link is invalid or has expired.')),
      );
      history.push('/login');
      return;
    }

    validateToken(token);
  }, [token, history]);

  const validateToken = async (resetToken: string) => {
    try {
      await SupersetClient.get({
        endpoint: `/api/v1/auth/validate-reset-token/${resetToken}`,
      });
      setTokenValid(true);
    } catch (error) {
      dispatch(
        addDangerToast(t('The password reset link is invalid or has expired.')),
      );
      history.push('/login');
    } finally {
      setValidatingToken(false);
    }
  };

  const calculatePasswordStrength = (password: string): PasswordStrength => {
    if (!password) return { score: 0, text: '', color: '' };

    let score = 0;
    if (password.length >= 8) score += 25;
    if (password.length >= 12) score += 25;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score += 25;
    if (/\d/.test(password)) score += 15;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score += 10;

    if (score < 40)
      return { score, text: t('Weak'), color: theme.colors.error.base };
    if (score < 70)
      return { score, text: t('Fair'), color: theme.colors.warning.base };
    if (score < 90)
      return { score, text: t('Good'), color: theme.colors.success.base };
    return { score, text: t('Strong'), color: theme.colors.success.dark1 };
  };

  const onPasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const password = e.target.value;
    setPasswordStrength(calculatePasswordStrength(password));
  };

  const onFinish = async (values: ResetPasswordForm) => {
    if (!token) return;

    setLoading(true);
    try {
      await SupersetClient.post({
        endpoint: '/api/v1/auth/reset-password',
        jsonPayload: {
          token,
          new_password: values.password,
          confirm_password: values.confirmPassword,
        },
      });

      dispatch(
        addSuccessToast(
          t(
            'Your password has been updated successfully. You can now sign in with your new password.',
          ),
        ),
      );

      history.push('/login');
    } catch (error: any) {
      let errorMessage = t(
        'Failed to reset password. Please try again or request a new reset link.',
      );

      // Try to extract specific error message from API response
      if (error?.response?.data?.message) {
        errorMessage = error.response.data.message;
      }

      dispatch(addDangerToast(errorMessage));
    } finally {
      setLoading(false);
    }
  };

  if (validatingToken) {
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
            title={t('Validating Reset Link')}
            data-test="validating-token"
          >
            <div
              css={css`
                text-align: center;
                padding: 20px;
              `}
            >
              <Typography.Paragraph>
                {t('Please wait while we validate your reset link...')}
              </Typography.Paragraph>
            </div>
          </StyledCard>
        </div>
      </LoginContainer>
    );
  }

  if (!tokenValid) {
    return null; // Will redirect to login
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
          title={t('Create New Password')}
          data-test="reset-password-form"
        >
          <Typography.Paragraph
            type="secondary"
            css={css`
              text-align: center;
              margin-bottom: 24px;
            `}
          >
            {t('Please enter your new password below.')}
          </Typography.Paragraph>
          <Form
            layout="vertical"
            requiredMark={false}
            form={form}
            onFinish={onFinish}
          >
            <Form.Item<ResetPasswordForm>
              label={<StyledLabel>{t('New Password')}</StyledLabel>}
              name="password"
              rules={[
                {
                  required: true,
                  message: t('Please enter your new password'),
                },
                {
                  min: 8,
                  message: t('Password must be at least 8 characters long'),
                },
              ]}
            >
              <Input.Password
                className="form-control"
                data-test="password-input"
                placeholder={t('New Password')}
                onChange={onPasswordChange}
              />
            </Form.Item>

            {passwordStrength.text && (
              <div
                css={css`
                  margin-bottom: 16px;
                `}
              >
                <div
                  css={css`
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 4px;
                  `}
                >
                  <Typography.Text
                    type="secondary"
                    css={css`
                      font-size: 12px;
                    `}
                  >
                    {t('Password Strength')}
                  </Typography.Text>
                  <Typography.Text
                    css={css`
                      font-size: 12px;
                      color: ${passwordStrength.color};
                      font-weight: 600;
                    `}
                  >
                    {passwordStrength.text}
                  </Typography.Text>
                </div>
                <ProgressBar
                  percent={passwordStrength.score}
                  striped={false}
                  showInfo={false}
                />
              </div>
            )}

            <Form.Item<ResetPasswordForm>
              label={<StyledLabel>{t('Confirm New Password')}</StyledLabel>}
              name="confirmPassword"
              dependencies={['password']}
              rules={[
                {
                  required: true,
                  message: t('Please confirm your new password'),
                },
                ({ getFieldValue }: any) => ({
                  validator(_: any, value: any) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(
                      new Error(t('Passwords do not match')),
                    );
                  },
                }),
              ]}
            >
              <Input.Password
                className="form-control"
                data-test="confirm-password-input"
                placeholder={t('Confirm New Password')}
              />
            </Form.Item>
            <Form.Item>
              <Button
                block
                type="primary"
                htmlType="submit"
                loading={loading}
                data-test="reset-password-button"
                className="btn-primary"
              >
                {t('Update Password')}
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
