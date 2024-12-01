// Initialize charts
let durationChart, contextChart, tokenChart;
let totalInputTokens = 0;
let totalOutputTokens = 0;

// Theme toggle
document.getElementById('theme-toggle').addEventListener('change', function() {
    const body = document.body;
    if (this.checked) {
        body.classList.remove('light-mode');
        body.classList.add('dark-mode');
        updateChartsTheme('dark');
    } else {
        body.classList.remove('dark-mode');
        body.classList.add('light-mode');
        updateChartsTheme('light');
    }
});

function updateChartsTheme(theme) {
    const textColor = theme === 'dark' ? '#ffffff' : '#1a1a1a';
    const gridColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

    const chartConfig = {
        color: textColor,
        grid: {
            color: gridColor
        }
    };

    [durationChart, contextChart, tokenChart].forEach(chart => {
        if (chart) {
            chart.options.scales.x.ticks.color = textColor;
            chart.options.scales.y.ticks.color = textColor;
            chart.options.scales.x.grid.color = gridColor;
            chart.options.scales.y.grid.color = gridColor;
            chart.update();
        }
    });
}

// Initialize charts with empty data
function initializeCharts() {
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 750,
            easing: 'easeInOutQuart'
        },
        plugins: {
            legend: {
                display: false
            }
        },
        scales: {
            x: {
                grid: {
                    display: true
                }
            },
            y: {
                beginAtZero: true,
                grid: {
                    display: true
                }
            }
        }
    };

    // Duration Chart
    const durationCtx = document.getElementById('duration-chart').getContext('2d');
    durationChart = new Chart(durationCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Request Duration (s)',
                data: [],
                borderColor: '#3498db',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: chartOptions
    });

    // Context Size Chart
    const contextCtx = document.getElementById('context-chart').getContext('2d');
    contextChart = new Chart(contextCtx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Context Size',
                data: [],
                backgroundColor: '#2ecc71',
                borderColor: '#27ae60',
                borderWidth: 1
            }]
        },
        options: chartOptions
    });

    // Token Usage Chart
    const tokenCtx = document.getElementById('token-chart').getContext('2d');
    tokenChart = new Chart(tokenCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Tokens Used',
                data: [],
                borderColor: '#e74c3c',
                backgroundColor: 'rgba(231, 76, 60, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: chartOptions
    });

    // Set initial theme
    updateChartsTheme(document.body.classList.contains('dark-mode') ? 'dark' : 'light');
}

// Calculate cost savings
function calculateCostSavings(inputTokens, outputTokens) {
    const inputCost = (inputTokens / 1000000) * 3; // $3 per million input tokens
    const outputCost = (outputTokens / 1000000) * 15; // $15 per million output tokens
    return inputCost + outputCost;
}

// Format numbers for display
function formatNumber(num) {
    return new Intl.NumberFormat().format(num);
}

// Update stats display
function updateStats(inputTokens, outputTokens) {
    document.getElementById('total-input-tokens').textContent = formatNumber(inputTokens);
    document.getElementById('total-output-tokens').textContent = formatNumber(outputTokens);
    const costSaved = calculateCostSavings(inputTokens, outputTokens);
    document.getElementById('cost-saved').textContent = `$${costSaved.toFixed(2)}`;
}

// Format timestamp
function formatTimestamp(timestamp) {
    return new Date(timestamp).toLocaleTimeString();
}

// Update history list
function updateHistoryList(requests) {
    const historyList = document.getElementById('history-list');
    historyList.innerHTML = '';
    
    requests.forEach(request => {
        const listItem = document.createElement('li');
        listItem.innerHTML = `
            <strong>Model:</strong> ${request.model}<br>
            <strong>Tokens:</strong> ${formatNumber(request.tokens_used || 0)} |
            <strong>Context:</strong> ${formatNumber(request.context_size || 0)} |
            <strong>Duration:</strong> ${(request.total_duration || 0).toFixed(2)}s
        `;
        historyList.appendChild(listItem);
    });
}

// Update charts with new data
function updateCharts(requests) {
    const labels = requests.map((_, index) => `Request ${index + 1}`);
    const durations = requests.map(r => r.total_duration || 0);
    const contextSizes = requests.map(r => r.context_size || 0);
    const tokens = requests.map(r => r.tokens_used || 0);

    // Update duration chart
    durationChart.data.labels = labels;
    durationChart.data.datasets[0].data = durations;
    durationChart.update();

    // Update context size chart
    contextChart.data.labels = labels;
    contextChart.data.datasets[0].data = contextSizes;
    contextChart.update();

    // Update token usage chart
    tokenChart.data.labels = labels;
    tokenChart.data.datasets[0].data = tokens;
    tokenChart.update();
}

// Fetch and update all data
async function fetchAndUpdateData() {
    try {
        // Fetch request history
        const historyResponse = await fetch('/api/request_history');
        const historyData = await historyResponse.json();
        
        // Update UI with history data
        updateHistoryList(historyData);
        updateCharts(historyData);

        // Calculate total tokens from history data
        const totalTokens = historyData.reduce((sum, req) => sum + (req.tokens_used || 0), 0);
        const totalContextSize = historyData.reduce((sum, req) => sum + (req.context_size || 0), 0);
        totalInputTokens = totalContextSize;
        totalOutputTokens = totalTokens - totalContextSize;
        updateStats(totalInputTokens, totalOutputTokens);

        // Fetch average stats
        const statsResponse = await fetch('/api/average_stats');
        const statsData = await statsResponse.json();
        
        // Additional stats processing if needed
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeCharts();
    fetchAndUpdateData();
    // Refresh data every 30 seconds
    setInterval(fetchAndUpdateData, 30000);
});
