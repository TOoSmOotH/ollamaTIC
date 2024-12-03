// RAG Management UI functionality

let currentTab = 'patterns';
let insightsData = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    fetchCollections();
    fetchInsights();
    setupEventListeners();
});

function setupEventListeners() {
    // Add event listeners for tab buttons
    document.querySelectorAll('.chart-tab').forEach(button => {
        button.addEventListener('click', () => {
            showTab(button.textContent.toLowerCase());
        });
    });
}

async function fetchCollections() {
    try {
        const response = await fetch('/api/agent/rag/collections');
        const collections = await response.json();
        
        // Update collections grid
        const grid = document.getElementById('collections-grid');
        grid.innerHTML = collections.map(collection => `
            <div class="stat-item">
                <h3>${collection.name}</h3>
                <p>Count: ${collection.count}</p>
                <p>Last Updated: ${new Date(collection.last_updated).toLocaleString()}</p>
            </div>
        `).join('');
        
        // Update collection selects
        ['collection-select', 'clean-collection-select', 'export-collection-select'].forEach(id => {
            const select = document.getElementById(id);
            select.innerHTML = '<option value="">Select Collection</option>' +
                collections.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
        });
    } catch (error) {
        console.error('Error fetching collections:', error);
        showError('Failed to fetch collections');
    }
}

