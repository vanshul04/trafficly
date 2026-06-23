// State database cache
let knownChallans = new Set();
let currentChallanData = [];
let donutChartInstance = null;
let ledgerChartInstance = null;

// DOM Elements
const elVehicles = document.getElementById('metric-vehicles');
const elViolations = document.getElementById('metric-violations');
const elCompliance = document.getElementById('metric-compliance');
const elOutstanding = document.getElementById('metric-outstanding');
const elClock = document.getElementById('live-clock');
const elStatusDot = document.getElementById('status-dot');
const elStatusMode = document.getElementById('status-mode');
const elFeedSource = document.getElementById('feed-source');
const elAlertStream = document.getElementById('alert-stream');
const elTableBody = document.getElementById('challan-table-body');
const elModal = document.getElementById('challan-modal');
const elModalBody = document.getElementById('modal-body');
const searchInput = document.getElementById('search-plate');

// Update system clock
function updateClock() {
    const now = new Date();
    const pad = (n) => String(n).padStart(2, '0');
    const y = now.getFullYear();
    const m = pad(now.getMonth() + 1);
    const d = pad(now.getDate());
    const h = pad(now.getHours());
    const min = pad(now.getMinutes());
    const s = pad(now.getSeconds());
    elClock.textContent = `${y}-${m}-${d} ${h}:${min}:${s}`;
}
setInterval(updateClock, 1000);

// Initialize Chart.js Donuts and Ledgers
function updateCharts(vehicles, violations, paidCount, unpaidCount) {
    const compliantCount = Math.max(0, vehicles - unpaidCount);
    
    // 1. Donut Chart - Helmet Compliance
    const donutCtx = document.getElementById('donutChart').getContext('2d');
    if (donutChartInstance) {
        donutChartInstance.destroy();
    }
    donutChartInstance = new Chart(donutCtx, {
        type: 'doughnut',
        data: {
            labels: ['Wearing Helmet', 'No Helmet'],
            datasets: [{
                data: [compliantCount, violations],
                backgroundColor: ['#10B981', '#FF4B4B'],
                borderWidth: 1,
                borderColor: 'rgba(255,255,255,0.05)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#9CA3AF', font: { size: 9, family: 'Inter' } }
                },
                title: {
                    display: true,
                    text: 'Helmet Safety Share',
                    color: '#FFF',
                    font: { size: 11, family: 'Outfit', weight: 'bold' }
                }
            },
            cutout: '60%'
        }
    });

    // 2. Bar Chart - Revenue Ledger
    const ledgerCtx = document.getElementById('ledgerChart').getContext('2d');
    if (ledgerChartInstance) {
        ledgerChartInstance.destroy();
    }
    ledgerChartInstance = new Chart(ledgerCtx, {
        type: 'bar',
        data: {
            labels: ['Paid Fines', 'Outstanding'],
            datasets: [{
                label: 'INR (₹)',
                data: [paidCount * 500, unpaidCount * 500],
                backgroundColor: ['rgba(16, 185, 129, 0.45)', 'rgba(255, 75, 75, 0.45)'],
                borderColor: ['#10B981', '#FF4B4B'],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    text: 'Violation Fines Ledger (₹)',
                    color: '#FFF',
                    font: { size: 11, family: 'Outfit', weight: 'bold' }
                }
            },
            scales: {
                x: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9CA3AF', font: { size: 9 } }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#9CA3AF', font: { size: 9 } }
                }
            }
        }
    });
}

// Fetch general system stats
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const data = await res.json();
        
        elVehicles.textContent = data.total_vehicles;
        elStatusMode.textContent = data.mode.toUpperCase();
        
        if (data.mode.includes("CCTV")) {
            elStatusDot.className = "status-dot-glowing";
            elFeedSource.textContent = "CCTV Video Ingestion Mode: 'dummy.mp4'";
        } else {
            elStatusDot.className = "status-dot-glowing";
            elStatusDot.style.backgroundColor = "#F59E0B";
            elStatusDot.style.boxShadow = "0 0 10px #F59E0B";
            elFeedSource.textContent = "Simulation fallback mode";
        }
    } catch (err) {
        console.error("Error fetching stats:", err);
    }
}
setInterval(fetchStats, 2000);

