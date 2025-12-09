// main.js
// نقطه ورودی اصلی برای بارگذاری ماژول‌های فرانت‌اند

import { initUI } from './ui.js';
import { enhanceForms } from './forms.js';
import { fetchJson } from './api.js';

/**
 * مقداردهی اولیه برنامه پس از لود DOM
 */
function bootstrap() {
    initUI();
    enhanceForms();

    // نمونه استفاده از API در صورت نیازهای آینده
    // fetchJson('/api/status').then((data) => console.log('API status', data));
}

document.addEventListener('DOMContentLoaded', bootstrap);
