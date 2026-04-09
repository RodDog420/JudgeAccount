const navToggle = document.getElementById('nav-toggle');
const navLinks = document.getElementById('nav-links');
const dropdownToggles = document.querySelectorAll('.nav-dropdown-toggle');

navToggle.addEventListener('click', function(e) {
    e.stopPropagation();
    navLinks.classList.toggle('nav-active');
    navToggle.classList.toggle('active');
});

navLinks.querySelectorAll('a:not(.nav-dropdown-menu a)').forEach(link => {
    link.addEventListener('click', function() {
        navLinks.classList.remove('nav-active');
        navToggle.classList.remove('active');
    });
});

dropdownToggles.forEach(toggle => {
    toggle.addEventListener('click', function(e) {
        e.stopPropagation();
        const dropdown = this.parentElement;
        const isOpen = dropdown.classList.contains('dropdown-open');

        document.querySelectorAll('.nav-dropdown').forEach(d => {
            d.classList.remove('dropdown-open');
        });

        if (!isOpen) {
            dropdown.classList.add('dropdown-open');
        }
    });
});

document.querySelectorAll('.nav-dropdown-menu a').forEach(link => {
    link.addEventListener('click', function() {
        document.querySelectorAll('.nav-dropdown').forEach(d => {
            d.classList.remove('dropdown-open');
        });
        navLinks.classList.remove('nav-active');
        navToggle.classList.remove('active');
    });
});

document.addEventListener('click', function(event) {
    if (!event.target.closest('.nav-dropdown')) {
        document.querySelectorAll('.nav-dropdown').forEach(d => {
            d.classList.remove('dropdown-open');
        });
    }

    if (!navLinks.contains(event.target) && !navToggle.contains(event.target)) {
        navLinks.classList.remove('nav-active');
        navToggle.classList.remove('active');
    }
});
