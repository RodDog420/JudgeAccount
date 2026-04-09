document.addEventListener('DOMContentLoaded', function() {
    const filterWrapper = document.getElementById('index-filter-container');
    const filterForm = document.getElementById('index-filter-form');
    const toggleBtn = document.getElementById('index-filter-toggle');
    const overlay = document.getElementById('index-filter-overlay');
    const closeBtn = document.getElementById('index-filter-close');

    if (!filterWrapper || !filterForm || !toggleBtn || !overlay) return;

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
