# Openverse Images for Vocabulary Cards Design

Date: 2026-08-03
Status: Approved

## Goal

Automatically add an openly licensed image to each newly created vocabulary card, let the teacher replace or remove it before publication, and show the selected image on both sides of the student's study card.

## Scope

The first release applies only to cards created after deployment. Existing cards remain valid and image-free unless they are recreated later. The feature covers both lesson-generated draft cards and manually created draft cards.

## Image Source

Use the public Openverse Images API. Requests identify the application with this non-secret user agent:

`EnglishTutorAI/0.1 (support@englishtutorai.ru)`

Search uses the English term plus available English definition, source phrase, or example context. Russian translation is not required in the external query. Search must have a short timeout and must never make card creation fail.

The application does not claim that Openverse owns the media. It preserves the provider's source URL, creator, and license metadata.

## Storage

Do not store image files in PostgreSQL or on the server. Add nullable metadata fields to each vocabulary card:

- `image_url`: selected display image or thumbnail URL;
- `image_source_url`: original landing page;
- `image_creator`: creator name when supplied;
- `image_license`: short license identifier;
- `image_license_url`: license page;
- `image_search_query`: query used for automatic selection.

A card with all fields null behaves exactly like existing cards.

## Automatic Selection

After a new draft card has been saved, request Openverse results with the commercial-use filter and select the first usable result. A usable result must include an HTTPS thumbnail or image URL and a source landing page. Allow only `cc0`, `pdm`, `by`, and `by-sa`; exclude non-commercial, no-derivatives, and unknown licenses.

Image enrichment is best-effort:

- a timeout, rate limit, malformed response, or empty result leaves the card without an image;
- card creation and lesson processing continue normally;
- external errors are logged without credentials or large response bodies;
- no Openverse request is made when students view a card.

For lesson-generated batches, requests use a low concurrency limit and a per-card timeout so external image search cannot overwhelm the application.

## Teacher Workflow

Each new draft card can show:

- the selected thumbnail;
- compact attribution;
- `Заменить картинку`;
- `Убрать картинку`.

Selecting `Заменить картинку` requests three alternative Openverse results using the stored query and excluding the current image. The teacher can choose one result, request `Показать ещё`, close the alternatives, or remove the current image.

Only the selected image metadata is persisted. Alternative search results remain transient. Teacher ownership checks apply to every image-update endpoint. The first release allows image editing only while the card is a draft.

## Attribution

Display a compact linked attribution for every selected image, even when the specific license does not legally require credit. This produces consistent UI and safely covers CC BY images.

Preferred text:

- creator available: `Фото: {creator} · {source} · {license}`;
- creator unavailable: `Фото: {source} · {license}`.

The attribution links to `image_source_url`. The license name links to `image_license_url` when available. For CC BY results, creator, source, and license must not be hidden.

## Student Experience

Show the selected image on both the front and back of the study card. Use one fixed-size image region in the same grid position on both sides:

- card height: 460 px;
- image region: 126 px high;
- image uses `object-fit: cover` and a rounded bordered frame;
- attribution appears immediately below the image;
- word, translation, example, hint, and action regions remain fixed;
- action-space reservation remains unchanged.

If no image exists or an external image fails to load, hide the image region and attribution without breaking the word, translation, example, or progress actions. The page does not retry indefinitely.

## API Shape

Extend teacher and student card response objects with nullable image metadata.

Add teacher-only draft endpoints:

- `GET /api/teacher/cards/{card_id}/image-options?offset=N` returns up to three transient Openverse candidates and the next offset;
- `PUT /api/teacher/cards/{card_id}/image` accepts one complete candidate metadata object returned by the options endpoint and persists it after validation;
- `DELETE /api/teacher/cards/{card_id}/image` clears all image metadata.

The server, not the browser, calls Openverse. Candidate URLs must be HTTPS and candidate licenses must be from the allowed Openverse set. Never accept arbitrary teacher-supplied URLs in this release.

## Configuration and Limits

Add non-secret settings with safe defaults:

- Openverse API base URL;
- Openverse request timeout;
- result page size;
- batch concurrency limit;
- application user agent.

Openverse failure must degrade to no image. Respect rate-limit responses and do not retry a `429` immediately. Search requests happen only on creation, replacement, or `Показать ещё`.

## Security and Privacy

Do not send student names, teacher names, Telegram IDs, lesson IDs, or Russian personal context to Openverse. Queries contain only vocabulary text and English learning context.

Escape attribution text in both WebApps. Validate external URLs as HTTPS before returning or storing them. Do not proxy arbitrary URLs through the backend.

## Database Migration

Create an Alembic migration adding the nullable metadata columns. No backfill is performed. Downgrade removes only these columns.

## Testing

Automated tests cover:

- Openverse response parsing and allowed-result filtering;
- correct user agent, timeout, and query construction;
- empty results, malformed responses, timeout, and `429` fallback;
- automatic enrichment for manual and lesson-generated new drafts;
- no image lookup for existing/student-view paths;
- teacher ownership and draft-only rules for options, selection, and removal;
- validation of HTTPS URLs and candidate metadata;
- API serialization for cards with and without images;
- attribution escaping;
- unchanged progress semantics;
- fixed student card geometry and image-failure fallback;
- database migration upgrade and downgrade shape.

Browser verification covers automatic teacher thumbnails, three alternatives, selection, removal, attribution links, student front/back display, external image failure, and zero geometry delta when flipping.

## Deployment and Preview Cleanup

Run the full test suite, Ruff, migration, and Docker build before deployment. After deployment verify `/health`, `/ready`, container health, production API/UI markers, and browser workflows.

Remove `/design-preview/student-image-card` only after production verification and confirm it returns `404`.
