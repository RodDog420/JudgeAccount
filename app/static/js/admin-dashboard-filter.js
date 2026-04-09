document.addEventListener('DOMContentLoaded', function() {
    const filterWrapper = document.getElementById('admin-dash-filter-container');
    const filterForm = document.getElementById('admin-dash-filter-form');
    const toggleBtn = document.getElementById('admin-dash-filter-toggle');
    const overlay = document.getElementById('admin-dash-filter-overlay');
    const closeBtn = document.getElementById('admin-dash-filter-close');

    if (!filterWrapper || !filterForm || !toggleBtn || !overlay) return;

    // Page load: start expanded, overlay hidden, toggle button hidden
    filterForm.classList.add('expanded');
    toggleBtn.classList.add('active');
    filterWrapper.classList.add('filter-open');

    // Scroll: if expanded, collapse and show overlay
    // Commented out per UX decision — auto-collapse on scroll disrupts workflow
    // Uncomment to restore auto-collapse behavior
    /*
    window.addEventListener('scroll', function() {
        if (filterForm.classList.contains('expanded')) {
            filterForm.classList.remove('expanded');
            filterForm.classList.add('collapsed');
            toggleBtn.classList.remove('active');
            overlay.classList.add('show');
            filterWrapper.classList.remove('filter-open');
        }
    });
    */

    function toggleFilter() {
        if (filterForm.classList.contains('expanded')) {
            filterForm.classList.remove('expanded');
            filterForm.classList.add('collapsed');
            toggleBtn.classList.remove('active');
            overlay.classList.add('show');
            filterWrapper.classList.remove('filter-open');
        } else {
            filterForm.classList.remove('collapsed');
            filterForm.classList.add('expanded');
            toggleBtn.classList.add('active');
            overlay.classList.remove('show');
            filterWrapper.classList.add('filter-open');
        }
    }

    toggleBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleFilter();
    });

    overlay.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleFilter();
    });

    if (closeBtn) {
        closeBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleFilter();
        });
    }
});
