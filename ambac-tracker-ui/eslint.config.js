import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import pluginQuery from '@tanstack/eslint-plugin-query'
import pluginRouter from '@tanstack/eslint-plugin-router'

export default tseslint.config(
  { ignores: ['dist', 'src/lib/api/generated.ts'] },
  ...pluginQuery.configs['flat/recommended'],
  ...pluginRouter.configs['flat/recommended'],
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': 'off', // Disabled - HMR convenience only, too noisy
      // TypeScript flexibility - allow 'any' during rapid development
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      // Prevent empty string value on SelectItem/CommandItem (causes runtime errors or filtering issues)
      'no-restricted-syntax': [
        'error',
        {
          selector: 'JSXElement[openingElement.name.name="SelectItem"] JSXAttribute[name.name="value"][value.value=""]',
          message: 'SelectItem value cannot be empty string. Use a sentinel like "__none__" instead.',
        },
        {
          selector: 'JSXElement[openingElement.name.name="CommandItem"] JSXAttribute[name.name="value"][value.value=""]',
          message: 'CommandItem value cannot be empty string (causes filtering issues). Use a sentinel like "__none__" instead.',
        },
        // =============================================================================
        // Zodios API Parameter Rules
        // =============================================================================
        // Zodios requires path parameters (like :id) to be wrapped in { params: { ... } }
        // and query parameters (like ?search=) to be wrapped in { queries: { ... } }
        //
        // CORRECT:   api.api_Foo_retrieve({ params: { id } })
        // CORRECT:   api.api_Foo_list({ queries: { search, limit } })
        // WRONG:     api.api_Foo_retrieve({ id })  <- causes literal ":id" in URL!
        //
        // These rules catch the most common mistake: passing `id` at the top level
        // instead of wrapping it in `params` for endpoints that use path parameters.
        // =============================================================================
        {
          selector: 'CallExpression[callee.property.name=/^api_.*_(retrieve|destroy|update|partial_update)$/] > ObjectExpression:first-child > Property[key.name="id"]',
          message: 'Zodios path params require wrapper: use { params: { id } } not { id }. Passing id directly causes literal ":id" in the URL.',
        },
        // Also catch other common path parameter names
        {
          selector: 'CallExpression[callee.property.name=/^api_.*_(retrieve|destroy|update|partial_update)$/] > ObjectExpression:first-child > Property[key.name="pk"]',
          message: 'Zodios path params require wrapper: use { params: { pk } } not { pk }. Passing pk directly causes literal ":pk" in the URL.',
        },
        // Catch custom action endpoints that typically need path params (e.g., api_Foo_some_action_create)
        {
          selector: 'CallExpression[callee.property.name=/^api_.*_create$/][callee.property.name!=/^api_[A-Z][a-z]+_create$/] > ObjectExpression:first-child > Property[key.name="id"]',
          message: 'Custom action endpoints with :id in path require wrapper: use { params: { id }, ... } not { id, ... }.',
        },
      ],
    },
  },
)
