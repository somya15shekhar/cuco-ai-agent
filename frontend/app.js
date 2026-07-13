
// ==========================================================================
// cuCO Agent Frontend - Logic & API Orchestrator (Multi-Page Version)
// ==========================================================================

const BACKEND_URL = 'http://localhost:8000';
const SUPABASE_URL = 'https://kyrwgasqgjdoqtofmntr.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_YdOGLHzIvApHagLJjXhJxw_l5LWmR4r';

// Initialize Supabase Client
const supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// State variables
let currentSession = null;
let selectedFile = null;
let activeClaimsList = [];

// Helper function to safely add event listener
function addSafeListener(elementId, event, handler) {
    const el = document.getElementById(elementId);
    if (el) {
        el.addEventListener(event, handler);
    }
}

function getEl(id) {
    return document.getElementById(id);
}

// ==========================================================================
// 1. Authentication & Session Management
// ==========================================================================

// Listen for Auth changes
supabaseClient.auth.onAuthStateChange(async (event, session) => {
    const path = window.location.pathname;
    const currentPage = path.split('/').pop() || 'index.html';
    
    if (session) {
        // User logged in
        if (getEl('user-email')) getEl('user-email').textContent = session.user.email;
        if (getEl('user-profile')) getEl('user-profile').classList.remove('hidden');
        
        // Redirect to dashboard if on public pages
        if (['login.html', 'signup.html', 'index.html', ''].includes(currentPage)) {
            window.location.href = 'dashboard.html';
            return;
        }
        
        if (currentPage === 'dashboard.html' && typeof loadClaims === 'function') {
            loadClaims();
            loadHouseholdData();
        }
    } else {
        // User logged out
        if (getEl('user-profile')) getEl('user-profile').classList.add('hidden');
        
        // Redirect to login if on protected pages
        if (currentPage === 'dashboard.html') {
            window.location.href = 'login.html';
        }
    }
});

// Handle Auth Form Submission
addSafeListener('auth-form', 'submit', async (e) => {
    e.preventDefault();
    const email = getEl('auth-email').value;
    const password = getEl('auth-password').value;
    const mode = getEl('auth-mode').value; // 'login' or 'signup'
    const btnSubmit = getEl('btn-submit-auth');

    btnSubmit.disabled = true;
    btnSubmit.textContent = mode === 'signup' ? 'Signing Up...' : 'Logging In...';

    try {
        if (mode === 'signup') {
            const { error } = await supabaseClient.auth.signUp({ email, password });
            if (error) throw error;
            showToast('Sign up successful! Redirecting...', 'info');
        } else {
            const { error } = await supabaseClient.auth.signInWithPassword({ email, password });
            if (error) throw error;
        }
    } catch (err) {
        showToast(err.message, 'error');
        btnSubmit.disabled = false;
        btnSubmit.textContent = mode === 'signup' ? 'Sign Up' : 'Log In';
    }
});

// Handle Logout
addSafeListener('btn-logout', 'click', async () => {
    try {
        const { error } = await supabaseClient.auth.signOut();
        if (error) throw error;
    } catch (err) {
        showToast(err.message, 'error');
    }
});

// ==========================================================================
// 2. Claims Database Integration
// ==========================================================================

