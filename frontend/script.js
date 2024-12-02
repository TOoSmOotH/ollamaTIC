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

// Update stats display
async function updateStats() {
    try {
        // Fetch history data for token counts
        const historyResponse = await fetch('/api/v1/history');
        const historyData = await historyResponse.json();

        // Calculate total tokens from history data
        const totalTokens = historyData.reduce((sum, req) => sum + (req.tokens_used || 0), 0);
        const totalContextSize = historyData.reduce((sum, req) => sum + (req.context_size || 0), 0);
        const inputTokens = totalContextSize;
        const outputTokens = totalTokens - totalContextSize;
        
        // Update token counts
        document.getElementById('total-input-tokens').textContent = formatNumber(inputTokens);
        document.getElementById('total-output-tokens').textContent = formatNumber(outputTokens);
        
        // Calculate costs
        const claudeInputCost = (inputTokens / 1_000_000) * 3;    // $3 per million input tokens
        const claudeOutputCost = (outputTokens / 1_000_000) * 15;  // $15 per million output tokens
        const claudeTotalCost = claudeInputCost + claudeOutputCost;
        
        const gpt4InputCost = (inputTokens / 1_000_000) * 2.5;    // $2.50 per million input tokens
        const gpt4OutputCost = (outputTokens / 1_000_000) * 10;    // $10 per million output tokens
        const gpt4TotalCost = gpt4InputCost + gpt4OutputCost;
        
        const savings = claudeTotalCost - gpt4TotalCost;
        const savingsPercentage = claudeTotalCost > 0 ? (savings / claudeTotalCost) * 100 : 0;
        
        // Update costs display
        document.getElementById('claude-cost').textContent = `$${claudeTotalCost.toFixed(2)}`;
        document.getElementById('gpt4-cost').textContent = `$${gpt4TotalCost.toFixed(2)}`;
        document.getElementById('cost-saved').textContent = `$${savings.toFixed(2)}`;
        document.getElementById('savings-percent').textContent = 
            `(${savingsPercentage > 0 ? '+' : ''}${savingsPercentage.toFixed(1)}%)`;
        
    } catch (error) {
        console.error('Error updating stats:', error);
        // Set default values on error
        document.getElementById('total-input-tokens').textContent = '0';
        document.getElementById('total-output-tokens').textContent = '0';
        document.getElementById('claude-cost').textContent = '$0.00';
        document.getElementById('gpt4-cost').textContent = '$0.00';
        document.getElementById('cost-saved').textContent = '$0.00';
        document.getElementById('savings-percent').textContent = '(0%)';
    }
}

// Format numbers for display
function formatNumber(num) {
    return new Intl.NumberFormat().format(Math.round(num));
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
        const historyResponse = await fetch('/api/v1/history');
        const historyData = await historyResponse.json();

        // Update visualizations
        updateHistoryList(historyData);
        updateCharts(historyData);

        // Calculate and update token stats and costs
        updateTokenStats(historyData);

    } catch (error) {
        console.error('Error fetching data:', error);
        setDefaultStats();
    }
}

