# Lighthouse (mobile) — production build, `/` via `vite preview`

`npx lighthouse@12 http://localhost:4173/ --only-categories=performance,accessibility --form-factor=mobile`, 5 runs each, median reported.

| | Main JS bundle | Performance (median, runs) | Accessibility | LCP (median) |
|---|---|---|---|---|
| Before (eager Dashboard) | 1,509.06 kB / 427.27 kB gzip | **59** (28, 49, 59, 60, 62) | **100** | 4.79 s |
| After (`React.lazy` Dashboard) | 1,000.20 kB / 286.31 kB gzip (+ 506.83 kB Dashboard chunk) | **66** (52, 62, 66, 67, 73) | **100** | 4.02 s |