async function loadClaims() {
    try {
        const { data, error } = await supabaseClient
            .from('claims')
            .select('*')
            .order('created_at', { ascending: false });

        if (error) throw error;

        activeClaimsList = data || [];
        
        // Populate dropdown
        const uploadClaimSelect = getEl('upload-claim-select');
        if (uploadClaimSelect) {
            uploadClaimSelect.innerHTML = '';
            if (activeClaimsList.length === 0) {
                const option = document.createElement('option');
                option.textContent = '-- No Claims Available (Create One First) --';
                option.disabled = true;
                uploadClaimSelect.appendChild(option);
            } else {
                activeClaimsList.forEach(claim => {
                    const option = document.createElement('option');
                    option.value = claim.id;
                    option.textContent = `${claim.patient_name} - ₹${claim.total_amount} (${claim.claim_type})`;
                    uploadClaimSelect.appendChild(option);
                });
            }
        }

        // Populate history table
        const historyTableBody = getEl('history-table-body');
        if (historyTableBody) {
            historyTableBody.innerHTML = '';
            
            if (activeClaimsList.length === 0) {
                const tr = document.createElement('tr');
                tr.innerHTML = `<td colspan="5" style="text-align: center; color: var(--text-secondary);">No claims found.</td>`;
                historyTableBody.appendChild(tr);
            } else {
                activeClaimsList.forEach(claim => {
                    const tr = document.createElement('tr');
                    const dateStr = new Date(claim.created_at).toLocaleDateString();
                    const formattedAmount = formatCurrency(claim.total_amount);
                    tr.innerHTML = `
                        <td>${dateStr}</td>
                        <td><strong>${claim.patient_name}</strong></td>
                        <td><span class="badge valid" style="background: rgba(255,255,255,0.05); color: var(--text-primary); border: none;">${claim.claim_type}</span></td>
                        <td>${formattedAmount}</td>
                        <td>${claim.primary_insurer}</td>
                    `;
                    historyTableBody.appendChild(tr);
                });
            }
        }
    } catch (err) {
        console.error('Error loading claims:', err);
        showToast('Failed to load active claims', 'error');
    }
}

// Handle Claim Creation
addSafeListener('claim-form', 'submit', async (e) => {
    e.preventDefault();
    
    // Retrieve current session or fall back to client retrieval
    let session = currentSession;
    if (!session) {
        const { data } = await supabaseClient.auth.getSession();
        session = data?.session;
    }
    
    if (!session || !session.user) {
        showToast('You must be logged in to create a claim.', 'error');
        return;
    }

    const patientName = getEl('claim-patient-select').value;
    const claimType = getEl('claim-type').value;
    const totalAmount = parseFloat(getEl('claim-amount').value);
    
    const primaryDisplayVal = getEl('claim-primary-display').value;
    const secondaryDisplayVal = getEl('claim-secondary-display').value;
    
    const primaryInsurer = primaryDisplayVal === "SecureHealth Premier" ? "Plan A" : "Plan B";
    const secondaryInsurer = secondaryDisplayVal === "SecureHealth Premier" ? "Plan A" : "Plan B";

    const payload = {
        user_id: session.user.id,
        patient_name: patientName,
        claim_type: claimType,
        total_amount: totalAmount,
        primary_insurer: primaryInsurer,
        secondary_insurer: secondaryInsurer
    };

    try {
        const res = await fetch(`${BACKEND_URL}/claims`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const errorText = await res.text();
            throw new Error(`Backend failed to create claim: ${res.status} - ${errorText}`);
        }

        const resultData = await res.json();
        showToast(`Claim successfully created!`, 'success');
        
        getEl('claim-form').reset();
        await loadClaims();
        
        if (resultData && resultData.length > 0 && getEl('upload-claim-select')) {
            getEl('upload-claim-select').value = resultData[0].id;
        }
    } catch (err) {
        showToast(err.message, 'error');
    }
});

// ==========================================================================
// 3. Document Dropzone Handlers
// ==========================================================================

const dropzone = getEl('dropzone');
if (dropzone) {
    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    });

    dropzone.addEventListener('click', () => {
        getEl('file-input').click();
    });
}

addSafeListener('file-input', 'change', (e) => {
    if (e.target.files.length > 0) {
        handleFileSelection(e.target.files[0]);
    }
});

function handleFileSelection(file) {
    selectedFile = file;
    getEl('selected-file-name').textContent = file.name;
    getEl('dropzone').classList.add('hidden');
    getEl('selected-file-info').classList.remove('hidden');
    getEl('btn-process').disabled = false;
}

