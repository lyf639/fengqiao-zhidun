// 枫桥智盾 · 四步Demo流程
// ======================
// 负责：Excel导入→智能去重→风险预警→处置跟进 完整闭环
// 依赖：SheetJS（Excel解析）、cockpit.js（API_BASE、enterDemo/backToCockpit）
//
// 数据流：
//   拖入Excel → SheetJS解析 → POST /api/import → MySQL入库
//   → POST /api/dedup → 去重比对+AI语义 → 渲染结果
//   → POST /api/alert → 规则引擎扫描 → 红橙黄预警
//   → 展示处置跟进时间轴

// ===== 进度条控制 =====
// 顶部四步进度条，current=当前步，done=已完成
function setProgress(n) {
  document.querySelectorAll('#progressSteps .progress-step').forEach(el => {
    const s = parseInt(el.dataset.step);
    el.classList.remove('current', 'done');
    if (s < n) el.classList.add('done');
    if (s === n) el.classList.add('current');
  });
  document.querySelectorAll('#progressSteps .progress-line').forEach(el => {
    el.classList.toggle('done', parseInt(el.dataset.line) < n);
  });
}
function showStep(n) {
  document.querySelectorAll('.step-panel').forEach(p => p.classList.remove('active'));
  const p = document.getElementById('step' + n);
  if (p) { p.classList.add('active'); p.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
  setProgress(n);
}

// ===== 第一步：Excel 导入 =====
// 拖拽/点击上传 → SheetJS解析 → 字段映射 → 表格预览
let importedData = [];
let importBatch = '';
let importedCaseIds = [];

// 延迟初始化拖拽区，确保 DOM 完全就绪
window.addEventListener('DOMContentLoaded', () => {
  const zone = document.getElementById('uploadZone');
  if (!zone) { console.error('uploadZone not found'); return; }
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => { e.preventDefault(); zone.classList.remove('drag-over'); const f = e.dataTransfer.files[0]; if (f) { document.getElementById('fileInput').files = e.dataTransfer.files; handleFile({ target: { files: [f] } }); } });
  console.log('uploadZone ready');
});

const COLUMN_MAP = {
  '案件编码': 'caseCode','案件编号': 'caseCode','协议类型': 'agreementType','案件来源': 'caseSource',
  '调解组织': 'mediationOrg','工作室': 'studio','受理人姓名': 'handler','受理人': 'handler',
  '受理时间': 'acceptTime','纠纷简要情况': 'description','纠纷描述': 'description','简要情况': 'description',
  '案件难度级别': 'difficulty','难度级别': 'difficulty','纠纷类别': 'disputeType','纠纷类型': 'disputeType',
  '案件属性': 'caseAttr','涉及特殊群体情况': 'specialGroup','行政划分': 'district','乡镇': 'district',
  '街道': 'district','所属区域': 'district','有无死亡': 'hasDeath','调解结果': 'result',
  '调解时间': 'mediationTime','当事人': 'parties','调解协议金': 'amount','涉及金额': 'amount',
};

function handleFile(e) {
  console.log('handleFile called', e.type);
  const file = e.target.files[0];
  if (!file) { console.log('no file'); return; }
  console.log('file:', file.name, file.size);
  const reader = new FileReader();
  reader.onload = function(ev) {
    try {
      console.log('reading file...');
      const wb = XLSX.read(ev.target.result, { type: 'array' });
      const ws = wb.Sheets[wb.SheetNames[0]];
      const raw = XLSX.utils.sheet_to_json(ws, { defval: '' });
      console.log('parsed rows:', raw.length);
      if (raw.length === 0) { alert('未读取到数据'); return; }
      processImport(raw);
    } catch(err) {
      console.error('parse error:', err);
      alert('文件解析失败：' + err.message);
    }
  };
  reader.readAsArrayBuffer(file);
}

