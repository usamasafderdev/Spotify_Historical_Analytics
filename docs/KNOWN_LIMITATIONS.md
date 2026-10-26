# Known limitations — version 0.1.0

**Internal review candidate; final client delivery is blocked.**

- Historical data is not included. The client is deciding whether complete preloaded history or client-supplied imports are required. No complete 2017-2026 coverage or commercial source approval is claimed.
- Metrics represent imported chart observations, not all-platform Spotify totals. Missing dates are not zero streams. Daily and weekly observations are separate.
- Artist collaborators receive full credit; totals can overlap. Exact album results require stable supplied track/album mappings. Different editions remain separate.
- Coverage indicators describe observed rows/dates. Overlapping sources require reconciliation before treating combined results as canonical history.
- A clean Windows 10/11 VM lifecycle test has not been performed. Developer-host checks cannot establish clean-machine compatibility or the absence of installed developer runtimes.
- Window constraints and Qt scaling were tested. True physical 100/125/150% display scaling, multiple monitors, manual keyboard/focus/accessibility, calendar interaction, shell file choosers, hover/zoom, and Excel desktop rendering still need human acceptance.
- Imports use background staging and transactions but can take minutes at 500k rows. Staging, backups, indexes, and memory scratch trees need additional disk/RAM. Client-like large datasets still need performance acceptance.
- Metadata-only import and a dedicated restore UI are unavailable. Restore requires a support procedure with all instances closed.
- The application and installer are unsigned. Legitimate signing or explicit customer security-policy acceptance is pending; security protections must not be bypassed.
- Dependency review is incomplete. Available notices are included for review; Qt module licensing, LGPL source/replacement materials, native/transitive notices, and bundled optional modules require release-owner review. This is not formal legal certification or a vulnerability-free guarantee.

Resolve these release gates before sending the product to the client. The candidate remains useful for controlled demonstrations with clearly labeled synthetic data.
