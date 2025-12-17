/**
 * Medya Takip Merkezi - Main Application
 */
const API_BASE = '/api';
let currentView = 'search';
let stats = { total_documents: 0, categories: {}, source_types: {} };
let allDocuments = [];

document.addEventListener('DOMContentLoaded', async () => {
    initNavigation();
    initSearch();
    initUpload();
    initDocuments();
    initExplore();
    initModal();
    await loadStats();
    await loadDocuments();
});

function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            switchView(item.dataset.view);
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        });
    });
}

function switchView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(`view-${viewName}`).classList.add('active');
    currentView = viewName;
    if (viewName === 'explore') loadExploreGraph();
    else if (viewName === 'documents') renderDocuments();
}

async function apiCall(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options
    });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'API hatası');
    }
    return await response.json();
}

async function loadStats() {
    try {
        stats = await apiCall('/documents/stats');
        document.getElementById('stat-total').textContent = stats.total_documents || 0;
        document.getElementById('stat-categories').textContent = Object.keys(stats.categories || {}).length;
        document.getElementById('stat-sources').textContent = Object.keys(stats.source_types || {}).length;
        updateFilterOptions();
    } catch (e) { console.error('Stats error:', e); }
}

function updateFilterOptions() {
    ['filter-category', 'explore-category'].forEach(id => {
        const sel = document.getElementById(id);
        while (sel.options.length > 1) sel.remove(1);
        Object.keys(stats.categories || {}).forEach(cat => {
            sel.add(new Option(`${cat} (${stats.categories[cat]})`, cat));
        });
    });
    ['filter-source', 'explore-source'].forEach(id => {
        const sel = document.getElementById(id);
        while (sel.options.length > 1) sel.remove(1);
        Object.keys(stats.source_types || {}).forEach(t => {
            sel.add(new Option(`${t} (${stats.source_types[t]})`, t));
        });
    });
}

function initSearch() {
    document.getElementById('search-btn').addEventListener('click', performSearch);
    document.getElementById('search-input').addEventListener('keypress', e => { if (e.key === 'Enter') performSearch(); });
    document.getElementById('filter-threshold').addEventListener('input', e => {
        document.getElementById('threshold-label').textContent = `Eşik: ${e.target.value}%`;
    });
}

async function performSearch() {
    const query = document.getElementById('search-input').value.trim();
    if (!query) { showToast('Arama terimi girin', 'warning'); return; }
    const container = document.getElementById('search-results');
    container.innerHTML = '<div class="loading">Aranıyor...</div>';
    try {
        const data = await apiCall('/search', {
            method: 'POST',
            body: JSON.stringify({
                query, limit: 20,
                score_threshold: parseInt(document.getElementById('filter-threshold').value) / 100,
                filter_category: document.getElementById('filter-category').value || null,
                filter_source_type: document.getElementById('filter-source').value || null
            })
        });
        document.getElementById('result-count').textContent = `(${data.total_results} sonuç)`;
        renderSearchResults(data.results);
        if (data.relationships) renderSearchGraph(data.relationships);
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><p>Arama hatası</p></div>';
        showToast(e.message, 'error');
    }
}

function renderSearchResults(results) {
    const c = document.getElementById('search-results');
    if (!results.length) { c.innerHTML = '<div class="empty-state"><p>Sonuç bulunamadı</p></div>'; return; }
    c.innerHTML = results.map(r => `
        <div class="result-item" onclick="showDocumentModal('${r.id}')">
            <div class="result-header">
                <span class="result-title">${escapeHtml(r.title)}</span>
                <span class="result-score">${Math.round(r.score * 100)}%</span>
            </div>
            <div class="result-content">${escapeHtml(r.content.substring(0, 200))}...</div>
            <div class="result-meta">
                ${r.category ? `<span class="meta-tag">${escapeHtml(r.category)}</span>` : ''}
                ${r.source_type ? `<span class="meta-tag">${escapeHtml(r.source_type)}</span>` : ''}
            </div>
            ${r.source ? `<div class="result-source">${escapeHtml(r.source)}</div>` : ''}
        </div>
    `).join('');
}

