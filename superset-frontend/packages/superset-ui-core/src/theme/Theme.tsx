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
/* eslint-disable react-prefer-function-component/react-prefer-function-component */
import {
  theme as antdThemeImport,
  ThemeConfig as AntdThemeConfig,
  ConfigProvider,
} from 'antd-v5';
import tinycolor from 'tinycolor2';
import {
  ThemeProvider as EmotionThemeProvider,
  CacheProvider as EmotionCacheProvider,
} from '@emotion/react';
import createCache from '@emotion/cache';
// import { merge } from 'lodash';

import {
  AntdTokens,
  SupersetTheme,
  allowedAntdTokens,
  SharedAntdTokens,
  SystemColors,
  DeprecatedThemeColors,
  LegacySupersetTheme,
  DeprecatedColorVariations,
  // SupersetSpecificTokens // <- Remove if truly unused here
} from './types';

// We have old references to color-literal usage in this file
/* eslint-disable theme-colors/no-literal-colors */

export class Theme {
  theme: SupersetTheme;

  private static readonly defaultTokens = {
    colorPrimary: '#20a7c9',
    colorError: '#e04355',
    colorWarning: '#fcc700',
    colorSuccess: '#5ac189',
    colorInfo: '#66bcfe',

    fontFamily: `'Inter', Helvetica, Arial`,
    fontFamilyCode: `'Fira Code', 'Courier New', monospace`,

    transitionTiming: 0.3,
    brandIconMaxWidth: 37,
    fontSizeXS: '8',
    fontSizeXXL: '28',
    fontWeightNormal: '400',
    fontWeightLight: '300',
    fontWeightMedium: '500',
  };

  private antdConfig: AntdThemeConfig;

  // Note: rename or remove unused parameters if you get warnings.
  private constructor({
    seed,
    antdConfig,
    isDark = false,
  }: {
    seed?: Partial<SupersetTheme>;
    antdConfig?: AntdThemeConfig;
    isDark?: boolean;
  }) {
    if (seed && antdConfig) {
      throw new Error('Pass either theme or antdConfig, not both.');
    } else if (antdConfig) {
      this.setThemeFromAntdConfig(antdConfig);
    } else if (seed) {
      this.setThemeFromSeed(seed || {}, isDark);
    }
  }

  static fromSeed(seed?: Partial<SupersetTheme>, isDark = false): Theme {
    return new Theme({ seed, isDark });
  }

  static fromAntdConfig(antdConfig: AntdThemeConfig): Theme {
    return new Theme({ antdConfig });
  }

  private static genDeprecatedColorVariations(
    color: string,
    isDark: boolean,
  ): DeprecatedColorVariations {
    const bg = isDark ? '#FFF' : '#000';
    const fg = isDark ? '#000' : '#FFF';
    const adjustColor = (
      baseColor: string,
      perc: number,
      target: string,
    ): string => tinycolor.mix(baseColor, target, perc).toHexString();

    return {
      base: color,
      light1: adjustColor(color, 20, fg),
      light2: adjustColor(color, 45, fg),
      light3: adjustColor(color, 70, fg),
      light4: adjustColor(color, 90, fg),
      light5: adjustColor(color, 95, fg),
      dark1: adjustColor(color, 10, bg),
      dark2: adjustColor(color, 20, bg),
      dark3: adjustColor(color, 40, bg),
      dark4: adjustColor(color, 60, bg),
      dark5: adjustColor(color, 80, bg),
    };
  }

  private static getColors(
    systemColors: SystemColors,
    isDark: boolean,
  ): DeprecatedThemeColors {
    const sc = systemColors;
    return {
      primary: Theme.genDeprecatedColorVariations(sc.colorPrimary, isDark),
      error: Theme.genDeprecatedColorVariations(sc.colorError, isDark),
      warning: Theme.genDeprecatedColorVariations(sc.colorWarning, isDark),
      success: Theme.genDeprecatedColorVariations(sc.colorSuccess, isDark),
      info: Theme.genDeprecatedColorVariations(sc.colorInfo, isDark),
      grayscale: Theme.genDeprecatedColorVariations('#666', isDark),
    };
  }

  private static augmentSeedWithDefaults(
    seed: Partial<SupersetTheme>,
  ): Partial<SupersetTheme> {
    return {
      ...Theme.defaultTokens,
      ...seed,
    };
  }

  private static getSystemColors(antdTokens: SharedAntdTokens): SystemColors {
    return {
      colorPrimary: antdTokens.colorPrimary,
      colorError: antdTokens.colorError,
      colorWarning: antdTokens.colorWarning,
      colorSuccess: antdTokens.colorSuccess,
      colorInfo: antdTokens.colorInfo,
    };
  }

  private static getSupersetTheme(
    seed: Partial<SupersetTheme>,
    isDark = false,
  ): SupersetTheme {
    const antdConfig = Theme.getAntdConfig(seed, isDark);
    const antdTokens = Theme.getFilteredAntdTheme(antdConfig);
    const systemColors = Theme.getSystemColors(antdTokens);

    return {
      colors: Theme.getColors(systemColors, isDark),
      ...Theme.defaultTokens,
      ...antdTokens,
    };
  }

