# SmartDoorControl

## Project Overview
SmartDoorControl is a Django-based web application for managing household door access. It provides a browser UI for household heads and members plus token-secured device endpoints for physical door controllers.

## Key Features
- **Authentication with roles:** Custom `User` model with `HEAD` and `MEMBER` roles drives redirects and permissions for dashboards and member access flows.【F:accounts/models.py†L1-L22】【F:accounts/views.py†L8-L28】
- **Household management:** Household heads own a household/building record and can view member counts and device totals from a dashboard.【F:households/views.py†L13-L22】
- **Member profiles with schedules:** Heads create member accounts with allowed time windows and active flags; updates and deletions are supported via forms.【F:households/forms.py†L8-L38】【F:households/views.py†L25-L58】
- **Access control flow:** Members request door access through the member panel; scheduling checks determine whether a `DoorCommand` is queued and an `AccessLog` recorded for success or denial.【F:access/views.py†L12-L62】
- **Command queue for devices:** Devices poll for pending commands, receive pulse durations, and acknowledge execution; stale commands expire after 15 seconds.【F:devices/views.py†L29-L76】【F:devices/views.py†L78-L100】
- **Firmware distribution:** Devices fetch firmware/config payloads with checksums calculated on save for integrity verification.【F:devices/views.py†L102-L123】【F:devices/models.py†L24-L65】
- **Device logging:** Devices post structured logs that are sanitized and stored with metadata; heads can review recent entries with level and event breakdowns.【F:devices/views.py†L125-L174】【F:devices/views.py†L176-L199】
- **Access and device history:** Heads can review access logs tied to their household and see device last-seen timestamps updated during API calls.【F:access/views.py†L64-L73】【F:devices/views.py†L37-L55】

## Architecture / Structure
- `accounts/`: Custom user model, login/logout views, and role-based decorators.
- `households/`: Building/household/member models, member forms, and head-facing dashboards.
- `access/`: Access logs, door command models, and member panel for requesting door actions.
- `devices/`: Device registration model with API token, firmware metadata, device logs, and endpoints consumed by hardware agents.
- `templates/`: Tailwind-styled HTML templates for the UI; `templates/base/base.html` provides navigation and layout.
- `static/`: Icons, manifest, service worker, and CSS inputs; Tailwind build scripts live in `package.json`.

## How It Works
1. Users authenticate via the login view; heads are redirected to their dashboard while members land on the member panel.【F:accounts/views.py†L8-L28】
2. A head’s household/building is created on first access if absent. Dashboard metrics include member and device counts.【F:households/utils.py†L4-L14】【F:households/views.py†L13-L22】
3. Heads manage members by creating users with allowed time windows; edits and deletions update associated `MemberProfile` records.【F:households/forms.py†L8-L38】【F:households/views.py†L25-L58】
4. When a user posts from the member panel, the system locates the building’s device, validates scheduling for members, queues a `DoorCommand`, and logs success or denial in `AccessLog`.【F:access/views.py†L12-L62】
5. Devices authenticate with `X-DEVICE-TOKEN` to poll `/api/device/command/`; pending commands mark expired after 15 seconds and return `open` instructions with a pulse duration. Devices acknowledge execution at `/api/device/command/ack/` to finalize the command record.【F:devices/views.py†L29-L100】
6. Devices fetch firmware payloads from `/api/device/firmware/` and submit runtime logs to `/api/device/logs/`, which store sanitized metadata and update `last_seen`. Heads can review device logs and breakdowns via the web UI.【F:devices/views.py†L102-L199】

## Requirements & Dependencies
- Python 3 (tested with Django 5.0.7).【F:requirements.txt†L1-L1】
- Node.js (optional) for building Tailwind CSS assets via `npm run build`.【F:package.json†L1-L18】

## Configuration
- Settings default to SQLite storage, `DEBUG=True`, and `ALLOWED_HOSTS=['*']`.【F:config/settings.py†L18-L43】
- Static files are served from `static/` with `STATIC_URL="static/"` and `STATICFILES_DIRS` set accordingly.【F:config/settings.py†L63-L68】
- Custom user model is registered as `accounts.User`, and authentication redirects to the member panel by default.【F:config/settings.py†L70-L72】【F:accounts/views.py†L8-L28】
- Application timezone is `Asia/Tehran`.【F:config/settings.py†L55-L59】
- Device endpoints expect `X-DEVICE-TOKEN` header matching a `Device.api_token`.【F:devices/views.py†L26-L42】

## How to Run / Use
1. Install dependencies: `pip install -r requirements.txt`.
2. Apply migrations: `python manage.py migrate`.
3. Create a user (e.g., head) with Django’s standard `createsuperuser` or via the admin site (enabled at `/admin/`).
4. Start the development server: `python manage.py runserver`.
5. Authenticate at `/accounts/login/` and navigate using the header links to manage members, view access logs, and review device logs.【F:templates/base/base.html†L37-L76】
6. Devices interact with the API endpoints under `/api/device/...` using their assigned tokens.

## Notes & Limitations
- The project ships with `DEBUG=True` and SQLite; adjust settings for production environments.【F:config/settings.py†L18-L43】
- Device registration UI is not exposed; `Device` records must be created via admin or Django shell before hardware agents can poll for commands.【F:devices/models.py†L12-L23】【F:templates/base/base.html†L37-L52】
- Command expiration is fixed at 15 seconds, and pulse duration is hardcoded to 1000 ms in responses.【F:devices/views.py†L37-L76】
