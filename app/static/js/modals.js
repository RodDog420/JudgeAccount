document.addEventListener('DOMContentLoaded', function () {
    document.addEventListener('click', function (e) {
        var opener = e.target.closest('[data-modal-open]');
        if (opener) {
            var id = opener.getAttribute('data-modal-open');
            var modal = document.getElementById(id);
            if (modal) {
                // If the trigger has an href, pass it to the modal's confirm button
                var confirmBtn = modal.querySelector('[data-modal-confirm-btn]');
                if (confirmBtn && opener.getAttribute('href')) {
                    confirmBtn.setAttribute('href', opener.getAttribute('href'));
                }
                modal.classList.add('active');
            }
            e.preventDefault();
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
