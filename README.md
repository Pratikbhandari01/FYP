# Hotel Booking Project

## Development Methodology

This project now follows the Incremental development methodology.

Instead of building all features in one large cycle, the system is delivered in small, testable increments. Each increment adds usable functionality on top of the previous stable baseline.

### Current Process

1. Define scope for one increment only.
2. Implement features for that increment.
3. Test increment in isolation and against existing features (regression).
4. Merge increment into stable branch after passing checklist.
5. Review, document, and plan the next increment.

### Increment Rules

- Each increment must be deployable.
- No breaking changes without migration notes.
- Each increment must include:
  - Functional changes
  - Test evidence
  - Release notes
  - Risk and rollback notes

### Where Process Files Live

- Method guide: docs/process/INCREMENTAL_METHODOLOGY.md
- Increment template: docs/increments/INCREMENT_TEMPLATE.md
- Release checklist: docs/process/RELEASE_CHECKLIST.md
- Change log template: docs/process/CHANGELOG_TEMPLATE.md
