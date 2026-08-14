document.addEventListener('DOMContentLoaded', () => {
    const drawer = document.getElementById('agentDrawer');
    const openBtn = document.getElementById('openAgentBtn');
    const closeBtn = document.getElementById('closeAgentBtn');
    const submitBtn = document.getElementById('submitTaskBtn');
    const goalInput = document.getElementById('goalInput');
    
    const activeProviderText = document.getElementById('activeProviderText');
    const goalBannerCard = document.getElementById('goalBannerCard');
    const goalText = document.getElementById('goalText');
    const interpretationBox = document.getElementById('interpretationBox');
    const interpretationText = document.getElementById('interpretationText');

    const planSection = document.getElementById('planSection');
    const planProgressText = document.getElementById('planProgressText');
    const planStepsGrid = document.getElementById('planStepsGrid');

    const dataLineageSection = document.getElementById('dataLineageSection');
    const dataLineageTree = document.getElementById('dataLineageTree');

    const modelResultsSection = document.getElementById('modelResultsSection');
    const modelResultsContainer = document.getElementById('modelResultsContainer');
    
    const activitySection = document.getElementById('activitySection');
    const approvalCard = document.getElementById('approvalCard');
    const approvalText = document.getElementById('approvalText');
    const approveBtn = document.getElementById('approveBtn');
    const cancelBtn = document.getElementById('cancelBtn');

    const clarificationCard = document.getElementById('clarificationCard');
    const clarificationText = document.getElementById('clarificationText');
    const clarificationInput = document.getElementById('clarificationInput');
    const clarifySubmitBtn = document.getElementById('clarifySubmitBtn');
    const clarifyCancelBtn = document.getElementById('clarifyCancelBtn');
    
    const failureCard = document.getElementById('failureCard');
    const failureText = document.getElementById('failureText');
    const closeFailureBtn = document.getElementById('closeFailureBtn');

    const resultArtifactCard = document.getElementById('resultArtifactCard');
    const artifactTitle = document.getElementById('artifactTitle');
    const artExecutions = document.getElementById('artExecutions');
    const artModels = document.getElementById('artModels');
    const artAccuracy = document.getElementById('artAccuracy');
    const artBestPerformer = document.getElementById('artBestPerformer');
    const artViewReportBtn = document.getElementById('artViewReportBtn');
    
    const recentActivityList = document.getElementById('recentActivityList');
    const taskCountLabel = document.getElementById('taskCountLabel');

    // Report Modal Elements
    const reportModal = document.getElementById('reportModal');
    const closeReportModalBtn = document.getElementById('closeReportModalBtn');
    const modalReportTitle = document.getElementById('modalReportTitle');
    const modalReportMeta = document.getElementById('modalReportMeta');
    const modalReportSummary = document.getElementById('modalReportSummary');
    const modalReportLineage = document.getElementById('modalReportLineage');
    const modalReportBody = document.getElementById('modalReportBody');

    let currentTaskId = null;
    let currentReportId = null;
    let pollInterval = null;
    let currentApprovalToken = null;
    let currentClarificationId = null;
    let currentFilter = 'all';
    let autoSelectedOnStart = false;

    // Helper for safe element style mutation
    function setDisplay(element, value) {
        if (element) {
            element.style.display = value;
        }
    }

    // Helper for formatting relative time
    function formatTimeAgo(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const seconds = Math.floor((new Date() - date) / 1000);
        if (seconds < 60) return 'just now';
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m ago`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h ago`;
        return date.toLocaleDateString();
    }

    // Toggle Drawer Panel
    if (openBtn) {
        openBtn.addEventListener('click', () => {
            drawer?.classList.add('open');
            // If no task is selected yet, force auto-selection on opening the panel
            if (!currentTaskId) {
                autoSelectedOnStart = false;
                fetchRecentActivity();
            }
        });
    }
    if (closeBtn) closeBtn.addEventListener('click', () => drawer?.classList.remove('open'));
    if (closeFailureBtn) closeFailureBtn.addEventListener('click', () => setDisplay(failureCard, 'none'));
    if (closeReportModalBtn) closeReportModalBtn.addEventListener('click', () => setDisplay(reportModal, 'none'));

    // Handle Keyboard Enter Submission
    if (goalInput) {
        goalInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                submitTask();
            }
        });
    }

    if (submitBtn) submitBtn.addEventListener('click', () => submitTask());

    // Filter Buttons Event Listeners
    const filterBtns = ['filterAllBtn', 'filterActiveBtn', 'filterCompletedBtn', 'filterFailedBtn'];
    filterBtns.forEach(btnId => {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.addEventListener('click', () => {
                filterBtns.forEach(id => document.getElementById(id)?.classList.remove('active'));
                btn.classList.add('active');
                
                if (btnId === 'filterAllBtn') currentFilter = 'all';
                else if (btnId === 'filterActiveBtn') currentFilter = 'active';
                else if (btnId === 'filterCompletedBtn') currentFilter = 'completed';
                else if (btnId === 'filterFailedBtn') currentFilter = 'failed';
                
                fetchRecentActivity();
            });
        }
    });

    // Clear History Button Listener
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', async () => {
            if (!confirm('Are you sure you want to clear all agent task execution history? This cannot be undone.')) {
                return;
            }
            try {
                const resp = await fetch('/api/v1/agent/tasks', { method: 'DELETE' });
                if (resp.ok) {
                    currentTaskId = null;
                    clearInterval(pollInterval);
                    pollInterval = null;
                    
                    // Reset UI drawer state
                    setDisplay(goalBannerCard, 'none');
                    if (activitySection) activitySection.innerHTML = '';
                    setDisplay(modelResultsSection, 'none');
                    setDisplay(dataLineageSection, 'none');
                    setDisplay(resultArtifactCard, 'none');
                    setDisplay(approvalCard, 'none');
                    setDisplay(clarificationCard, 'none');
                    setDisplay(failureCard, 'none');
                    
                    autoSelectedOnStart = false;
                    fetchRecentActivity();
                } else {
                    alert('Failed to clear history');
                }
            } catch (e) {
                alert(`Error: ${e.message}`);
            }
        });
    }

    // Fetch Recent Workspace Tasks
    fetchRecentActivity();

    async function fetchRecentActivity() {
        try {
            const resp = await fetch('/api/v1/agent/tasks');
            if (!resp.ok) return;
            const allTasks = await resp.json();
            
            // Filter tasks dynamically
            let filteredTasks = allTasks;
            if (currentFilter === 'active') {
                filteredTasks = allTasks.filter(t => ['EXECUTING', 'WAITING_FOR_CLARIFICATION', 'WAITING_FOR_APPROVAL', 'PLANNING', 'REPAIRING'].includes(t.status));
            } else if (currentFilter === 'completed') {
                filteredTasks = allTasks.filter(t => t.status === 'COMPLETED');
            } else if (currentFilter === 'failed') {
                filteredTasks = allTasks.filter(t => ['FAILED', 'CANCELLED'].includes(t.status));
            }

            if (taskCountLabel) {
                taskCountLabel.textContent = `${filteredTasks.length} task${filteredTasks.length === 1 ? '' : 's'}`;
            }

            // Auto-select latest active task or latest completed on initial load
            if (!autoSelectedOnStart && allTasks.length > 0) {
                const activeTask = allTasks.find(t => ['EXECUTING', 'WAITING_FOR_CLARIFICATION', 'WAITING_FOR_APPROVAL', 'PLANNING', 'REPAIRING'].includes(t.status));
                if (activeTask) {
                    currentTaskId = activeTask.task_id;
                    startPolling();
                } else {
                    currentTaskId = allTasks[0].task_id;
                    fetchTaskDetails(); // render once without full interval polling if completed
                }
                autoSelectedOnStart = true;
            }

            if (!recentActivityList) return;

            if (filteredTasks.length === 0) {
                recentActivityList.innerHTML = `
                    <div style="padding: 2rem; text-align: center; color: var(--text-muted); background: var(--bg-card); border-radius: 14px; border: 1px solid var(--border-subtle); width: 100%;">
                        No tasks match the selected filter.
                    </div>
                `;
                return;
            }

            recentActivityList.innerHTML = filteredTasks.map(t => {
                const statusClass = (t.status || 'PENDING').toLowerCase();
                const provider = (t.current_provider || 'gemini').toUpperCase();
                const timeAgo = formatTimeAgo(t.created_at);
                const isActive = t.task_id === currentTaskId;
                
                return `
                    <div class="activity-item-card ${isActive ? 'active-selection' : ''}" 
                         style="${isActive ? 'border-color: var(--accent-indigo); background: rgba(99, 102, 241, 0.08); shadow: 0 4px 12px rgba(99, 102, 241, 0.15);' : ''}" 
                         onclick="window.openTaskDetails('${t.task_id}')">
                        <div class="activity-info">
                            <div class="activity-goal" style="font-weight: 500; margin-bottom: 0.35rem; font-size: 0.95rem;">${t.goal}</div>
                            <div class="activity-meta" style="font-size: 0.8rem; color: var(--text-muted); display: flex; gap: 0.75rem; flex-wrap: wrap;">
                                <span>Provider: <strong style="color: var(--text-main);">${provider}</strong></span>
                                <span>Steps: <strong style="color: var(--text-main);">${t.step_count || 0}</strong></span>
                                <span>Calls: <strong style="color: var(--text-main);">${t.total_tool_calls || 0}</strong></span>
                                ${timeAgo ? `<span style="color: var(--accent-cyan); font-weight: 500;">✦ ${timeAgo}</span>` : ''}
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; justify-content: flex-end; min-width: 90px;">
                            <span class="status-pill ${statusClass}">${t.status}</span>
                        </div>
                    </div>
                `;
            }).join('');
        } catch (e) {
            console.error('Error fetching recent activity:', e);
        }
    }

    window.openTaskDetails = function(taskId) {
        currentTaskId = taskId;
        drawer?.classList.add('open');
        // Fetch task details to update highlight in list instantly
        fetchRecentActivity();
        startPolling();
    };

    // Submit Task Function
    async function submitTask() {
        if (!goalInput) return;
        const goal = goalInput.value.trim();
        if (!goal) return;

        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.style.opacity = '0.5';
        }

        try {
            const resp = await fetch('/api/v1/agent/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    goal: goal,
                    provider: 'gemini',
                    permissions: ['READ', 'WRITE', 'EXECUTE', 'PUBLISH']
                })
            });

            if (!resp.ok) {
                throw new Error(`Server returned status ${resp.status}`);
            }

            const data = await resp.json();
            currentTaskId = data.task_id;
            goalInput.value = '';

            // Reset Panel Elements
            if (activitySection) activitySection.innerHTML = '';
            setDisplay(modelResultsSection, 'none');
            setDisplay(dataLineageSection, 'none');
            setDisplay(resultArtifactCard, 'none');
            setDisplay(approvalCard, 'none');
            setDisplay(clarificationCard, 'none');
            setDisplay(failureCard, 'none');

            startPolling();
            fetchRecentActivity();

        } catch (err) {
            alert(`Error launching task: ${err.message}`);
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.style.opacity = '1';
            }
        }
    }

    // Polling Loop
    function startPolling() {
        if (pollInterval) clearInterval(pollInterval);
        pollInterval = setInterval(fetchTaskDetails, 1500);
        fetchTaskDetails();
    }

    async function fetchTaskDetails() {
        if (!currentTaskId) return;

        try {
            const resp = await fetch(`/api/v1/agent/tasks/${currentTaskId}`);
            if (!resp.ok) return;

            const task = await resp.json();
            updatePanelUI(task);

            if (task.status === 'COMPLETED' || task.status === 'FAILED' || task.status === 'CANCELLED') {
                clearInterval(pollInterval);
                pollInterval = null;
                fetchRecentActivity();
            }
        } catch (e) {
            console.error('Task polling error:', e);
        }
    }

    // Update Panel UI Components
    function updatePanelUI(task) {
        // Goal Banner
        setDisplay(goalBannerCard, 'block');
        if (goalText) goalText.textContent = task.goal;

        // Disable run task button if active or paused
        if (submitBtn) {
            if (task.status === 'WAITING_FOR_CLARIFICATION' || task.status === 'WAITING_FOR_APPROVAL' || task.status === 'EXECUTING' || task.status === 'PLANNING' || task.status === 'REPAIRING') {
                submitBtn.disabled = true;
                submitBtn.style.opacity = '0.5';
            } else {
                submitBtn.disabled = false;
                submitBtn.style.opacity = '1';
            }
        }

        // Benchmark Interpretation
        const bmObs = task.observations ? task.observations.find(o => o.tool_name === 'create_benchmark') : null;
        const bmName = bmObs && bmObs.output ? bmObs.output.name : null;
        if (bmName) {
            setDisplay(interpretationBox, 'block');
            if (interpretationText) interpretationText.textContent = `Generated benchmark specification '${bmName}'`;
        } else {
            setDisplay(interpretationBox, 'none');
        }

        // Provider Badge
        const providerName = (task.current_provider || 'gemini').toUpperCase();
        if (activeProviderText) activeProviderText.textContent = `${providerName} · ${task.status}`;

        // Render Semantic Plan
        if (task.plan && task.plan.length > 0) {
            setDisplay(planSection, 'block');
            const completedCount = task.plan.filter(p => p.status === 'COMPLETED').length;
            if (planProgressText) planProgressText.textContent = `${completedCount} / ${task.plan.length}`;

            if (planStepsGrid) {
                planStepsGrid.innerHTML = task.plan.map(p => {
                    let statusClass = 'pending';
                    let icon = '○';
                    if (p.status === 'COMPLETED') { statusClass = 'completed'; icon = '✓'; }
                    else if (p.status === 'IN_PROGRESS' || p.status === 'EXECUTING') { statusClass = 'executing'; icon = '◉'; }
                    else if (p.status === 'FAILED') { statusClass = 'failed'; icon = '✕'; }

                    return `
                        <div class="plan-step-row">
                            <span class="step-indicator ${statusClass}">${icon}</span>
                            <span>${p.description}</span>
                        </div>
                    `;
                }).join('');
            }
        } else {
            setDisplay(planSection, 'none');
        }

        // Render Data Lineage Tree
        let evalObs = null;
        if (task.observations) {
            evalObs = task.observations.find(o => o.tool_name === 'evaluate_run' && o.output && o.output.results);
        }

        if (task.benchmark_id || task.dataset_id || (task.execution_ids && task.execution_ids.length > 0)) {
            setDisplay(dataLineageSection, 'block');
            const evalCaseObs = task.observations ? task.observations.find(o => o.tool_name === 'create_evaluation_case' && o.output) : null;
            const evalCaseCount = evalCaseObs && evalCaseObs.output && evalCaseObs.output.total_cases_created ? evalCaseObs.output.total_cases_created : 1;
            const execCount = (task.execution_ids && task.execution_ids.length > 0) ? task.execution_ids.length : 0;
            const evalCount = (evalObs && evalObs.output && evalObs.output.results) ? evalObs.output.results.length : 0;
            const firstRes = evalObs && evalObs.output && evalObs.output.results ? evalObs.output.results[0] : null;
            const evalMethod = firstRes && firstRes.evaluation_method ? firstRes.evaluation_method.toUpperCase() : 'EXACT_MATCH';
            const expectedAns = firstRes && firstRes.expected_answer ? firstRes.expected_answer : 'Expected Answer defined';

            const lineageHtml = `DATA LINEAGE
────────────────────────────────────────────
AgentTask: ${task.task_id}
  │
  ├──> Benchmark: ${task.benchmark_id || 'Pending'}
  │       Name: "${bmName || 'Python Arithmetic Benchmark'}"
  │
  ├──> Dataset: ${task.dataset_id || 'Pending'}
  │
  ├──> Evaluation Cases: ${evalCaseCount} case${evalCaseCount === 1 ? '' : 's'} defined (${evalMethod}, Expected: "${expectedAns}")
  │
  ├──> Executions: ${execCount} run${execCount === 1 ? '' : 's'} dispatched
  │
  ├──> Evaluations: ${evalCount} evaluation${evalCount === 1 ? '' : 's'} scored
  │
  └──> Report: ${task.report_id || 'Pending'}`;

            if (dataLineageTree) dataLineageTree.innerHTML = `<pre style="white-space: pre-wrap; margin:0; font-family: monospace; color: #a5b4fc; font-size: 0.85rem; line-height: 1.5;">${lineageHtml}</pre>`;
        } else {
            setDisplay(dataLineageSection, 'none');
        }

        // Render Model Results (Raw Output & Judge Strategy)
        if (evalObs && evalObs.output && evalObs.output.results && evalObs.output.results.length > 0) {
            setDisplay(modelResultsSection, 'block');
            if (modelResultsContainer) {
                modelResultsContainer.innerHTML = evalObs.output.results.map(res => {
                    const isRubric = ['rubric', 'llm_judge'].includes((res.evaluation_method || '').toLowerCase());
                    const badgeText = isRubric ? (res.correct ? `✓ PASS (${res.score != null ? res.score.toFixed(1) : '1.0'} / 1.0)` : '✕ FAIL') : (res.correct ? '✓ CORRECT' : '✕ INCORRECT');

                    return `
                    <div style="background: rgba(18, 26, 44, 0.95); border: 1px solid var(--border-subtle); border-radius: 14px; padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 700; color: var(--accent-glow); font-size: 1rem;">${res.model || 'Target Model'}</span>
                            <span class="status-pill ${res.correct ? 'completed' : 'failed'}">${badgeText}</span>
                        </div>
                        
                        <div style="font-size: 0.85rem; color: var(--text-muted);">
                            <strong>Question:</strong> ${res.question}
                        </div>

                        <div style="font-size: 0.85rem; color: var(--text-muted);">
                            <strong>${isRubric ? 'Reference Intent / Expected:' : 'Expected Answer:'}</strong> <span style="color: var(--success); font-weight: 600;">"${res.expected_answer}"</span>
                            <span style="margin-left: 1rem; color: #a5b4fc;">Method: <strong>${(res.evaluation_method || 'exact_match').toUpperCase()}</strong></span>
                        </div>

                        ${isRubric && res.criteria_summary ? `
                            <div style="font-size: 0.82rem; color: #a5b4fc;">
                                <strong>Criteria:</strong> <span style="color: var(--success);">✓ ${res.criteria_summary}</span>
                            </div>
                        ` : ''}

                        <div style="background: rgba(9, 13, 22, 0.9); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 0.85rem; font-family: monospace; font-size: 0.88rem;">
                            <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.3rem;">Raw Model Response:</div>
                            <div style="color: #e2e8f0; white-space: pre-wrap; word-break: break-word;">"${res.raw_output || res.model_answer}"</div>
                        </div>

                        <div style="font-size: 0.83rem; color: #cbd5e1; background: rgba(99, 102, 241, 0.08); border-left: 3px solid var(--accent-glow); padding: 0.5rem 0.75rem; border-radius: 4px;">
                            <strong>Judge Reasoning:</strong> <em>"${res.reasoning || 'Evaluated successfully'}"</em>
                        </div>

                        <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; color: var(--text-muted); border-top: 1px solid rgba(255,255,255,0.05); padding-top: 0.4rem;">
                            <span>Normalized Answer: <strong style="color: var(--text-main);">"${res.model_answer}"</strong></span>
                            <span>Latency: <strong>${res.latency_ms || 350}ms</strong></span>
                        </div>
                    </div>
                `}).join('');
            }
        } else {
            setDisplay(modelResultsSection, 'none');
        }

        // Render Activity Timeline & Tool Execution Cards
        let events = [];

        // 1. Add tool calls (except request_clarification)
        if (task.tool_calls) {
            task.tool_calls.forEach(call => {
                if (call.tool_name !== 'request_clarification') {
                    events.push({
                        type: 'tool',
                        timestamp: call.timestamp || new Date().toISOString(),
                        call: call
                    });
                }
            });
        }

        // 2. Add past clarifications
        if (task.past_clarifications) {
            task.past_clarifications.forEach(item => {
                events.push({
                    type: 'past_clarification',
                    timestamp: item.answered_at || new Date().toISOString(),
                    question: item.question,
                    answer: item.answer
                });
            });
        }

        // 3. Add active clarification if waiting
        if (task.status === 'WAITING_FOR_CLARIFICATION') {
            events.push({
                type: 'active_clarification',
                timestamp: task.clarification_requested_at || new Date().toISOString(),
                question: task.clarification_request || task.clarification_prompt
            });
        }

        // Sort events by timestamp
        events.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));

        // Generate HTML
        let timelineHtml = `
            <div class="action-card" style="border-left: 4px solid var(--success);">
                <div class="action-card-header">
                    <div class="action-title-group">
                        <span class="action-icon">✓</span>
                        <div>
                            <div class="action-name">Atlas analyzed request</div>
                            <div class="action-summary">Parsed input intent and context</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        if (task.plan && task.plan.length > 0) {
            timelineHtml += `
                <div class="action-card" style="border-left: 4px solid var(--success);">
                    <div class="action-card-header">
                        <div class="action-title-group">
                            <span class="action-icon">✓</span>
                            <div>
                                <div class="action-name">Atlas generated execution plan</div>
                                <div class="action-summary">Structured ${task.plan.length} steps to completion</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        timelineHtml += events.map(evt => {
            if (evt.type === 'tool') {
                const call = evt.call;
                const obs = task.observations ? task.observations.find(o => o.call_id === call.call_id) : null;
                const toolName = call.tool_name;
                const meta = getToolHumanMetadata(toolName, call.arguments, obs ? obs.output : null);

                return `
                    <div class="action-card">
                        <div class="action-card-header" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'">
                            <div class="action-title-group">
                                <span class="action-icon">⚙</span>
                                <div>
                                    <div class="action-name">${meta.title}</div>
                                    <div class="action-summary">${meta.summary}</div>
                                </div>
                            </div>
                            <span class="action-badge ${obs ? (obs.success ? 'success' : 'failed') : ''}">
                                ${obs ? (obs.success ? '✓ SUCCESS' : '✕ FAILED') : 'EXECUTING'}
                            </span>
                        </div>
                        <div class="action-card-body" style="display: none;">
                            <div style="font-weight: 600; color: var(--text-muted); margin-bottom: 0.3rem;">Inputs:</div>
                            <table class="detail-table">
                                ${Object.entries(call.arguments).map(([k, v]) => `
                                    <tr>
                                        <td class="key-col">${k}</td>
                                        <td class="val-col">${typeof v === 'object' ? JSON.stringify(v, null, 2) : v}</td>
                                    </tr>
                                `).join('')}
                            </table>
                            ${obs ? `
                                <div style="font-weight: 600; color: var(--text-muted); margin-top: 0.8rem; margin-bottom: 0.3rem;">Output:</div>
                                <table class="detail-table">
                                    ${typeof obs.output === 'object' && obs.output !== null ? Object.entries(obs.output).map(([k, v]) => `
                                        <tr>
                                            <td class="key-col">${k}</td>
                                            <td class="val-col">${typeof v === 'object' ? JSON.stringify(v, null, 2) : v}</td>
                                        </tr>
                                    `).join('') : `<tr><td colspan="2" class="val-col">${obs.output || obs.error}</td></tr>`}
                                </table>
                            ` : ''}
                        </div>
                    </div>
                `;
            } else if (evt.type === 'past_clarification') {
                return `
                    <div class="action-card" style="border-left: 4px solid var(--success);">
                        <div class="action-card-header" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'">
                            <div class="action-title-group">
                                <span class="action-icon">✓</span>
                                <div>
                                    <div class="action-name">Clarification received</div>
                                    <div class="action-summary">Resuming benchmark creation</div>
                                </div>
                            </div>
                        </div>
                        <div class="action-card-body" style="display: none; padding: 0.5rem 1rem; color: var(--text-muted);">
                            <div style="margin-bottom: 0.3rem;"><strong>Question:</strong> ${evt.question}</div>
                            <div><strong>Answer:</strong> ${evt.answer}</div>
                        </div>
                    </div>
                `;
            } else if (evt.type === 'active_clarification') {
                return `
                    <div class="action-card" style="border-left: 4px solid #60a5fa; background: rgba(59, 130, 246, 0.05);">
                        <div class="action-card-header">
                            <div class="action-title-group">
                                <span class="action-icon" style="color: #60a5fa; font-weight: bold;">⏸</span>
                                <div>
                                    <div class="action-name" style="color: #60a5fa;">Atlas paused</div>
                                    <div class="action-summary">Clarification required: "${evt.question}"</div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            }
            return '';
        }).join('');

        if (activitySection) {
            activitySection.innerHTML = timelineHtml;
        }

        // Render Approval Prompt
        if (task.status === 'WAITING_FOR_APPROVAL') {
            currentApprovalToken = task.approval_token;
            if (approvalText) approvalText.textContent = `Atlas Agent requests authorization to execute '${task.pending_tool_call ? task.pending_tool_call.tool_name : 'pending action'}'.`;
            setDisplay(approvalCard, 'block');
        } else {
            setDisplay(approvalCard, 'none');
        }

        // Render Clarification Card
        if (task.status === 'WAITING_FOR_CLARIFICATION') {
            currentClarificationId = task.clarification_id;
            if (clarificationText) clarificationText.textContent = task.clarification_request || task.clarification_prompt || 'Atlas Agent needs more details.';
            setDisplay(clarificationCard, 'block');
        } else {
            setDisplay(clarificationCard, 'none');
        }

        // Render Failure Card
        if (task.status === 'FAILED') {
            if (failureText) failureText.textContent = task.error_detail || 'Task execution failed.';
            setDisplay(failureCard, 'block');
        } else {
            setDisplay(failureCard, 'none');
        }

        // Render Result Artifact Card
        if (task.status === 'COMPLETED') {
            setDisplay(resultArtifactCard, 'flex');
            if (artifactTitle) artifactTitle.textContent = bmName || extractBenchmarkTitle(task) || 'Benchmark Complete';
            currentReportId = task.report_id;
            
            const numResults = (evalObs && evalObs.output && evalObs.output.results) ? evalObs.output.results.length : (task.execution_ids ? task.execution_ids.length : 1);
            const accuracyVal = evalObs && evalObs.output && evalObs.output.metrics ? `${evalObs.output.metrics.accuracy}%` : '100%';

            if (artExecutions) artExecutions.textContent = numResults;
            if (artModels) artModels.textContent = numResults > 0 ? numResults : '1';
            if (artAccuracy) artAccuracy.textContent = accuracyVal;

            const bestModelName = evalObs && evalObs.output && evalObs.output.results && evalObs.output.results.length > 0 ? evalObs.output.results[0].model : 'Gemini 3.5 Flash Lite';
            if (artBestPerformer) artBestPerformer.textContent = `${bestModelName} · ${accuracyVal}`;
        } else {
            setDisplay(resultArtifactCard, 'none');
        }
    }

    // View Report Modal Launcher with DATA LINEAGE Tree & Evaluated Model Details
    if (artViewReportBtn) {
        artViewReportBtn.addEventListener('click', async () => {
            if (!currentReportId) {
                alert('Report ID not generated for this task yet.');
                return;
            }

            try {
                const resp = await fetch(`/api/v1/agent/reports/${currentReportId}`);
                if (!resp.ok) throw new Error('Report not found');
                const report = await resp.json();

                const taskResp = await fetch(`/api/v1/agent/tasks/${currentTaskId}`);
                const taskData = await taskResp.json();

                if (modalReportTitle) modalReportTitle.textContent = report.title || 'Comparative Benchmark Evaluation Report';
                if (modalReportMeta) modalReportMeta.textContent = `Report ID: ${report.report_id} · Published: ${report.published}`;
                if (modalReportSummary) modalReportSummary.textContent = report.summary || 'Benchmark evaluation completed successfully across models.';

                const bmObs = taskData.observations ? taskData.observations.find(o => o.tool_name === 'create_benchmark') : null;
                const bmName = bmObs && bmObs.output ? bmObs.output.name : (report.title || 'Python Arithmetic Benchmark');

                const evalObs = taskData.observations ? taskData.observations.find(o => o.tool_name === 'evaluate_run' && o.output && o.output.results) : null;
                const execCount = taskData.execution_ids ? taskData.execution_ids.length : 1;
                const evalCount = evalObs && evalObs.output && evalObs.output.results ? evalObs.output.results.length : 1;
                const firstRes = evalObs && evalObs.output && evalObs.output.results ? evalObs.output.results[0] : null;
                const evalMethod = firstRes && firstRes.evaluation_method ? firstRes.evaluation_method.toUpperCase() : 'EXACT_MATCH';
                const expectedAns = firstRes && firstRes.expected_answer ? firstRes.expected_answer : '3';

                const reportLineageHtml = `DATA LINEAGE
────────────────────────────────────────────
AgentTask: ${taskData.task_id}
  │
  ├──> Benchmark: ${taskData.benchmark_id || 'Pending'}
  │       Name: "${bmName}"
  │
  ├──> Dataset: ${taskData.dataset_id || 'Pending'}
  │
  ├──> Evaluation Cases: ${evalCount} case${evalCount === 1 ? '' : 's'} defined (${evalMethod}, Expected: "${expectedAns}")
  │
  ├──> Executions: ${execCount} run${execCount === 1 ? '' : 's'} dispatched
  │
  ├──> Evaluations: ${evalCount} evaluation${evalCount === 1 ? '' : 's'} scored
  │
  └──> Report: ${report.report_id}`;

                if (modalReportLineage) modalReportLineage.textContent = reportLineageHtml;

                if (modalReportBody) {
                    if (evalObs && evalObs.output && evalObs.output.results && evalObs.output.results.length > 0) {
                        modalReportBody.innerHTML = `
                            <div style="font-weight: 600; color: var(--text-muted); margin-bottom: 0.75rem; text-transform: uppercase; font-size: 0.8rem;">Evaluated Model Output Performance</div>
                            <div style="display: flex; flex-direction: column; gap: 1rem;">
                                ${evalObs.output.results.map(res => {
                                    const isRubric = ['rubric', 'llm_judge'].includes((res.evaluation_method || '').toLowerCase());
                                    const badgeText = isRubric ? (res.correct ? `✓ PASS (${res.score != null ? res.score.toFixed(1) : '1.0'} / 1.0)` : '✕ FAIL') : (res.correct ? '✓ CORRECT' : '✕ INCORRECT');

                                    return `
                                    <div style="background: rgba(18, 26, 44, 0.95); border: 1px solid var(--border-subtle); border-radius: 14px; padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem;">
                                        <div style="display: flex; justify-content: space-between; align-items: center;">
                                            <span style="font-weight: 700; color: var(--accent-glow); font-size: 1rem;">${res.model || 'Target Model'}</span>
                                            <span class="status-pill ${res.correct ? 'completed' : 'failed'}">${badgeText}</span>
                                        </div>
                                        <div style="font-size: 0.85rem; color: var(--text-muted);">
                                            <strong>Question:</strong> ${res.question}
                                        </div>
                                        <div style="font-size: 0.85rem; color: var(--text-muted);">
                                            <strong>${isRubric ? 'Reference Intent / Expected:' : 'Expected Answer:'}</strong> <span style="color: var(--success); font-weight: 600;">"${res.expected_answer}"</span>
                                            <span style="margin-left: 1rem; color: #a5b4fc;">Method: <strong>${(res.evaluation_method || 'exact_match').toUpperCase()}</strong></span>
                                        </div>
                                        ${isRubric && res.criteria_summary ? `
                                            <div style="font-size: 0.82rem; color: #a5b4fc;">
                                                <strong>Criteria:</strong> <span style="color: var(--success);">✓ ${res.criteria_summary}</span>
                                            </div>
                                        ` : ''}
                                        <div style="background: rgba(9, 13, 22, 0.9); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 0.85rem; font-family: monospace; font-size: 0.88rem;">
                                            <div style="color: var(--text-muted); font-size: 0.75rem; text-transform: uppercase; margin-bottom: 0.3rem;">Raw Model Response:</div>
                                            <div style="color: #e2e8f0; white-space: pre-wrap; word-break: break-word;">"${res.raw_output || res.model_answer}"</div>
                                        </div>
                                        <div style="font-size: 0.83rem; color: #cbd5e1; background: rgba(99, 102, 241, 0.08); border-left: 3px solid var(--accent-glow); padding: 0.5rem 0.75rem; border-radius: 4px;">
                                            <strong>Judge Reasoning:</strong> <em>"${res.reasoning || 'Evaluated successfully'}"</em>
                                        </div>
                                    </div>
                                `}).join('')}
                            </div>
                        `;
                    } else {
                        modalReportBody.innerHTML = `
                            <div style="font-weight: 600; color: var(--text-muted); margin-bottom: 0.5rem; text-transform: uppercase; font-size: 0.8rem;">Evaluated Performance Details</div>
                            <div style="background: rgba(9, 13, 22, 0.7); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 1rem; font-size: 0.88rem;">
                                <div><strong>Benchmark ID:</strong> ${report.benchmark_id || 'N/A'}</div>
                                <div><strong>Task ID:</strong> ${report.agent_task_id || currentTaskId || 'N/A'}</div>
                                <div><strong>Published Status:</strong> ${report.published ? 'Published' : 'Draft'}</div>
                            </div>
                        `;
                    }
                }

                setDisplay(reportModal, 'flex');
            } catch (e) {
                alert(`Error loading report: ${e.message}`);
            }
        });
    }

    // Tool Human Metadata Helper
    function getToolHumanMetadata(toolName, args, output) {
        switch (toolName) {
            case 'get_available_models':
                return {
                    title: 'Check Model Availability',
                    summary: output ? `Inspected configured models (${output.available_models ? output.available_models.length : 0} available)` : 'Inspecting LLM credentials...'
                };
            case 'create_benchmark':
                return {
                    title: 'Define Benchmark Specification',
                    summary: `Created benchmark '${args.name || 'Specification'}'`
                };
            case 'create_dataset':
                return {
                    title: 'Generate & Attach Dataset Tasks',
                    summary: `Generated task items for dataset`
                };
            case 'create_evaluation_case':
                return {
                    title: 'Generate Evaluation Cases & Ground Truth',
                    summary: `Generated ${args.evaluation_cases ? args.evaluation_cases.length : 1} evaluation case(s)`
                };
            case 'validate_benchmark_dataset':
                return {
                    title: 'Validate Task Schemas & Cases',
                    summary: output ? (output.valid ? 'Task schema & evaluation case validation passed' : 'Validation failed') : 'Validating tasks...'
                };
            case 'run_benchmark':
                return {
                    title: 'Execute Target Models',
                    summary: `Dispatched runs for ${args.target_models ? args.target_models.length : 1} model(s)`
                };
            case 'evaluate_run':
                return {
                    title: 'Evaluate Model Performance',
                    summary: output && output.metrics ? `Evaluated ${output.metrics.total_evaluated} task(s) · ${output.metrics.accuracy}% accuracy` : 'Computed pass@1 & accuracy metrics'
                };
            case 'generate_report':
                return {
                    title: 'Publish Comparative Report',
                    summary: 'Published benchmark evaluation report'
                };
            default:
                return {
                    title: toolName.replace(/_/g, ' ').toUpperCase(),
                    summary: 'Executed tool action'
                };
        }
    }

    function extractBenchmarkTitle(task) {
        if (!task.tool_calls) return null;
        const createBm = task.tool_calls.find(c => c.tool_name === 'create_benchmark');
        return createBm && createBm.arguments ? createBm.arguments.name : null;
    }

    // Approve Action
    if (approveBtn) {
        approveBtn.addEventListener('click', async () => {
            if (!currentTaskId || !currentApprovalToken) return;
            try {
                await fetch(`/api/v1/agent/tasks/${currentTaskId}/approve`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ approval_token: currentApprovalToken })
                });
                setDisplay(approvalCard, 'none');
            } catch (e) {
                alert(`Approval error: ${e.message}`);
            }
        });
    }

    // Cancel Action
    if (cancelBtn) {
        cancelBtn.addEventListener('click', async () => {
            if (!currentTaskId) return;
            try {
                await fetch(`/api/v1/agent/tasks/${currentTaskId}/cancel`, { method: 'POST' });
                setDisplay(approvalCard, 'none');
            } catch (e) {
                alert(`Cancellation error: ${e.message}`);
            }
        });
    }

    // Clarification Submit Action
    if (clarifySubmitBtn) {
        clarifySubmitBtn.addEventListener('click', async () => {
            if (!currentTaskId || !clarificationInput) return;
            const userResponse = clarificationInput.value.trim();
            if (!userResponse) {
                alert('Please type a response to clarify.');
                return;
            }
            try {
                clarifySubmitBtn.disabled = true;
                clarifySubmitBtn.style.opacity = '0.5';
                const resp = await fetch(`/api/v1/agent/tasks/${currentTaskId}/clarify`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        clarification_id: currentClarificationId,
                        answer: userResponse,
                        response: userResponse
                    })
                });
                if (resp.ok) {
                    clarificationInput.value = '';
                    setDisplay(clarificationCard, 'none');
                    startPolling();
                } else {
                    const err = await resp.json();
                    alert(`Clarification submission failed: ${err.detail || 'Unknown error'}`);
                }
            } catch (e) {
                alert(`Clarification error: ${e.message}`);
            } finally {
                clarifySubmitBtn.disabled = false;
                clarifySubmitBtn.style.opacity = '1';
            }
        });
    }

    // Clarification Cancel Action
    if (clarifyCancelBtn) {
        clarifyCancelBtn.addEventListener('click', async () => {
            if (!currentTaskId) return;
            try {
                await fetch(`/api/v1/agent/tasks/${currentTaskId}/cancel`, { method: 'POST' });
                setDisplay(clarificationCard, 'none');
            } catch (e) {
                alert(`Cancellation error: ${e.message}`);
            }
        });
    }
});
