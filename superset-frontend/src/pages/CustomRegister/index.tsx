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
import { styled, t } from '@superset-ui/core';
import getBootstrapData from 'src/utils/getBootstrapData';
import ReactCAPTCHA from 'react-google-recaptcha';

interface RegisterForm {
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  conf_password: string;
}

interface FieldError {
  [key: string]: string[];
}

interface PolicyState {
  usernameLength: boolean;
  passwordLength: boolean;
  passwordUppercase: boolean;
  passwordLowercase: boolean;
  passwordNumber: boolean;
}

const StyledContainer = styled.div`
  body {
    background-color: #f2f4f7;
    background-image: url("data:image/svg+xml,%3Csvg width='80' height='80' viewBox='0 0 80 80' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg font-family='monospace' font-size='10' fill='%23283E53' fill-opacity='0.08'%3E%3Ctext x='0' y='15'%3E1010%3C/text%3E%3Ctext x='40' y='15'%3E0101%3C/text%3E%3Ctext x='0' y='35'%3E0101%3C/text%3E%3Ctext x='40' y='35'%3E1010%3C/text%3E%3Ctext x='0' y='55'%3E1010%3C/text%3E%3Ctext x='40' y='55'%3E0101%3C/text%3E%3Ctext x='0' y='75'%3E0101%3C/text%3E%3Ctext x='40' y='75'%3E1010%3C/text%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    margin: 0;
    padding: 20px 0;
  }

  background-color: #f2f4f7;
  background-image: url("data:image/svg+xml,%3Csvg width='80' height='80' viewBox='0 0 80 80' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg font-family='monospace' font-size='10' fill='%23283E53' fill-opacity='0.08'%3E%3Ctext x='0' y='15'%3E1010%3C/text%3E%3Ctext x='40' y='15'%3E0101%3C/text%3E%3Ctext x='0' y='35'%3E0101%3C/text%3E%3Ctext x='40' y='35'%3E1010%3C/text%3E%3Ctext x='0' y='55'%3E1010%3C/text%3E%3Ctext x='40' y='55'%3E0101%3C/text%3E%3Ctext x='0' y='75'%3E0101%3C/text%3E%3Ctext x='40' y='75'%3E1010%3C/text%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  margin: 0;
  padding: 20px 0;

  .register-container {
    max-width: 420px;
    width: 100%;
  }

  .login-logo {
    text-align: center;
    margin-bottom: 25px;
  }

  .login-logo img {
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

  .panel-default {
    border: none;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08), 0 0 20px rgba(40, 62, 83, 0.1);
    overflow: hidden;
  }

  .panel-heading {
    background-color: #ffffff !important;
    border-bottom: 1px solid #e7e7e7;
    text-align: center;
    padding: 20px 15px;
  }

  .panel-title {
    font-weight: 600;
    font-size: 22px;
    color: #333;
  }

  .panel-body {
    padding: 30px;
    background-color: #ffffff;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  .form-control {
    width: 100%;
    height: 44px;
    border-radius: 6px;
    border: 1px solid #dce4e8;
    box-shadow: none !important;
    padding: 8px 12px;
    font-size: 14px;
    box-sizing: border-box;
  }

  .form-control:focus {
    border-color: #283E53;
    outline: none;
  }

  .form-control.is-invalid {
    border-color: #d9534f !important;
  }

  .btn-primary {
    width: 100%;
    background-color: #283E53;
    border-color: #283E53;
    border-radius: 6px;
    padding: 10px;
    font-size: 16px;
    font-weight: 600;
    color: white;
    border: none;
    cursor: pointer;
  }

  .btn-primary:hover {
    background-color: #1e2f3f;
    border-color: #1e2f3f;
  }

  .btn-primary:disabled {
    background-color: #6c757d;
    border-color: #6c757d;
    cursor: not-allowed;
  }

  .invalid-feedback {
    color: #d9534f;
    font-size: 0.875em;
    margin-top: 0.25rem;
    display: block;
  }

  .login-link a {
    color: #283E53;
    font-weight: 600;
    text-decoration: none;
  }

  .login-link a:hover {
    text-decoration: underline;
  }

  .policy-container {
    font-size: 0.875em;
    color: #556270;
    padding: 10px 15px;
    margin-top: 8px;
    border-radius: 4px;
    background-color: #f8f9fa;
  }

  .policy-container ul {
    list-style-type: none;
    padding-left: 0;
    margin-bottom: 0;
  }

  .policy-container li {
    transition: all 0.3s ease;
    margin-bottom: 4px;
  }

  .policy-container li.valid {
    color: #28a745;
    text-decoration: line-through;
  }

  .policy-container li.valid::before {
    content: '✓ ';
    color: #28a745;
  }

  .policy-container li.invalid::before {
    content: '✗ ';
    color: #d9534f;
  }

  .spinner {
    display: inline-block;
    width: 1em;
    height: 1em;
    vertical-align: -0.125em;
    border: .2em solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    animation: spinner-spin .75s linear infinite;
    margin-right: .5rem;
  }

  @keyframes spinner-spin {
    to { transform: rotate(360deg); }
  }

  label {
    display: block;
    margin-bottom: 5px;
    font-weight: 500;
    color: #333;
  }
`;

