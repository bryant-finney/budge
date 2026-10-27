// ESLint flat config: typed typescript-eslint rules for .ts and .svelte, plus eslint-plugin-svelte.
//
// ref: https://sveltejs.github.io/eslint-plugin-svelte/user-guide/
// ref: https://typescript-eslint.io/getting-started/typed-linting/
//
// pattern: formatting is prettier's job alone, so eslint-config-prettier comes last
import js from '@eslint/js';
import prettier from 'eslint-config-prettier/flat';
import svelte from 'eslint-plugin-svelte';
import { defineConfig } from 'eslint/config';
import globals from 'globals';
import ts from 'typescript-eslint';

export default defineConfig(
  { ignores: ['build/', '.svelte-kit/', 'node_modules/', 'coverage/'] },
  js.configs.recommended,
  ts.configs.strictTypeChecked,
  ts.configs.stylisticTypeChecked,
  svelte.configs.recommended,
  svelte.configs.prettier,
  {
    languageOptions: {
      globals: globals.browser,
      parserOptions: {
        projectService: true,
        // keep identical for .ts and .svelte so the project service isn't reloaded
        extraFileExtensions: ['.svelte'],
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      // AGENT.md: no `any`, no unexplained non-null assertions, no bare ts-comments.
      // strictTypeChecked enables these; restating them pins the contract.
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-non-null-assertion': 'error',
      '@typescript-eslint/ban-ts-comment': [
        'error',
        { 'ts-expect-error': 'allow-with-description', minimumDescriptionLength: 10 },
      ],
      '@typescript-eslint/consistent-type-imports': 'error',
    },
  },
  {
    files: ['**/*.svelte', '**/*.svelte.ts'],
    languageOptions: {
      parserOptions: { parser: ts.parser },
    },
  },
  {
    // config files sit outside tsconfig.json's program and run under Node
    files: ['*.js'],
    extends: [ts.configs.disableTypeChecked],
    languageOptions: { globals: globals.node },
  },
  prettier,
);
