import js from '@eslint/js';
import prettier from 'eslint-config-prettier';
import globals from 'globals';

export default [
  {
    ignores: ['node_modules/', 'coverage/', 'test-results/', 'playwright-report/'],
  },
  js.configs.recommended,
  {
    files: ['www/**/*.js'],
    languageOptions: {
      sourceType: 'module',
      globals: { ...globals.browser, maplibregl: 'readonly', pmtiles: 'readonly' },
    },
  },
  {
    files: ['www/load_sport_markings.js'],
    languageOptions: { sourceType: 'script' },
    rules: { 'no-unused-vars': ['error', { vars: 'local' }] },
  },
  {
    files: ['tests/**/*.{js,mjs}', '*.config.{js,mjs}'],
    languageOptions: {
      sourceType: 'module',
      globals: { ...globals.node, ...globals.browser, ...globals.vitest },
    },
  },
  prettier,
];
