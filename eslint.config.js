import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import globals from 'globals'
import prettier from 'eslint-config-prettier'
export default tseslint.config(
  {
    ignores: [
      'node_modules/**',
      'backend/.venv/**',
      'coverage/**',
      'dist/**',
      '.husky/_/**',
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  { languageOptions: { globals: { ...globals.node, ...globals.browser } } },
  prettier,
)
