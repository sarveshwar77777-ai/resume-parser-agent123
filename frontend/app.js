// DOM Elements
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const browseBtn = document.getElementById('browseBtn');
const fileNameDisplay = document.getElementById('fileNameDisplay');
const fileNameSpan = document.getElementById('fileName');
const removeFileBtn = document.getElementById('removeFileBtn');
const jdInput = document.getElementById('jdInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const errorBanner = document.getElementById('errorBanner');
const errorMessage = document.getElementById('errorMessage');
const loadingState = document.getElementById('loadingState');
const resultsSection = document.getElementById('resultsSection');
const profileCards = document.getElementById('profileCards');
const fitCards = document.getElementById('fitCards');
const fitSummaryText = document.getElementById('fitSummaryText');
const progressFill = document.getElementById('progressFill');
const toggleJsonBtn = document.getElementById('toggleJsonBtn');
const rawJsonContainer = document.getElementById('rawJsonContainer');
const rawJsonCode = document.getElementById('rawJsonCode');
const copyJsonBtn = document.getElementById('copyJsonBtn');
const jdCount = document.getElementById('jdCount');

// State
let selectedFile = null;
let lastResult = null;

const FIELD_LABELS = {
  'FULL-NAME': 'Full Name',
  'EMAIL': 'Email Address',
  'PHONE': 'Phone Number',
  'URL-LINKEDIN': 'LinkedIn / Portfolio',
  'DEGREE-HIGHEST': 'Highest Degree',
  'JOB-RECENT': 'Most Recent Position',
  'LOCATION': 'Location',
  'SKILLS-LIST': 'Skills',
  'CERTIFICATIONS-LIST': 'Certifications',
  'PROJECTS-NOTABLE': 'Notable Projects'
};

const CATEGORY_ORDER = ['Contact', 'Education', 'Experience', 'Skills', 'Certifications', 'Projects'];

// Event Listeners for File Upload
uploadZone.addEventListener('click', (e) => {
  if (e.target !== removeFileBtn && !removeFileBtn.contains(e.target)) {
    fileInput.click();
  }
});

browseBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  fileInput.click();
});

uploadZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', () => {
  uploadZone.classList.remove('dragover');
});

uploadZone.addEventListener('drop', (e) => {
  e.preventDefault();
  uploadZone.classList.remove('dragover');
  if (e.dataTransfer.files.length) {
    handleFile(e.dataTransfer.files[0]);
  }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files.length) {
    handleFile(fileInput.files[0]);
  }
});

removeFileBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  selectedFile = null;
  fileInput.value = '';
  fileNameDisplay.style.display = 'none';
  browseBtn.style.display = 'inline-block';
  document.querySelector('.upload-title').style.display = 'block';
  document.querySelector('.upload-subtitle').style.display = 'block';
  document.querySelector('.upload-icon').style.display = 'block';
  updateAnalyzeBtnState();
});

jdInput.addEventListener('input', () => {
  jdCount.textContent = `${jdInput.value.trim().length.toLocaleString()} characters`;
  updateAnalyzeBtnState();
});

function handleFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (ext !== 'pdf' && ext !== 'docx') {
    showError('Only PDF and DOCX files are supported.');
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    showError('This file is larger than 10 MB. Please choose a smaller resume.');
    return;
  }
  
  selectedFile = file;
  fileNameSpan.textContent = file.name;
  fileNameDisplay.style.display = 'flex';
  browseBtn.style.display = 'none';
  document.querySelector('.upload-title').style.display = 'none';
  document.querySelector('.upload-subtitle').style.display = 'none';
  document.querySelector('.upload-icon').style.display = 'none';
  hideError();
  updateAnalyzeBtnState();
}

function updateAnalyzeBtnState() {
  const hasFile = !!selectedFile;
  const hasJd = jdInput.value.trim().length > 0;
  analyzeBtn.disabled = !(hasFile && hasJd);
}

function showError(msg) {
  errorMessage.textContent = msg;
  errorBanner.style.display = 'flex';
}

function hideError() {
  errorBanner.style.display = 'none';
}

// Form Submission
analyzeBtn.addEventListener('click', async () => {
  if (!selectedFile || !jdInput.value.trim()) return;

  // Reset UI
  hideError();
  resultsSection.style.display = 'none';
  loadingState.style.display = 'flex';
  analyzeBtn.disabled = true;
  profileCards.innerHTML = '';
  fitCards.innerHTML = '';

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('job_description', jdInput.value.trim());

  try {
    const response = await fetch('/parse', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      let message = `We couldn’t analyze this resume (${response.status}).`;
      try {
        const error = await response.json();
        message = error.detail || message;
      } catch (_) { /* Use the friendly fallback message. */ }
      throw new Error(message);
    }

    const data = await response.json();
    lastResult = data;
    
    renderResults(data);
    
    loadingState.style.display = 'none';
    resultsSection.style.display = 'block';
    
    // Smooth scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    loadingState.style.display = 'none';
    showError(err.message || 'An error occurred during analysis.');
  } finally {
    updateAnalyzeBtnState();
  }
});

// Rendering Functions
function renderResults(data) {
  renderProfile(data.fields || []);
  renderFitReport(data.fit_report || []);
  
  // Set JSON
  rawJsonCode.textContent = JSON.stringify(data, null, 2);
}

