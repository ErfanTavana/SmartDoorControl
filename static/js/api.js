// api.js
// مسئول درخواست‌های ارتباط با بک‌اند و مدیریت پاسخ‌ها

const DEFAULT_HEADERS = {
    'Content-Type': 'application/json'
};

/**
 * ارسال درخواست به سرور با استفاده از Fetch API
 * @param {string} url - آدرس endpoint
 * @param {RequestInit} options - تنظیمات اضافی fetch
 * @returns {Promise<Response>} - پاسخ خام fetch
 */
export async function request(url, options = {}) {
    const mergedOptions = {
        headers: { ...DEFAULT_HEADERS, ...(options.headers || {}) },
        ...options
    };

    return fetch(url, mergedOptions);
}

/**
 * نمونه تابع برای دریافت داده JSON از سرور
 * @param {string} url - آدرس endpoint
 * @returns {Promise<any>} - داده‌های JSON یا null در صورت خطا
 */
export async function fetchJson(url) {
    try {
        const response = await request(url);
        if (!response.ok) {
            console.error('API error:', response.statusText);
            return null;
        }
        return await response.json();
    } catch (error) {
        console.error('Network error:', error);
        return null;
    }
}