export default function CustomRegister() {
  const bootstrapData = getBootstrapData();
  const registrationData = (bootstrapData as any)?.registration || {};
  
  const [formData, setFormData] = useState<RegisterForm>({
    username: '',
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    conf_password: '',
  });
  
  const [fieldErrors, setFieldErrors] = useState<FieldError>({});
  const [loading, setLoading] = useState(false);
  const [policyState, setPolicyState] = useState<PolicyState>({
    usernameLength: false,
    passwordLength: false,
    passwordUppercase: false,
    passwordLowercase: false,
    passwordNumber: false,
  });
  const [captchaResponse, setCaptchaResponse] = useState<string | null>(null);

  // Get reCAPTCHA public key from bootstrap data
  const authRecaptchaPublicKey: string = 
    (bootstrapData as any)?.common?.conf?.RECAPTCHA_PUBLIC_KEY || '';

  // Real-time validation for username
  useEffect(() => {
    setPolicyState(prev => ({
      ...prev,
      usernameLength: formData.username.length >= 5,
    }));
  }, [formData.username]);

  // Real-time validation for password
  useEffect(() => {
    const password = formData.password;
    setPolicyState(prev => ({
      ...prev,
      passwordLength: password.length >= 8,
      passwordUppercase: /[A-Z]/.test(password),
      passwordLowercase: /[a-z]/.test(password),
      passwordNumber: /[0-9]/.test(password),
    }));
  }, [formData.password]);

  const handleInputChange = (field: keyof RegisterForm, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Clear field error when user starts typing
    if (fieldErrors[field]) {
      setFieldErrors(prev => ({ ...prev, [field]: [] }));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setFieldErrors({});

    // Use traditional form submission to let browser handle redirect naturally
    const form = e.target as HTMLFormElement;
    const formData = new FormData(form);
    
    // Get CSRF token from bootstrap data or DOM
    const csrfToken = bootstrapData?.common?.conf?.CSRF_TOKEN || 
                     document.querySelector<HTMLInputElement>('#csrf_token')?.value || '';
    formData.append('csrf_token', csrfToken);
    
    // Add captcha response if available
    if (captchaResponse) {
      formData.append('g-recaptcha-response', captchaResponse);
    }

    // Create a hidden form and submit it traditionally
    const hiddenForm = document.createElement('form');
    hiddenForm.method = 'POST';
    hiddenForm.action = '/register/form';
    hiddenForm.style.display = 'none';

    // Add all form data as hidden inputs
    for (const [key, value] of formData.entries()) {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = key;
      input.value = value as string;
      hiddenForm.appendChild(input);
    }

    document.body.appendChild(hiddenForm);
    hiddenForm.submit();
  };

  return (
    <StyledContainer>
      <div className="register-container">
        <div className="login-logo">
          <a href="/">
            <img src="/static/assets/images/patent-1024.png" alt="Logo" />
          </a>
          <p className="tagline">{t('Create Your Account')}</p>
        </div>

        <div className="panel panel-default">
          <div className="panel-heading">
            <h3 className="panel-title">{registrationData.title || t('Create Your Account')}</h3>
          </div>
          <div className="panel-body">
            <form className="form" onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="username">{t('User Name')}</label>
                <input
                  type="text"
                  id="username"
                  name="username"
                  className={`form-control ${fieldErrors.username ? 'is-invalid' : ''}`}
                  value={formData.username}
                  onChange={(e) => handleInputChange('username', e.target.value)}
                  required
                />
                <div className="policy-container">
                  <ul>
                    <li className={policyState.usernameLength ? 'valid' : 'invalid'}>
                      {t('At least 5 characters')}
                    </li>
                  </ul>
                </div>
                {fieldErrors.username && (
                  <div className="invalid-feedback">
                    {fieldErrors.username.map((error, idx) => (
                      <span key={idx}>{error}</span>
                    ))}
                  </div>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="first_name">{t('First Name')}</label>
                <input
                  type="text"
                  id="first_name"
                  name="first_name"
                  className={`form-control ${fieldErrors.first_name ? 'is-invalid' : ''}`}
                  value={formData.first_name}
                  onChange={(e) => handleInputChange('first_name', e.target.value)}
                  required
                />
                {fieldErrors.first_name && (
                  <div className="invalid-feedback">
                    {fieldErrors.first_name.map((error, idx) => (
                      <span key={idx}>{error}</span>
                    ))}
                  </div>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="last_name">{t('Last Name')}</label>
                <input
                  type="text"
                  id="last_name"
                  name="last_name"
                  className={`form-control ${fieldErrors.last_name ? 'is-invalid' : ''}`}
                  value={formData.last_name}
                  onChange={(e) => handleInputChange('last_name', e.target.value)}
                  required
                />
                {fieldErrors.last_name && (
                  <div className="invalid-feedback">
                    {fieldErrors.last_name.map((error, idx) => (
                      <span key={idx}>{error}</span>
                    ))}
                  </div>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="email">{t('Email')}</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  className={`form-control ${fieldErrors.email ? 'is-invalid' : ''}`}
                  value={formData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  required
                />
                {fieldErrors.email && (
                  <div className="invalid-feedback">
                    {fieldErrors.email.map((error, idx) => (
                      <span key={idx}>{error}</span>
                    ))}
                  </div>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="password">{t('Password')}</label>
                <input
                  type="password"
                  id="password"
                  name="password"
                  className={`form-control ${fieldErrors.password ? 'is-invalid' : ''}`}
                  value={formData.password}
                  onChange={(e) => handleInputChange('password', e.target.value)}
                  required
                />
                <div className="policy-container">
                  <ul>
                    <li className={policyState.passwordLength ? 'valid' : 'invalid'}>
                      {t('At least 8 characters')}
                    </li>
                    <li className={policyState.passwordUppercase ? 'valid' : 'invalid'}>
                      {t('An uppercase letter')}
                    </li>
                    <li className={policyState.passwordLowercase ? 'valid' : 'invalid'}>
                      {t('A lowercase letter')}
                    </li>
                    <li className={policyState.passwordNumber ? 'valid' : 'invalid'}>
                      {t('At least one number')}
                    </li>
                  </ul>
                </div>
                {fieldErrors.password && (
                  <div className="invalid-feedback">
                    {fieldErrors.password.map((error, idx) => (
                      <span key={idx}>{error}</span>
                    ))}
                  </div>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="conf_password">{t('Confirm Password')}</label>
                <input
                  type="password"
                  id="conf_password"
                  name="conf_password"
                  className={`form-control ${fieldErrors.conf_password ? 'is-invalid' : ''}`}
                  value={formData.conf_password}
                  onChange={(e) => handleInputChange('conf_password', e.target.value)}
                  required
                />
                {fieldErrors.conf_password && (
                  <div className="invalid-feedback">
                    {fieldErrors.conf_password.map((error, idx) => (
                      <span key={idx}>{error}</span>
                    ))}
                  </div>
                )}
              </div>

              {/* Google reCAPTCHA */}
              {authRecaptchaPublicKey && (
                <div className="form-group">
                  <label>{t('Captcha')}</label>
                  <ReactCAPTCHA
                    sitekey={authRecaptchaPublicKey}
                    onChange={(value) => {
                      setCaptchaResponse(value);
                    }}
                    data-test="captcha-input"
                  />
                </div>
              )}

              <button
                type="submit"
                className="btn btn-primary"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner"></span>
                    {t('Processing...')}
                  </>
                ) : (
                  t('Sign Up')
                )}
              </button>
            </form>

            {fieldErrors.general && (
              <div className="invalid-feedback" style={{ marginTop: '15px', textAlign: 'center' }}>
                {fieldErrors.general.map((error, idx) => (
                  <span key={idx}>{error}</span>
                ))}
              </div>
            )}

            <div className="text-center login-link" style={{ paddingTop: '15px' }}>
              {t('Already have an account?')}{' '}
              <a href="/login/">
                {t('Sign In')}
              </a>
            </div>
          </div>
        </div>
      </div>
    </StyledContainer>
  );
} 