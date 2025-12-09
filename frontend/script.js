// Base API URL
const API_BASE_URL = 'http://localhost:8000';

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
        resultDiv.classList.remove('hidden');

    } catch (error) {
        reportContent.textContent = error.message;
        resultDiv.classList.remove('hidden');
    } finally {
        loading.classList.add('hidden');
    }
}
