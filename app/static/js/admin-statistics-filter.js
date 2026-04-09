document.addEventListener('DOMContentLoaded', function() {
    const filterWrapper = document.getElementById('stats-filter-container');
    const filterForm = document.getElementById('stats-filter-form');
    const toggleBtn = document.getElementById('filter-toggle-mobile');
    const overlay = document.getElementById('filter-overlay');

    if (!filterWrapper || !filterForm || !toggleBtn) return;

    let isMobile = window.innerWidth < 768;

    filterForm.classList.add('collapsed');
    toggleBtn.classList.remove('active');
    if (overlay) overlay.classList.add('show');

    window.addEventListener('scroll', function() {
        if (filterForm.classList.contains('expanded') || filterForm.classList.contains('initial-expanded')) {
            filterForm.classList.remove('expanded', 'initial-expanded');
            filterForm.classList.add('collapsed');
            toggleBtn.classList.remove('active');
            if (overlay) overlay.classList.add('show');
        }
    });

    function toggleFilter() {
        if (filterForm.classList.contains('expanded') || filterForm.classList.contains('initial-expanded')) {
            filterForm.classList.remove('expanded', 'initial-expanded');
            filterForm.classList.add('collapsed');
            toggleBtn.classList.remove('active');
            if (overlay) overlay.classList.add('show');
        } else {
            filterForm.classList.remove('collapsed');
            filterForm.classList.add('expanded');
            toggleBtn.classList.add('active');
            if (overlay) overlay.classList.remove('show');
        }
    }

    toggleBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleFilter();
    });

    if (overlay) {
        overlay.addEventListener('click', function(e) {
            e.stopPropagation();
            toggleFilter();
        });
    }

    window.addEventListener('resize', function() {
        isMobile = window.innerWidth < 768;

        if (!isMobile) {
            filterForm.classList.remove('expanded', 'collapsed', 'initial-expanded');
            toggleBtn.classList.remove('active');
            if (overlay) overlay.classList.remove('show');
        } else {
            filterForm.classList.add('initial-expanded');
            if (overlay) overlay.classList.remove('show');
        }
    });
});
