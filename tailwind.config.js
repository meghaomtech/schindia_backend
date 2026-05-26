/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Shichida India palette (warm, Japanese-zen, earthy minimalism)
        charcoal: '#2F2F2B',
        olive: '#5B6653',
        'olive-2': '#6e7b65',
        sage: '#8A9683',
        cream: '#F6F2EA',
        beige: '#E7DDD0',
        sand: '#D6C8B7',
        gold: '#B79C72',
        'gold-soft': '#cdb593',
        brown: '#8C6F4D',

        // Semantic surfaces (light theme)
        bg: {
          DEFAULT: '#F6F2EA', // cream page background
          card: '#FFFFFF', // white cards
          elev: '#FBF8F2', // elevated surface
          tertiary: '#E7DDD0', // beige for secondary panels
        },
        border: {
          DEFAULT: '#E2DBD2',
          strong: '#cabfb1',
        },
        text: {
          DEFAULT: '#2B2B28',
          muted: '#5F5B55',
          dim: '#8B877F',
        },

        // Semantic tokens (mapped to brand)
        info: '#5B6653', // olive — primary action
        'info-soft': '#dde1d8',
        success: '#5B6653',
        warn: '#B79C72',
        danger: '#A8412C', // muted earth red, brand-aligned
        accent: {
          purple: '#7c5fbf',
          'purple-soft': '#ece6f8',
          coral: '#d36450',
          'coral-soft': '#fbe7e2',
          blue: '#3b6db8',
          'blue-soft': '#e3ecf8',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'system-ui',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'sans-serif',
        ],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(47,47,43,0.04), 0 4px 12px rgba(47,47,43,0.05)',
      },
    },
  },
  plugins: [],
};