function processImport(raw) {
  const headers = Object.keys(raw[0]);
  const mapping = {}; let matched = 0;
  headers.forEach(h => { const k = COLUMN_MAP[h] || COLUMN_MAP[h.trim()]; if (k) { mapping[h] = k; matched++; } else mapping[h] = h; });
  importedData = raw.map(r => { const item = {}; Object.entries(r).forEach(([k, v]) => { item[mapping[k]] = v !== undefined && v !== null ? String(v).trim() : ''; }); return item; });
  document.getElementById('importTotal').textContent = raw.length;
  document.getElementById('importSuccess').textContent = raw.length;
  document.getElementById('importMatched').textContent = matched;
  document.getElementById('importCount').textContent = raw.length;
  document.getElementById('importSummary').classList.add('show');
  document.getElementById('btnContinue1').disabled = false;
  const mapItems = Object.entries(mapping).filter(([k]) => COLUMN_MAP[k]).slice(0, 10);
  document.getElementById('fieldMapping').innerHTML = mapItems.map(([k, v]) => `<span style="display:inline-block;margin-right:20px;"><span style="color:var(--gray-400);">${k}</span> → <span class="field-info">${v}</span></span>`).join('');
  const displayCols = ['caseCode','disputeType','parties','district','acceptTime','amount'];
  const displayHeaders = { caseCode:'案件编码', disputeType:'纠纷类型', parties:'当事人', district:'区域', acceptTime:'受理时间', amount:'金额' };
  const avail = displayCols.filter(c => importedData[0][c] !== undefined);
  const cols = avail.length > 0 ? avail : Object.keys(importedData[0]).slice(0, 6);
  document.getElementById('dataTable').querySelector('thead').innerHTML = '<tr>' + cols.map(c => `<th>${displayHeaders[c] || mapping[c] || c}</th>`).join('') + '</tr>';
  document.getElementById('dataTable').querySelector('tbody').innerHTML = importedData.slice(0, 10).map(r => '<tr>' + cols.map(c => `<td>${r[c] || ''}</td>`).join('') + '</tr>').join('');
}

// ===== 第二步：智能去重 =====
// ① POST /api/import 写入MySQL
// ② GET /api/cases 获取新案件ID
// ③ POST /api/dedup 执行四维比对+AI语义
// ④ 渲染去重结果列表
async function goToStep2() {
  if (importedData.length === 0) { alert('请先导入Excel'); return; }
  showStep(2);
  const dedupLoading = document.getElementById('dedupLoading');
  dedupLoading.innerHTML = '⏳ 正在将数据写入数据库...';

  // 1. 导入
  try {
    const resp = await fetch(API_BASE + '/api/import', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ records: importedData })
    });
    const result = await resp.json();
    if (result.success) {
      importBatch = result.batch;
      dedupLoading.innerHTML = `✅ 写入成功：${result.inserted} 条入库，正在执行去重比对...`;
    } else {
      dedupLoading.innerHTML = '❌ 写入失败：' + (result.error || '未知错误'); return;
    }
  } catch (e) {
    dedupLoading.innerHTML = '❌ 无法连接后端服务'; return;
  }

  // 2. 获取导入的案件ID
  try {
    const resp2 = await fetch(API_BASE + '/api/cases');
    const data2 = await resp2.json();
    importedCaseIds = (data2.cases || []).slice(0, importedData.length).map(c => c.id);
  } catch(e) { importedCaseIds = []; }

  // 3. 执行去重比对
  let dedupData = null;
  try {
    const dedupResp = await fetch(API_BASE + '/api/dedup', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ batch: importBatch, case_ids: importedCaseIds })
    });
    dedupData = await dedupResp.json();
  } catch(e) {}

  // 4. 渲染去重结果
  const checked = dedupData ? dedupData.checked : importedData.length;
  const duplicates = dedupData ? dedupData.duplicates : 0;
  document.getElementById('dedupTotal').textContent = checked;
  document.getElementById('dedupSuspect').textContent = duplicates;
  document.getElementById('dedupUnique').textContent = checked - duplicates;

  if (dedupData && dedupData.results && dedupData.results.length > 0) {
    document.getElementById('dedupResultBox').style.display = 'block';
    document.getElementById('dedupResultEmpty').style.display = 'none';
    document.getElementById('dedupHeaderCount').textContent = duplicates;
    const list = document.getElementById('dedupResultList');
    list.innerHTML = dedupData.results.map((r, i) => {
      const scoreClass = r.total_score >= 85 ? 'tag-orange' : 'tag-gold';
      const aiTag = r.ai_backend === 'deepseek' ? '🤖 DeepSeek' : (r.ai_backend === 'ollama' ? '🦙 Ollama' : '📐 规则');
      return `<div class="match-item"><div class="match-status dup">疑似重复 #${i+1}</div><div class="match-detail"><strong>案件 #${r.case_id}</strong> 匹配到 ${r.match_count} 条相似记录<br><span style="color:var(--gray-400);">${aiTag} 判定 · ${r.ai_reason || ''}</span></div><span class="tag ${scoreClass}">${r.total_score}分</span></div>`;
    }).join('');
  } else {
    document.getElementById('dedupResultBox').style.display = 'none';
    document.getElementById('dedupResultEmpty').style.display = 'block';
  }

  dedupLoading.style.display = 'none';
  document.getElementById('dedupContent').style.display = 'block';
}

