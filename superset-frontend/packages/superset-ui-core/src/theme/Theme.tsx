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
// eslint-disable-next-line no-restricted-syntax
import React from 'react';
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

type AntdTokens = ReturnType<typeof antdThemeImport.getDesignToken>;
/* eslint-disable theme-colors/no-literal-colors */

interface SystemColors {
  colorPrimary: string;
  colorError: string;
  colorWarning: string;
  colorSuccess: string;
  colorInfo: string;
}
interface ColorVariants {
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

interface ColorVariations {
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

interface ThemeColors {
  primary: ColorVariations;
  error: ColorVariations;
  warning: ColorVariations;
  success: ColorVariations;
  info: ColorVariations;
  grayscale: ColorVariations;
}

// Tokens to be removed
interface LegacySupersetTheme {
  // Old colors structure with light/dark semantics still heavily referenced in code base
  // TODO: replace/realign with antd-type tokens
  colors: ThemeColors;
  transitionTiming: number;
}

interface SupersetSpecificTokens {
  // Brand-related
  brandIconMaxWidth: number;

  // Font-related
  fontSizeXS: string;
  fontSizeXXL: string;
  fontWeightNormal: string;
  fontWeightLight: string;
  fontWeightMedium: string;
}

const allowedAntdTokens = [
  'borderRadius',
  'borderRadiusLG',
  'borderRadiusOuter',
  'borderRadiusSM',
  'borderRadiusXS',
  'boxShadow',
  'boxShadowCard',
  'boxShadowDrawerDown',
  'boxShadowDrawerLeft',
  'boxShadowDrawerRight',
  'boxShadowDrawerUp',
  'boxShadowPopoverArrow',
  'boxShadowSecondary',
  'boxShadowTabsOverflowBottom',
  'boxShadowTabsOverflowLeft',
  'boxShadowTabsOverflowRight',
  'boxShadowTabsOverflowTop',
  'boxShadowTertiary',
  'colorError',
  'colorErrorActive',
  'colorErrorBg',
  'colorErrorBgActive',
  'colorErrorBgHover',
  'colorErrorBorder',
  'colorErrorBorderHover',
  'colorErrorHover',
  'colorErrorOutline',
  'colorErrorText',
  'colorErrorTextActive',
  'colorErrorTextHover',
  'colorPrimary',
  'colorPrimaryActive',
  'colorPrimaryBg',
  'colorPrimaryBgHover',
  'colorPrimaryBorder',
  'colorPrimaryBorderHover',
  'colorPrimaryHover',
  'colorPrimaryText',
  'colorPrimaryTextActive',
  'colorPrimaryTextHover',
  'colorSuccess',
  'colorSuccessActive',
  'colorSuccessBg',
  'colorSuccessBgHover',
  'colorSuccessBorder',
  'colorSuccessBorderHover',
  'colorSuccessHover',
  'colorSuccessText',
  'colorSuccessTextActive',
  'colorSuccessTextHover',
  'colorBgBase',
  'colorBgBlur',
  'colorBgContainer',
  'colorBgContainerDisabled',
  'colorBgElevated',
  'colorBgLayout',
  'colorBgMask',
  'colorBgSpotlight',
  'colorBgTextActive',
  'colorBgTextHover',
  'colorBorder',
  'colorBorderBg',
  'colorBorderSecondary',
  'colorFill',
  'colorFillAlter',
  'colorFillContent',
  'colorFillContentHover',
  'colorFillQuaternary',
  'colorFillSecondary',
  'colorFillTertiary',
  'colorHighlight',
  'colorIcon',
  'colorIconHover',
  'colorInfo',
  'colorInfoActive',
  'colorInfoBg',
  'colorInfoBgHover',
  'colorInfoBorder',
  'colorInfoBorderHover',
  'colorInfoHover',
  'colorInfoText',
  'colorInfoTextActive',
  'colorInfoTextHover',
  'colorLink',
  'colorLinkActive',
  'colorLinkHover',
  'colorSplit',
  'colorText',
  'colorTextBase',
  'colorTextDescription',
  'colorTextDisabled',
  'colorTextHeading',
  'colorTextLabel',
  'colorTextLightSolid',
  'colorTextPlaceholder',
  'colorTextQuaternary',
  'colorTextSecondary',
  'colorTextTertiary',
  'colorWarning',
  'colorWarningActive',
  'colorWarningBg',
  'colorWarningBgHover',
  'colorWarningBorder',
  'colorWarningBorderHover',
  'colorWarningHover',
  'colorWarningOutline',
  'colorWarningText',
  'colorWarningTextActive',
  'colorWarningTextHover',
  'colorWhite',
  'controlHeight',
  'controlHeightLG',
  'controlHeightSM',
  'controlHeightXS',
  'controlInteractiveSize',
  'controlItemBgActive',
  'controlItemBgActiveDisabled',
  'controlItemBgActiveHover',
  'controlItemBgHover',
  'controlOutline',
  'controlOutlineWidth',
  'controlPaddingHorizontal',
  'controlPaddingHorizontalSM',
  'controlTmpOutline',
  'fontFamily',
  'fontFamilyCode',
  'fontHeight',
  'fontHeightLG',
  'fontHeightSM',
  'fontSize',
  'fontSizeHeading1',
  'fontSizeHeading2',
  'fontSizeHeading3',
  'fontSizeHeading4',
  'fontSizeHeading5',
  'fontSizeIcon',
  'fontSizeLG',
  'fontSizeSM',
  'fontSizeXL',
  'fontWeightStrong',
  'lineHeight',
  'lineHeightHeading1',
  'lineHeightHeading2',
  'lineHeightHeading3',
  'lineHeightHeading4',
  'lineHeightHeading5',
  'lineHeightLG',
  'lineHeightSM',
  'lineType',
  'lineWidth',
  'lineWidthBold',
  'lineWidthFocus',
  'linkDecoration',
  'linkFocusDecoration',
  'linkHoverDecoration',
  'margin',
  'marginLG',
  'marginMD',
  'marginSM',
  'marginXL',
  'marginXS',
  'marginXXL',
  'marginXXS',
  'motion',
  'motionBase',
  'motionDurationFast',
  'motionDurationMid',
  'motionDurationSlow',
  'motionEaseInBack',
  'motionEaseInOut',
  'motionEaseInOutCirc',
  'motionEaseInQuint',
  'motionEaseOut',
  'motionEaseOutBack',
  'motionEaseOutCirc',
  'motionEaseOutQuint',
  'motionUnit',
  'opacityImage',
  'opacityLoading',
  'padding',
  'paddingContentHorizontal',
  'paddingContentHorizontalLG',
  'paddingContentHorizontalSM',
  'paddingContentVertical',
  'paddingContentVerticalLG',
  'paddingContentVerticalSM',
  'paddingLG',
  'paddingMD',
  'paddingSM',
  'paddingXL',
  'paddingXS',
  'paddingXXS',
  'screenLG',
  'screenLGMax',
  'screenLGMin',
  'screenMD',
  'screenMDMax',
  'screenMDMin',
  'screenSM',
  'screenSMMax',
  'screenSMMin',
  'screenXL',
  'screenXLMax',
  'screenXLMin',
  'screenXS',
  'screenXSMax',
  'screenXSMin',
  'screenXXL',
  'screenXXLMin',
  'size',
  'sizeLG',
  'sizeMD',
  'sizeMS',
  'sizePopupArrow',
  'sizeSM',
  'sizeStep',
  'sizeUnit',
  'sizeXL',
  'sizeXS',
  'sizeXXL',
  'sizeXXS',
  'wireframe',
  'zIndexBase',
  'zIndexPopupBase',
] as const;

// Playing some tricks to preserve token types from antd while creating a subset
// 1. create a type from the array
type AllowedAntdTokenKeys = Extract<
  (typeof allowedAntdTokens)[number],
  keyof AntdTokens
>;
// 2. derive the type dynamically
export type SharedAntdTokens = Pick<AntdTokens, AllowedAntdTokenKeys>;

export type SupersetTheme = LegacySupersetTheme &
  SharedAntdTokens &
  SupersetSpecificTokens;

export class Theme {
  theme: SupersetTheme;

