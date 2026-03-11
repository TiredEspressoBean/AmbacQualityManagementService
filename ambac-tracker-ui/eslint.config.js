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
      // Catch forgotten console.log before production
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      // Prevent empty catch blocks (swallowing errors silently)
      'no-empty': ['error', { allowEmptyCatch: false }],
      // Require explanation when bypassing TypeScript
      '@typescript-eslint/ban-ts-comment': ['warn', {
        'ts-ignore': 'allow-with-description',
        'ts-expect-error': 'allow-with-description',
        minimumDescriptionLength: 10,
      }],
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
        // =============================================================================
        // List Hook Query Parameter Rules
        // =============================================================================
        // List hooks handle { queries: ... } wrapping internally. Callers pass params directly.
        //
        // LIST HOOKS (3-arg: queries, config, options):
        //   useRetrieveParts, useRetrieveOrders, useRetrieveUsers, useListCapas, etc.
        //
        // EXCLUDED (single-item or special hooks with 2-arg signature):
        //   useRetrievePart, useRetrieveWorkOrder, useRetrieveProcessWithSteps, etc.
        //
        // CORRECT:   useRetrieveParts({ search, limit, offset })
        // WRONG:     useRetrieveParts({ queries: { search, limit } })
        // =============================================================================
        {
          selector: 'CallExpression[callee.name=/^use(Retrieve(Parts|Orders|Users|Companies|Customers|Cores|Documents|Steps|Processes|Equipments|Groups|Errors|Types)$|List|QualityReports|FpiRecords|MeasurementDefinitions)/] > ObjectExpression:first-child > Property[key.name="queries"]',
          message: 'List hooks handle { queries } wrapping internally. Pass query params directly: useRetrieveFoo({ search, limit }) not useRetrieveFoo({ queries: { search, limit } }).',
        },
        // =============================================================================
        // List Hook Argument Order Rules
        // =============================================================================
        // List hooks have signature: (queries?, config?, options?)
        // - queries: API query params (search, limit, offset, etc.)
        // - config: Zodios config (headers, etc.) - pass undefined if not needed
        // - options: React Query options (enabled, staleTime, etc.)
        //
        // CORRECT:   useRetrieveParts({ search }, undefined, { enabled: false })
        // WRONG:     useRetrieveParts({ search }, { enabled: false })
        // =============================================================================
        {
          selector: 'CallExpression[callee.name=/^use(Retrieve(Parts|Orders|Users|Companies|Customers|Cores|Documents|Steps|Processes|Equipments|Groups)$|List|QualityReports|FpiRecords|MeasurementDefinitions)/] > ObjectExpression:nth-child(2) > Property[key.name="enabled"]',
          message: 'List hooks: React Query options (enabled) go in 3rd arg, not 2nd. Use: hook(queries, undefined, { enabled }) not hook(queries, { enabled }).',
        },
        {
          selector: 'CallExpression[callee.name=/^use(Retrieve(Parts|Orders|Users|Companies|Customers|Cores|Documents|Steps|Processes|Equipments|Groups)$|List|QualityReports|FpiRecords|MeasurementDefinitions)/] > ObjectExpression:nth-child(2) > Property[key.name="staleTime"]',
          message: 'List hooks: React Query options (staleTime) go in 3rd arg, not 2nd. Use: hook(queries, undefined, { staleTime }) not hook(queries, { staleTime }).',
        },
        {
          selector: 'CallExpression[callee.name=/^use(Retrieve(Parts|Orders|Users|Companies|Customers|Cores|Documents|Steps|Processes|Equipments|Groups)$|List|QualityReports|FpiRecords|MeasurementDefinitions)/] > ObjectExpression:nth-child(2) > Property[key.name="refetchInterval"]',
          message: 'List hooks: React Query options (refetchInterval) go in 3rd arg, not 2nd. Use: hook(queries, undefined, { refetchInterval }) not hook(queries, { refetchInterval }).',
        },
        // =============================================================================
        // Code Quality & Security Rules
        // =============================================================================
        // Prevent direct fetch() - use typed API client instead
        {
          selector: 'CallExpression[callee.name="fetch"]',
          message: 'Use the typed API client (api.api_*) instead of raw fetch() for API calls.',
        },
        // Catch hardcoded localhost/API URLs
        {
          selector: 'Literal[value=/https?:\\/\\/(localhost|127\\.0\\.0\\.1)/]',
          message: 'Avoid hardcoded localhost URLs. Use environment variables instead.',
        },
      ],
    },
  },
)
