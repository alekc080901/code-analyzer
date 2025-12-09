let lastReport = '';
// Base API URL - use same hostname as the frontend to avoid CORS issues
const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8080`;

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