addSafeListener('btn-clear-file', 'click', (e) => {
    e.stopPropagation();
    selectedFile = null;
    getEl('file-input').value = '';
    getEl('selected-file-info').classList.add('hidden');
    getEl('dropzone').classList.remove('hidden');
    getEl('btn-process').disabled = true;
});

// ==========================================================================
// 4. Multi-Step Adjudication Orchestrator
// ==========================================================================

addSafeListener('btn-process', 'click', async () => {
    const uploadClaimSelect = getEl('upload-claim-select');
    const uploadDocType = getEl('upload-doc-type');
    const btnProcess = getEl('btn-process');
    const loadingOverlay = getEl('loading-overlay');
    const resultsPanel = getEl('results-panel');

    const claimId = uploadClaimSelect.value;
    const docType = uploadDocType.value;

    if (!claimId) { showToast('Please select a claim first', 'error'); return; }
    if (!selectedFile) { showToast('Please select a file to process', 'error'); return; }

    loadingOverlay.classList.remove('hidden');
    resultsPanel.classList.add('hidden');
    btnProcess.disabled = true;

    try {
        updateJourneyStep('step-upload');
        setLoadingStatus('Uploading document...', 'Storing file metadata in Supabase bucket...');
        const uploadForm = new FormData();
        uploadForm.append('claim_id', claimId);
        uploadForm.append('document_type', docType);
        uploadForm.append('file', selectedFile);

        const uploadRes = await fetch(`${BACKEND_URL}/upload`, { method: 'POST', body: uploadForm });
        if (!uploadRes.ok) {
            const errorText = await uploadRes.text();
            throw new Error(`Upload failed: ${uploadRes.status} - ${errorText}`);
        }

        updateJourneyStep('step-ocr');
        setLoadingStatus('Parsing claim contents...', 'Running OCR & structured extraction via Groq...');
        const parseForm = new FormData();
        parseForm.append('claim_id', claimId);
        parseForm.append('file', selectedFile);

        const parseRes = await fetch(`${BACKEND_URL}/parse`, { method: 'POST', body: parseForm });
        if (!parseRes.ok) {
            const errorText = await parseRes.text();
            throw new Error(`Document parsing failed: ${parseRes.status} - ${errorText}`);
        }

        updateJourneyStep('step-reasoning');
        setLoadingStatus('Assembling claim context...', 'Loading parsed parameters from database...');
        const { data: parsedRows, error: parsedErr } = await supabaseClient
            .from('parsed_claims')
            .select('*')
            .eq('claim_id', claimId)
            .order('created_at', { ascending: false });

        if (parsedErr) throw parsedErr;
        if (!parsedRows || parsedRows.length === 0) throw new Error('No parsed claim metadata found.');
        
        const parsedRow = parsedRows[0];
        const selectedClaim = activeClaimsList.find(c => c.id === claimId);

        setLoadingStatus('Running COB calculation engine...', 'LangGraph validation & ledger reconciliation active...');
        
        let networkStatus = { "SecureHealth Premier": "IN", "FlexiCare Plus": "IN" };
        let provider = parsedRow.provider_name || selectedClaim.patient_name + "'s Provider";

        const cobPayload = {
            claim_id: parsedRow.claim_id,
            patient_name: parsedRow.patient_name,
            member_id: selectedClaim.member_id || null,
            diagnosis: parsedRow.diagnosis,
            cpt_codes: parsedRow.cpt_codes || [],
            icd10_codes: parsedRow.icd_codes || [],
            total_amount: parsedRow.total_amount,
            billed_amounts: {},
            primary_insurer: selectedClaim.primary_insurer,
            secondary_insurer: selectedClaim.secondary_insurer,
            hospital: parsedRow.parsed_json?.hospital || null,
            provider: provider,
            network_status: networkStatus
        };

        updateJourneyStep('step-eligibility');
        await new Promise(r => setTimeout(r, 600));
        updateJourneyStep('step-preauth');
        await new Promise(r => setTimeout(r, 600));
        updateJourneyStep('step-adjudication');
        await new Promise(r => setTimeout(r, 600));
        updateJourneyStep('step-cob');
        await new Promise(r => setTimeout(r, 600));
        updateJourneyStep('step-validation');

        const processRes = await fetch(`${BACKEND_URL}/process-claim`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(cobPayload)
        });

        if (!processRes.ok) throw new Error('COB claims processing agent failed');
        const cobOutput = await processRes.json();
        
        updateJourneyStep('step-breakdown');
        renderAdjudicationResults(cobOutput);
        showToast('Claim adjudicated successfully!', 'success');

    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        loadingOverlay.classList.add('hidden');
        btnProcess.disabled = false;
    }
});