// Fetch registry database and update lists/charts
async function fetchChallans() {
    try {
        const res = await fetch('/api/challans');
        if (!res.ok) return;
        const challans = await res.json();
        currentChallanData = challans;
        
        // Count totals
        const totalViolations = challans.length;
        const paidCount = challans.filter(c => c.status === 'PAID').length;
        const unpaidCount = totalViolations - paidCount;
        
        // Update metric indicators
        elViolations.textContent = totalViolations;
        elOutstanding.textContent = `₹${unpaidCount * 500}`;
        
        // Dynamic compliance recalculation
        const totalVehicles = parseInt(elVehicles.textContent) || totalViolations * 3;
        const rate = totalVehicles > 0 ? (((totalVehicles - unpaidCount) / totalVehicles) * 100).toFixed(1) : 100.0;
        elCompliance.textContent = `${rate}%`;

        // Render logs database
        renderTable(challans);
        
        // Trigger alert additions
        let newDetected = false;
        challans.forEach(ch => {
            if (!knownChallans.has(ch.challan_no)) {
                knownChallans.add(ch.challan_no);
                pushAlert(ch);
                newDetected = true;
            }
        });
        
        // Update graphics
        updateCharts(totalVehicles, totalViolations, paidCount, unpaidCount);
    } catch (err) {
        console.error("Error loading registry:", err);
    }
}
setInterval(fetchChallans, 1500);

// Push alert to dashboard scrolling notifications bar
function pushAlert(ch) {
    const empty = document.getElementById('alert-empty');
    if (empty) empty.remove();
    
    const card = document.createElement('div');
    card.className = 'alert-card';
    card.innerHTML = `
        <div class="alert-meta">
            <span class="alert-title">🚨 ${ch.violation_type.toUpperCase()}</span>
            <span class="alert-time">${ch.timestamp.split(' ')[1]}</span>
        </div>
        <div class="alert-body">
            <span class="alert-desc">Vehicle: <b>${ch.license_plate}</b> (ID: ${ch.track_id})</span>
            <span class="alert-fine">₹${ch.fine_amount}</span>
        </div>
    `;
    elAlertStream.insertBefore(card, elAlertStream.firstChild);
    
    if (elAlertStream.children.length > 15) {
        elAlertStream.lastChild.remove();
    }
}

