import { defineConfig } from 'eslint/config';
import eslintConfigPrettier from 'eslint-config-prettier/flat';
import tseslint from 'typescript-eslint';

export default defineConfig(
  { ignores: ['bin/', 'coverage/', 'node_modules/'] },
  tseslint.configs.strictTypeChecked,
  tseslint.configs.stylisticTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      // Pulumi: an un-awaited promise can drop errors or race the engine.
      '@typescript-eslint/no-floating-promises': 'error',
      // Pulumi: an Output in a template or `+` stringifies to a warning, not its value;
      // use pulumi.interpolate / pulumi.concat / .apply instead. Severity only, so the
      // strictTypeChecked options (every allow* false) are kept.
      '@typescript-eslint/restrict-template-expressions': 'error',
      '@typescript-eslint/restrict-plus-operands': 'error',
      '@typescript-eslint/no-base-to-string': 'error',
      // Stand-in for verbatimModuleSyntax, which tsconfig.json turns off for CommonJS output.
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/no-import-type-side-effects': 'error',
    },
  },
  {
    files: ['**/*.mjs'],
    extends: [tseslint.configs.disableTypeChecked],
  },
  eslintConfigPrettier,
);