function setLoadingStatus(status, substatus) {
    if(getEl('loading-status')) getEl('loading-status').textContent = status;
    if(getEl('loading-substatus')) getEl('loading-substatus').textContent = substatus;
}

// ==========================================================================
// 5. Results Rendering UI Component Logic
// ==========================================================================

function renderAdjudicationResults(output) {
    const resultsPanel = getEl('results-panel');
    if (!resultsPanel) return;
    resultsPanel.classList.remove('hidden');

    const summary = output.claim_summary || {};
    const breakdown = output.payment_breakdown || {};
    const patientResp = output.patient_responsibility || {};
    const validation = output.validation_status || {};
    const log = output.workflow_log || [];
    const explanation = output.explanation || {};
    const primExp = explanation.primary || {};
    const secExp = explanation.secondary || {};

    const validationBadge = getEl('validation-badge');
    if (validation.is_valid) {
        validationBadge.textContent = 'Reconciliation Valid';
        validationBadge.className = 'badge valid';
    } else {
        validationBadge.textContent = 'Ledger Discrepancy';
        validationBadge.className = 'badge invalid';
    }

    // Populate Context Header
    let primaryName = summary.primary_insurer === "Plan A" ? "SecureHealth Premier" : "FlexiCare Plus";
    let secondaryName = summary.secondary_insurer === "Plan A" ? "SecureHealth Premier" : "FlexiCare Plus";
    
    getEl('info-patient-name').textContent = summary.patient_name || '-';
    getEl('info-household-name').textContent = activeHousehold ? activeHousehold.household.household_name : 'Sharma Family';
    getEl('info-diagnosis').textContent = summary.diagnosis || 'ACL Tear Surgery';
    
    // Find active claim type from selection
    const uploadClaimSelect = getEl('upload-claim-select');
    let selectedClaimType = 'Surgery';
    if (uploadClaimSelect && uploadClaimSelect.selectedIndex >= 0) {
        const claimText = uploadClaimSelect.options[uploadClaimSelect.selectedIndex].textContent;
        if (claimText.includes('(physiotherapy)')) selectedClaimType = 'Physiotherapy';
        else if (claimText.includes('(consultation)')) selectedClaimType = 'Consultation';
        else if (claimText.includes('(diagnostic)')) selectedClaimType = 'Diagnostic';
    }
    getEl('info-claim-type').textContent = selectedClaimType;
    getEl('info-billed-amount').textContent = formatCurrency(summary.total_billed);
    getEl('info-primary-insurer').textContent = primaryName;
    getEl('info-secondary-insurer').textContent = secondaryName;
    getEl('info-claim-status').textContent = validation.is_valid ? 'Validated' : 'Discrepancy';
    getEl('info-claim-status').className = validation.is_valid ? 'text-green font-bold' : 'text-orange font-bold';

    // Populate Visual Flow
    getEl('flow-hospital-bill').textContent = formatCurrency(summary.total_billed);
    getEl('flow-primary-paid').textContent = formatCurrency(breakdown.primary_insurer_payment);
    getEl('flow-remaining-balance').textContent = formatCurrency(summary.total_billed - breakdown.primary_insurer_payment);
    getEl('flow-secondary-paid').textContent = formatCurrency(breakdown.secondary_insurer_payment);
    getEl('flow-patient-liability').textContent = formatCurrency(patientResp.total_patient_cost);

    // Populate Ledger Rows
    getEl('val-total-billed').textContent = formatCurrency(summary.total_billed);
    getEl('val-primary-paid').textContent = formatCurrency(breakdown.primary_insurer_payment);
    getEl('val-secondary-paid').textContent = formatCurrency(breakdown.secondary_insurer_payment);
    getEl('val-patient-liability').textContent = formatCurrency(patientResp.total_patient_cost);
    getEl('val-patient-covered').textContent = formatCurrency(patientResp.patient_liability_covered);
    getEl('val-patient-uncovered').textContent = formatCurrency(patientResp.uncovered_amount);

    // Populate Dynamic Calculations Toggles
    getEl('calc-details-primary').innerHTML = `
        <div class="calc-details-row"><span>Billed Amount</span><span>${formatCurrency(primExp.total_billed || summary.total_billed)}</span></div>
        <div class="calc-details-row"><span>Allowed Amount</span><span>${formatCurrency(primExp.allowed || summary.total_billed)}</span></div>
        <div class="calc-details-row"><span>Deductible Applied</span><span>-${formatCurrency(primExp.deductible || 0.0)}</span></div>
        <div class="calc-details-row"><span>Patient Coinsurance</span><span>-${formatCurrency(primExp.coinsurance || 0.0)}</span></div>
        <div class="calc-details-row font-bold"><span>Final Primary Paid</span><span>${formatCurrency(primExp.paid || breakdown.primary_insurer_payment)}</span></div>
    `;

    getEl('calc-details-secondary').innerHTML = `
        <div class="calc-details-row"><span>Residual from Primary</span><span>${formatCurrency(secExp.residual_from_primary || 0.0)}</span></div>
        <div class="calc-details-row"><span>Allowed Residual</span><span>${formatCurrency(secExp.allowed_residual || 0.0)}</span></div>
        <div class="calc-details-row"><span>Deductible Applied</span><span>-${formatCurrency(secExp.deductible || 0.0)}</span></div>
        <div class="calc-details-row"><span>Patient Coinsurance</span><span>-${formatCurrency(secExp.coinsurance || 0.0)}</span></div>
        <div class="calc-details-row font-bold"><span>Final Secondary Paid</span><span>${formatCurrency(secExp.paid || breakdown.secondary_insurer_payment)}</span></div>
    `;

    // Populate Plan Details
    const primKey = (summary.primary_insurer === "Plan A") ? "insurer1" : "insurer2";
    const secKey = (summary.secondary_insurer === "Plan A") ? "insurer1" : "insurer2";
    
    const primRules = planRulesCache[primKey] || {};
    const secRules = planRulesCache[secKey] || {};
    
    const primDedApplied = primExp.deductible || 0.0;
    const secDedApplied = secExp.deductible || 0.0;
    
    const primDedRemaining = Math.max(0.0, (primRules.deductible || 0.0) - (primRules.deductible_met || 0.0) - primDedApplied);
    const secDedRemaining = Math.max(0.0, (secRules.deductible || 0.0) - (secRules.deductible_met || 0.0) - secDedApplied);
    
    const primOopUsed = (primRules.oop_met || 0.0) + (patientResp.primary_oop_contribution || 0.0);
    const secOopUsed = (secRules.oop_met || 0.0) + (patientResp.secondary_oop_contribution || 0.0);
    
    getEl('plan-details-primary-grid').innerHTML = `
        <div class="detail-stat"><span>Plan Name</span><span>${primRules.plan_name || primaryName}</span></div>
        <div class="detail-stat"><span>Network Status</span><span>IN</span></div>
        <div class="detail-stat"><span>Total Deductible</span><span>${formatCurrency(primRules.deductible)}</span></div>
        <div class="detail-stat"><span>Deductible Applied</span><span>${formatCurrency(primDedApplied)}</span></div>
        <div class="detail-stat"><span>Deductible Remaining</span><span>${formatCurrency(primDedRemaining)}</span></div>
        <div class="detail-stat"><span>Coinsurance Rate</span><span>${(primRules.coinsurance_rate * 100).toFixed(0)}% / ${(100 - primRules.coinsurance_rate * 100).toFixed(0)}%</span></div>
        <div class="detail-stat"><span>Out-of-Pocket Max</span><span>${formatCurrency(primRules.oop_max)}</span></div>
        <div class="detail-stat"><span>Out-of-Pocket Used</span><span>${formatCurrency(primOopUsed)}</span></div>
    `;

    getEl('plan-details-secondary-grid').innerHTML = `
        <div class="detail-stat"><span>Plan Name</span><span>${secRules.plan_name || secondaryName}</span></div>
        <div class="detail-stat"><span>Network Status</span><span>IN</span></div>
        <div class="detail-stat"><span>Total Deductible</span><span>${formatCurrency(secRules.deductible)}</span></div>
        <div class="detail-stat"><span>Deductible Applied</span><span>${formatCurrency(secDedApplied)}</span></div>
        <div class="detail-stat"><span>Deductible Remaining</span><span>${formatCurrency(secDedRemaining)}</span></div>
        <div class="detail-stat"><span>Coinsurance Rate</span><span>${(secRules.coinsurance_rate * 100).toFixed(0)}% / ${(100 - secRules.coinsurance_rate * 100).toFixed(0)}%</span></div>
        <div class="detail-stat"><span>Out-of-Pocket Max</span><span>${formatCurrency(secRules.oop_max)}</span></div>
        <div class="detail-stat"><span>Out-of-Pocket Used</span><span>${formatCurrency(secOopUsed)}</span></div>
    `;

    // Populate Structured Explanations
    getEl('exp-prim-allowed').textContent = formatCurrency(primExp.allowed || summary.total_billed);
    getEl('exp-prim-deductible').textContent = formatCurrency(primExp.deductible || 0.0);
    getEl('exp-prim-coinsurance').textContent = formatCurrency(primExp.coinsurance || 0.0);
    getEl('exp-prim-payment').textContent = formatCurrency(breakdown.primary_insurer_payment);

    getEl('exp-sec-residual').textContent = formatCurrency(secExp.residual_from_primary || 0.0);
    getEl('exp-sec-allowed').textContent = formatCurrency(secExp.allowed_residual || 0.0);
    getEl('exp-sec-deductible').textContent = formatCurrency(secExp.deductible || 0.0);
    getEl('exp-sec-payment').textContent = formatCurrency(breakdown.secondary_insurer_payment);

    getEl('exp-pat-covered').textContent = formatCurrency(patientResp.patient_liability_covered);
    getEl('exp-pat-uncovered').textContent = formatCurrency(patientResp.uncovered_amount);
    getEl('exp-pat-total').textContent = formatCurrency(patientResp.total_patient_cost);

    getEl('exp-val-retries').textContent = validation.retry_count || 0;
    getEl('exp-val-reflection').textContent = validation.reflection_notes || 'Completed Successfully';

    // Populate Timeline
    const executionTimeline = getEl('execution-timeline');
    executionTimeline.innerHTML = '';
    log.forEach((logMessage) => {
        const item = document.createElement('div');
        item.className = 'timeline-item';
        const dot = document.createElement('div');
        dot.className = 'timeline-dot';
        if (logMessage.includes('completed successfully') || logMessage.includes('OutputNode')) {
            dot.classList.add('success');
        } else {
            dot.classList.add('active');
        }
        const content = document.createElement('div');
        content.className = 'timeline-content';
        content.textContent = logMessage;
        item.appendChild(dot);
        item.appendChild(content);
        executionTimeline.appendChild(item);
    });

    getEl('raw-json-output').textContent = JSON.stringify(output, null, 2);
}