  private static getFilteredAntdTheme(
    antdConfig: AntdThemeConfig,
  ): SharedAntdTokens {
    const theme = Theme.getAntdTokens(antdConfig);
    return Object.fromEntries(
      allowedAntdTokens.map(key => [key, theme[key]]),
    ) as SharedAntdTokens;
  }

  private static getAntdConfig(
    seed: Partial<SupersetTheme>,
    isDark: boolean,
  ): AntdThemeConfig {
    const algorithm = isDark
      ? antdThemeImport.darkAlgorithm
      : antdThemeImport.defaultAlgorithm;
    return {
      token: seed,
      algorithm,
    };
  }

  private static getAntdTokens(antdConfig: AntdThemeConfig): AntdTokens {
    return antdThemeImport.getDesignToken(antdConfig);
  }

  private updateTheme(theme: SupersetTheme, antdConfig: AntdThemeConfig): void {
    this.theme = theme;
    this.antdConfig = antdConfig;
    // No more calling setState in a class. We'll just store it.
    // If you want dynamic theme updates, you'd handle that differently.
  }

  public getFontSize(size?: string): string {
    const sizeMap: Record<string, any> = {
      xs: 'fontSizeXS',
      s: 'fontSizeSM',
      m: 'fontSize',
      l: 'fontSizeLG',
      xl: 'fontSizeXL',
      xxl: 'fontSizeXXL',
    };
    return this.theme[sizeMap[size || 'm']] || this.theme.fontSize;
  }

  private isThemeDark(): boolean {
    return tinycolor(this.theme.colorBgContainer).isDark();
  }

  setThemeFromSeed(seed: Partial<SupersetTheme>, isDark: boolean): void {
    const augmentedSeed = Theme.augmentSeedWithDefaults(seed);
    const theme = Theme.getSupersetTheme(augmentedSeed, isDark);
    const antdConfig = Theme.getAntdConfig(augmentedSeed, isDark);
    this.updateTheme(theme, antdConfig);
  }

  setThemeFromAntdConfig(antdConfig: AntdThemeConfig): void {
    this.antdConfig = antdConfig;
    const tokens = Theme.getFilteredAntdTheme(antdConfig);
    const systemColors = Theme.getSystemColors(tokens);
    const isDark = this.isThemeDark();
    this.theme = {
      colors: Theme.getColors(systemColors, isDark),
      ...Theme.defaultTokens,
      ...tokens,
    };
    // no dynamic provider updates from here
  }

  mergeTheme(_partialTheme: Partial<LegacySupersetTheme>): void {
    // If you need a dynamic merge, do it and then call updateTheme,
    // otherwise remove or keep this as a no-op
  }

  getColorVariants(color: string) {
    if (color === 'default' || color === 'grayscale') {
      const isDark = this.isThemeDark();
      const flipBrightness = (baseColor: string): string => {
        if (!isDark) return baseColor;
        const { r, g, b } = tinycolor(baseColor).toRgb();
        return tinycolor({ r: 255 - r, g: 255 - g, b: 255 - b }).toHexString();
      };
      return {
        active: flipBrightness('#222'),
        textActive: flipBrightness('#444'),
        text: flipBrightness('#555'),
        textHover: flipBrightness('#666'),
        hover: flipBrightness('#888'),
        borderHover: flipBrightness('#AAA'),
        border: flipBrightness('#CCC'),
        bgHover: flipBrightness('#DDD'),
        bg: flipBrightness('#F4F4F4'),
      };
    }
    const firstLetterCapped = color.charAt(0).toUpperCase() + color.slice(1);
    return {
      active: this.theme[`color${firstLetterCapped}Active`],
      textActive: this.theme[`color${firstLetterCapped}TextActive`],
      text: this.theme[`color${firstLetterCapped}Text`],
      textHover: this.theme[`color${firstLetterCapped}TextHover`],
      hover: this.theme[`color${firstLetterCapped}Hover`],
      borderHover: this.theme[`color${firstLetterCapped}BorderHover`],
      border: this.theme[`color${firstLetterCapped}Border`],
      bgHover: this.theme[`color${firstLetterCapped}BgHover`],
      bg: this.theme[`color${firstLetterCapped}Bg`],
    };
  }

  // Provide a simple, non-Hook-based provider for your app.
  SupersetThemeProvider({ children }: { children: React.ReactNode }) {
    if (!this.theme || !this.antdConfig) {
      throw new Error('Theme is not initialized.');
    }
    return (
      <EmotionCacheProvider value={createCache({ key: 'superset' })}>
        <EmotionThemeProvider theme={this.theme}>
          <ConfigProvider theme={this.antdConfig} prefixCls="antd5">
            {children}
          </ConfigProvider>
        </EmotionThemeProvider>
      </EmotionCacheProvider>
    );
  }
}

/* eslint-enable theme-colors/no-literal-colors */
