const API = window.location.origin + '/api/v1';
let token = localStorage.getItem('admin_token') || '';
let refreshToken = localStorage.getItem('admin_refresh') || '';
let currentUser = null;
let ws = null;
let charts = {};

const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);

async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    try {
        const res = await fetch(API + path, { ...options, headers });
        if (res.status === 401 && refreshToken) {
            if (await refreshAccessToken()) {
                headers['Authorization'] = `Bearer ${token}`;
                return await (await fetch(API + path, { ...options, headers })).json();
            }
        }
        const data = await res.json().catch(() => ({}));
        if (!res.ok) { if (res.status === 401) { localStorage.clear(); showLogin(); } throw new Error(data.error || 'Request failed'); }
        return data;
    } catch (e) { toast('Error: ' + e.message, 'error'); throw e; }
}

async function refreshAccessToken() {
    try {
        const res = await fetch(API + '/auth/refresh', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: refreshToken }) });
        if (res.ok) { const d = await res.json(); token = d.token; localStorage.setItem('admin_token', token); return true; }
    } catch (e) {}
    return false;
}

function toast(msg, type = 'info', ms = 4000) {
    const colors = { success: 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300', error: 'bg-red-500/20 border-red-500/50 text-red-300', info: 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300', warning: 'bg-amber-500/20 border-amber-500/50 text-amber-300' };
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    const d = document.createElement('div');
    d.className = `${colors[type]} border backdrop-blur-lg px-4 py-3 rounded-lg shadow-lg max-w-sm flex items-center gap-2 transition-all`;
    d.innerHTML = `<span>${icons[type]}</span><span class="text-sm">${msg}</span>`;
    $('#toastContainer').appendChild(d);
    setTimeout(() => { d.style.opacity = '0'; setTimeout(() => d.remove(), 300); }, ms);
}

const fmt = (n) => { if (n == null) return '0'; if (n >= 1e9) return (n/1e9).toFixed(1)+'B'; if (n >= 1e6) return (n/1e6).toFixed(1)+'M'; if (n >= 1e3) return (n/1e3).toFixed(1)+'K'; return String(n); };
const fmtDate = (d) => d ? new Date(d).toLocaleString() : '-';

function togglePassword() { $('#loginPassword').type = $('#loginPassword').type === 'password' ? 'text' : 'password'; }

$('#loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        const body = { username: $('#loginUsername').value, password: $('#loginPassword').value };
        if ($('#login2fa').value) body.code = $('#login2fa').value;
        const res = await fetch(API + '/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        const data = await res.json();
        if (!res.ok) { if (data.require_2fa) { $('#twoFactorField').classList.remove('hidden'); $('#login2fa').focus(); return; } throw new Error(data.error || 'Login failed'); }
        token = data.token; refreshToken = data.refresh_token;
        localStorage.setItem('admin_token', token);
        localStorage.setItem('admin_refresh', refreshToken);
        currentUser = data.user;
        showApp();
    } catch (e) { const err = $('#loginError'); err.textContent = e.message; err.classList.remove('hidden'); }
});

function showLogin() { $('#loginScreen').classList.remove('hidden'); $('#appScreen').classList.add('hidden'); }

function showApp() {
    $('#loginScreen').classList.add('hidden'); $('#appScreen').classList.remove('hidden');
    if (currentUser) {
        $('#userName').textContent = currentUser.full_name || currentUser.username;
        $('#userEmail').textContent = currentUser.email;
        $('#userAvatar').textContent = (currentUser.full_name || currentUser.username)[0].toUpperCase();
    }
    loadPage('dashboard');
    connectWS();
}

function logout() { api('/auth/logout', { method: 'POST' }).catch(() => {}); localStorage.clear(); token = ''; refreshToken = ''; if (ws) ws.close(); showLogin(); }

function connectWS() {
    const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/admin?token=' + token;
    try { ws = new WebSocket(wsUrl); ws.onmessage = (e) => { try { const d = JSON.parse(e.data); if (d.type === 'new_user') toast('New user: ' + d.username, 'info'); if (d.type === 'scan_complete') toast('Scan done: ' + d.target, 'success'); } catch (x) {} }; ws.onclose = () => setTimeout(connectWS, 5000); } catch (e) {}
}

let currentPage = 'dashboard';
$$('.sidebar-item').forEach(item => item.addEventListener('click', (e) => { e.preventDefault(); $$('.sidebar-item').forEach(i => i.classList.remove('active')); item.classList.add('active'); loadPage(item.dataset.page); }));

