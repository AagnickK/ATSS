// Lock / unlock timetable entry
document.querySelectorAll('.lock-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        const res = await fetch(`/timetable/lock/${id}`, {
            method: 'POST',
            headers: { 'X-CSRFToken': document.cookie.match(/csrf_token=([^;]+)/)?.[1] || '' },
        });
        const data = await res.json();
        btn.textContent = data.locked ? '🔒' : '🔓';
        btn.closest('tr').classList.toggle('locked-row', data.locked);
    });
});

// Theme toggle
(function () {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('atss-theme', theme);
        btn.textContent = theme === 'dark' ? '☀ Light' : '◑ Dark';
    }

    const saved = localStorage.getItem('atss-theme') || 'dark';
    applyTheme(saved);

    btn.addEventListener('click', () => {
        const current = document.documentElement.getAttribute('data-theme');
        applyTheme(current === 'dark' ? 'light' : 'dark');
    });
})();
