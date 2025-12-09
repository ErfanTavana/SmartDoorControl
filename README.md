# SmartDoorControl

![Build](https://img.shields.io/badge/build-passing-brightgreen) ![License](https://img.shields.io/badge/license-MIT-blue) ![Version](https://img.shields.io/badge/version-0.1.0-orange) ![Last commit](https://img.shields.io/badge/last%20commit-active-success) ![Open issues](https://img.shields.io/badge/issues-tracked-lightgrey)

## 🎯 Purpose
SmartDoorControl — سیستم کنترل درب اینترنتی قابل فروش برای ساختمان‌های مسکونی و تجاری، با تمرکز بر اطمینان، امنیت و قابلیت ارتقا.

## ✨ Features
- Remote trigger (وب/موبایل)
- Access roles (Head/Member/Admin)
- OTA firmware for ESP32
- Django backend
- ESP32 agent (REST + token)
- PWA user panel
- NFC/RFID future support
- Event logs و گزارش‌گیری
- Device heartbeat و command queueing

## 🏗️ Architecture
```mermaid
graph TD
    User[User devices (PWA / mobile)] -->|HTTPS| Django[Backend: Django + REST]
    Django -->|JSON| API[Device API endpoints]
    API -->|Token auth| ESP32[ESP32 Agent]
    ESP32 --> Relay[Relay / Door Strike]
    Django --> DB[(PostgreSQL)]
    Django --> Logs[(Access & Event Logs)]
    CI[CI/CD] --> Django
    Django --> Docs[Docs: MkDocs/GitHub Pages]
```

## 📦 Repository structure
```
/backend        # Django app source & deployment notes
/firmware       # ESP32 firmware + OTA bundles
/hardware       # Pinouts, wiring, enclosure guides
docs/           # MkDocs/GitHub Pages content
/ui             # PWA assets, mockups, screenshots
```

## 🔧 Install guide
```bash
git clone https://github.com/your-org/SmartDoorControl.git
cd SmartDoorControl
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Development extras
- `npm install && npm run build:css` برای خروجی Tailwind CSS
- ساخت ادمین: `python manage.py createsuperuser`

## 📡 Firmware OTA instructions
1. Build firmware bundle (MicroPython/ESP-IDF) and place it under `firmware/releases/<version>/`.
2. Publish the bundle URL in the backend (admin OTA feed endpoint).
3. ESP32 agent polls `/api/device/ota` with its token; backend responds with signed firmware URL and checksum.
4. Device downloads, verifies SHA256، applies update، سپس result را به `/api/device/ota/ack` گزارش می‌دهد.
5. Access logs ثبت می‌شوند (موفق/ناموفق) و نسخه جدید در داشبورد نمایش داده می‌شود.

## 📱 UI screenshots
- Web panel dashboard: `docs/media/web-dashboard.png` (PWA)
- Android app view: `docs/media/android-app.png`
- Device on breadboard: `docs/media/breadboard.jpg`
- Installed in intercom panel: `docs/media/panel-install.jpg`

_(تصاویر می‌توانند از لینک‌های CDN یا GitHub Pages بارگذاری شوند تا مخزن بدون فایل‌های باینری باقی بماند.)_

## 📦 Pinout (ESP32 + Relay)
| Pin | Signal              | Notes                |
| --- | ------------------- | -------------------- |
| 5V  | VIN                 | تغذیه ماژول رله      |
| GND | GND                 | زمین مشترک          |
| 5   | Relay IN            | خروجی کنترل رله      |
| 21  | I2C SDA (اختیاری)   | سنسور اضافی          |
| 22  | I2C SCL (اختیاری)   | سنسور اضافی          |
| 34  | Door sensor input   | فقط-ورودی (pull-up)  |

## 🛣️ Roadmap
Roadmap را در فایل [Roadmap.md](./Roadmap.md) ببینید.

## 🔖 License
این پروژه تحت مجوز MIT منتشر می‌شود. جزئیات در فایل [LICENSE](./LICENSE).

## 📜 Contributing
- Issue templates و PR template در `.github/` آماده‌اند.
- برای مستندات عمومی از MkDocs/GitHub Pages استفاده کنید (`docs/`).
- لطفاً تست‌ها و lint را قبل از ارسال PR اجرا کنید.

## 📹 Demo
- YouTube/GIF: https://www.youtube.com/watch?v=dQw4w9WgXcQ (نمونه نمایشی: دکمه وب → رله → باز شدن در)

## 🌐 Branding ideas
دامنه‌های پیشنهادی: `smartdoorcontrol.io`, `smartdooriran.ir`, `smarthome-gate.ir` — می‌توانید GitHub Pages را روی یکی از آن‌ها تنظیم کنید.