async function loadDocuments() {
    try { allDocuments = await apiCall('/documents?limit=500'); renderDocuments(); } catch (e) { console.error(e); }
}

function initDocuments() {
    document.getElementById('doc-search').addEventListener('input', e => renderDocuments(e.target.value));
    document.getElementById('refresh-docs').addEventListener('click', async () => {
        await loadDocuments(); await loadStats(); showToast('Yenilendi', 'success');
    });
}

function renderDocuments(filter = '') {
    const c = document.getElementById('documents-list');
    let docs = filter ? allDocuments.filter(d => d.title.toLowerCase().includes(filter.toLowerCase()) || d.content.toLowerCase().includes(filter.toLowerCase())) : allDocuments;
    if (!docs.length) { c.innerHTML = '<div class="empty-state"><p>Doküman yok</p></div>'; return; }
    c.innerHTML = docs.map(d => `
        <div class="document-card">
            <div class="doc-card-header">
                <span class="doc-card-title" onclick="showDocumentModal('${d.id}')">${escapeHtml(d.title)}</span>
                <div class="doc-card-actions">
                    <button onclick="findSimilar('${d.id}')" title="Benzer">🔗</button>
                    <button class="delete" onclick="deleteDocument('${d.id}')" title="Sil">🗑</button>
                </div>
            </div>
            <div class="doc-card-content">${escapeHtml(d.content)}</div>
            <div class="doc-card-footer">
                ${d.category ? `<span class="doc-card-category">${escapeHtml(d.category)}</span>` : '<span></span>'}
                <span class="doc-card-date">${formatDate(d.created_at)}</span>
            </div>
        </div>
    `).join('');
}

async function deleteDocument(id) {
    if (!confirm('Silmek istediğinize emin misiniz?')) return;
    try { await apiCall(`/documents/${id}`, { method: 'DELETE' }); showToast('Silindi', 'success'); await loadDocuments(); await loadStats(); } catch (e) { showToast(e.message, 'error'); }
}

async function findSimilar(id) {
    try {
        const data = await apiCall('/search/similar', { method: 'POST', body: JSON.stringify({ document_id: id, limit: 10, score_threshold: 0.5 }) });
        switchView('search');
        document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
        document.querySelector('[data-view="search"]').classList.add('active');
        document.getElementById('result-count').textContent = `(${data.similar_documents.length} benzer)`;
        renderSearchResults(data.similar_documents);
        showToast(`${data.total_found} benzer doküman`, 'info');
    } catch (e) { showToast(e.message, 'error'); }
}

function initUpload() {
    document.getElementById('single-upload-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const doc = {
            title: document.getElementById('doc-title').value,
            content: document.getElementById('doc-content').value,
            source: document.getElementById('doc-source').value || null,
            source_type: document.getElementById('doc-source-type').value || null,
            category: document.getElementById('doc-category').value || null,
            tags: document.getElementById('doc-tags').value ? document.getElementById('doc-tags').value.split(',').map(t => t.trim()) : []
        };
        try { await apiCall('/documents', { method: 'POST', body: JSON.stringify(doc) }); showToast('Eklendi', 'success'); e.target.reset(); await loadDocuments(); await loadStats(); } catch (e) { showToast(e.message, 'error'); }
    });

    const bulkArea = document.getElementById('bulk-upload-area');
    const bulkInput = document.getElementById('bulk-file-input');
    bulkArea.addEventListener('click', () => bulkInput.click());
    bulkArea.addEventListener('dragover', e => { e.preventDefault(); bulkArea.classList.add('dragover'); });
    bulkArea.addEventListener('dragleave', () => bulkArea.classList.remove('dragover'));
    bulkArea.addEventListener('drop', e => { e.preventDefault(); bulkArea.classList.remove('dragover'); handleBulkFile(e.dataTransfer.files[0]); });
    bulkInput.addEventListener('change', e => handleBulkFile(e.target.files[0]));
}

