let lastReport = '';
// Base API URL - use same hostname as the frontend to avoid CORS issues
const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8080`;
let reportsCache = [];

function persistReportsCache() {
    try {
        localStorage.setItem('reportsCache', JSON.stringify(reportsCache));
    } catch (e) {
        console.warn('Failed to persist reports cache', e);
    }
}

function loadReportsCacheFromStorage() {
    try {
        const raw = localStorage.getItem('reportsCache');
        if (raw) {
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed)) {
                reportsCache = parsed;
                return true;
            }
        }
    } catch (e) {
        console.warn('Failed to read reports cache', e);
    }
    return false;
}

function attachRefreshHandler() {
    const refreshBtn = document.getElementById('refreshReportsBtn');
    if (refreshBtn && !refreshBtn.dataset.bound) {
        refreshBtn.addEventListener('click', () => {
            console.log('Refresh clicked -> loadReports');
            loadReports();
        });
        refreshBtn.dataset.bound = 'true';
    }
}

function persistLastRepoUrl(url) {
    try {
        localStorage.setItem('lastRepoUrl', url);
    } catch (e) {
        console.warn('Failed to persist last repo url', e);
    }
}

function restoreLastRepoUrl() {
    try {
        const saved = localStorage.getItem('lastRepoUrl');
        if (saved) {
            const input = document.getElementById('repoUrl');
            if (input) {
                input.value = saved;
            }
        }
    } catch (e) {
        console.warn('Failed to restore last repo url', e);
    }
}

async function analyzeRepo() {
    const urlInput = document.getElementById('repoUrl');
    const loading = document.getElementById('loadingRepo');
    const resultDiv = document.getElementById('resultRepo');
    const reportContent = document.getElementById('reportContentRepo');

    const url = urlInput.value;
    if (!url) {
        alert("Please enter a URL");
        return;
    }

    // persist last used repo url
    persistLastRepoUrl(url);

    loading.classList.remove('hidden');
    resultDiv.classList.add('hidden');
    reportContent.textContent = '';

    try {
        const response = await fetch(`${API_BASE_URL}/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });

        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }

        const data = await response.json();
        reportContent.textContent = data.result || JSON.stringify(data, null, 2);
        lastReport = reportContent.textContent;
        resultDiv.classList.remove('hidden');

    } catch (error) {
        reportContent.textContent = error.message;
        lastReport = reportContent.textContent;
        resultDiv.classList.remove('hidden');
    } finally {
        loading.classList.add('hidden');
    }
}

async function loadReports() {
    console.log('loadReports invoked');
    const loading = document.getElementById('reportsLoading');
    const list = document.getElementById('reportsList');
    loading.classList.remove('hidden');
    list.textContent = '';

    // Show cached reports immediately if available
    const hadCached = loadReportsCacheFromStorage();
    if (hadCached && reportsCache.length > 0) {
        renderReports(list, reportsCache);
    }

    try {
        const response = await fetch(`${API_BASE_URL}/reports?limit=20`);
        if (!response.ok) {
            throw new Error(`Error: ${response.statusText}`);
        }
        const data = await response.json();
        reportsCache = data;
        persistReportsCache();
        renderReports(list, data);
    } catch (error) {
        // If fetch failed but we have cached data, keep showing it
        if (reportsCache.length > 0) {
            renderReports(list, reportsCache);
            list.appendChild(document.createTextNode(`\n(offline cache shown: ${error.message})`));
        } else {
            list.textContent = error.message;
        }
    } finally {
        loading.classList.add('hidden');
    }
}

function renderReports(list, data) {
    list.textContent = '';
    if (!Array.isArray(data) || data.length === 0) {
        list.textContent = 'No saved reports found.';
        return;
    }

    const normalized = normalizeReportsForDisplay(data);
    const frag = document.createDocumentFragment();
    normalized.forEach((item) => {
        const details = document.createElement('details');
        details.className = 'report-item';

        const summary = document.createElement('summary');
        summary.className = 'report-header';
        summary.textContent = `#${item.displayId} • ${item.repo_url || 'no repo url'} • ${item.status}`;

        const pre = document.createElement('pre');
        pre.className = 'report-body';
        pre.textContent = item.result || '';

        const actions = document.createElement('div');
        actions.className = 'report-actions';

        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'btn-danger';
        deleteBtn.textContent = 'Delete';
        deleteBtn.addEventListener('click', async (ev) => {
            ev.stopPropagation();
            await deleteReport(item.id);
        });

        actions.appendChild(deleteBtn);

        details.appendChild(summary);
        details.appendChild(actions);
        details.appendChild(pre);
        frag.appendChild(details);
    });

    list.appendChild(frag);
}

function normalizeReportsForDisplay(data) {
    // Sort descending by real id (newest first), then assign displayId in reverse (N..1)
    const sorted = [...data].sort((a, b) => (b.id ?? 0) - (a.id ?? 0));
    const total = sorted.length;
    return sorted.map((item, idx) => ({ ...item, displayId: total - idx }));
}

async function deleteReport(id) {
    try {
        const res = await fetch(`${API_BASE_URL}/report/${id}`, {
            method: 'DELETE',
        });
        if (!res.ok) {
            const text = await res.text();
            throw new Error(text || `Failed to delete report #${id}`);
        }
        // Update local cache and persist
        reportsCache = reportsCache.filter((r) => r.id !== id);
        persistReportsCache();

        // Re-render list
        const list = document.getElementById('reportsList');
        renderReports(list, reportsCache);
    } catch (e) {
        alert(e.message || 'Failed to delete report');
    }
}

// Auto-load reports and restore last repo URL on page load
window.addEventListener('DOMContentLoaded', () => {
    restoreLastRepoUrl();
    attachRefreshHandler();
    loadReports();
});

// In case DOMContentLoaded already fired before this script, try to bind once more.
attachRefreshHandler();

// Expose functions for inline onclick handlers
window.analyzeRepo = analyzeRepo;
window.loadReports = loadReports;
window.downloadReport = downloadReport;

function downloadReport() {
    if (!lastReport) {
        alert('No report to download. Run an analysis first.');
        return;
    }

    const formatSelect = document.getElementById('reportFormat');
    const format = formatSelect ? formatSelect.value : 'txt';
    let content = lastReport;
    let mime = 'text/plain';
    let ext = format;

    if (format === 'json') {
        mime = 'application/json';
        // Попробуем парсить, иначе сохраняем как строку
        try {
            content = JSON.stringify(JSON.parse(lastReport), null, 2);
        } catch (_) {
            // оставляем как есть
        }
    } else if (format === 'md') {
        mime = 'text/markdown';
    }

    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
