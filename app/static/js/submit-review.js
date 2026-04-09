const courtsDataEl = document.getElementById('courts-data');
const courtsByState = JSON.parse(courtsDataEl.getAttribute('data-courts'));
const preselectedCourt = courtsDataEl.getAttribute('data-preselected-court') || null;
const redirectUrl = courtsDataEl.getAttribute('data-redirect-url');

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

            if (preselectedCourt && court[0] === preselectedCourt) {
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

const courtDateField = document.getElementById('court_date');
if (courtDateField) {
    const today = new Date().toISOString().split('T')[0];
    courtDateField.max = today;
}

const appearedNoButton = document.getElementById('appeared-no');
if (appearedNoButton) {
    appearedNoButton.addEventListener('change', function() {
        if (this.checked) {
            if (confirm('You will be redirected to submit a media link instead. Continue?')) {
                window.location.href = redirectUrl;
            } else {
                document.getElementById('appeared-yes').checked = true;
            }
        }
    });
}
