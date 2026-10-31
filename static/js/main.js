/**
 * Brightloop Software - Subscription Management System
 * Front-end Dashboard Interactivity
 */

document.addEventListener('DOMContentLoaded', function () {
    // Sidebar Mobile Toggle
    const sidebar = document.querySelector('.saas-sidebar');
    const toggleBtn = document.querySelector('.btn-sidebar-toggle');
    const backdrop = document.querySelector('.sidebar-backdrop');

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function () {
            sidebar.classList.toggle('sidebar-open');
            if (backdrop) {
                backdrop.classList.toggle('show');
            }
        });
    }

    if (backdrop) {
        backdrop.addEventListener('click', function () {
            sidebar.classList.remove('sidebar-open');
            backdrop.classList.remove('show');
        });
    }

    // Initialize Bootstrap tooltips
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert ? bootstrap.Alert.getInstance(alert) : null;
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });
});
