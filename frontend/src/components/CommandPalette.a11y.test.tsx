import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { CommandPalette } from './CommandPalette';

describe('CommandPalette accessibility', () => {
    it('has no axe violations when open', async () => {
        const { container } = render(<CommandPalette onAction={vi.fn()} />);
        fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
        await screen.findByPlaceholderText(/type a command/i);
        const results = await axe(container);
        console.info(`axe violations: ${results.violations.length}`, results.violations.map((v) => v.id));
        expect(results.violations).toHaveLength(0);
    });
});