  private static readonly defaultTokens = {
    // Default colors
    colorPrimary: '#20a7c9',
    colorError: '#e04355',
    colorWarning: '#fcc700',
    colorSuccess: '#5ac189',
    colorInfo: '#66bcfe',

    // Forcing some default tokens
    fontFamily: `'Inter', Helvetica, Arial`,
    fontFamilyCode: `'Fira Code', 'Courier New', monospace`,

    // Extra tokens
    transitionTiming: 0.3,
    brandIconMaxWidth: 37,
    fontSizeXS: '8',
    fontSizeXXL: '28',
    fontWeightNormal: '400',
    fontWeightLight: '300',
    fontWeightMedium: '500',
  };

  private antdConfig: AntdThemeConfig;

  private constructor() {
    this.updateTheme = this.updateTheme.bind(this);
    this.SupersetThemeProvider = this.SupersetThemeProvider.bind(this);
  }

  static fromSeed(seed?: Partial<SupersetTheme>, isDark = false): Theme {
    const theme = new Theme();
    theme.setThemeFromSeed(seed || {}, isDark);
    return theme;
  }

  static fromAntdConfig(antdConfig: AntdThemeConfig): Theme {
    const theme = new Theme();
    theme.setThemeFromAntdConfig(antdConfig);
    return theme;
  }

