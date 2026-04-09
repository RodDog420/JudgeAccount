const courtsDataEl = document.getElementById('courts-data');
const courtsByState = JSON.parse(courtsDataEl.getAttribute('data-courts'));
const preselectedCourt = courtsDataEl.getAttribute('data-preselected-court') || null;

const stateSelect = document.getElementById('state-select');
const courtSelect = document.getElementById('court-select');

function updateCourtOptions() {
    const selectedState = stateSelect.value;
    const currentCourtSelection = courtSelect.value;

    courtSelect.innerHTML = '<option value="">Select a court...</option>';

    if (selectedState && courtsByState[selectedState]) {
        courtsByState[selectedState].forEach(function(court) {
            const option = document.createElement('option');
            option.value = court[0];
            option.text = court[1];

            const courtToSelect = preselectedCourt || currentCourtSelection;
            if (courtToSelect && court[0] === courtToSelect) {
                option.selected = true;
            }

            courtSelect.appendChild(option);
        });
        courtSelect.disabled = preselectedCourt ? true : false;
    } else {
        courtSelect.disabled = true;
    }
}

stateSelect.addEventListener('change', updateCourtOptions);
updateCourtOptions();

const publicationDateField = document.getElementById('publication_date');
if (publicationDateField) {
    const today = new Date().toISOString().split('T')[0];
    publicationDateField.max = today;
}
