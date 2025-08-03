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

import { styled, css } from '@superset-ui/core';
import { Card, Typography } from '@superset-ui/core/components';

export const LoginContainer = styled.div`
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

export const LoginLogo = styled.div`
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
    text-shadow: 0 1px 1px rgba(255, 255, 255, 0.5);
  }
`;

export const StyledCard = styled(Card)`
  border: none;
  border-radius: 8px;
  box-shadow:
    0 4px 20px rgba(0, 0, 0, 0.08),
    0 0 20px rgba(40, 62, 83, 0.1);
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
    border-color: #283e53;
  }
  .btn-primary {
    background-color: #283e53;
    border-color: #283e53;
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

export const StyledLabel = styled(Typography.Text)`
  ${({ theme }) => css`
    font-size: ${theme.fontSizeSM}px;
  `}
`;

export const PageContainer = css`
  max-width: 420px;
  width: 100%;
  padding: 20px;
`;

export const LinkSection = css`
  text-center;
  padding-top: 15px;
  a {
    color: #283E53;
    font-weight: 600;
    text-decoration: none;
  }
  a:hover {
    text-decoration: underline;
  }
`;
