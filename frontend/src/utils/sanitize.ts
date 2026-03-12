import DOMPurify from 'dompurify';

export const sanitizeHTML = (dirty: string): string =>
    DOMPurify.sanitize(dirty, { USE_PROFILES: { html: true } });

export const sanitizeText = (dirty: string): string =>
    DOMPurify.sanitize(dirty, { ALLOWED_TAGS: [] });
