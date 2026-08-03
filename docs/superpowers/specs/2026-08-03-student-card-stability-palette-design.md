# Student Card Stability and Soft Lilac Palette Design

Date: 2026-08-03
Status: Approved

## Goal

Improve the student WebApp study experience by preventing visible layout shifts when a card is flipped, removing a duplicate study action, and replacing harsh colors with the approved soft lilac light palette.

## Scope

This change applies only to the student WebApp at `/student/cards`. It does not change the teacher WebApp, API contracts, database schema, or student progress statuses.

## Study Card Layout

The flashcard keeps a fixed height and uses stable internal regions for:

1. side label (`English` or `Перевод`);
2. main word or translation;
3. optional example/details;
4. guidance text.

The main word and translation must occupy the same vertical region before and after the flip. Variable-length details must scroll inside their own region instead of shifting the main text.

The action area below the card keeps a fixed height in both states. Before the card is flipped, the area remains present but visually hidden. After the flip, it displays the study actions. This prevents the page height and surrounding content from jumping.

## Study Actions

Remove the `Не знаю` button because it currently sends the same `learning` status as `Ещё учу`.

Keep two actions:

- `Ещё учу` → sends `learning`;
- `Знаю` → sends `known`.

No backend behavior or progress schema changes are required.

## Approved Visual Direction

Use a consistent light theme rather than Telegram theme colors for this iteration.

### Palette

- Page background: very light lilac-gray.
- Primary active controls: muted lilac.
- Inactive controls: pale gray-lilac.
- Cards: white with a subtle lilac border and soft shadow.
- `Ещё учу`: muted dusty peach.
- `Знаю`: muted soft green.
- New-word badge: pale green with dark green text.
- Error surfaces: subdued red/pink with readable dark red text.
- Main text: dark gray-purple with accessible contrast.

### Interaction hierarchy

- `Карточки / Статистика` remain the primary navigation.
- `Учить / Список` remain visually secondary.
- `Учу / Знаю` remain compact list-filter chips.
- Buttons use visible but soft borders so controls do not blend together.

## Responsive Behavior

The layout must remain usable on narrow Telegram mobile viewports. Long terms and translations may wrap inside the fixed main-text region. Long examples scroll only inside the details region. No horizontal scrolling is allowed.

## Error Handling

Existing API error behavior remains unchanged. If a progress update fails, the clicked button is re-enabled and the existing status error message is shown.

## Testing

### Automated checks

Update the student WebApp page test to verify:

- `Не знаю` is absent;
- `Ещё учу` and `Знаю` remain;
- only one study action sends `learning`;
- the fixed internal flashcard layout markers are present;
- a fixed action-area container is rendered in both flip states;
- the approved lilac, peach, and green palette tokens are present;
- existing student API tests continue to pass.

### Browser verification

Verify on the deployed page with controlled card data:

- the main text has the same vertical position before and after a flip;
- the flashcard bounding box does not change;
- the action-area bounding box does not change;
- only `Ещё учу` and `Знаю` appear after a flip;
- long example text remains inside the details region;
- `/health` and `/ready` remain healthy.

## Preview Cleanup

The temporary comparison page at `/design-preview/cards` is only a design artifact. Remove its public Nginx route and preview file after the selected design is implemented and verified in the real student WebApp.
