import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CommandPalette } from './CommandPalette';

const openWith = (mod: 'ctrlKey' | 'metaKey') => fireEvent.keyDown(window, { key: 'k', [mod]: true });
const options = () => screen.getAllByRole('option');
const selected = () => options().find((o) => o.getAttribute('aria-selected') === 'true');

describe('CommandPalette', () => {
    it.each(['ctrlKey', 'metaKey'] as const)('opens with %s+K and focuses the search', (mod) => {
        render(<CommandPalette onAction={vi.fn()} />);
        expect(screen.queryByRole('dialog')).toBeNull();
        openWith(mod);
        expect(screen.getByRole('dialog', { name: 'Command palette' })).toBeTruthy();
        expect(document.activeElement).toBe(screen.getByRole('combobox', { name: 'Search commands' }));
    });

    it('filters commands as you type', async () => {
        render(<CommandPalette onAction={vi.fn()} />);
        openWith('ctrlKey');
        expect(options()).toHaveLength(5);
        await userEvent.type(screen.getByRole('combobox'), 'sync');
        expect(options().map((o) => o.textContent)).toEqual([expect.stringContaining('Force Sync Inbox')]);
        await userEvent.clear(screen.getByRole('combobox'));
        await userEvent.type(screen.getByRole('combobox'), 'zzz');
        expect(screen.queryAllByRole('option')).toHaveLength(0);
        expect(screen.getByText('No matching commands.')).toBeTruthy();
    });

    it('moves the selection with ArrowDown/ArrowUp, wrapping at the ends', async () => {
        render(<CommandPalette onAction={vi.fn()} />);
        openWith('ctrlKey');
        expect(selected()?.textContent).toContain('Force Sync Inbox');
        await userEvent.keyboard('{ArrowDown}');
        expect(selected()?.textContent).toContain('Compose New Email');
        await userEvent.keyboard('{ArrowUp}{ArrowUp}');
        expect(selected()?.textContent).toContain('Logout');
        await userEvent.keyboard('{ArrowDown}');
        expect(selected()?.textContent).toContain('Force Sync Inbox');
    });

    it('runs the selected command on Enter and closes', async () => {
        const onAction = vi.fn();
        render(<CommandPalette onAction={onAction} />);
        openWith('metaKey');
        await userEvent.keyboard('{ArrowDown}{Enter}');
        expect(onAction).toHaveBeenCalledWith('compose');
        await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    });

    it('closes on Escape and returns focus to the previously focused element', async () => {
        render(
            <>
                <button>before</button>
                <CommandPalette onAction={vi.fn()} />
            </>,
        );
        const trigger = screen.getByRole('button', { name: 'before' });
        trigger.focus();
        openWith('ctrlKey');
        expect(document.activeElement).not.toBe(trigger);
        await userEvent.keyboard('{Escape}');
        await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
        expect(document.activeElement).toBe(trigger);
    });

    it('traps Tab focus inside the dialog', async () => {
        render(
            <>
                <button>outside</button>
                <CommandPalette onAction={vi.fn()} />
            </>,
        );
        openWith('ctrlKey');
        const input = screen.getByRole('combobox');
        await userEvent.tab();
        expect(document.activeElement).toBe(input);
        await userEvent.tab({ shift: true });
        expect(document.activeElement).toBe(input);
    });
});
