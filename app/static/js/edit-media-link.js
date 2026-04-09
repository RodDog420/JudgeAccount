const courtsDataEl = document.getElementById('courts-data');
const courtsByState = JSON.parse(courtsDataEl.getAttribute('data-courts'));
const preselectedCourt = courtsDataEl.getAttribute('data-preselected-court');

const stateSelect = document.getElementById('state-select');
const courtSelect = document.getElementById('court-select');

function updateCourtOptions() {
    const selectedState = stateSelect.value;

    courtSelect.innerHTML = '<option value="">Select a court...</option>';

    if (selectedState && courtsByState[selectedState]) {
        courtsByState[selectedState].forEach(function(court) {
            const option = document.createElement('option');
            option.value = court[0];
            option.text = court[1];

            if (court[0] === preselectedCourt) {
                option.selected = true;
            }

            courtSelect.appendChild(option);
        });
        courtSelect.disabled = true;
    } else {
        courtSelect.disabled = true;
    }
}

stateSelect.addEventListener('change', updateCourtOptions);
updateCourtOptions();