// Render database registry rows
function renderTable(challans) {
    // If search active, filter table
    const query = searchInput.value.trim().toUpperCase();
    let displayList = challans;
    if (query) {
        displayList = challans.filter(c => c.license_plate.toUpperCase().includes(query));
    }

    if (displayList.length === 0) {
        elTableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted" style="padding: 24px; color: var(--text-muted);">No records found.</td>
            </tr>
        `;
        return;
    }

    elTableBody.innerHTML = '';
    displayList.forEach(ch => {
        const tr = document.createElement('tr');
        tr.onclick = () => openDetails(ch.challan_no);
        
        const isPaid = ch.status === 'PAID';
        const actionBtn = isPaid 
            ? `<button class="btn-action" onclick="event.stopPropagation(); openDetails('${ch.challan_no}')">Review Notice</button>`
            : `<button class="btn-pay" onclick="event.stopPropagation(); payChallan('${ch.challan_no}')">Pay Challan</button>`;
            
        tr.innerHTML = `
            <td>${ch.timestamp}</td>
            <td><b>${ch.challan_no}</b></td>
            <td><code style="font-family: var(--fonts-display); font-size: 0.8rem; background: #0f172a; padding: 3px 8px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05); color: #FFF;">${ch.license_plate}</code></td>
            <td>${ch.violation_type}</td>
            <td><span class="text-muted" style="font-size: 0.75rem;">${ch.section_code}</span></td>
            <td><b>₹${ch.fine_amount}</b></td>
            <td><span class="badge ${isPaid ? 'badge-green' : 'badge-red'}">${ch.status}</span></td>
            <td>
                <div style="display: flex; gap: 8px;">
                    ${actionBtn}
                </div>
            </td>
        `;
        elTableBody.appendChild(tr);
    });
}

// Search bar filter handler
function filterTable() {
    renderTable(currentChallanData);
}

// Trigger payment POST call and update metrics immediately
async function payChallan(challanNo) {
    try {
        const res = await fetch(`/api/challans/${challanNo}/pay`, {
            method: 'POST'
        });
        if (!res.ok) {
            alert("Payment Gateway response error.");
            return;
        }
        const data = await res.json();
        if (data.status === 'success') {
            // Update cache item status immediately
            const target = currentChallanData.find(c => c.challan_no === challanNo);
            if (target) {
                target.status = 'PAID';
            }
            // Trigger quick sound or log alert
            console.log(`Payment settled for Challan: ${challanNo}`);
            
            // Re-render UI table and update lists
            closeModal();
            fetchChallans();
        } else {
            alert(`Payment transaction failed: ${data.message}`);
        }
    } catch (err) {
        console.error("Payment Gateway processing failure:", err);
    }
}

// Open citation details panel modal
function openDetails(challanNo) {
    const ch = currentChallanData.find(c => c.challan_no === challanNo);
    if (!ch) return;
    
    const isPaid = ch.status === 'PAID';
    const payButtonHtml = isPaid
        ? `<span style="color: var(--accent-green); font-weight: 700; display: inline-flex; align-items: center; gap: 6px;">✅ Fine Settled (Transaction Completed)</span>`
        : `<button class="btn-settle" onclick="payChallan('${ch.challan_no}')">Settle Citation Now (Pay ₹${ch.fine_amount})</button>`;

    elModalBody.innerHTML = `
        <div class="modal-grid-container">
            <!-- Notices Metadata -->
            <div class="modal-details-list">
                <div class="detail-row">
                    <span class="detail-lbl">Challan Ref ID</span>
                    <span class="detail-val" style="color: var(--accent-blue);">${ch.challan_no}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-lbl">Offense Plate</span>
                    <span class="detail-val"><b>${ch.license_plate}</b> (ID: ${ch.track_id})</span>
                </div>
                <div class="detail-row">
                    <span class="detail-lbl">Offense Type</span>
                    <span class="detail-val red-val">${ch.violation_type}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-lbl">Legal Section</span>
                    <span class="detail-val">${ch.section_code}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-lbl">Citation Date & Time</span>
                    <span class="detail-val" style="font-family: monospace;">${ch.timestamp}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-lbl">Payment Status</span>
                    <span class="badge ${isPaid ? 'badge-green' : 'badge-red'}">${ch.status}</span>
                </div>
                <div class="detail-row" style="margin-top: 8px;">
                    <span class="detail-lbl">Fine Demand</span>
                    <span class="detail-val large red-val">₹${ch.fine_amount}.00</span>
                </div>
            </div>

            <!-- Evidence crops & QR link -->
            <div class="modal-visuals-grid">
                <div class="visual-holder">
                    <span class="visual-lbl">Plate Crop Evidence</span>
                    <img src="${ch.crop_url}" alt="Rider Evidence Crop" onerror="this.src='/static/no-img.png';">
                </div>
                <div class="visual-holder qr-holder" style="display: ${isPaid ? 'none' : 'flex'}">
                    <span class="visual-lbl">Unified UPI Payment QR</span>
                    <img src="/api/files/challans/${ch.challan_no}_qr.png" alt="UPI Scan QR">
                    <span style="font-size: 0.6rem; color: var(--text-secondary); text-align: center;">Pre-routed to: vanshullalwani2-3@okhdfcbank</span>
                </div>
            </div>
        </div>

        <div class="modal-footer-actions">
            ${payButtonHtml}
            <a href="${ch.pdf_url}" target="_blank" class="btn-primary" style="text-decoration: none; display: inline-flex; align-items: center; justify-content: center;">View PDF Notice</a>
            <button class="btn-cancel" onclick="closeModal()">Close Panel</button>
        </div>
    `;
    
    elModal.classList.add('open');
}

function closeModal() {
    elModal.classList.remove('open');
}

// Background overlay exit
window.onclick = function(event) {
    if (event.target === elModal) {
        closeModal();
    }
}

// Load initial states
fetchStats();
fetchChallans();
updateClock();