async function handleBulkFile(file) {
    if (!file?.name.endsWith('.json')) { showToast('JSON dosyası seçin', 'warning'); return; }
    try {
        const documents = JSON.parse(await file.text());
        if (!Array.isArray(documents)) throw new Error('JSON dizi olmalı');
        const result = await apiCall('/documents/bulk', { method: 'POST', body: JSON.stringify({ documents }) });
        showToast(`${result.count} doküman yüklendi`, 'success');
        await loadDocuments(); await loadStats();
    } catch (e) { showToast(e.message, 'error'); }
}

function initExplore() { document.getElementById('explore-btn').addEventListener('click', loadExploreGraph); }

async function loadExploreGraph() {
    const c = document.getElementById('explore-graph');
    c.innerHTML = '<div class="loading">Yükleniyor...</div>';
    try {
        let url = '/search/explore?limit=50';
        const cat = document.getElementById('explore-category').value;
        const src = document.getElementById('explore-source').value;
        if (cat) url += `&category=${encodeURIComponent(cat)}`;
        if (src) url += `&source_type=${encodeURIComponent(src)}`;
        const data = await apiCall(url);
        if (data.nodes.length < 2) { c.innerHTML = '<div class="empty-state"><p>Yeterli doküman yok</p></div>'; return; }
        c.innerHTML = '';
        renderForceGraph(c, data.nodes, data.edges, true);
    } catch (e) { c.innerHTML = '<div class="empty-state"><p>Graf yüklenemedi</p></div>'; }
}

function initModal() {
    const modal = document.getElementById('doc-modal');
    modal.querySelector('.modal-close').addEventListener('click', () => modal.classList.add('hidden'));
    modal.querySelector('.modal-overlay').addEventListener('click', () => modal.classList.add('hidden'));
    document.addEventListener('keydown', e => { if (e.key === 'Escape') modal.classList.add('hidden'); });
}

async function showDocumentModal(id) {
    const modal = document.getElementById('doc-modal');
    const body = document.getElementById('modal-body');
    body.innerHTML = '<div class="loading">Yükleniyor...</div>';
    modal.classList.remove('hidden');
    try {
        const doc = await apiCall(`/documents/${id}`);
        body.innerHTML = `
            <h2 style="margin-bottom:16px">${escapeHtml(doc.title)}</h2>
            <div style="display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap">
                ${doc.category ? `<span class="meta-tag">${escapeHtml(doc.category)}</span>` : ''}
                ${doc.source_type ? `<span class="meta-tag">${escapeHtml(doc.source_type)}</span>` : ''}
                ${(doc.tags || []).map(t => `<span class="meta-tag">#${escapeHtml(t)}</span>`).join('')}
            </div>
            <div style="background:var(--bg-tertiary);padding:20px;border-radius:12px;margin-bottom:20px">
                <p style="white-space:pre-wrap;color:var(--text-secondary);line-height:1.7">${escapeHtml(doc.content)}</p>
            </div>
            ${doc.source ? `<p><strong>Kaynak:</strong> ${escapeHtml(doc.source)}</p>` : ''}
            <p style="font-size:0.85rem;color:var(--text-muted)">Oluşturulma: ${formatDate(doc.created_at)}</p>
            <div style="margin-top:24px;display:flex;gap:12px">
                <button class="btn-secondary" onclick="findSimilar('${doc.id}');document.getElementById('doc-modal').classList.add('hidden')">Benzer Bul</button>
                <button class="btn-secondary" style="border-color:var(--error);color:var(--error)" onclick="deleteDocument('${doc.id}');document.getElementById('doc-modal').classList.add('hidden')">Sil</button>
            </div>`;
    } catch (e) { body.innerHTML = '<div class="empty-state"><p>Yüklenemedi</p></div>'; }
}

function showToast(msg, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = msg;
    document.getElementById('toast-container').appendChild(toast);
    setTimeout(() => { toast.style.animation = 'toastIn 0.25s reverse'; setTimeout(() => toast.remove(), 250); }, 4000);
}

function escapeHtml(t) { if (!t) return ''; const d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
function formatDate(d) { if (!d) return '-'; try { return new Date(d).toLocaleDateString('tr-TR', { year: 'numeric', month: 'short', day: 'numeric' }); } catch { return d; } }