async function loadPage(page) {
    currentPage = page;
    const titles = { dashboard: '📊 Dashboard', users: '👥 Users', scans: '🔍 Scans', organizations: '🏢 Organizations', analytics: '📈 Analytics', lab: '🧪 Lab Tools', logs: '📜 Activity Logs', broadcast: '📢 Broadcast', settings: '⚙️ Settings', system: '💚 System' };
    $('#pageTitle').textContent = titles[page] || page;
    $('#pageContent').innerHTML = '<div class="flex items-center justify-center h-64"><div class="animate-spin w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full"></div></div>';
    try { await ({ dashboard: renderDashboard, users: renderUsers, scans: renderScans, organizations: renderOrgs, analytics: renderAnalytics, lab: renderLab, logs: renderLogs, broadcast: renderBroadcast, settings: renderSettings, system: renderSystem })[page](); }
    catch (e) { $('#pageContent').innerHTML = `<div class="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-300">Error: ${e.message}</div>`; }
}

async function renderDashboard() {
    const [s, c] = await Promise.all([api('/admin/dashboard/stats'), api('/admin/dashboard/charts?days=30')]);
    $('#pageSubtitle').textContent = `Overview • ${new Date().toLocaleDateString()}`;
    $('#pageContent').innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            ${statCard('👥 Users', s.users.total, '+' + s.users.new_24h + ' today', 'from-blue-500 to-cyan-500')}
            ${statCard('🔍 Scans', s.scans.total, s.scans.running + ' running', 'from-emerald-500 to-teal-500')}
            ${statCard('🏢 Organizations', s.organizations.total, s.organizations.active + ' active', 'from-purple-500 to-pink-500')}
            ${statCard('💰 Revenue', '$' + fmt(s.revenue.total), '$' + fmt(s.revenue.month_30d) + ' /30d', 'from-amber-500 to-orange-500')}
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div class="glass rounded-xl p-6"><h3 class="text-lg font-semibold mb-4">📈 User Growth</h3><canvas id="userGrowthChart" height="200"></canvas></div>
            <div class="glass rounded-xl p-6"><h3 class="text-lg font-semibold mb-4">🔍 Scan Activity</h3><canvas id="scanGrowthChart" height="200"></canvas></div>
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="glass rounded-xl p-6">
                <h3 class="text-lg font-semibold mb-4">💎 Plans</h3>
                ${planBar('Free', s.subscriptions.free, s.users.total, 'slate')}
                ${planBar('Pro', s.subscriptions.pro, s.users.total, 'indigo')}
                ${planBar('Business', s.subscriptions.business, s.users.total, 'purple')}
                ${planBar('Enterprise', s.subscriptions.enterprise, s.users.total, 'amber')}
            </div>
            <div class="glass rounded-xl p-6 lg:col-span-2">
                <h3 class="text-lg font-semibold mb-4">⚡ Quick Actions</h3>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <button onclick="loadPage('users')" class="p-4 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg text-left"><div class="text-2xl mb-1">👤</div><div class="text-sm font-medium">Users</div></button>
                    <button onclick="loadPage('broadcast')" class="p-4 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg text-left"><div class="text-2xl mb-1">📢</div><div class="text-sm font-medium">Broadcast</div></button>
                    <button onclick="loadPage('lab')" class="p-4 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg text-left"><div class="text-2xl mb-1">🧪</div><div class="text-sm font-medium">Lab</div></button>
                    <button onclick="loadPage('system')" class="p-4 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg text-left"><div class="text-2xl mb-1">💚</div><div class="text-sm font-medium">System</div></button>
                </div>
            </div>
        </div>`;
    drawChart('userGrowthChart', c.user_growth, 'indigo');
    drawChart('scanGrowthChart', c.scan_growth, 'emerald');
}

function statCard(title, value, change, gradient) { return `<div class="glass rounded-xl p-5 card-hover"><div class="flex items-start justify-between mb-3"><div class="text-sm text-slate-400">${title}</div><div class="w-8 h-8 rounded-lg bg-gradient-to-br ${gradient} flex items-center justify-center text-xs">●</div></div><div class="text-3xl font-bold mb-1">${value}</div><div class="text-xs text-emerald-400">${change}</div></div>`; }

function planBar(name, count, total, color) { const p = total ? (count / total * 100).toFixed(1) : 0; return `<div class="mb-3"><div class="flex justify-between text-sm mb-1"><span>${name}</span><span class="text-slate-400">${count} (${p}%)</span></div><div class="h-2 bg-slate-800 rounded-full overflow-hidden"><div class="h-full bg-${color}-500" style="width:${p}%"></div></div></div>`; }

function drawChart(id, data, color) {
    const ctx = document.getElementById(id); if (!ctx) return;
    if (charts[id]) charts[id].destroy();
    charts[id] = new Chart(ctx, { type: 'line', data: { labels: data.map(d => d.date), datasets: [{ data: data.map(d => d.count), borderColor: color === 'indigo' ? '#6366f1' : '#10b981', backgroundColor: color === 'indigo' ? 'rgba(99,102,241,0.1)' : 'rgba(16,185,129,0.1)', tension: 0.4, fill: true }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { color: 'rgba(148,163,184,0.1)' }, ticks: { color: '#94a3b8', maxTicksLimit: 7 } }, y: { grid: { color: 'rgba(148,163,184,0.1)' }, ticks: { color: '#94a3b8' }, beginAtZero: true } } } });
}

async function renderUsers(p = 1) {
    const d = await api(`/admin/users?page=${p}&per_page=20`);
    $('#pageSubtitle').textContent = `Total: ${d.total} users`;
    $('#pageContent').innerHTML = `<div class="glass rounded-xl p-6"><div class="flex justify-between mb-4"><input id="userSearch" placeholder="🔍 Search..." class="px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg w-64 text-sm"><button onclick="loadPage('users')" class="px-4 py-2 bg-slate-700 rounded-lg text-sm">🔄</button></div><div class="overflow-x-auto scrollbar-thin"><table class="w-full text-sm"><thead class="text-left text-slate-400 border-b border-slate-700"><tr><th class="pb-3">User</th><th class="pb-3">Email</th><th class="pb-3">Role</th><th class="pb-3">Plan</th><th class="pb-3">Status</th><th class="pb-3">Actions</th></tr></thead><tbody>${d.users.map(uRow).join('')}</tbody></table></div><div class="flex justify-between mt-4 text-sm"><div class="text-slate-400">Page ${d.page}/${d.pages}</div><div class="flex gap-2">${d.page > 1 ? `<button onclick="renderUsers(${d.page-1})" class="px-3 py-1 bg-slate-700 rounded">←</button>` : ''}${d.page < d.pages ? `<button onclick="renderUsers(${d.page+1})" class="px-3 py-1 bg-slate-700 rounded">→</button>` : ''}</div></div></div>`;
    if ($('#userSearch')) $('#userSearch').addEventListener('input', debounce(async (e) => { const q = e.target.value; if (q.length > 0 && q.length < 2) return; const nd = await api(`/admin/users?page=1&per_page=20&search=${q}`); document.querySelector('tbody').innerHTML = nd.users.map(uRow).join(''); }, 300));
}

function uRow(u) { return `<tr class="border-b border-slate-800 hover:bg-slate-800/30"><td class="py-3"><div class="flex items-center gap-2"><div class="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-xs">${(u.full_name || u.username)[0]}</div><span>${u.full_name || u.username}</span></div></td><td class="text-slate-400">${u.email}</td><td><span class="px-2 py-0.5 rounded ${u.is_admin ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-700'} text-xs">${u.role || 'user'}</span></td><td><span class="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-xs">${u.plan || 'free'}</span></td><td>${u.is_banned ? '🔴' : u.is_active ? '🟢' : '⚪'}</td><td class="flex gap-1"><button onclick="uAct(${u.id},'ban')" class="px-2 py-1 bg-red-500/20 text-red-300 rounded text-xs">${u.is_banned ? 'Unban' : 'Ban'}</button><button onclick="uAct(${u.id},'reset')" class="px-2 py-1 bg-amber-500/20 text-amber-300 rounded text-xs">Reset</button></td></tr>`; }

async function uAct(id, action) { try { if (action === 'ban') await api(`/admin/users/${id}/${id ? 'ban' : ''}`, { method: 'POST', body: JSON.stringify({ reason: 'Admin' }) }); else if (action === 'unban') await api(`/admin/users/${id}/unban`, { method: 'POST' }); else if (action === 'reset') { const d = await api(`/admin/users/${id}/reset-password`, { method: 'POST' }); prompt('New password (save!):', d.new_password); return; } toast('Done', 'success'); loadPage('users'); } catch (e) { toast(e.message, 'error'); } }

async function renderScans() { const d = await api('/admin/scans?per_page=50'); $('#pageSubtitle').textContent = `${d.total} scans`; $('#pageContent').innerHTML = `<div class="glass rounded-xl p-6"><table class="w-full text-sm"><thead class="text-left text-slate-400 border-b border-slate-700"><tr><th class="pb-3">Target</th><th>Status</th><th>User</th><th>Created</th></tr></thead><tbody>${d.scans.map(s => `<tr class="border-b border-slate-800"><td class="py-3 mono text-xs">${s.target}</td><td><span class="px-2 py-0.5 rounded text-xs ${s.status==='completed'?'bg-emerald-500/20 text-emerald-300':s.status==='running'?'bg-amber-500/20 text-amber-300':'bg-red-500/20 text-red-300'}">${s.status}</span></td><td>${s.user_id}</td><td class="text-slate-400 text-xs">${fmtDate(s.created_at)}</td></tr>`).join('')}</tbody></table></div>`; }
async function renderOrgs() { const o = await api('/admin/organizations'); $('#pageContent').innerHTML = `<div class="glass rounded-xl p-6"><table class="w-full text-sm"><thead class="text-left text-slate-400 border-b border-slate-700"><tr><th class="pb-3">Name</th><th>Plan</th><th>Seats</th><th>Status</th></tr></thead><tbody>${o.map(x => `<tr class="border-b border-slate-800"><td class="py-3 font-medium">${x.name}</td><td><span class="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 text-xs">${x.plan}</span></td><td>${x.max_seats}</td><td>${x.is_active ? '🟢' : '⚪'}</td></tr>`).join('')}</tbody></table></div>`; }
async function renderAnalytics() { const o = await api('/admin/analytics/overview?days=30'); const t = await api('/admin/analytics/top-targets?limit=10'); $('#pageContent').innerHTML = `<div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">${statCard('👥 New Users', o.new_users, '30d', 'from-blue-500 to-cyan-500')}${statCard('🔍 Scans', o.total_scans, '30d', 'from-emerald-500 to-teal-500')}${statCard('⚠️ Findings', o.total_findings, '30d', 'from-red-500 to-pink-500')}${statCard('⏱️ Avg Time', (o.avg_scan_duration || 0).toFixed(1) + 's', '30d', 'from-amber-500 to-orange-500')}</div><div class="glass rounded-xl p-6"><h3 class="text-lg font-semibold mb-4">🎯 Top Targets</h3><div class="space-y-2">${t.map((x, i) => `<div class="flex items-center gap-3 p-2 bg-slate-800/30 rounded"><div class="w-8 h-8 rounded bg-indigo-500/20 flex items-center justify-center text-xs">${i+1}</div><div class="flex-1 mono text-sm">${x.target}</div><div class="text-slate-400 text-sm">${x.scans} scans</div></div>`).join('')}</div></div>`; }

async function renderLab() {
    const d = await api('/lab/functions');
    $('#pageSubtitle').textContent = `${d.total} security tools ready`;
    $('#pageContent').innerHTML = `<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">${d.categories.map(c => `<button onclick="filterLab('${c}')" class="glass p-4 rounded-xl text-left card-hover"><div class="text-sm text-slate-400">Category</div><div class="text-xl font-bold">${c}</div><div class="text-xs text-indigo-400 mt-1">${d.functions.filter(f => f.category === c).length} funcs →</div></button>`).join('')}</div><div class="glass rounded-xl p-6"><input id="labSearch" placeholder="🔍 Search..." class="w-full px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg mb-4"><div id="labGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">${d.functions.map(f => `<div class="lab-card p-3 bg-slate-800/30 rounded-lg hover:bg-slate-700/50 cursor-pointer transition" data-name="${f.name.toLowerCase()}" onclick="runLab('${f.id}')"><div class="flex items-center justify-between mb-1"><div class="font-medium text-sm">${f.name}</div><span class="text-xs text-slate-500">${f.category}</span></div><div class="text-xs text-slate-400">${f.params.map(p => p.name).join(', ') || 'no params'}</div></div>`).join('')}</div></div>`;
    $('#labSearch').addEventListener('input', (e) => { const q = e.target.value.toLowerCase(); document.querySelectorAll('.lab-card').forEach(c => c.style.display = c.dataset.name.includes(q) ? '' : 'none'); });
}

function filterLab(cat) { document.querySelectorAll('.lab-card').forEach(c => c.style.display = c.textContent.includes(cat) ? '' : 'none'); }

async function runLab(id) { const p = prompt(`Params as JSON for ${id} (e.g. {"text":"hello"}):`); if (!p) return; try { const r = await api(`/lab/exec/${id}`, { method: 'POST', body: JSON.stringify(JSON.parse(p)) }); alert('Result:\n' + JSON.stringify(r, null, 2)); } catch (e) { toast(e.message, 'error'); } }

async function renderLogs() { const d = await api('/admin/logs?per_page=100'); $('#pageContent').innerHTML = `<div class="glass rounded-xl p-6"><div class="space-y-1 text-sm font-mono max-h-[600px] overflow-y-auto scrollbar-thin">${d.logs.map(l => `<div class="p-2 bg-slate-800/30 rounded flex items-start gap-3"><span class="text-slate-500 text-xs whitespace-nowrap">${fmtDate(l.created_at)}</span><span class="text-slate-400 text-xs">[${l.action}]</span><span class="flex-1">${l.user_id ? 'User #' + l.user_id : 'System'}</span><span class="text-xs text-slate-500">${l.ip_address || ''}</span></div>`).join('')}</div></div>`; }

async function renderBroadcast() { $('#pageContent').innerHTML = `<div class="glass rounded-xl p-6 max-w-2xl"><h3 class="text-lg font-semibold mb-4">📢 Broadcast</h3><form id="bf" class="space-y-4"><div><label class="block text-sm font-medium mb-2">Target</label><select id="bt" class="w-full px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg"><option value="all">All Users</option><option value="verified">Verified</option></select></div><div><label class="block text-sm font-medium mb-2">Message</label><textarea id="bm" rows="6" required class="w-full px-4 py-2 bg-slate-800/50 border border-slate-700 rounded-lg"></textarea></div><button type="submit" class="px-6 py-2 bg-gradient-to-r from-indigo-500 to-purple-600 rounded-lg font-semibold">Send</button></form></div>`; $('#bf').addEventListener('submit', async (e) => { e.preventDefault(); const r = await api('/admin/broadcast', { method: 'POST', body: JSON.stringify({ target: $('#bt').value, message: $('#bm').value }) }); toast(r.message, 'success'); $('#bm').value = ''; }); }

async function renderSettings() { const s = await api('/admin/settings'); $('#pageContent').innerHTML = `<div class="glass rounded-xl p-6"><h3 class="text-lg font-semibold mb-4">⚙️ Settings</h3><div class="space-y-3">${Object.entries(s).map(([k, v]) => `<div class="flex items-center gap-3 p-3 bg-slate-800/30 rounded"><div class="flex-1"><div class="font-medium text-sm">${k}</div><div class="text-xs text-slate-400 mono">${String(v).substring(0, 80)}</div></div><button onclick="editSet('${k}')" class="px-3 py-1 bg-slate-700 rounded text-xs">Edit</button></div>`).join('')}</div></div>`; }

async function editSet(k) { const v = prompt(`New value for ${k}:`); if (v === null) return; await api('/admin/settings', { method: 'PUT', body: JSON.stringify({ [k]: v }) }); toast('Updated', 'success'); loadPage('settings'); }

async function renderSystem() { const h = await api('/admin/system/health'); $('#pageContent').innerHTML = `<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">${statCard('💻 CPU', h.cpu_percent + '%', '', h.cpu_percent > 80 ? 'from-red-500 to-pink-500' : 'from-emerald-500 to-teal-500')}${statCard('🧠 Memory', h.memory.percent + '%', fmt(h.memory.used) + '/' + fmt(h.memory.total), h.memory.percent > 80 ? 'from-red-500 to-pink-500' : 'from-blue-500 to-cyan-500')}${statCard('💾 Disk', h.disk.percent + '%', fmt(h.disk.used) + '/' + fmt(h.disk.total), h.disk.percent > 80 ? 'from-red-500 to-pink-500' : 'from-amber-500 to-orange-500')}</div><div class="glass rounded-xl p-6"><h3 class="text-lg font-semibold mb-4">⚙️ Actions</h3><div class="grid grid-cols-3 gap-3"><button onclick="clearCache()" class="p-4 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg text-left"><div class="text-2xl mb-1">🗑️</div><div class="font-medium">Clear Cache</div></button><button onclick="toggleMaint()" class="p-4 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg text-left"><div class="text-2xl mb-1">🔧</div><div class="font-medium">Maintenance</div></button><button onclick="loadPage('system')" class="p-4 bg-slate-800/50 hover:bg-slate-700/50 rounded-lg text-left"><div class="text-2xl mb-1">🔄</div><div class="font-medium">Refresh</div></button></div></div>`; }

async function clearCache() { await api('/admin/system/cache/clear', { method: 'POST' }); toast('Cache cleared', 'success'); }
async function toggleMaint() { await api('/admin/system/maintenance', { method: 'POST' }); toast('Done', 'success'); }

function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }

if (token) { api('/auth/me').then(u => { currentUser = u; if (u.is_admin) showApp(); else { toast('Admin required', 'error'); showLogin(); } }).catch(() => showLogin()); } else { showLogin(); }