addSafeListener('btn-toggle-json', 'click', () => {
    const rawJsonOutput = getEl('raw-json-output');
    const btnToggleJson = getEl('btn-toggle-json');
    const isHidden = rawJsonOutput.classList.contains('hidden');
    if (isHidden) {
        rawJsonOutput.classList.remove('hidden');
        btnToggleJson.innerHTML = 'Hide Raw JSON Output <i class="fa-solid fa-chevron-up"></i>';
    } else {
        rawJsonOutput.classList.add('hidden');
        btnToggleJson.innerHTML = 'Show Raw JSON Output <i class="fa-solid fa-chevron-down"></i>';
    }
});

function formatCurrency(value) {
    if (value === undefined || value === null) return '₹0.00';
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 2 }).format(value);
}

// ==========================================================================
// 6. Toast Notification System
// ==========================================================================

let toastTimeout = null;
function showToast(message, type = 'info') {
    const toast = getEl('toast');
    if(!toast) return;
    
    getEl('toast-message').textContent = message;
    
    const icon = toast.querySelector('.toast-icon');
    if (type === 'success') {
        icon.className = 'fa-solid fa-circle-check toast-icon text-green';
        toast.style.borderColor = 'rgba(16, 185, 129, 0.4)';
    } else if (type === 'error') {
        icon.className = 'fa-solid fa-triangle-exclamation toast-icon text-orange';
        toast.style.borderColor = 'rgba(239, 68, 68, 0.4)';
    } else {
        icon.className = 'fa-solid fa-circle-info toast-icon primary-icon';
        toast.style.borderColor = 'rgba(99, 102, 241, 0.4)';
    }

    toast.classList.remove('hidden');
    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => { toast.classList.add('hidden'); }, 4000);
}

