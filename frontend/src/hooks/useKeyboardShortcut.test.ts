import { describe, it, expect, vi } from 'vitest';
import { renderHook, fireEvent } from '@testing-library/react';
import { useKeyboardShortcut } from './useKeyboardShortcut';

describe('useKeyboardShortcut', () => {
    it('fires only on the exact modifier combo', () => {
        const cb = vi.fn();
        renderHook(() => useKeyboardShortcut({ key: 'k', ctrlKey: true }, cb));

        fireEvent.keyDown(window, { key: 'k' });
        fireEvent.keyDown(window, { key: 'k', metaKey: true });
        fireEvent.keyDown(window, { key: 'k', ctrlKey: true, shiftKey: true });
        expect(cb).not.toHaveBeenCalled();

        fireEvent.keyDown(window, { key: 'K', ctrlKey: true });
        expect(cb).toHaveBeenCalledTimes(1);
    });

    it('removes the listener on unmount', () => {
        const cb = vi.fn();
        const { unmount } = renderHook(() => useKeyboardShortcut({ key: 'Escape' }, cb));
        unmount();
        fireEvent.keyDown(window, { key: 'Escape' });
        expect(cb).not.toHaveBeenCalled();
    });
});
