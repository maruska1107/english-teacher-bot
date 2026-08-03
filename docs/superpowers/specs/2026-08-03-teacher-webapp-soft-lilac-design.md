# Teacher WebApp Soft Lilac Theme Design

Date: 2026-08-03
Status: Approved

## Goal

Bring the teacher card-management WebApp into the same visual family as the student WebApp while keeping teacher actions slightly more prominent and preserving every existing workflow.

## Scope

This is a presentation-only update to `app/api/teacher_webapp.py`.

The following remain unchanged:

- teacher API endpoints and payloads;
- profile selection for students and groups;
- draft and published card tabs;
- manual card creation and its required-field validation;
- card deletion and bulk publication;
- Telegram authentication and initialization;
- backend data and status semantics.

## Approved Visual Direction

The teacher WebApp uses the same soft lilac system as the student WebApp:

- page background: `#f7f5fa`;
- surface background: white;
- main text: dark gray-purple;
- secondary text: muted gray-purple;
- borders: subtle light lilac;
- shadows: low-contrast gray-purple.

Teacher primary actions use a slightly darker lilac (`#746e9f`) than student primary actions so important work controls remain prominent.

## Components

### Profile and card surfaces

Profile buttons, card rows, and panels use white surfaces with a subtle lilac border, rounded corners, and a soft shadow. Existing layout and click behavior remain unchanged.

### Badges

All profile metadata badges have visible 1 px borders:

- `ученик / группа`: light lilac background, text, and border;
- `+N новых слов`: soft green background with a matching green border;
- `N опубликовано`: light lilac background with a matching lilac border.

The borders are required because borderless badges visually merge into white cards.

### Buttons and tabs

- primary actions and the selected tab: darker muted lilac with white text and a darker lilac border;
- secondary actions: pale lilac with dark muted text and a light lilac border;
- ghost actions: neutral lilac-gray with a visible border;
- delete actions: subdued rose background, dark rose text, and a matching rose border;
- disabled actions: reduced opacity while retaining their borders and disabled cursor.

### Form controls

Inputs and textareas use the shared white surface, dark text, and a light lilac border. Focus uses a darker lilac border plus a soft translucent lilac ring. Required-field validation and button enablement behavior remain unchanged.

### Empty and error states

Empty states use the soft green family. Errors use subdued rose colors. Both retain readable contrast and avoid saturated red or green.

## Responsive Behavior

The current teacher layout and wrapping behavior remain intact. Badges and action buttons continue wrapping on narrow screens. No new fixed widths or horizontal scrolling are introduced.

## Testing

Automated regression checks will verify:

- approved palette markers are present;
- Telegram theme color variables are absent from teacher CSS;
- badges include visible borders;
- existing teacher profile, tab, form, delete, and publish markers remain present;
- required manual-card fields and disabled-button behavior remain intact.

Browser verification will inspect profile selection, tab switching, form controls, badge borders, delete buttons, disabled states, and mobile-width wrapping.

The full test suite, Ruff, and `git diff --check` must pass before deployment.

## Deployment and Verification

Deploy through the existing Docker Compose workflow. Verify:

- `/health` returns healthy;
- `/ready` reports the database ready;
- production teacher HTML contains the approved palette and border markers;
- containers are running without new backend errors;
- browser behavior matches the approved mockup.

After successful production verification, remove the temporary preview at `/design-preview/teacher-theme` and confirm it returns `404`.
