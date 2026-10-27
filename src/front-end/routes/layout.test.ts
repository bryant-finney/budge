import { render, screen, within } from '@testing-library/svelte';
import { createRawSnippet } from 'svelte';
import { describe, expect, test } from 'vitest';

import Layout from './+layout.svelte';

const children = createRawSnippet(() => ({ render: () => '<p>view content</p>' }));

describe('the app layout', () => {
  test('renders banner, navigation, and main landmarks', () => {
    render(Layout, { children });

    expect(screen.getByRole('banner')).toBeInTheDocument();
    expect(screen.getByRole('navigation')).toBeInTheDocument();
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  test('links every navigation item to a hash route', () => {
    render(Layout, { children });

    const links = within(screen.getByRole('navigation')).getAllByRole('link');

    expect(links).not.toHaveLength(0);
    for (const link of links) {
      expect(link).toHaveAttribute('href', expect.stringMatching(/^#\//));
    }
  });

  test('renders the children snippet inside main', () => {
    render(Layout, { children });

    expect(within(screen.getByRole('main')).getByText('view content')).toBeInTheDocument();
  });
});
