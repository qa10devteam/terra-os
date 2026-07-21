import type { Config } from 'tailwindcss';

/**
 * YU-NA | BudOS — Tailwind v4 compat config
 * Brand Bible: PRECYZJA · ZWIAD · PRZEWAGA
 * Archetyp: Sage 60% + Hero 40%
 *
 * Token hierarchy:
 *   @theme in globals.css  → ink-* / em / signal vars (PRIMARY SOURCE)
 *   extend here            → fontFamily, shadows, animations
 */
const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        display: ['var(--font-space)', 'Space Grotesk', 'sans-serif'],
        sans:    ['var(--font-space)', 'Space Grotesk', 'sans-serif'],
        mono:    ['var(--font-jetbrains)', 'JetBrains Mono', 'monospace'],
      },

      colors: {
        // ── Ink backgrounds ────────────────────────────────────────────
        ink: {
          950:  '#07070d',
          900:  '#0d0d16',
          800:  '#13131e',
          700:  '#1a1a28',
          600:  '#222232',
          500:  '#2e2e42',
          line: '#2a2a3e',
          'line-strong': '#3a3a52',
        },
        // ── Emerald accent (BudOS signals only) ────────────────────────
        em: {
          DEFAULT: '#10b981',
          light:   '#34d399',
          bg:      'rgba(16,185,129,0.06)',
          brd:     'rgba(16,185,129,0.22)',
        },
        // ── Signals ────────────────────────────────────────────────────
        go:   '#10b981',
        nogo: '#ef4444',
        warn: '#f59e0b',
        score: '#818cf8',
        gold: '#d4a843',
        // ── Semantic aliases ───────────────────────────────────────────
        'go-bg':    'rgba(16,185,129,0.08)',
        'go-brd':   'rgba(16,185,129,0.25)',
        'nogo-bg':  'rgba(239,68,68,0.08)',
        'nogo-brd': 'rgba(239,68,68,0.22)',
        'warn-bg':  'rgba(245,158,11,0.08)',
        'em-bg':    'rgba(16,185,129,0.06)',
        'em-brd':   'rgba(16,185,129,0.22)',
      },

      // ── Box shadows (ink-tinted) ──────────────────────────────────────
      boxShadow: {
        'sm':   '0 1px 3px rgba(0,0,0,0.5), 0 1px 2px rgba(0,0,0,0.4)',
        'md':   '0 4px 8px rgba(0,0,0,0.6), 0 2px 4px rgba(0,0,0,0.4)',
        'lg':   '0 12px 24px rgba(0,0,0,0.7), 0 4px 8px rgba(0,0,0,0.4)',
        'em':   '0 0 16px rgba(16,185,129,0.12)',
      },

      // ── Border radius ─────────────────────────────────────────────────
      borderRadius: {
        'sm':  '4px',
        'md':  '8px',
        'lg':  '12px',
        'xl':  '16px',
        '2xl': '20px',
      },

      // ── Keyframe animations ───────────────────────────────────────────
      keyframes: {
        shimmer: {
          '0%':   { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%':      { opacity: '0.5' },
        },
        'fade-up': {
          '0%':   { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'score-reveal': {
          '0%':   { opacity: '0', transform: 'translateY(4px) scale(0.96)' },
          '60%':  { opacity: '1', transform: 'translateY(-1px) scale(1.01)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        'go-pop': {
          '0%':   { opacity: '0', transform: 'scale(0.88)' },
          '65%':  { transform: 'scale(1.04)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },
      animation: {
        'shimmer':     'shimmer 1.8s linear infinite',
        'pulse-soft':  'pulse-soft 2s ease-in-out infinite',
        'fade-up':     'fade-up 0.35s ease-out both',
        'fade-in':     'fade-in 0.25s ease-out both',
        'score-reveal':'score-reveal 0.8s cubic-bezier(0.16,1,0.3,1) both',
        'go-pop':      'go-pop 0.5s cubic-bezier(0.16,1,0.3,1) both',
      },

      // ── Transitions ───────────────────────────────────────────────────
      transitionTimingFunction: {
        spring: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
};

export default config;
