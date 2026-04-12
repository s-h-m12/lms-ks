document.addEventListener('DOMContentLoaded', function() {
    const notifications = document.querySelectorAll('.notification');

    notifications.forEach(notification => {
        setTimeout(function() {
            notification.classList.add('fade-out');
            setTimeout(function() {
                notification.remove();
            }, 300);
        }, 5000);

        const closeBtn = notification.querySelector('.notification-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                notification.classList.add('fade-out');
                setTimeout(function() {
                    notification.remove();
                }, 300);
            });
        }
    });
});