import { useEffect } from 'react';

type KeyCombo = {
    key: string;
    ctrlKey?: boolean;
    metaKey?: boolean;
    shiftKey?: boolean;
    altKey?: boolean;
};

export function useKeyboardShortcut(combo: KeyCombo, callback: (e: KeyboardEvent) => void) {
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            const match =
                e.key.toLowerCase() === combo.key.toLowerCase() &&
                !!e.ctrlKey === !!combo.ctrlKey &&
                !!e.metaKey === !!combo.metaKey &&
                !!e.shiftKey === !!combo.shiftKey &&
                !!e.altKey === !!combo.altKey;

            if (match) {
                callback(e);
            }
        };

        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [combo, callback]);
}
