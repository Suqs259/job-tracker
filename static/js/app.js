const STATUSES = [...document.querySelectorAll('#filter-status option')].map(o => o.value).filter(Boolean);

const state = {
  keyword: '',
  status: '',
  page: 1,
  pageSize: 20,
  total: 0,
  pages: 0,
  records: [],
  statusChart: null,
  channelChart: null,
};

const $ = (id) => document.getElementById(id);

function createEl(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = text;
  return node;
}

async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (response.status === 401) {
    window.location.href = '/login';
    throw new Error('登录已过期，请重新登录');
  }
  if (response.status === 204) return null;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `请求失败（${response.status}）`);
  return data;
}

async function loadRecords() {
  const params = new URLSearchParams({
    page: state.page,
    page_size: state.pageSize,
  });
  if (state.keyword) params.set('keyword', state.keyword);
  if (state.status) params.set('status', state.status);

  const data = await api(`/api/applications?${params.toString()}`);
  state.records = data.items;
  state.total = data.total;
  state.page = data.page;
  state.pages = data.pages;
  renderTable();
  renderPagination();
}

async function loadStats() {
  const stats = await api('/api/stats');
  $('stat-total').textContent = stats.total;
  $('stat-interview').textContent = stats.interview;
  $('stat-offer').textContent = stats.offers;
  $('stat-interview-rate').textContent = `转化率 ${stats.interview_rate}%`;
  $('stat-offer-rate').textContent = `转化率 ${stats.offer_rate}%`;
  $('stat-active').textContent = stats.total - stats.offers - (stats.by_status['已挂'] || 0);
  renderStatusChart(stats.by_status);
  renderChannelChart(stats.by_channel);
}

function renderTable() {
  const tbody = $('table-body');
  tbody.replaceChildren();
  $('list-count').textContent = `共 ${state.total} 条`;
  $('empty-hint').hidden = state.records.length > 0;

  for (const record of state.records) {
    const tr = document.createElement('tr');

    const companyCell = createEl('td');
    companyCell.appendChild(createEl('span', 'company', record.company));
    if (record.jd_url) {
      const link = createEl('a', 'link', ' JD');
      link.href = record.jd_url;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      companyCell.appendChild(link);
    }
    tr.appendChild(companyCell);

    tr.appendChild(createEl('td', '', record.position));
    tr.appendChild(createEl('td', '', record.city || '—'));
    tr.appendChild(createEl('td', '', record.channel || '—'));
    tr.appendChild(createEl('td', '', record.apply_date));

    const statusCell = createEl('td');
    const badge = createEl('span', 'badge', record.status);
    badge.dataset.status = record.status;
    statusCell.appendChild(badge);
    tr.appendChild(statusCell);

    const actionCell = createEl('td');
    const editBtn = createEl('button', 'btn-link', '编辑');
    editBtn.type = 'button';
    editBtn.addEventListener('click', () => openDialog(record));
    const deleteBtn = createEl('button', 'btn-link danger', '删除');
    deleteBtn.type = 'button';
    deleteBtn.addEventListener('click', () => removeRecord(record));
    actionCell.append(editBtn, deleteBtn);
    tr.appendChild(actionCell);

    if (record.note) tr.title = record.note;
    tbody.appendChild(tr);
  }
}

function renderPagination() {
  const pager = $('pager');
  pager.hidden = state.pages <= 1;
  $('page-info').textContent = `第 ${state.page} / ${state.pages} 页`;
  $('btn-prev').disabled = state.page <= 1;
  $('btn-next').disabled = state.page >= state.pages;
}

function renderStatusChart(byStatus) {
  const labels = STATUSES.filter(Boolean);
  const data = labels.map(label => byStatus[label] || 0);
  const ctx = $('chart-status');
  if (!ctx) return;

  if (state.statusChart) {
    state.statusChart.data.datasets[0].data = data;
    state.statusChart.update();
    return;
  }
  state.statusChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ data, backgroundColor: '#3b82f6', borderRadius: 6, maxBarThickness: 36 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#f1f5f9' } },
        x: { grid: { display: false }, ticks: { font: { size: 11 } } },
      },
    },
  });
}

