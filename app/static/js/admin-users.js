const selectAllCheckbox = document.getElementById('select-all');
const userCheckboxes = document.querySelectorAll('.user-checkbox');
const selectedCount = document.getElementById('selected-count');
const bulkReasonInput = document.getElementById('bulk-reason');
const bulkActionSelect = document.getElementById('bulk-action-select');

function updateSelectedCount() {
    const checked = document.querySelectorAll('.user-checkbox:checked').length;
    selectedCount.textContent = `${checked} selected`;

    const hasSelection = checked > 0;
    bulkActionSelect.disabled = !hasSelection;
    bulkReasonInput.disabled = !hasSelection;
}

if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener('change', function() {
        userCheckboxes.forEach(checkbox => {
            checkbox.checked = this.checked;
        });
        updateSelectedCount();
    });
}

userCheckboxes.forEach(checkbox => {
    checkbox.addEventListener('change', function() {
        const allChecked = Array.from(userCheckboxes).every(cb => cb.checked);
        const noneChecked = Array.from(userCheckboxes).every(cb => !cb.checked);

        if (selectAllCheckbox) {
            selectAllCheckbox.checked = allChecked;
            selectAllCheckbox.indeterminate = !allChecked && !noneChecked;
        }

        updateSelectedCount();
    });
});

updateSelectedCount();

bulkActionSelect.disabled = true;
bulkReasonInput.disabled = true;

