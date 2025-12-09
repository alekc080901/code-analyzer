async function analyzeRepo() {
    const urlInput = document.getElementById('repoUrl');
    const loading = document.getElementById('loading');
    const resultDiv = document.getElementById('result');
    const reportContent = document.getElementById('reportContent');

    const url = urlInput.value;
    if (!url) {
        alert("Please enter a URL");
        return;
    }

    loading.classList.remove('hidden');
    resultDiv.classList.add('hidden');
    reportContent.textContent = '';

    try {
        const response = await fetch('http://localhost:8000/analyze', {
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