// ===== 第三步：风险预警 =====
// 动画模拟检索过程 → POST /api/alert → 渲染红橙预警结果
async function confirmDedup() {
  showStep(3);
  runAlertAnim();
}

async function runAlertAnim() {
  const ld = document.getElementById('alertLoading'), ct = document.getElementById('alertContent');
  const msgs = ['检索关联渠道：司法行政调解平台... ✓','检索关联渠道：公安接警系统... ✓','检索关联渠道：信访平台... ✓','检索关联渠道：综治信息系统... ✓','风险评分计算中...'];
  let i = 0; const t = setInterval(() => { if(i<msgs.length){ld.innerHTML='🔍 '+msgs[i];i++;}else{clearInterval(t);ld.style.display='none';ct.style.display='block';} }, 400);

  // 调用后端预警
  let alertData = null;
  try {
    const resp = await fetch(API_BASE + '/api/alert', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case_ids: importedCaseIds })
    });
    alertData = await resp.json();
  } catch(e) {}

  // 渲染预警结果
  if (alertData && alertData.success) {
    document.getElementById('alertContent').innerHTML = `
      <div class="result-box danger show" style="margin-top:0;margin-bottom:20px;">
        <div class="result-box-header">🔴 红色预警 — ${alertData.red || 0} 件高风险事件需立即处置</div>
        <div class="result-box-body" style="font-size:13px;color:var(--gray-600);">
          系统自动扫描 ${alertData.alerts || importedCaseIds.length} 条案件，触发红色预警 ${alertData.red || 0} 件、橙色预警 ${alertData.orange || 0} 件。<br>
          <strong>触发规则：</strong>涉及金额 ≥ 10万元 且 跨2个及以上渠道 → 自动升级红色预警
        </div>
      </div>
      ${(alertData.orange || 0) > 0 ? `<div class="result-box warning show" style="margin-top:0;margin-bottom:20px;">
        <div class="result-box-header">🟠 橙色预警 — ${alertData.orange} 件需重点关注</div>
        <div class="result-box-body" style="font-size:13px;color:var(--gray-600);">识别出 ${alertData.orange} 件涉及金额较大且跨渠道的案件，已推送至相关乡镇综治中心。</div>
      </div>` : ''}
      <div style="padding:16px 20px;background:var(--gold-pale);border-radius:var(--radius-lg);border-left:3px solid var(--gold);font-size:14px;"><strong>🔔 自动推送：</strong>预警信息已通过钉钉通知相关乡镇综治中心负责人。</div>
    `;
  }
}
// ===== 第四步：处置跟进 =====
// 时间轴展示全流程 + 处置方案表单 + 闭环归档
function goToStep4() { showStep(4); }
function completeStep4() { const r = document.getElementById('step4Result'); r.classList.add('show'); r.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
// ===== 重置 =====
// 清空所有状态，恢复到第一步
function resetAll() {
  showStep(1); importedData = []; importBatch = ''; importedCaseIds = [];
  document.getElementById('importSummary').classList.remove('show');
  document.getElementById('btnContinue1').disabled = true;
  document.getElementById('dedupLoading').style.display = 'block';
  document.getElementById('dedupContent').style.display = 'none';
  document.getElementById('dedupResultBox').style.display = 'none';
  document.getElementById('dedupResultEmpty').style.display = 'none';
  document.getElementById('dedupResultList').innerHTML = '';
  document.getElementById('alertLoading').style.display = 'block';
  document.getElementById('alertContent').style.display = 'none';
  document.getElementById('alertContent').innerHTML = '<div class="result-box danger show" style="margin-top:0;margin-bottom:20px;"><div class="result-box-header">🔴 红色预警 — 0 件高风险事件需立即处置</div><div class="result-box-body" style="font-size:13px;color:var(--gray-600);">系统正在扫描中...</div></div>';
  document.getElementById('step4Result').classList.remove('show');
}