// Update token statistics and cost calculations
function updateTokenStats(historyData) {
    try {
        if (!Array.isArray(historyData)) {
            console.error('History data is not an array:', historyData);
            setDefaultStats();
            return;
        }

        // Calculate total tokens from history data
        const totalTokens = historyData.reduce((sum, req) => sum + (req.tokens_used || 0), 0);
        const totalContextSize = historyData.reduce((sum, req) => sum + (req.context_size || 0), 0);
        const inputTokens = totalContextSize;
        const outputTokens = totalTokens - totalContextSize;
        
        console.log('Token stats:', { inputTokens, outputTokens, totalTokens, totalContextSize });
        
        // Update token counts
        document.getElementById('total-input-tokens').textContent = formatNumber(inputTokens);
        document.getElementById('total-output-tokens').textContent = formatNumber(outputTokens);
        
        // Calculate costs
        const claudeInputCost = (inputTokens / 1_000_000) * 3;    // $3 per million input tokens
        const claudeOutputCost = (outputTokens / 1_000_000) * 15;  // $15 per million output tokens
        const claudeTotalCost = claudeInputCost + claudeOutputCost;
        
        const gpt4InputCost = (inputTokens / 1_000_000) * 2.5;    // $2.50 per million input tokens
        const gpt4OutputCost = (outputTokens / 1_000_000) * 10;    // $10 per million output tokens
        const gpt4TotalCost = gpt4InputCost + gpt4OutputCost;
        
        const savings = claudeTotalCost - gpt4TotalCost;
        const savingsPercentage = claudeTotalCost > 0 ? (savings / claudeTotalCost) * 100 : 0;
        
        console.log('Cost calculations:', {
            claudeInputCost,
            claudeOutputCost,
            claudeTotalCost,
            gpt4InputCost,
            gpt4OutputCost,
            gpt4TotalCost,
            savings,
            savingsPercentage
        });
        
        // Update costs display
        document.getElementById('claude-cost').textContent = `$${claudeTotalCost.toFixed(2)}`;
        document.getElementById('gpt4-cost').textContent = `$${gpt4TotalCost.toFixed(2)}`;
        document.getElementById('cost-saved').textContent = `$${savings.toFixed(2)}`;
        document.getElementById('savings-percent').textContent = 
            `(${savingsPercentage > 0 ? '+' : ''}${savingsPercentage.toFixed(1)}%)`;
        
    } catch (error) {
        console.error('Error updating token stats:', error);
        setDefaultStats();
    }
}

// Set default values for stats
function setDefaultStats() {
    document.getElementById('total-input-tokens').textContent = '0';
    document.getElementById('total-output-tokens').textContent = '0';
    document.getElementById('claude-cost').textContent = '$0.00';
    document.getElementById('gpt4-cost').textContent = '$0.00';
    document.getElementById('cost-saved').textContent = '$0.00';
    document.getElementById('savings-percent').textContent = '(0%)';
}

// Prompt Management
let editor;
let currentTemplate = null;
let templates = [];

function initializePromptManagement() {
    // Initialize CodeMirror
    editor = CodeMirror.fromTextArea(document.getElementById('template-editor'), {
        mode: 'markdown',
        theme: 'dracula',
        lineNumbers: true,
        lineWrapping: true,
        extraKeys: {"Ctrl-Space": "autocomplete"}
    });

    // Load templates
    loadTemplates();

    // Add event listeners
    document.getElementById('new-template-btn').addEventListener('click', createNewTemplate);
    document.getElementById('save-template-btn').addEventListener('click', saveTemplate);
    document.getElementById('preview-btn').addEventListener('click', togglePreview);
    document.getElementById('add-variable-btn').addEventListener('click', addVariable);

    // Add navigation listeners
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.dataset.view;
            showView(view);
        });
    });
}

function showView(viewName) {
    // Hide all views
    document.querySelectorAll('.view-container').forEach(view => {
        view.style.display = 'none';
    });
    
    // Show selected view
    document.getElementById(`${viewName}-view`).style.display = 'block';
    
    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === viewName);
    });

    // Refresh CodeMirror if showing prompts view
    if (viewName === 'prompts' && editor) {
        editor.refresh();
    }
}

async function loadTemplates() {
    try {
        const response = await fetch('/api/v1/agent/templates');
        if (response.ok) {
            templates = await response.json();
            renderTemplatesList();
        }
    } catch (error) {
        console.error('Error loading templates:', error);
    }
}

function renderTemplatesList() {
    const list = document.getElementById('templates-list');
    list.innerHTML = '';
    
    templates.forEach(template => {
        const li = document.createElement('li');
        li.className = 'template-item';
        li.innerHTML = `
            <div class="template-info">
                <h4>${template.name}</h4>
                <p>${template.description || ''}</p>
            </div>
            <div class="template-actions">
                <button class="secondary-btn edit-btn">Edit</button>
                <button class="secondary-btn delete-btn">Delete</button>
            </div>
        `;
        
        // Add event listeners
        li.querySelector('.edit-btn').addEventListener('click', () => editTemplate(template));
        li.querySelector('.delete-btn').addEventListener('click', () => deleteTemplate(template));
        
        list.appendChild(li);
    });
}

