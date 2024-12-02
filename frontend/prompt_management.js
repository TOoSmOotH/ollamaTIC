document.addEventListener('DOMContentLoaded', () => {
    // Initialize CodeMirror editor
    const templateEditor = CodeMirror.fromTextArea(document.getElementById('template-editor'), {
        mode: 'markdown',
        theme: 'dracula',
        lineNumbers: true,
        lineWrapping: true
    });

    // Dark mode toggle
    const themeToggle = document.getElementById('theme-toggle');
    themeToggle.addEventListener('change', () => {
        document.body.classList.toggle('dark-mode');
        templateEditor.setOption('theme', document.body.classList.contains('dark-mode') ? 'dracula' : 'default');
    });

    // Template management
    const templatesList = document.getElementById('templates-list');
    const newTemplateBtn = document.getElementById('new-template-btn');
    const saveTemplateBtn = document.getElementById('save-template-btn');
    const previewBtn = document.getElementById('preview-btn');
    const templateName = document.getElementById('template-name');
    const variablesList = document.getElementById('variables-list');
    const addVariableBtn = document.getElementById('add-variable-btn');
    const previewPanel = document.querySelector('.preview-panel');
    const previewContent = document.getElementById('preview-content');

    let currentTemplate = null;

    // Add variable button
    addVariableBtn.addEventListener('click', () => {
        const varName = prompt('Enter variable name:');
        if (varName) {
            addVariableToPanel(varName);
        }
    });

    function addVariableToPanel(varName) {
        const varDiv = document.createElement('div');
        varDiv.className = 'variable-item';
        varDiv.innerHTML = `
            <span class="variable-name">${varName}</span>
            <button class="delete-var-btn">×</button>
        `;
        varDiv.querySelector('.delete-var-btn').addEventListener('click', () => varDiv.remove());
        variablesList.appendChild(varDiv);
    }

    // Preview button
    previewBtn.addEventListener('click', () => {
        const template = templateEditor.getValue();
        const variables = Array.from(variablesList.querySelectorAll('.variable-name')).map(span => span.textContent);
        const sampleValues = {};
        variables.forEach(v => sampleValues[v] = `[${v}]`);
        
        const preview = template.replace(/\{(\w+)\}/g, (match, key) => sampleValues[key] || match);
        previewContent.textContent = preview;
        previewPanel.style.display = 'block';
    });

    // Save template
    saveTemplateBtn.addEventListener('click', async () => {
        const template = {
            name: templateName.value,
            template: templateEditor.getValue(),
            variables: Array.from(variablesList.querySelectorAll('.variable-name')).map(span => span.textContent),
            model_id: 'default', // You might want to add a model selector
            priority: 1
        };

        const method = currentTemplate ? 'PUT' : 'POST';
        const url = currentTemplate ? `/agent/prompts/${currentTemplate.id}` : '/agent/prompts';

        try {
            const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(template)
            });

            if (response.ok) {
                await loadTemplates();
                clearEditor();
            } else {
                alert('Failed to save template');
            }
        } catch (error) {
            console.error('Error saving template:', error);
            alert('Failed to save template');
        }
    });

    // New template button
    newTemplateBtn.addEventListener('click', clearEditor);

    function clearEditor() {
        currentTemplate = null;
        templateName.value = '';
        templateEditor.setValue('');
        variablesList.innerHTML = '';
        previewPanel.style.display = 'none';
    }

    // Load and display templates
    async function loadTemplates() {
        try {
            const response = await fetch('/agent/prompts');
            if (response.ok) {
                const templates = await response.json();
                templatesList.innerHTML = '';
                
                templates.forEach(template => {
                    const li = document.createElement('li');
                    li.className = 'template-item';
                    li.innerHTML = `
                        <div class="template-info">
                            <h3>${template.name}</h3>
                            <p class="template-preview">${template.template.substring(0, 100)}...</p>
                            <p class="template-meta">Variables: ${template.variables.join(', ')}</p>
                        </div>
                        <div class="template-actions">
                            <button class="edit-btn">Edit</button>
                            <button class="delete-btn">Delete</button>
                        </div>
                    `;

                    // Edit button
                    li.querySelector('.edit-btn').addEventListener('click', () => {
                        currentTemplate = template;
                        templateName.value = template.name;
                        templateEditor.setValue(template.template);
                        variablesList.innerHTML = '';
                        template.variables.forEach(addVariableToPanel);
                    });

                    // Delete button
                    li.querySelector('.delete-btn').addEventListener('click', async () => {
                        if (confirm('Are you sure you want to delete this template?')) {
                            try {
                                const response = await fetch(`/agent/prompts/${template.id}`, {
                                    method: 'DELETE'
                                });
                                if (response.ok) {
                                    await loadTemplates();
                                } else {
                                    alert('Failed to delete template');
                                }
                            } catch (error) {
                                console.error('Error deleting template:', error);
                                alert('Failed to delete template');
                            }
                        }
                    });

                    templatesList.appendChild(li);
                });
            }
        } catch (error) {
            console.error('Error loading templates:', error);
        }
    }

    loadTemplates();
});
