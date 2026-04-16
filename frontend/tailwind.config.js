/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'media',
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}'
  ],
  theme: {
    extend: {
      colors: {
        // Primary brand colors (HubSpot Atomic)
        primary: {
          50: 'var(--color-primary-50)',
          100: 'var(--color-primary-100)',
          200: 'var(--color-primary-200)',
          300: 'var(--color-primary-300)',
          400: 'var(--color-primary-400)',
          500: 'var(--color-primary-500)',
          600: 'var(--color-primary-600)',
          700: 'var(--color-primary-700)',
          800: 'var(--color-primary-800)',
          900: 'var(--color-primary-900)',
        },
        // Background colors
        page: 'var(--color-bg-main)',
        'bg-main': 'var(--color-bg-main)',
        'bg-card': 'var(--color-bg-card)',
        'bg-sidebar': 'var(--color-bg-sidebar)',
        'bg-hover': 'var(--color-bg-hover)',
        'bg-subtle': 'var(--color-bg-subtle)',
        'bg-soft': 'var(--color-bg-soft)',
        // Text colors
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-muted': 'var(--color-text-muted)',
        'text-inverse': 'var(--color-text-inverse)',
        // Border colors
        'border-light': 'var(--color-border-light)',
        'border-medium': 'var(--color-border-medium)',
        'border-dark': 'var(--color-border-dark)',
        // Status colors
        success: {
          100: 'var(--color-success-100)',
          500: 'var(--color-success-500)',
          600: 'var(--color-success-600)',
        },
        warning: {
          100: 'var(--color-warning-100)',
          500: 'var(--color-warning-500)',
          600: 'var(--color-warning-600)',
        },
        error: {
          100: 'var(--color-error-100)',
          500: 'var(--color-error-500)',
          600: 'var(--color-error-600)',
        },
        danger: {
          100: 'var(--color-error-100)',
          500: 'var(--color-error-500)',
          600: 'var(--color-error-600)',
        },
        info: {
          100: 'var(--color-info-100)',
          500: 'var(--color-info-500)',
          600: 'var(--color-info-600)',
        },
        premium: {
          100: 'var(--color-premium-100)',
          500: 'var(--color-premium-500)',
          600: 'var(--color-premium-600)',
        },
        // Accent colors
        accent: {
          coral: 'var(--color-accent-coral-500)',
          amber: 'var(--color-accent-amber-500)',
          emerald: 'var(--color-accent-emerald-500)',
          sky: 'var(--color-accent-sky-500)',
        },
        // Overlay colors
        overlay: {
          soft: 'var(--color-overlay-soft)',
          strong: 'var(--color-overlay-strong)',
        },
        // Legacy navy colors (mapped to primary for compatibility)
        navy: {
          50: 'var(--color-bg-soft)',
          100: 'var(--color-bg-subtle)',
          300: 'var(--color-text-muted)',
          800: 'var(--color-bg-hover)',
          900: 'var(--color-bg-card)',
        },
        // Legacy royal colors (mapped to primary for compatibility)
        royal: {
          400: 'var(--color-primary-400)',
          600: 'var(--color-primary-600)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        heading: ['"Plus Jakarta Sans"', 'sans-serif'],
      },
      boxShadow: {
        'sm': 'var(--shadow-sm)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
        'card': 'var(--shadow-card)',
        'focus': 'var(--shadow-focus)',
      },
      borderRadius: {
        'none': '0',
        'xs': 'var(--radius-xs)',
        'sm': 'var(--radius-sm)',
        'DEFAULT': 'var(--radius-md)',
        'md': 'var(--radius-md)',
        'lg': 'var(--radius-lg)',
        'xl': 'var(--radius-xl)',
        '2xl': '0.875rem',
        '3xl': '1rem',
        'full': '9999px',
      },
      spacing: {
        '1': 'var(--space-1)',
        '2': 'var(--space-2)',
        '3': 'var(--space-3)',
        '4': 'var(--space-4)',
        '5': 'var(--space-5)',
        '6': 'var(--space-6)',
      },
    },
  },
  plugins: [],
}