function renderChannelChart(byChannel) {
  const ctx = $('chart-channel');
  if (!ctx) return;
  const labels = byChannel.map(item => item.name);
  const data = byChannel.map(item => item.count);
  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#64748b', '#0ea5e9'];

  if (state.channelChart) {
    state.channelChart.data.labels = labels.length ? labels : ['暂无数据'];
    state.channelChart.data.datasets[0].data = data.length ? data : [1];
    state.channelChart.data.datasets[0].backgroundColor = data.length
      ? colors.slice(0, labels.length)
      : ['#e5e7eb'];
    state.channelChart.update();
    return;
  }
  state.channelChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels.length ? labels : ['暂无数据'],
      datasets: [{
        data: data.length ? data : [1],
        backgroundColor: data.length ? colors.slice(0, labels.length) : ['#e5e7eb'],
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '58%',
      plugins: { legend: { position: 'right', labels: { boxWidth: 10, font: { size: 12 } } } },
    },
  });
}

function openDialog(record = null) {
  $('form-error').hidden = true;
  $('record-form').reset();
  $('record-id').value = record ? record.id : '';
  $('dialog-title').textContent = record ? '编辑投递' : '新增投递';

  if (record) {
    $('f-company').value = record.company;
    $('f-position').value = record.position;
    $('f-city').value = record.city || '';
    $('f-channel').value = record.channel || '';
    $('f-salary').value = record.salary || '';
    $('f-apply-date').value = record.apply_date;
    $('f-status').value = record.status;
    $('f-jd-url').value = record.jd_url || '';
    $('f-note').value = record.note || '';
  } else {
    $('f-apply-date').value = new Date().toISOString().slice(0, 10);
  }
  $('form-dialog').showModal();
  $('f-company').focus();
}

function collectForm() {
  return {
    company: $('f-company').value.trim(),
    position: $('f-position').value.trim(),
    city: $('f-city').value.trim(),
    channel: $('f-channel').value.trim(),
    salary: $('f-salary').value.trim(),
    apply_date: $('f-apply-date').value,
    status: $('f-status').value,
    jd_url: $('f-jd-url').value.trim(),
    note: $('f-note').value.trim(),
  };
}

async function submitForm(event) {
  event.preventDefault();
  const id = $('record-id').value;
  const payload = collectForm();
  const saveBtn = $('btn-save');
  saveBtn.disabled = true;
  saveBtn.textContent = '保存中...';

  try {
    if (id) {
      await api(`/api/applications/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
    } else {
      await api('/api/applications', { method: 'POST', body: JSON.stringify(payload) });
      state.page = 1;
    }
    $('form-dialog').close();
    await Promise.all([loadRecords(), loadStats()]);
  } catch (error) {
    $('form-error').textContent = error.message;
    $('form-error').hidden = false;
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = '保存';
  }
}

async function removeRecord(record) {
  if (!confirm(`确定删除「${record.company} · ${record.position}」这条记录吗？`)) return;
  try {
    await api(`/api/applications/${record.id}`, { method: 'DELETE' });
    await Promise.all([loadRecords(), loadStats()]);
  } catch (error) {
    alert(error.message);
  }
}

let searchTimer = null;
$('search').addEventListener('input', (event) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.keyword = event.target.value.trim();
    state.page = 1;
    loadRecords().catch(error => alert(error.message));
  }, 250);
});

$('filter-status').addEventListener('change', (event) => {
  state.status = event.target.value;
  state.page = 1;
  loadRecords().catch(error => alert(error.message));
});

$('btn-prev').addEventListener('click', () => {
  if (state.page <= 1) return;
  state.page -= 1;
  loadRecords().catch(error => alert(error.message));
});

$('btn-next').addEventListener('click', () => {
  if (state.page >= state.pages) return;
  state.page += 1;
  loadRecords().catch(error => alert(error.message));
});

$('btn-create').addEventListener('click', () => openDialog());
$('btn-cancel').addEventListener('click', () => $('form-dialog').close());
$('record-form').addEventListener('submit', submitForm);

$('btn-logout').addEventListener('click', async () => {
  await fetch('/api/auth/logout', { method: 'POST' });
  window.location.href = '/login';
});

Promise.all([loadRecords(), loadStats()]).catch(error => {
  $('empty-hint').hidden = false;
  $('empty-hint').textContent = `加载失败：${error.message}`;
});
