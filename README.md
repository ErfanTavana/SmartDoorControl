# SmartDoorControl

This repository will host the Django-based SmartDoorControl system. The goal is to mirror the architecture and coding style used in the referenced `unischedule` project while implementing the door access workflow described in the initial brief.

## System overview
- Web-first experience using Django templates and session authentication.
- Roles: **Head** (household admin), **Member** (limited to opening the door), and **System Administrator** (Django admin backend).
- ESP32 connects only through REST/JSON APIs with token-based authentication.
- Progressive Web App support for the template-driven UI (manifest and service worker) without exposing extra APIs.

## Application structure
- Django project with custom user model and apps: `accounts`, `households`, `access`, and `devices` (matching the earlier task list).
- Models: `User` (HEAD/MEMBER roles), `Household`, `MemberProfile` (access windows), `Device` (API token, last seen), `DoorCommand` (execution queue), and `AccessLog` (success/denied records).
- Web flows follow POST/Redirect/Template patterns similar to `unischedule` (HTML forms, server-rendered dashboards, and CRUD views).
- API endpoints limited to devices: command polling and acknowledgement with JSON responses and token headers.

## Development notes
- Align coding conventions and project layout with the `unischedule` reference: Django templates for forms, class-based views where practical, and clear separation of concerns between apps.
- Middleware or decorators enforce role-based access; `Member` users are redirected to the door control page, while `Head` users see management dashboards.
- Access control logic: inactive members or out-of-window requests create denied `AccessLog` entries; valid requests create `DoorCommand` records and successful logs.
- Device polling updates `last_seen`, returns the earliest pending command, and marks commands executed via an acknowledgement endpoint.

## Next steps
- Scaffold the Django project and apps reflecting this design.
- Add PWA assets (manifest, service worker, icons) to the template-based UI.
- Port reusable patterns from `unischedule` where applicable (form handling, template organization, and settings structure).

## How to run locally
1. **Prepare Python deps**
   - (اختیاری) یک virtualenv بسازید.
   - `pip install -r requirements.txt`
2. **اجرای مایگریشن‌ها**
   - `python manage.py migrate`
3. **ساخت حساب ادمین (اختیاری)**
   - `python manage.py createsuperuser`
4. **کامپایل Tailwind (نسخه CLI)**
   - `npm install`
   - `npm run build:css` (فایل `static/css/tailwind.css` ساخته/به‌روز می‌شود)
5. **اجرای سرور توسعه Django**
   - `python manage.py runserver`
6. برنامه از طریق `http://127.0.0.1:8000/` در دسترس است.
