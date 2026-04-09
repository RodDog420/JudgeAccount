document.addEventListener('DOMContentLoaded', function() {
    const flagTypeSelect = document.querySelector('select[name="flag_type"]');
    const descriptionField = document.querySelector('textarea[name="description"]');
    const form = flagTypeSelect.closest('form');

    function toggleDescriptionRequired() {
        if (flagTypeSelect.value === 'other') {
            descriptionField.setAttribute('required', 'required');
        } else {
            descriptionField.removeAttribute('required');
        }
    }

    toggleDescriptionRequired();

    flagTypeSelect.addEventListener('change', toggleDescriptionRequired);

    form.addEventListener('submit', function(e) {
        if (flagTypeSelect.value === 'other' && !descriptionField.value.trim()) {
            e.preventDefault();
            alert('Please provide an explanation when selecting "Other" as the violation type.');
            descriptionField.focus();
        }
    });
});
