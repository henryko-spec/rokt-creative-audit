/* Upload */
function initUpload() {
    const area = document.getElementById('upload-area');
    const input = document.getElementById('file-input');
    if (!area || !input) return;

    area.addEventListener('click', () => input.click());

    area.addEventListener('dragover', (e) => {
        e.preventDefault();
        area.classList.add('dragover');
    });

    area.addEventListener('dragleave', () => {
        area.classList.remove('dragover');
    });

    area.addEventListener('drop', (e) => {
        e.preventDefault();
        area.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) uploadFile(file);
    });

    input.addEventListener('change', () => {
        if (input.files[0]) uploadFile(input.files[0]);
    });
}

async function uploadFile(file) {
    const status = document.getElementById('upload-status');
    const statusText = document.getElementById('upload-status-text');
    const error = document.getElementById('upload-error');
    const area = document.getElementById('upload-area');

    error.style.display = 'none';
    status.style.display = 'flex';
    area.style.display = 'none';
    statusText.textContent = `Uploading ${file.name}...`;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/upload', { method: 'POST', body: formData });
        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.error || 'Upload failed');
        }

        statusText.textContent = `Uploaded! ${data.total_rows} creatives queued for audit.`;
        setTimeout(() => {
            window.location.href = `/jobs/${data.job_id}`;
        }, 1000);

    } catch (err) {
        status.style.display = 'none';
        area.style.display = '';
        error.style.display = 'block';
        error.textContent = err.message;
    }
}

/* Jobs List */
async function loadJobs() {
    const list = document.getElementById('jobs-list');
    if (!list) return;

    try {
        const res = await fetch('/api/jobs');
        const data = await res.json();
        const jobs = data.jobs;

        if (!jobs.length) {
            list.innerHTML = '<div class="empty-state"><p>No audits yet. Upload a CSV to get started.</p></div>';
            return;
        }

        list.innerHTML = jobs.map(job => `
            <a href="/jobs/${job.id}" class="job-card">
                <div class="job-card-left">
                    <span class="status-badge status-${job.status}">${job.status}</span>
                    <div>
                        <div class="job-filename">${escapeHtml(job.filename)}</div>
                        <div class="job-date">${job.created_at}</div>
                    </div>
                </div>
                <div class="job-card-right">
                    <span class="job-stats-mini">
                        ${job.total_rows} rows &middot;
                        <span class="approved">${job.approved_count} approved</span> &middot;
                        <span class="rejected">${job.rejected_count} rejected</span>
                    </span>
                </div>
            </a>
        `).join('');
    } catch (err) {
        list.innerHTML = `<div class="upload-error">Failed to load jobs: ${err.message}</div>`;
    }
}

/* Job Progress Polling */
let pollInterval = null;

async function pollJobProgress(jobId) {
    async function update() {
        try {
            const res = await fetch(`/api/jobs/${jobId}/progress`);
            const data = await res.json();

            const pct = data.total_rows > 0 ? Math.round((data.processed_rows / data.total_rows) * 100) : 0;
            const bar = document.getElementById('progress-bar');
            const text = document.getElementById('progress-text');
            const statsGrid = document.getElementById('stats-grid');
            const actionsBar = document.getElementById('actions-bar');
            const creativesSection = document.getElementById('creatives-section');

            if (bar) bar.style.width = pct + '%';
            if (text) text.textContent = `${data.processed_rows} / ${data.total_rows} creatives processed (${pct}%)`;

            document.getElementById('stat-approved').textContent = data.approved_count;
            document.getElementById('stat-rejected').textContent = data.rejected_count;
            document.getElementById('stat-flagged').textContent = data.flagged_count;
            document.getElementById('stat-total').textContent = data.total_rows;

            if (data.status === 'completed' || data.status === 'failed') {
                if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
                if (text) {
                    text.textContent = data.status === 'completed'
                        ? `Audit complete. ${data.processed_rows} creatives reviewed.`
                        : 'Audit failed. Check server logs.';
                }
                if (statsGrid) statsGrid.style.display = '';
                if (actionsBar) actionsBar.style.display = '';
                if (creativesSection) creativesSection.style.display = '';

                const reviewCount = data.rejected_count + data.flagged_count;
                const rc = document.getElementById('review-count');
                if (rc) rc.textContent = reviewCount;

                loadCreativesTable(jobId, '');
                initFilterButtons(jobId);
            } else {
                if (statsGrid) statsGrid.style.display = '';
            }
        } catch (err) {
            console.error('Poll error:', err);
        }
    }

    await update();
    pollInterval = setInterval(update, 3000);
}

async function loadCreativesTable(jobId, filter) {
    const tbody = document.getElementById('creatives-tbody');
    if (!tbody) return;

    const url = filter ? `/api/jobs/${jobId}/creatives?filter=${filter}` : `/api/jobs/${jobId}/creatives`;
    const res = await fetch(url);
    const data = await res.json();

    tbody.innerHTML = data.creatives.map(c => `
        <tr>
            <td>${c.row_index}</td>
            <td>${escapeHtml(c.advertiser)}</td>
            <td>${escapeHtml(c.creative_id)}</td>
            <td title="${escapeHtml(c.creative_title)}">${escapeHtml(truncate(c.creative_title, 40))}</td>
            <td><span class="${c.alpha_pass ? 'pass-badge' : 'fail-badge'}">${c.alpha_pass ? 'PASS' : 'FAIL'}</span></td>
            <td><span class="${c.beta_pass ? 'pass-badge' : 'fail-badge'}">${c.beta_pass ? 'PASS' : 'FAIL'}</span></td>
            <td><span class="${c.arbiter_pass ? 'pass-badge' : 'fail-badge'}">${c.arbiter_pass ? 'PASS' : 'FAIL'}</span></td>
            <td title="${escapeHtml(c.arbiter_fail_reason || '')}">${escapeHtml(truncate(c.arbiter_fail_reason || '—', 50))}</td>
        </tr>
    `).join('');
}

