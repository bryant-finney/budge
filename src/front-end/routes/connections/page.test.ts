import { render, screen } from '@testing-library/svelte';
import { expect, test } from 'vitest';

import Page from './+page.svelte';

test('the #/connections view renders exactly one level-1 heading', () => {
  render(Page);

  expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
});
