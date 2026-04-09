document.addEventListener('DOMContentLoaded', function () {
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('[data-confirm]');
        if (!btn) return;
        var message = btn.getAttribute('data-confirm');
        if (!confirm(message)) {
            e.preventDefault();
            e.stopImmediatePropagation();
        }
    });
});
