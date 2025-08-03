/**
 * Custom Login Page
 */

import { useState } from 'react';
import { SupersetClient, t } from '@superset-ui/core';
import { Link } from 'react-router-dom';
import {
  Button,
  Form,
  Input,
} from '@superset-ui/core/components';
import getBootstrapData from 'src/utils/getBootstrapData';
import {
  LoginContainer,
  LoginLogo,
  StyledCard,
  StyledLabel,
  PageContainer,
  LinkSection,
} from '../shared/LoginStyles';


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
      <div css={PageContainer}>
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
            <div className="text-center" css={LinkSection}>
              {t("Don't have an account?")}{' '}
              <a href="/register/form">{t('Sign Up')}</a>
            </div>
          )}
          <div className="text-center" css={LinkSection}>
            <Link to="/forgot-password/">{t('Forgot your password?')}</Link>
          </div>
        </StyledCard>
      </div>
    </LoginContainer>
  );
} 