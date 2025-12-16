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

  .success-icon {
    width: 60px;
    height: 60px;
    background: #28a745;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 20px;
    font-size: 30px;
    color: white;
  }

  .countdown {
    color: #6c757d;
    font-size: 14px;
    margin-top: 15px;
    font-style: italic;
  }

  .redirect-link {
    color: #283E53;
    text-decoration: none;
    font-weight: 600;
  }

  .redirect-link:hover {
    text-decoration: underline;
  }
`;

export default function ActivationSuccess() {
  const [timeLeft, setTimeLeft] = useState(5);
  
  const bootstrapData = getBootstrapData();
  const activationData = (bootstrapData as any)?.activationSuccess || {};
  const username = activationData.username || '';
  const firstName = activationData.first_name || '';

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          // Redirect to login
          window.location.href = '/login/';
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const handleGoToLogin = () => {
    window.location.href = '/login/';
  };

  const displayName = firstName || username;

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
            <h3 className="panel-title">{t('Account Activated Successfully!')}</h3>
          </div>
          <div className="panel-body">
            <div className="success-icon">✓</div>
            
            <p>
              <strong>
                {t('Welcome')}
                {displayName ? `, ${displayName}` : ''}!
              </strong>
            </p>
            <p>
              {t('Your account has been successfully activated. You can now access all features of Superset.')}
            </p>
            
            <hr />
            
            <button
              type="button"
              className="btn btn-primary"
              onClick={handleGoToLogin}
            >
              {t('Go to Login')}
            </button>
            
                         <div className="countdown">
               {timeLeft > 0 ? (
                 <>
                   {t('Automatically redirecting to login in ')} 
                   {timeLeft} 
                   {t(' second')}{timeLeft !== 1 ? t('s') : ''}...
                 </>
               ) : (
                 t('Redirecting...')
               )}
             </div>
            
            <p style={{ marginTop: '20px', fontSize: '14px' }}>
              {t('If the automatic redirect doesn\'t work, click ')}{' '}
              <a href="/login/" className="redirect-link">{t('here to login')}</a>.
            </p>
          </div>
        </div>
      </div>
    </StyledContainer>
  );
} 