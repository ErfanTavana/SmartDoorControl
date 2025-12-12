// ui.js
// توابع مرتبط با رابط کاربری و تعاملات بصری

const NAV_OPEN_CLASS = 'nav-open';

/**
 * فعال‌سازی منوی موبایل با دکمه همبرگری
 */
export function initNavigation() {
    const nav = document.querySelector('header nav');
    const toggleBtn = document.querySelector('[data-nav-toggle]');

    if (!nav || !toggleBtn) return;

    const closeNav = () => {
        nav.classList.remove(NAV_OPEN_CLASS);
        toggleBtn.setAttribute('aria-expanded', 'false');
    };

    const openNav = () => {
        nav.classList.add(NAV_OPEN_CLASS);
        toggleBtn.setAttribute('aria-expanded', 'true');
    };

    toggleBtn.addEventListener('click', () => {
        const isOpen = nav.classList.contains(NAV_OPEN_CLASS);
        if (isOpen) {
            closeNav();
        } else {
            openNav();
        }
    });

    // بستن منو هنگام تغییر اندازه به دسکتاپ
    window.addEventListener('resize', () => {
        if (window.innerWidth >= 993) {
            closeNav();
        }
    });

    // بستن منو در صورت کلیک بیرون از منو
    document.addEventListener('click', (event) => {
        const isInsideNav = nav.contains(event.target) || toggleBtn.contains(event.target);
        if (!isInsideNav) {
            closeNav();
        }
    });
}

/**
 * نمایش سایه هنگام اسکرول در container جدول برای نمایش قابلیت اسکرول افقی
 */
export function enhanceTables() {
    const tableContainers = document.querySelectorAll('.table-container');

    tableContainers.forEach((container) => {
        const shadowClass = 'scroll-shadow';
        const updateShadow = () => {
            if (container.scrollWidth > container.clientWidth && container.scrollLeft > 0) {
                container.classList.add(shadowClass);
            } else {
                container.classList.remove(shadowClass);
            }
        };

        container.addEventListener('scroll', updateShadow);
        window.addEventListener('resize', updateShadow);
        updateShadow();
    });
}

/**
 * راه‌اندازی همه تعاملات UI
 */
export function initUI() {
    initNavigation();
    enhanceTables();
}
