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

const toggleColumnsBtn = document.getElementById('toggle-columns');
const adminTableBox = document.getElementById('admin-user-table');

if (toggleColumnsBtn && adminTableBox) {
    let showingAll = false;

    toggleColumnsBtn.addEventListener('click', function() {
        showingAll = !showingAll;

        if (showingAll) {
            adminTableBox.classList.add('show-all-columns');
            this.textContent = 'Show Priority Columns';
        } else {
            adminTableBox.classList.remove('show-all-columns');
            this.textContent = 'Show All Columns';
        }
    });
}