function initFilterButtons(jobId) {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            loadCreativesTable(jobId, btn.dataset.filter);
        });
    });
}

/* Review Queue */
async function loadReviewQueue(jobId) {
    const container = document.getElementById('review-cards');
    const emptyState = document.getElementById('review-empty');
    const counter = document.getElementById('review-counter');
    if (!container) return;

    try {
        const res = await fetch(`/api/jobs/${jobId}/creatives?filter=flagged`);
        const data = await res.json();
        const creatives = data.creatives;

        if (!creatives.length) {
            container.style.display = 'none';
            emptyState.style.display = '';
            return;
        }

        const pendingCount = creatives.filter(c => c.review_status === 'pending').length;
        counter.textContent = `${pendingCount} of ${creatives.length} flagged creatives need review`;

        container.innerHTML = creatives.map(c => renderReviewCard(c)).join('');
    } catch (err) {
        container.innerHTML = `<div class="upload-error">Failed to load review queue: ${err.message}</div>`;
    }
}

function renderReviewCard(c) {
    const isReviewed = c.review_status !== 'pending';
    const reasons = (c.arbiter_fail_reason || '').split(' | ').filter(r => r.trim());

    return `
    <div class="review-card ${isReviewed ? 'reviewed' : ''}" id="card-${c.id}">
        <div class="review-card-header">
            <div>
                <div class="review-card-title">${escapeHtml(c.advertiser)} — ${escapeHtml(c.creative_id)}</div>
                <div class="review-card-meta">
                    Row ${c.row_index} &middot; ${escapeHtml(c.campaign_brand_name)} &middot; ${escapeHtml(c.campaign_language)}
                </div>
            </div>
            ${isReviewed ? `<span class="review-status-badge status-completed">${c.review_status.replace('_', ' ')}</span>` : ''}
        </div>

        <div class="creative-fields">
            <div class="creative-field">
                <label>Title</label>
                <div>${escapeHtml(c.creative_title)}</div>
            </div>
            <div class="creative-field">
                <label>CTA</label>
                <div>${escapeHtml(c.cta_response)}</div>
            </div>
            <div class="creative-field creative-field-full">
                <label>Body</label>
                <div>${escapeHtml(c.creative_body)}</div>
            </div>
            ${c.disclaimer_text ? `
            <div class="creative-field creative-field-full">
                <label>Disclaimer</label>
                <div>${escapeHtml(c.disclaimer_text)}</div>
            </div>` : ''}
            <div class="creative-field creative-field-full">
                <label>Target URL</label>
                <div>${escapeHtml(c.target_url)}</div>
            </div>
        </div>

        <div class="fail-reasons">
            <strong>Issues Found:</strong>
            ${reasons.map(r => `<div class="fail-reason-item">${escapeHtml(r)}</div>`).join('')}
        </div>

        ${!isReviewed ? `
        <div class="review-actions">
            <button class="btn btn-success btn-sm" onclick="submitReview(${c.id}, 'looks_good')">Looks Good</button>
            <button class="btn btn-danger btn-sm" onclick="submitReview(${c.id}, 'flagged')">Flag</button>
            <button class="btn btn-warning btn-sm" onclick="openEmailModal(${c.id})">Flag & Email AM</button>
        </div>` : ''}
    </div>`;
}

async function submitReview(creativeId, action, emailTo, note) {
    const body = { action };
    if (emailTo) body.email_to = emailTo;
    if (note) body.note = note;

    try {
        const res = await fetch(`/api/creatives/${creativeId}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

        if (!res.ok) {
            const data = await res.json();
            throw new Error(data.detail || 'Review failed');
        }

        const card = document.getElementById(`card-${creativeId}`);
        if (card) {
            card.classList.add('reviewed');
            const actions = card.querySelector('.review-actions');
            if (actions) actions.innerHTML = `<span class="review-status-badge status-completed">${action.replace('_', ' ')}</span>`;
        }

        updateReviewCounter();
    } catch (err) {
        alert('Error: ' + err.message);
    }
}

function updateReviewCounter() {
    const counter = document.getElementById('review-counter');
    const cards = document.querySelectorAll('.review-card:not(.reviewed)');
    const total = document.querySelectorAll('.review-card').length;
    if (counter) counter.textContent = `${cards.length} of ${total} flagged creatives need review`;
}

/* Email Modal */
let emailModalCreativeId = null;

function openEmailModal(creativeId) {
    emailModalCreativeId = creativeId;
    document.getElementById('email-modal').style.display = 'flex';
    document.getElementById('email-to').value = '';
    document.getElementById('email-note').value = '';

    document.getElementById('send-email-btn').onclick = () => {
        const emailTo = document.getElementById('email-to').value.trim();
        const note = document.getElementById('email-note').value.trim();
        if (!emailTo) { alert('Please enter an email address.'); return; }
        closeEmailModal();
        submitReview(emailModalCreativeId, 'flagged_emailed', emailTo, note);
    };
}

function closeEmailModal() {
    document.getElementById('email-modal').style.display = 'none';
    emailModalCreativeId = null;
}

/* Util */
function escapeHtml(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

function truncate(str, len) {
    if (!str) return '';
    return str.length > len ? str.slice(0, len) + '...' : str;
}