// ==========================================================================
// 7. Dashboard Navigation (Sidebar)
// ==========================================================================
const navItems = document.querySelectorAll('.nav-item');
const tabPanes = document.querySelectorAll('.tab-pane');

navItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        navItems.forEach(nav => nav.classList.remove('active'));
        item.classList.add('active');
        tabPanes.forEach(tab => tab.classList.add('hidden'));
        
        const targetId = item.getAttribute('data-target');
        const targetTab = getEl(targetId);
        if (targetTab) targetTab.classList.remove('hidden');
    });
});

// ==========================================================================
// 8. Eligibility & Pre-Auth Checker
// ==========================================================================

async function handleInsuranceCheck(endpoint, actionName) {
    const insurerValue = getEl('eligibility-insurer').value;
    const cptRaw = getEl('eligibility-cpt').value;

    if (!cptRaw) {
        showToast('Please enter at least one CPT code', 'error');
        return;
    }

    const cptCodes = cptRaw.split(',').map(s => s.trim()).filter(s => s);
    getEl('eligibility-results').classList.add('hidden');
    
    try {
        const res = await fetch(`${BACKEND_URL}/insurance/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cpt_codes: cptCodes, plan_name: insurerValue })
        });

        if (!res.ok) throw new Error(`${actionName} check failed`);

        const data = await res.json();
        getEl('eligibility-results').classList.remove('hidden');
        
        let outputHtml = `<strong>${actionName} Results for ${insurerValue}:</strong><br><br>`;
        
        if (endpoint === 'eligibility') {
            const elig = data.eligibility || {};
            for (const [cpt, status] of Object.entries(elig)) {
                const color = status === "Covered" ? "var(--color-accent)" : "var(--color-warning)";
                outputHtml += `CPT <strong>${cpt}</strong>: <span style="color: ${color}">${status}</span><br>`;
            }
        } else if (endpoint === 'preauth') {
            const reqs = data.preauthorization_requirements || {};
            for (const [cpt, status] of Object.entries(reqs)) {
                const color = status === "Required" ? "var(--color-warning)" : "var(--color-accent)";
                outputHtml += `CPT <strong>${cpt}</strong>: Pre-Auth <span style="color: ${color}">${status}</span><br>`;
            }
        }
        
        getEl('eligibility-output').innerHTML = outputHtml;
        showToast(`${actionName} complete`, 'success');
        
    } catch (err) {
        showToast(err.message, 'error');
    }
}

addSafeListener('btn-check-eligibility', 'click', () => handleInsuranceCheck('eligibility', 'Eligibility'));
addSafeListener('btn-check-preauth', 'click', () => handleInsuranceCheck('preauth', 'Pre-Authorization'));

// ==========================================================================
// 9. Household & Claim Journey revamping helper functions
// ==========================================================================
let activeHousehold = null;
let planRulesCache = {};

window.toggleElement = function(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.toggle('hidden');
    }
};

async function loadHouseholdData() {
    try {
        const res = await fetch(`${BACKEND_URL}/households/default`);
        if (!res.ok) throw new Error("Failed to load household details");
        activeHousehold = await res.json();
        
        // Load plan rules cache
        const resA = await fetch(`${BACKEND_URL}/insurance/insurer1`);
        const resB = await fetch(`${BACKEND_URL}/insurance/insurer2`);
        if (resA.ok) planRulesCache['insurer1'] = await resA.json();
        if (resB.ok) planRulesCache['insurer2'] = await resB.json();
        
        renderHouseholdContext();
        populatePatientSelect();
    } catch (e) {
        console.error(e);
        showToast("Failed to initialize household information", "error");
    }
}

function renderHouseholdContext() {
    const titleDisp = getEl('household-title-display');
    const membersGrid = getEl('household-members-grid');
    if (!activeHousehold) return;
    
    if (titleDisp) {
        titleDisp.textContent = `${activeHousehold.household.household_name} (Active Dual-Coverage Household)`;
    }
    
    if (membersGrid) {
        membersGrid.innerHTML = '';
        activeHousehold.members.forEach(member => {
            const card = document.createElement('div');
            card.className = 'member-detail-card';
            card.innerHTML = `
                <h5><i class="fa-solid fa-user text-purple"></i> ${member.name}</h5>
                <div class="policy-badge-row">
                    <div class="policy-badge primary-role">
                        Primary: <span>${member.primary}</span>
                    </div>
                    <div class="policy-badge dependent-role">
                        Secondary: <span>${member.secondary}</span>
                    </div>
                </div>
            `;
            membersGrid.appendChild(card);
        });
    }
}

function populatePatientSelect() {
    const select = getEl('claim-patient-select');
    if (!select || !activeHousehold) return;
    select.innerHTML = '<option value="" disabled selected>-- Select Member --</option>';
    activeHousehold.members.forEach(member => {
        const option = document.createElement('option');
        option.value = member.name;
        option.textContent = member.name;
        select.appendChild(option);
    });
    
    // When patient is changed, load primary & secondary read-only values
    select.addEventListener('change', () => {
        const selectedName = select.value;
        const member = activeHousehold.members.find(m => m.name === selectedName);
        if (member) {
            getEl('claim-primary-display').value = member.primary;
            getEl('claim-secondary-display').value = member.secondary;
        }
    });
}

function updateJourneyStep(activeStepId) {
    const steps = ['step-upload', 'step-ocr', 'step-reasoning', 'step-eligibility', 'step-preauth', 'step-adjudication', 'step-cob', 'step-validation', 'step-breakdown'];
    let activeFound = false;
    steps.forEach(stepId => {
        const el = getEl(stepId);
        if (!el) return;
        if (stepId === activeStepId) {
            el.className = 'journey-step active';
            activeFound = true;
        } else if (!activeFound) {
            el.className = 'journey-step completed';
        } else {
            el.className = 'journey-step';
        }
    });
}
