// 枫桥智盾 · 驾驶舱逻辑
const API_BASE = window.location.port === '5000' ? '' : 'http://localhost:5000';

// ===== COCKPIT CLOCK & COUNTERS =====
function updateClock() {
  const now = new Date();
  document.getElementById('cockpitClock').textContent = now.toLocaleDateString('zh-CN') + ' ' + now.toLocaleTimeString('zh-CN', { hour12: false });
}
updateClock(); setInterval(updateClock, 10000);

// Animate counters on load
function animateCounters() {
  document.querySelectorAll('.counter').forEach(el => {
    const target = parseInt(el.dataset.target);
    let current = 0;
    const step = Math.ceil(target / 40);
    const timer = setInterval(() => {
      current += step;
      if (current >= target) { current = target; clearInterval(timer); }
      el.textContent = current;
    }, 30);
  });
}

// Mini chart
let miniChart = null;
function drawMiniChart() {
  const c = document.getElementById('chartMini');
  if (!c) return;
  if (miniChart) miniChart.destroy();
  miniChart = new Chart(c, {
    type: 'bar',
    data: {
      labels: ['菜园镇','五龙乡','嵊山镇','洋山镇','枸杞乡'],
      datasets: [
        { label: '红色', data: [1,0,0,0,1], backgroundColor: '#C41E3A', borderRadius: 2 },
        { label: '橙色', data: [2,1,1,1,2], backgroundColor: '#E67E22', borderRadius: 2 },
        { label: '黄色', data: [5,3,2,2,2], backgroundColor: '#D4A83A', borderRadius: 2 },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12, font: { size: 10 } } } },
      scales: { x: { stacked: true }, y: { stacked: true, ticks: { stepSize: 2 } } }
    }
  });
}

// Live feed - fetch from Redis-backed API
let feedLastTs = '';
async function fetchFeed() {
  try {
    const resp = await fetch(API_BASE + '/api/feed');
    const items = await resp.json();
    if (!items.length) return;
    const ul = document.getElementById('liveFeed');
    const typeMap = { danger: 'red', warning: 'orange', info: 'green' };
    ul.innerHTML = '';
    items.forEach(item => {
      const li = document.createElement('li');
      const dotClass = typeMap[item.type] || 'green';
      li.innerHTML = `<span class="lf-dot ${dotClass}"></span><span class="lf-text">${item.msg}</span><span class="lf-time">${item.time}</span>`;
      li.style.animation = 'fadeSlideIn 0.5s ease';
      ul.appendChild(li);
    });
  } catch(e) {}
}

// Fetch dashboard stats from API and update counters
async function fetchDashboard() {
  try {
    const resp = await fetch(API_BASE + '/api/dashboard');
    const data = await resp.json();
    document.querySelectorAll('.counter').forEach(el => {
      const key = el.dataset.key;
      if (data[key] !== undefined) {
        el.dataset.target = data[key];
        el.textContent = data[key];
      }
    });
  } catch(e) {}
}

// Init cockpit
window.addEventListener('DOMContentLoaded', () => {
  fetchDashboard().then(() => animateCounters());
  fetchFeed();
  initReportSelects();
  setTimeout(drawMiniChart, 400);
  setInterval(fetchDashboard, 5000);
  setInterval(fetchFeed, 5000);
});

// ===== REPORT GENERATION =====
function initReportSelects() {
  const y = document.getElementById('reportYear');
  const now = new Date().getFullYear();
  for (let i = now; i >= 2020; i--) { y.innerHTML += `<option value="${i}">${i}年</option>`; }
  onReportPeriodChange();
}

function onReportPeriodChange() {
  const p = document.getElementById('reportPeriod').value;
  const sub = document.getElementById('reportSub');
  sub.innerHTML = '';
  if (p === 'monthly') {
    sub.style.display = '';
    for (let i = 1; i <= 12; i++) sub.innerHTML += `<option value="${i}">${i}月</option>`;
  } else if (p === 'quarterly') {
    sub.style.display = '';
    for (let i = 1; i <= 4; i++) sub.innerHTML += `<option value="${i}">第${i}季度</option>`;
  } else {
    sub.style.display = 'none';
  }
}

async function generateReport() {
  document.getElementById('reportModal').classList.add('show');
  document.getElementById('reportModalBody').innerHTML = '<div class="report-loading"><span class="spinner"></span>AI 正在分析数据，生成报告...</div>';
  const period = document.getElementById('reportPeriod').value;
  const year = parseInt(document.getElementById('reportYear').value);
  const subEl = document.getElementById('reportSub');
  const body = { period, year };
  if (period === 'monthly') body.month = parseInt(subEl.value);
  if (period === 'quarterly') body.quarter = parseInt(subEl.value);

  try {
    const resp = await fetch(API_BASE + '/api/report/generate', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    });
    const data = await resp.json();
    if (data.success) {
      document.getElementById('reportModalTitle').textContent = data.title;
      const s = data.stats;
      document.getElementById('reportModalBody').innerHTML = `
        <div class="report-stats">
          <div class="report-stat"><div class="rs-val">${s.total}</div><div class="rs-lbl">事件总数</div></div>
          <div class="report-stat"><div class="rs-val" style="color:var(--green);">${s.resolve_rate}%</div><div class="rs-lbl">化解率</div></div>
          <div class="report-stat"><div class="rs-val" style="color:var(--red);">${s.alert_red}</div><div class="rs-lbl">红色预警</div></div>
          <div class="report-stat"><div class="rs-val">¥${(s.total_amount/10000).toFixed(1)}万</div><div class="rs-lbl">涉及金额</div></div>
        </div>
        <div style="margin-bottom:16px;font-size:12px;color:var(--gray-400);">🤖 AI 引擎：${data.ai_backend === 'deepseek' ? 'DeepSeek-v4-pro 云端' : data.ai_backend === 'ollama' ? 'Ollama 本地' : '规则引擎'}</div>
        <div class="report-content">${marked.parse(data.analysis || '')}</div>
      `;
    }
  } catch(e) {
    document.getElementById('reportModalBody').innerHTML = '<p style="color:var(--red);text-align:center;">生成失败：请确认后端服务已启动</p>';
  }
}

function closeReport() {
  document.getElementById('reportModal').classList.remove('show');
}
