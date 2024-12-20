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
import { ReactNode, ReactElement } from 'react';

import { AntdDropdown, AntdTooltip } from 'src/components';
import { styled } from '@superset-ui/core';
import { kebabCase } from 'lodash';

const StyledDropdownButton = styled.div`
  .ant-btn-group {
    button.ant-btn {
      background-color: ${({ theme }) => theme.colorPrimaryText};
      border-color: transparent;
      color: ${({ theme }) => theme.colors.grayscale.light5};
      font-size: 12px;
      line-height: 13px;
      outline: none;
      &:first-of-type {
        border-radius: ${({ theme }) =>
          `${theme.sizeUnit}px 0 0 ${theme.sizeUnit}px`};
        margin: 0;
      }

      &:disabled {
        background-color: ${({ theme }) => theme.colors.grayscale.light2};
        color: ${({ theme }) => theme.colors.grayscale.base};
      }
      &:nth-of-type(2) {
        margin: 0;
        border-radius: ${({ theme }) =>
          `0 ${theme.sizeUnit}px ${theme.sizeUnit}px 0`};
        width: ${({ theme }) => theme.sizeUnit * 9}px;
        &:before,
        &:hover:before {
          border-left: 1px solid ${({ theme }) => theme.colors.grayscale.light5};
          content: '';
          display: block;
          height: ${({ theme }) => theme.sizeUnit * 8}px;
          margin: 0;
          position: absolute;
          width: ${({ theme }) => theme.sizeUnit * 0.25}px;
        }

        &:disabled:before {
          border-left: 1px solid ${({ theme }) => theme.colors.grayscale.base};
        }
      }
    }
  }
`;

export interface DropdownButtonProps {
  overlay: ReactElement;
  tooltip?: string;
  placement?: 'topLeft' | 'topRight' | 'bottomLeft' | 'bottomRight';
  buttonsRender?: ((buttons: ReactNode[]) => ReactNode[]) | undefined;
}

export const DropdownButton = ({
  overlay,
  tooltip,
  placement,
  ...rest
}: DropdownButtonProps) => {
  const buildButton = (
    props: {
      buttonsRender?: DropdownButtonProps['buttonsRender'];
    } = {},
  ) => (
    <StyledDropdownButton>
      <AntdDropdown.Button overlay={overlay} {...rest} {...props} />
    </StyledDropdownButton>
  );
  if (tooltip) {
    return buildButton({
      buttonsRender: ([leftButton, rightButton]) => [
        <AntdTooltip
          placement={placement}
          id={`${kebabCase(tooltip)}-tooltip`}
          title={tooltip}
        >
          {leftButton}
        </AntdTooltip>,
        rightButton,
      ],
    });
  }
  return buildButton();
};
