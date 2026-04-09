document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-toggle-target]').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var fieldId = btn.getAttribute('data-toggle-target');
            var field = document.getElementById(fieldId);
            if (!field) return;
            if (field.type === 'password') {
                field.type = 'text';
                btn.textContent = 'Hide';
            } else {
                field.type = 'password';
                btn.textContent = 'Show';
            }
        });
    });
});