  private static genColorVariations(
    color: string,
    isDark: boolean,
  ): ColorVariations {
    const bg = isDark ? '#FFF' : '#000';
    const fg = isDark ? '#000' : '#FFF';
    const adjustColor = (color: string, perc: number, target: string): string =>
      tinycolor.mix(color, target, perc).toHexString();
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
  ): ThemeColors {
    const sc = systemColors;
    return {
      primary: Theme.genColorVariations(sc.colorPrimary, isDark),
      error: Theme.genColorVariations(sc.colorError, isDark),
      warning: Theme.genColorVariations(sc.colorWarning, isDark),
      success: Theme.genColorVariations(sc.colorSuccess, isDark),
      info: Theme.genColorVariations(sc.colorInfo, isDark),
      grayscale: Theme.genColorVariations('#666', isDark),
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

    const theme: SupersetTheme = {
      colors: Theme.getColors(systemColors, isDark),
      ...Theme.defaultTokens,
      // Bring allowed tokens from antd
      ...antdTokens,
    };
    return theme;
  }

  private static getFilteredAntdTheme(
    antdConfig: AntdThemeConfig,
  ): SharedAntdTokens {
    const theme = Theme.getAntdTokens(antdConfig);

    return Object.fromEntries(
      allowedAntdTokens.map(key => [key, theme[key]]), // Map keys to their values from the theme
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

  mergeTheme(partialTheme: Partial<LegacySupersetTheme>): void {
    // const mergedTheme = merge({}, this.theme, partialTheme);
    // const isDark = tinycolor(mergedTheme.colorBgBase).isDark();
    // const antdConfig = Theme.getAntdConfig(systemColors, isDark);
    // this.updateTheme(mergedTheme, antdConfig, isDark);
  }

  private updateTheme(theme: SupersetTheme, antdConfig: AntdThemeConfig): void {
    this.theme = theme;
    this.antdConfig = antdConfig;
    this.updateProviders(
      this.theme,
      this.antdConfig,
      createCache({ key: 'superset' }),
    );
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

  setThemeFromSeed(seed: Partial<SupersetTheme>, isDark: boolean): void {
    const augmentedSeed = Theme.augmentSeedWithDefaults(seed);
    const theme = Theme.getSupersetTheme(augmentedSeed, isDark);
    const antdConfig = Theme.getAntdConfig(augmentedSeed, isDark);
    this.updateTheme(theme, antdConfig);
  }

  getColorVariants(color: string): ColorVariants {
    const firstLetterCapped = color.charAt(0).toUpperCase() + color.slice(1);
    if (color === 'default' || color === 'grayscale') {
      const isDark = this.isThemeDark();

      const flipBrightness = (baseColor: string): string => {
        if (!isDark) return baseColor;
        const { r, g, b } = tinycolor(baseColor).toRgb();
        const invertedColor = tinycolor({ r: 255 - r, g: 255 - g, b: 255 - b });
        return invertedColor.toHexString();
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

  private static getAntdTokens(antdConfig: AntdThemeConfig): AntdTokens {
    return antdThemeImport.getDesignToken(antdConfig);
  }

  private isThemeDark(): boolean {
    return tinycolor(this.theme.colorBgContainer).isDark();
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
    this.updateProviders(
      this.theme,
      this.antdConfig,
      createCache({ key: 'superset' }),
    );
  }

  private updateProviders(
    theme: SupersetTheme,
    antdConfig: AntdThemeConfig,
    emotionCache: any,
  ): void {}

  SupersetThemeProvider({ children }: { children: React.ReactNode }) {
    if (!this.theme || !this.antdConfig) {
      throw new Error('Theme is not initialized.');
    }

    // eslint-disable-next-line react-hooks/rules-of-hooks
    const [themeState, setThemeState] = React.useState({
      theme: this.theme,
      antdConfig: this.antdConfig,
      emotionCache: createCache({ key: 'superset' }),
    });

    this.updateProviders = (theme, antdConfig, emotionCache) => {
      setThemeState({ theme, antdConfig, emotionCache });
    };
    return (
      <EmotionCacheProvider value={themeState.emotionCache}>
        <EmotionThemeProvider theme={themeState.theme}>
          <ConfigProvider theme={themeState.antdConfig} prefixCls="antd5">
            {children}
          </ConfigProvider>
        </EmotionThemeProvider>
      </EmotionCacheProvider>
    );
  }
}
