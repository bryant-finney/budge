// Vitest setup: register jest-dom's DOM matchers (toBeInTheDocument, toHaveAttribute, ...).
//
// ref: https://github.com/testing-library/jest-dom#with-vitest
//
// pattern: this file is in tsconfig.json's program (`*.ts`), so its import also types the matchers
import '@testing-library/jest-dom/vitest';
