// Cache initialized server-rendered views so navigation does not reload the document.
(function () {
    const initialPage = document.querySelector('[data-app-view]');
    if (!initialPage) return;

    const cacheTtl = 5 * 60 * 1000;
    const pageCache = new Map();
    const inFlight = new Map();
    const appStore = window.appStore = {
        views: pageCache,
        inFlight,
        stats: { requests: 0, cacheHits: 0, deduplicatedRequests: 0 },
    };
    let activePage = initialPage;
    let activeKey = location.pathname + location.search;
    let navigationId = 0;
    let knownRevision = null;
    const loadingStatus = document.getElementById('app-navigation-status');

    pageCache.set(activeKey, {
        page: initialPage,
        title: document.title,
        initialized: true,
        lastUsed: Date.now(),
    });

    function pageKey(value) {
        const url = new URL(value, location.href);
        return url.pathname + url.search;
    }

    function parsePage(html) {
        const parsed = new DOMParser().parseFromString(html, 'text/html');
        const page = parsed.querySelector('[data-app-view]');
        if (!page) return null;
        return {
            page: document.importNode(page, true),
            title: parsed.title,
            initialized: false,
            lastUsed: Date.now(),
        };
    }

    function initializePage(record) {
        if (record.initialized) return;
        for (const inertScript of Array.from(record.page.querySelectorAll('script'))) {
            const script = document.createElement('script');
            for (const attribute of inertScript.attributes) {
                script.setAttribute(attribute.name, attribute.value);
            }
            if (!inertScript.src) {
                script.textContent = `(function(){\n${inertScript.textContent}\n})();`;
            }
            inertScript.remove();
            document.body.appendChild(script);
            if (!script.src) script.remove();
        }
        record.initialized = true;
    }

    async function fetchPage(url, key) {
        if (inFlight.has(key)) {
            appStore.stats.deduplicatedRequests += 1;
            return inFlight.get(key);
        }
        const pending = fetch(url, {
            credentials: 'same-origin',
            headers: { 'X-App-Navigation': '1' },
        }).then(async response => {
            if (!response.ok) throw new Error(`Navigation failed (${response.status}).`);
            const record = parsePage(await response.text());
            if (!record) throw new Error('The requested page is not an application view.');
            record.url = response.url;
            return record;
        });
        appStore.stats.requests += 1;
        inFlight.set(key, pending);
        try {
            return await pending;
        } finally {
            inFlight.delete(key);
        }
    }

    async function showPage(url, options = {}) {
        const target = new URL(url, location.href);
        if (target.origin !== location.origin) {
            location.assign(target.href);
            return;
        }
        const key = pageKey(target.href);
        if (!options.force && !options.record && key === activeKey) return;
        const requestId = ++navigationId;
        const sourcePath = new URL(activeKey, location.origin).pathname;
        const dashboardTimetableLoader = sourcePath === '/dashboard' && target.pathname === '/timetable'
            ? activePage.querySelector('#dashboard-timetable-loading')
            : null;
        let record = options.record || (options.force ? null : pageCache.get(key));
        if (options.force) pageCache.delete(key);
        if (record && !options.record && Date.now() - record.lastUsed > cacheTtl) {
            pageCache.delete(key);
            record = null;
        }
        if (!record) {
            dashboardTimetableLoader?.classList.remove('hidden');
            if (loadingStatus && !dashboardTimetableLoader) loadingStatus.classList.remove('hidden');
            activePage.setAttribute('aria-busy', 'true');
            try {
                record = await fetchPage(target.href, key);
            } catch (_error) {
                dashboardTimetableLoader?.classList.add('hidden');
                if (loadingStatus) loadingStatus.classList.add('hidden');
                location.assign(target.href);
                return;
            }
        } else {
            appStore.stats.cacheHits += 1;
        }
        if (requestId !== navigationId) {
            dashboardTimetableLoader?.classList.add('hidden');
            return;
        }

        dashboardTimetableLoader?.classList.add('hidden');
        record.lastUsed = Date.now();
        pageCache.set(key, record);
        activePage.replaceWith(record.page);
        activePage = record.page;
        activeKey = key;
        document.title = record.title;
        activePage.removeAttribute('aria-busy');
        if (loadingStatus) loadingStatus.classList.add('hidden');
        initializePage(record);
        if (options.history === 'replace') history.replaceState({}, '', target.href);
        else if (options.history !== false) history.pushState({}, '', target.href);
        window.scrollTo(0, 0);
    }

    function invalidateViews(paths) {
        for (const key of pageCache.keys()) {
            if (paths.has(new URL(key, location.origin).pathname)) pageCache.delete(key);
        }
    }

    function affectedViews(path) {
        if (path.startsWith('/faculty/')) return new Set(['/faculty', '/dashboard', '/timetable']);
        if (path.startsWith('/subjects/')) return new Set(['/subjects', '/dashboard', '/timetable']);
        if (path.startsWith('/rooms/')) return new Set(['/rooms', '/dashboard', '/timetable']);
        if (path === '/timetable/generate') return new Set(['/dashboard', '/timetable']);
        return null;
    }

    document.addEventListener('click', event => {
        const link = event.target.closest('a[data-app-nav]');
        if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        if (link.target || link.hasAttribute('download')) return;
        const target = new URL(link.href, location.href);
        if (target.origin !== location.origin) return;
        event.preventDefault();
        showPage(target.href);
    });

    document.addEventListener('submit', async event => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || event.defaultPrevented) return;
        const method = (form.method || 'GET').toUpperCase();
        const action = new URL(form.action || location.href, location.href);
        const affected = affectedViews(action.pathname);
        if (method !== 'POST' || !affected || action.origin !== location.origin || form.target) return;

        event.preventDefault();
        const requestId = ++navigationId;
        try {
            const response = await fetch(action.href, {
                method,
                body: new FormData(form),
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            const record = parsePage(await response.text());
            if (!record || !response.ok) throw new Error('The update could not be completed.');
            invalidateViews(affected);
            if (requestId !== navigationId) return;
            record.url = response.url;
            await showPage(response.url, { record, history: 'replace' });
            const revisionResponse = await fetch('/timetable/revision', {
                credentials: 'same-origin',
                headers: { Accept: 'application/json' },
            });
            if (revisionResponse.ok) knownRevision = (await revisionResponse.json()).revision;
        } catch (error) {
            if (requestId !== navigationId) return;
            invalidateViews(affected);
            window.alert(error.message || 'The update could not be completed.');
            await showPage(location.href, { force: true, history: false });
        }
    });

    window.addEventListener('popstate', () => showPage(location.href, { history: false }));

    async function checkDataRevision() {
        if (document.hidden) return;
        try {
            const response = await fetch('/timetable/revision', {
                credentials: 'same-origin',
                headers: { Accept: 'application/json' },
            });
            if (!response.ok) return;
            const data = await response.json();
            if (knownRevision === null) {
                knownRevision = data.revision;
                return;
            }
            if (knownRevision === data.revision) return;
            knownRevision = data.revision;
            for (const key of pageCache.keys()) {
                if (key !== activeKey) pageCache.delete(key);
            }
            await showPage(location.href, { force: true, history: false });
        } catch (_error) {
            // Leave cached pages available while offline.
        }
    }

    checkDataRevision();
    window.setInterval(checkDataRevision, 30000);
})();

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
