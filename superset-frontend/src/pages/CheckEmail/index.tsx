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
import { t } from '@superset-ui/core';
import { styled } from '@apache-superset/core/ui';
import getBootstrapData from 'src/utils/getBootstrapData';

const StyledContainer = styled.div`
  background-color: #f2f4f7;
  background-image: url("data:image/svg+xml,%3Csvg width='80' height='80' viewBox='0 0 80 80' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg font-family='monospace' font-size='10' fill='%23283E53' fill-opacity='0.08'%3E%3Ctext x='0' y='15'%3E1010%3C/text%3E%3Ctext x='40' y='15'%3E0101%3C/text%3E%3Ctext x='0' y='35'%3E0101%3C/text%3E%3Ctext x='40' y='35'%3E1010%3C/text%3E%3Ctext x='0' y='55'%3E1010%3C/text%3E%3Ctext x='40' y='55'%3E0101%3C/text%3E%3Ctext x='0' y='75'%3E0101%3C/text%3E%3Ctext x='40' y='75'%3E1010%3C/text%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  margin: 0;

  .login-container {
    max-width: 420px;
    width: 100%;
    padding: 20px;
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
    text-align: center;
  }

  .btn-primary {
    background-color: #283E53;
    border-color: #283E53;
    border-radius: 6px;
    padding: 10px 20px;
    font-size: 16px;
    font-weight: 600;
    transition: background-color 0.2s ease-in-out;
    color: white;
    border: none;
    cursor: pointer;
  }

  .btn-primary:hover:not(:disabled) {
    background-color: #1e2f3f;
    border-color: #1e2f3f;
  }

  .btn-primary:disabled {
    background-color: #6c757d;
    border-color: #6c757d;
    cursor: not-allowed;
  }

  hr {
    border: none;
    border-top: 1px solid #e7e7e7;
    margin: 20px 0;
  }

  p {
    margin-bottom: 15px;
    color: #333;
    line-height: 1.5;
  }
`;

export default function CheckEmail() {
  const [timeLeft, setTimeLeft] = useState(60);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const bootstrapData = getBootstrapData();
  const checkEmailData = (bootstrapData as any)?.checkEmail || {};
  const email = checkEmailData.email || '';
  const registerUserId = checkEmailData.register_user_id || '';

  useEffect(() => {
    if (timeLeft > 0) {
      const timer = setTimeout(() => {
        setTimeLeft(timeLeft - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [timeLeft]);

  const handleResendEmail = async () => {
    if (!registerUserId) {
      console.error('No register_user_id available');
      return;
    }

    setIsSubmitting(true);
    
    try {
      // Get CSRF token from bootstrap data or DOM
      const csrfToken = (bootstrapData as any)?.common?.conf?.CSRF_TOKEN || 
                       document.querySelector<HTMLInputElement>('#csrf_token')?.value || '';
      
      const response = await fetch(`/register/resend-activation/${registerUserId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `csrf_token=${encodeURIComponent(csrfToken)}`,
        credentials: 'same-origin',
      });

      if (response.ok) {
        // Reset timer and disable button again
        setTimeLeft(60);
      } else {
        console.error('Failed to resend activation email');
      }
    } catch (error) {
      console.error('Error resending activation email:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <StyledContainer>
      <div className="login-container">
        <div className="login-logo">
          <a href="/">
            <img src="/static/assets/images/patent-1024.png" alt="Logo" />
          </a>
          <p className="tagline">{t('Unlock Insights from US Patent Data')}</p>
        </div>

        <div className="panel panel-default">
          <div className="panel-heading">
            <h3 className="panel-title">{t('Check Your Email')}</h3>
          </div>
          <div className="panel-body">
            <p>
              {t("We've sent an activation link to your email address: ")}<strong>{email}</strong>.
            </p>
            <p>
              {t('Please click the link in that email to activate your account.')}
            </p>
            <p>
              {t("If you don't see the email in your inbox, please check your spam folder.")}
            </p>
            <hr />
            <p>
              {t("Didn't receive the email after a minute?")}
            </p>
            <button
              type="button"
              className="btn btn-primary"
              disabled={timeLeft > 0 || isSubmitting}
              onClick={handleResendEmail}
            >
              {isSubmitting ? t('Processing...') : t('Resend Activation Email')}
            </button>
            {timeLeft > 0 && (
              <p style={{ marginTop: '10px' }}>
                {t('You can resend the email in ')} {timeLeft} {t(' seconds.')}
              </p>
            )}
          </div>
        </div>
      </div>
    </StyledContainer>
  );
} 