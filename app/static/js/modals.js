document.addEventListener('DOMContentLoaded', function () {
    document.addEventListener('click', function (e) {
        var opener = e.target.closest('[data-modal-open]');
        if (opener) {
            var id = opener.getAttribute('data-modal-open');
            var modal = document.getElementById(id);
            if (modal) modal.classList.add('active');
            return;
        }

        var closer = e.target.closest('[data-modal-close]');
        if (closer) {
            var id = closer.getAttribute('data-modal-close');
            var modal = document.getElementById(id);
            if (modal) modal.classList.remove('active');
            return;
        }

        if (e.target.classList.contains('modal-overlay')) {
            e.target.classList.remove('active');
        }
    });
});
