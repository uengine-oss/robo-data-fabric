/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'minds-primary': '#0A0E27',
        'minds-secondary': '#1A1F3A',
        'minds-accent': '#00D4AA',
        'minds-accent-hover': '#00B894',
        'minds-text': '#E8E8E8',
        'minds-muted': '#6B7280',
        'minds-border': '#2D3250',
        'minds-surface': '#151929',
      },
      fontFamily: {
        'display': ['Space Grotesk', 'system-ui', 'sans-serif'],
        'body': ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
