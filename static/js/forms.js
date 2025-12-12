// forms.js
// مدیریت اعتبارسنجی اولیه و تجربه کاربری فرم‌ها

const ERROR_CLASS = 'input-error';

/**
 * اضافه کردن استایل خطا به فیلدهای خالی اجباری
 * @param {HTMLFormElement} form
 */
function bindValidation(form) {
    const requiredFields = form.querySelectorAll('[required]');

    requiredFields.forEach((field) => {
        field.addEventListener('input', () => {
            if (field.validity.valid) {
                field.classList.remove(ERROR_CLASS);
            }
        });
    });

    form.addEventListener('submit', (event) => {
        let hasError = false;
        requiredFields.forEach((field) => {
            if (!field.validity.valid) {
                field.classList.add(ERROR_CLASS);
                hasError = true;
            }
        });
        if (hasError) {
            event.preventDefault();
            form.querySelector('[type="submit"], button').focus();
        }
    });
}

/**
 * جلوگیری از ارسال‌های مکرر فرم و افزودن وضعیت در حال ارسال
 * @param {HTMLFormElement} form
 */
function preventMultipleSubmit(form) {
    form.addEventListener('submit', (event) => {
        if (event.defaultPrevented) return;
        const submitBtn = form.querySelector('[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.classList.add('opacity-70');
            submitBtn.textContent = submitBtn.dataset.loadingText || submitBtn.textContent;
        }
    });
}

/**
 * راه‌اندازی بهبودهای فرم برای همه فرم‌های صفحه
 */
export function enhanceForms() {
    const forms = document.querySelectorAll('form');
    forms.forEach((form) => {
        bindValidation(form);
        preventMultipleSubmit(form);
    });
}