async function searchCollection() {
    const collection = document.getElementById('collection-select').value;
    const query = document.getElementById('search-query').value;
    
    if (!collection || !query) {
        showError('Please select a collection and enter a search query');
        return;
    }
    
    try {
        const response = await fetch(`/api/agent/rag/search/${collection}?query=${encodeURIComponent(query)}`);
        const results = await response.json();
        
        const resultsContainer = document.getElementById('search-results');
        if (results.length === 0) {
            resultsContainer.innerHTML = '<p class="no-results">No results found</p>';
            return;
        }
        
        resultsContainer.innerHTML = results.map(result => `
            <div class="result-item">
                <div class="result-content">${formatContent(result.content)}</div>
                <div class="result-meta">
                    <span>Score: ${result.score.toFixed(3)}</span>
                    ${Object.entries(result.metadata).map(([key, value]) => 
                        `<span>${key}: ${formatValue(value)}</span>`
                    ).join('')}
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error searching collection:', error);
        showError('Failed to search collection');
    }
}

async function fetchInsights() {
    try {
        const response = await fetch('/api/insights');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        insightsData = await response.json();
        console.log('Fetched insights:', insightsData);  // Debug log
        showTab(currentTab);
    } catch (error) {
        console.error('Error fetching insights:', error);
        showError('Failed to fetch insights');
    }
}

function showTab(tab) {
    currentTab = tab;
    const content = document.getElementById('insights-content');
    
    // Update active tab
    document.querySelectorAll('.chart-tab').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.toLowerCase() === tab);
    });
    
    if (!insightsData) {
        content.innerHTML = '<p class="loading">Loading insights...</p>';
        return;
    }
    
    if (!Array.isArray(insightsData) || insightsData.length === 0) {
        content.innerHTML = '<p class="no-data">No insights available. Start using the system to generate insights.</p>';
        return;
    }
    
    let filteredInsights;
    switch (tab) {
        case 'patterns':
            filteredInsights = insightsData.filter(i => 
                i.pattern_type === 'import_pattern' || 
                i.pattern_type === 'function_pattern' ||
                i.pattern_type === 'best_practice'
            );
            renderPatterns(filteredInsights);
            break;
        case 'errors':
            filteredInsights = insightsData.filter(i => i.pattern_type === 'error_pattern');
            renderErrors(filteredInsights);
            break;
        case 'metrics':
            renderMetrics(insightsData);
            break;
    }
}

function renderPatterns(patterns) {
    const content = document.getElementById('insights-content');
    if (!patterns.length) {
        content.innerHTML = '<p class="no-data">No patterns found</p>';
        return;
    }

    // Group patterns by language
    const patternsByLanguage = patterns.reduce((acc, pattern) => {
        if (!acc[pattern.collection_name]) {
            acc[pattern.collection_name] = [];
        }
        acc[pattern.collection_name].push(pattern);
        return acc;
    }, {});

    content.innerHTML = Object.entries(patternsByLanguage).map(([language, langPatterns]) => `
        <div class="language-section">
            <h2>${language}</h2>
            <div class="pattern-grid">
                ${langPatterns.map(pattern => `
                    <div class="insight-card">
                        <h3>${formatPatternType(pattern.pattern_type)}</h3>
                        <div class="insight-stats">
                            <span>Frequency: ${pattern.frequency}</span>
                            <span>Success Rate: ${(pattern.success_rate * 100).toFixed(1)}%</span>
                        </div>
                        <div class="insight-examples">
                            ${pattern.examples.map(ex => `<pre><code>${ex}</code></pre>`).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
}

function renderErrors(errors) {
    const content = document.getElementById('insights-content');
    if (!errors.length) {
        content.innerHTML = '<p class="no-data">No errors found</p>';
        return;
    }

    // Group errors by language
    const errorsByLanguage = errors.reduce((acc, error) => {
        if (!acc[error.collection_name]) {
            acc[error.collection_name] = [];
        }
        acc[error.collection_name].push(error);
        return acc;
    }, {});

    content.innerHTML = Object.entries(errorsByLanguage).map(([language, langErrors]) => `
        <div class="language-section">
            <h2>${language}</h2>
            <div class="error-grid">
                ${langErrors.map(error => `
                    <div class="insight-card error">
                        <h3>Error Pattern</h3>
                        <div class="insight-stats">
                            <span>Frequency: ${error.frequency}</span>
                            <span>Last Seen: ${new Date(error.last_used).toLocaleString()}</span>
                        </div>
                        <div class="insight-examples">
                            ${error.examples.map(ex => `<pre><code>${ex}</code></pre>`).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `).join('');
}

function renderMetrics(insights) {
    const content = document.getElementById('insights-content');
    
    // Calculate metrics
    const totalPatterns = insights.filter(i => i.pattern_type !== 'error_pattern').length;
    const totalErrors = insights.filter(i => i.pattern_type === 'error_pattern').length;
    const avgSuccessRate = insights.reduce((sum, i) => sum + i.success_rate, 0) / insights.length;
    
    // Group by language
    const languageStats = insights.reduce((acc, i) => {
        if (!acc[i.collection_name]) {
            acc[i.collection_name] = {
                patterns: 0,
                errors: 0,
                successRate: 0,
                count: 0
            };
        }
        
        acc[i.collection_name].count++;
        acc[i.collection_name].successRate += i.success_rate;
        if (i.pattern_type === 'error_pattern') {
            acc[i.collection_name].errors++;
        } else {
            acc[i.collection_name].patterns++;
        }
        
        return acc;
    }, {});
    
    // Calculate averages
    Object.values(languageStats).forEach(stats => {
        stats.successRate = stats.successRate / stats.count;
    });
    
    content.innerHTML = `
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Total Patterns</h3>
                <div class="metric-value">${totalPatterns}</div>
            </div>
            <div class="metric-card">
                <h3>Total Errors</h3>
                <div class="metric-value">${totalErrors}</div>
            </div>
            <div class="metric-card">
                <h3>Average Success Rate</h3>
                <div class="metric-value">${(avgSuccessRate * 100).toFixed(1)}%</div>
            </div>
        </div>
        
        <h2>Language Statistics</h2>
        <div class="language-metrics-grid">
            ${Object.entries(languageStats).map(([language, stats]) => `
                <div class="language-metric-card">
                    <h3>${language}</h3>
                    <div class="metric-stats">
                        <div>Patterns: ${stats.patterns}</div>
                        <div>Errors: ${stats.errors}</div>
                        <div>Success Rate: ${(stats.successRate * 100).toFixed(1)}%</div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function formatPatternType(type) {
    return type.split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

async function cleanCollection() {
    const collection = document.getElementById('clean-collection-select').value;
    const olderThan = document.getElementById('older-than-days').value;
    const minScore = document.getElementById('min-score').value;
    
    if (!collection) {
        showError('Please select a collection to clean');
        return;
    }
    
    try {
        const response = await fetch(`/api/agent/rag/clean/${collection}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                older_than_days: olderThan ? parseInt(olderThan) : null,
                min_score: minScore ? parseFloat(minScore) : null
            })
        });
        
        if (response.ok) {
            showSuccess('Collection cleaned successfully');
            fetchCollections();
        } else {
            throw new Error('Failed to clean collection');
        }
    } catch (error) {
        console.error('Error cleaning collection:', error);
        showError('Failed to clean collection');
    }
}

async function exportCollection() {
    const collection = document.getElementById('export-collection-select').value;
    
    if (!collection) {
        showError('Please select a collection to export');
        return;
    }
    
    try {
        const response = await fetch(`/api/agent/rag/export/${collection}`);
        const data = await response.json();
        
        // Create and download file
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${collection}_export.json`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showSuccess('Collection exported successfully');
    } catch (error) {
        console.error('Error exporting collection:', error);
        showError('Failed to export collection');
    }
}

async function importCollection() {
    const fileInput = document.getElementById('import-file');
    fileInput.click();
}

// Helper functions
function formatContent(content) {
    // Handle different content types (code, text, etc.)
    if (typeof content === 'string') {
        if (content.includes('```')) {
            return content.replace(/```(\w*)\n([\s\S]*?)```/g, 
                (_, lang, code) => `<pre><code class="${lang}">${code}</code></pre>`
            );
        }
        return `<p>${content}</p>`;
    }
    return JSON.stringify(content, null, 2);
}

function formatValue(value) {
    if (typeof value === 'object') {
        return JSON.stringify(value);
    }
    if (typeof value === 'number') {
        return value.toFixed(value % 1 === 0 ? 0 : 3);
    }
    return value;
}

function showError(message) {
    // Implement error notification
    console.error(message);
    // You can add a toast/notification system here
}

function showSuccess(message) {
    // Implement success notification
    console.log(message);
    // You can add a toast/notification system here
}
