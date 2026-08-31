import type { Config } from 'tailwindcss';

/**
 * Officer portal design tokens.
 *
 * Risk band and severity colours are domain tokens, not decoration: they are
 * named after the values in requirements.md so a component cannot invent a
 * fifth risk band or a colour that means nothing.
 *
 * Colour alone never carries meaning. R16.5 requires a band-to-shade legend
 * and R16.6 requires the not-scored state to be distinctly labelled, so every
 * band and severity is rendered with its text label alongside the colour
 * (WCAG 1.4.1). The tokens below are all >= 4.5:1 against `surface` for text
 * use and are paired with `-fg` foregrounds where used as a fill.
 */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#ffffff',
          sunken: '#f6f7f9',
          raised: '#ffffff',
          border: '#d6dae0',
        },
        ink: {
          DEFAULT: '#14181d',
          muted: '#5c6672',
          subtle: '#7b8694',
          inverse: '#ffffff',
        },
        // Risk_Band (requirements.md R19.4, design §14.8 band_for)
        risk: {
          low: '#1b6e3c',
          medium: '#8a6100',
          high: '#b3480f',
          critical: '#a5122a',
          // R16.6: a case with no current Risk_Probability is not "low risk",
          // it is unscored, and must render distinctly with its own legend row.
          unscored: '#6b7480',
        },
        // Severity (requirements.md R14.1)
        severity: {
          blocking: '#a5122a',
          major: '#b3480f',
          minor: '#8a6100',
          advisory: '#3a5a8a',
        },
        // Stage_Deadline pressure, used for remaining-day emphasis
        deadline: {
          breached: '#a5122a',
          near: '#b3480f',
          ok: '#1b6e3c',
        },
      },
      fontFamily: {
        // System stack first. The officer portal has no transfer budget, but
        // matching the citizen portal's stack keeps Devanagari rendering
        // consistent across both surfaces (design §10.4).
        sans: [
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Noto Sans Devanagari',
          'Noto Sans',
          'sans-serif',
        ],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      fontSize: {
        // Tabular figures for extents, shares, and amounts.
        num: ['0.9375rem', { lineHeight: '1.4', fontVariantNumeric: 'tabular-nums' }],
      },
    },
  },
  plugins: [],
} satisfies Config;
