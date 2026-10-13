import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ErrorBoundary from './ErrorBoundary';

let shouldThrow = true;
function Bomb() {
    if (shouldThrow) throw new Error('boom');
    return <p>recovered</p>;
}

describe('ErrorBoundary', () => {
    it('shows the fallback instead of blanking the app, and can recover', async () => {
        vi.spyOn(console, 'error').mockImplementation(() => {});
        render(
            <>
                <h1>App shell</h1>
                <ErrorBoundary name="the inbox">
                    <Bomb />
                </ErrorBoundary>
            </>,
        );

        expect(screen.getByRole('alert').textContent).toContain('Something went wrong in the inbox.');
        expect(screen.getByRole('heading', { name: 'App shell' })).toBeTruthy();

        shouldThrow = false;
        await userEvent.click(screen.getByRole('button', { name: 'Try again' }));
        expect(screen.getByText('recovered')).toBeTruthy();
    });
});
