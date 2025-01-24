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
/* eslint-disable @typescript-eslint/no-unused-vars */
import { theme as antdThemeImport } from 'antd-v5';
import tinycolor from 'tinycolor2';

export type AntdTokens = ReturnType<typeof antdThemeImport.getDesignToken>;

export interface SystemColors {
  colorPrimary: string;
  colorError: string;
  colorWarning: string;
  colorSuccess: string;
  colorInfo: string;
}

export interface ColorVariants {
  bg: string;
  border: string;
  hover: string;
  active: string;
  textHover: string;
  text: string;
  borderHover: string;
  bgHover: string;
  textActive: string;
}

export interface DeprecatedColorVariations {
  base: string;
  light1: string;
  light2: string;
  light3: string;
  light4: string;
  light5: string;
  dark1: string;
  dark2: string;
  dark3: string;
  dark4: string;
  dark5: string;
}

export interface DeprecatedThemeColors {
  primary: DeprecatedColorVariations;
  error: DeprecatedColorVariations;
  warning: DeprecatedColorVariations;
  success: DeprecatedColorVariations;
  info: DeprecatedColorVariations;
  grayscale: DeprecatedColorVariations;
}

export interface LegacySupersetTheme {
  colors: DeprecatedThemeColors;
  transitionTiming: number;
}

export interface SupersetSpecificTokens {
  brandIconMaxWidth: number;
  fontSizeXS: string;
  fontSizeXXL: string;
  fontWeightNormal: string;
  fontWeightLight: string;
  fontWeightMedium: string;
}

export const allowedAntdTokens = [
  // ...
] as const;

export type AllowedAntdTokenKeys = Extract<
  (typeof allowedAntdTokens)[number],
  keyof AntdTokens
>;

export type SharedAntdTokens = Pick<AntdTokens, AllowedAntdTokenKeys>;

export type SupersetTheme = LegacySupersetTheme &
  SharedAntdTokens &
  SupersetSpecificTokens;