function createNewTemplate() {
    currentTemplate = null;
    document.getElementById('template-name').value = '';
    editor.setValue('');
    clearVariables();
    hidePreview();
}

function editTemplate(template) {
    currentTemplate = template;
    document.getElementById('template-name').value = template.name;
    editor.setValue(template.template);
    renderVariables(template.variables || []);
    hidePreview();
}

async function saveTemplate() {
    const name = document.getElementById('template-name').value;
    if (!name) {
        alert('Please enter a template name');
        return;
    }

    const template = {
        name,
        template: editor.getValue(),
        variables: getVariables(),
        model_id: '*',  // Apply to all models by default
    };

    try {
        const url = '/api/v1/agent/templates' + (currentTemplate ? `/${currentTemplate.id}` : '');
        const method = currentTemplate ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(template)
        });

        if (response.ok) {
            await loadTemplates();
            alert(`Template ${currentTemplate ? 'updated' : 'created'} successfully!`);
        }
    } catch (error) {
        console.error('Error saving template:', error);
        alert('Error saving template');
    }
}

async function deleteTemplate(template) {
    if (!confirm(`Are you sure you want to delete template "${template.name}"?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/v1/agent/templates/${template.id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadTemplates();
            if (currentTemplate && currentTemplate.id === template.id) {
                createNewTemplate();
            }
        }
    } catch (error) {
        console.error('Error deleting template:', error);
        alert('Error deleting template');
    }
}

function addVariable() {
    const variablesList = document.getElementById('variables-list');
    const variableItem = document.createElement('div');
    variableItem.className = 'variable-item';
    variableItem.innerHTML = `
        <input type="text" class="variable-name" placeholder="Variable name">
        <input type="text" class="variable-default" placeholder="Default value">
        <button class="secondary-btn remove-variable">×</button>
    `;
    
    variableItem.querySelector('.remove-variable').addEventListener('click', () => {
        variableItem.remove();
    });
    
    variablesList.appendChild(variableItem);
}

function getVariables() {
    const variables = [];
    document.querySelectorAll('.variable-item').forEach(item => {
        const name = item.querySelector('.variable-name').value;
        const defaultValue = item.querySelector('.variable-default').value;
        if (name) {
            variables.push({ name, default: defaultValue });
        }
    });
    return variables;
}

function renderVariables(variables) {
    clearVariables();
    variables.forEach(variable => {
        const variableItem = document.createElement('div');
        variableItem.className = 'variable-item';
        variableItem.innerHTML = `
            <input type="text" class="variable-name" value="${variable.name}" placeholder="Variable name">
            <input type="text" class="variable-default" value="${variable.default || ''}" placeholder="Default value">
            <button class="secondary-btn remove-variable">×</button>
        `;
        
        variableItem.querySelector('.remove-variable').addEventListener('click', () => {
            variableItem.remove();
        });
        
        document.getElementById('variables-list').appendChild(variableItem);
    });
}

function clearVariables() {
    document.getElementById('variables-list').innerHTML = '';
}

function togglePreview() {
    const previewPanel = document.querySelector('.preview-panel');
    const isVisible = previewPanel.style.display !== 'none';
    
    if (isVisible) {
        hidePreview();
    } else {
        showPreview();
    }
}

function showPreview() {
    const template = editor.getValue();
    const variables = getVariables();
    const preview = document.getElementById('preview-content');
    
    // Replace variables with their default values
    let previewText = template;
    variables.forEach(variable => {
        const regex = new RegExp(`\\{${variable.name}\\}`, 'g');
        previewText = previewText.replace(regex, variable.default || `[${variable.name}]`);
    });
    
    preview.textContent = previewText;
    document.querySelector('.preview-panel').style.display = 'block';
}

function hidePreview() {
    document.querySelector('.preview-panel').style.display = 'none';
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeCharts();
    fetchAndUpdateData();
    
    // Refresh data every 30 seconds
    setInterval(fetchAndUpdateData, 30000);
});
