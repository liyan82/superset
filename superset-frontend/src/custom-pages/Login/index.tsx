/**
 * Custom Login Page
 */

import React, { useState } from 'react';
import { SupersetClient, styled, t, css } from '@superset-ui/core';
import {
  Button,
  Card,
  Form,
  Input,
  Typography,
} from '@superset-ui/core/components';
import getBootstrapData from 'src/utils/getBootstrapData';

// Styled components from your original login.html
const LoginContainer = styled.div`
  background-color: #f2f4f7;
  background-image: url("data:image/svg+xml,%3Csvg width='80' height='80' viewBox='0 0 80 80' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg font-family='monospace' font-size='10' fill='%23283E53' fill-opacity='0.08'%3E%3Ctext x='0' y='15'%3E1010%3C/text%3E%3Ctext x='40' y='15'%3E0101%3C/text%3E%3Ctext x='0' y='35'%3E0101%3C/text%3E%3Ctext x='40' y='35'%3E1010%3C/text%3E%3Ctext x='0' y='55'%3E1010%3C/text%3E%3Ctext x='40' y='55'%3E0101%3C/text%3E%3Ctext x='0' y='75'%3E0101%3C/text%3E%3Ctext x='40' y='75'%3E1010%3C/text%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  margin: 0;
`;

const LoginLogo = styled.div`
  text-align: center;
  margin-bottom: 25px;

  img {
    max-width: 200px;
    height: auto;
    margin-bottom: 10px;
  }

  .tagline {
    color: #556270;
    font-size: 1em;
    margin: 0;
    text-shadow: 0 1px 1px rgba(255,255,255,0.5);
  }
`;

const StyledCard = styled(Card)`
  border: none;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08), 0 0 20px rgba(40, 62, 83, 0.1);
  overflow: hidden;
  .ant-card-head {
    background-color: #ffffff !important;
    border-bottom: 1px solid #e7e7e7;
    text-align: center;
    padding: 20px 15px;
  }
  .ant-card-head-title {
    font-weight: 600;
    font-size: 22px;
    color: #333;
    padding: 0;
  }
  .ant-card-body {
    padding: 30px;
  }
  .ant-form-item {
      margin-bottom: 20px;
  }
  .form-control {
      height: 44px;
      border-radius: 6px;
      border: 1px solid #dce4e8;
      box-shadow: none !important;
  }
  .form-control:focus {
      border-color: #283E53;
  }
  .btn-primary {
      background-color: #283E53;
      border-color: #283E53;
      border-radius: 6px;
      padding: 10px;
      font-size: 16px;
      font-weight: 600;
      transition: background-color 0.2s ease-in-out;
  }
  .btn-primary:hover {
      background-color: #1e2f3f;
      border-color: #1e2f3f;
  }
`;

const StyledLabel = styled(Typography.Text)`
  ${({ theme }) => css`
    font-size: ${theme.fontSizeSM}px;
  `}
`;

interface LoginForm {
  username: string;
  password: string;
}

export default function CustomLoginPage() {
  const [form] = Form.useForm<LoginForm>();
  const [loading, setLoading] = useState(false);
  const bootstrapData = getBootstrapData();
  const authRegistration: boolean = bootstrapData.common.conf.AUTH_USER_REGISTRATION;

  const onFinish = (values: LoginForm) => {
    setLoading(true);
    SupersetClient.postForm('/login/', values, '')
      .catch(() => {
        // The SupersetClient already handles showing an error toast
      })
      .finally(() => {
        setLoading(false);
        // On successful login the page will redirect
      });
  };

  return (
    <LoginContainer>
      <div
        css={css`
          max-width: 420px;
          width: 100%;
          padding: 20px;
        `}
      >
        <LoginLogo>
          <a href="/">
            <img src="/static/assets/images/patent-1024.png" alt="Logo" />
          </a>
          <p className="tagline">Unlock Insights from US Patent Data</p>
        </LoginLogo>
        <StyledCard title={t('Sign In')} data-test="login-form">
            <Form
              layout="vertical"
              requiredMark={false}
              form={form}
              onFinish={onFinish}
            >
              <Form.Item<LoginForm>
                label={<StyledLabel>{t('User Name')}</StyledLabel>}
                name="username"
                rules={[
                  { required: true, message: t('Please enter your username') },
                ]}
              >
                <Input
                  className="form-control"
                  data-test="username-input"
                  placeholder={t('User Name')}
                />
              </Form.Item>
              <Form.Item<LoginForm>
                label={<StyledLabel>{t('Password')}</StyledLabel>}
                name="password"
                rules={[
                  { required: true, message: t('Please enter your password') },
                ]}
              >
                <Input.Password
                  className="form-control"
                  data-test="password-input"
                  placeholder={t('Password')}
                />
              </Form.Item>
              <Form.Item>
                <Button
                  block
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  data-test="login-button"
                  className="btn-primary"
                >
                  {t('Sign In')}
                </Button>
              </Form.Item>
            </Form>
          {authRegistration && (
            <div
              className="text-center"
              css={css`
                padding-top: 15px;
                a {
                  color: #283E53;
                  font-weight: 600;
                }
              `}
            >
              {t("Don't have an account?")}{' '}
              <a href="/register/">{t('Sign Up')}</a>
            </div>
          )}
        </StyledCard>
      </div>
    </LoginContainer>
  );
} 