function renderProfile(fields) {
  if (!fields.length) {
    profileCards.innerHTML = '<div class="empty-state"><strong>No profile details found</strong><span>Try a text-based PDF or DOCX file.</span></div>';
    return;
  }
  // Group by category
  const grouped = {};
  fields.forEach(f => {
    const cat = f.category || 'Other';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(f);
  });

  CATEGORY_ORDER.forEach(cat => {
    if (grouped[cat] && grouped[cat].length > 0) {
      const catDiv = document.createElement('div');
      catDiv.className = 'profile-category';
      catDiv.innerHTML = `<h3 class="category-title">${cat}</h3>`;
      
      grouped[cat].forEach(field => {
        catDiv.appendChild(createProfileCard(field));
      });
      
      profileCards.appendChild(catDiv);
    }
  });

  // Render any remaining categories
  Object.keys(grouped).forEach(cat => {
    if (!CATEGORY_ORDER.includes(cat) && grouped[cat].length > 0) {
      const catDiv = document.createElement('div');
      catDiv.className = 'profile-category';
      catDiv.innerHTML = `<h3 class="category-title">${cat}</h3>`;
      
      grouped[cat].forEach(field => {
        catDiv.appendChild(createProfileCard(field));
      });
      
      profileCards.appendChild(catDiv);
    }
  });
}

function createProfileCard(field) {
  const card = document.createElement('div');
  card.className = 'card profile-card';
  
  const label = FIELD_LABELS[field.field_id] || field.field_id;
  const statusClass = field.status ? field.status.toLowerCase() : 'ambiguous';
  const displayValue = field.status === 'NOT_FOUND' ? 'Not detected' : (field.value || 'N/A');
  
  let evidenceHtml = '';
  if (field.evidence) {
    evidenceHtml = `
      <button class="evidence-toggle" onclick="toggleEvidence(this)">
        View Evidence
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
      </button>
      <div class="evidence-content">${escapeHtml(field.evidence)}</div>
    `;
  }

  card.innerHTML = `
    <div class="card-header">
      <h4>${escapeHtml(label)}</h4>
      <span class="badge ${statusClass}">${escapeHtml(field.status || 'UNKNOWN')}</span>
    </div>
    <div class="value">${escapeHtml(displayValue)}</div>
    ${evidenceHtml}
  `;
  
  return card;
}

window.toggleEvidence = function(btn) {
  btn.classList.toggle('open');
  const content = btn.nextElementSibling;
  content.classList.toggle('show');
};

function renderFitReport(report) {
  if (!report || report.length === 0) {
    fitSummaryText.textContent = "No requirements analyzed";
    progressFill.style.width = '0%';
    return;
  }

  const matched = report.filter(r => r.match_status === 'MATCHED').length;
  const total = report.length;
  
  fitSummaryText.textContent = `${matched}/${total} Requirements Matched`;
  
  // Animate progress bar slightly after render
  setTimeout(() => {
    progressFill.style.width = `${(matched / total) * 100}%`;
  }, 100);

  report.forEach(item => {
    const card = document.createElement('div');
    card.className = `card fit-card ${item.match_status === 'MISSING' ? 'missing' : ''}`;
    
    const statusClass = item.match_status ? item.match_status.toLowerCase() : 'ambiguous';
    const confClass = item.confidence ? item.confidence.toLowerCase() : 'medium';
    
    let refHtml = '';
    if (item.evidence_ref) {
      const refLabel = FIELD_LABELS[item.evidence_ref] || item.evidence_ref;
      refHtml = `<div class="fit-evidence-ref">Refers to: ${escapeHtml(refLabel)}</div>`;
    }

    card.innerHTML = `
      <div class="fit-card-header">
        <div class="fit-req">${escapeHtml(item.requirement)}</div>
        <span class="badge ${statusClass}">${escapeHtml(item.match_status || 'UNKNOWN')}</span>
      </div>
      <div class="confidence-indicator">
        <span class="confidence-dot ${confClass}"></span>
        Confidence: ${escapeHtml(item.confidence || 'Medium')}
      </div>
      <div class="fit-explanation">${escapeHtml(item.explanation || 'No explanation provided.')}</div>
      ${refHtml}
    `;
    
    fitCards.appendChild(card);
  });
}

// JSON Toggle
toggleJsonBtn.addEventListener('click', () => {
  toggleJsonBtn.classList.toggle('open');
  const isOpening = rawJsonContainer.style.display === 'none';
  toggleJsonBtn.setAttribute('aria-expanded', String(isOpening));
  if (isOpening) {
    rawJsonContainer.style.display = 'block';
  } else {
    rawJsonContainer.style.display = 'none';
  }
});

copyJsonBtn.addEventListener('click', async () => {
  try {
    await navigator.clipboard.writeText(rawJsonCode.textContent);
    const originalHtml = copyJsonBtn.innerHTML;
    copyJsonBtn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" color="var(--success)"><polyline points="20 6 9 17 4 12"></polyline></svg>';
    setTimeout(() => {
      copyJsonBtn.innerHTML = originalHtml;
    }, 2000);
  } catch (_) {
    showError('Unable to copy JSON. Please select and copy it manually.');
  }
});

// Utils
function escapeHtml(unsafe) {
  if (typeof unsafe !== 'string') return unsafe;
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
