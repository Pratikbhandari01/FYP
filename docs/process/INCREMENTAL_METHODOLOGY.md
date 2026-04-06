# Incremental Methodology Guide

## Objective

Deliver the Hotel Booking system as a sequence of small, valuable increments with continuous validation.

## Increment Lifecycle

### 1. Planning

- Define increment goal.
- Select small set of features.
- Define acceptance criteria.
- Identify dependency and migration impact.

### 2. Design

- Confirm model, view, template, and route updates.
- Confirm database migration strategy if needed.
- Define test scope and rollback approach.

### 3. Build

- Implement only approved scope for increment.
- Keep commit and PR scope focused.
- Update UI and backend together for feature completeness.

### 4. Verification

- Unit-level checks.
- Flow-level checks.
- Regression checks on existing booking/auth/agent flows.

### 5. Release

- Complete release checklist.
- Document behavior changes and known limits.
- Tag increment and create release note.

### 6. Feedback

- Collect defects and UX feedback.
- Prioritize for next increment.

## Team Cadence (Suggested)

- Increment duration: 1 to 2 weeks.
- Daily sync: blockers, progress, risks.
- End of increment:
  - Demo
  - Retrospective
  - Backlog grooming for next increment

## Increment Definition of Done

- Feature works end-to-end.
- No critical regression.
- Migration safety verified.
- Templates and routes resolved.
- Basic user-facing documentation updated.
- Release checklist completed.

## Increment Naming Convention

Use this format:

- INC-01 Foundation
- INC-02 Agent Management
- INC-03 Booking Enhancements

## Recommended Initial Increments

- INC-01: Auth stabilization + role access rules
- INC-02: Agent dashboard + hotel CRUD + room type CRUD
- INC-03: Room inventory, pricing currency consistency (NPR), and booking flow hardening
- INC-04: Customer booking history + profile improvements
- INC-05: Admin quality, analytics, and reporting baseline
