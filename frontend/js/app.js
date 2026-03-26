// ── API base — change port if needed
const API = "https://campus-issue-resolver-5u2w.onrender.com";

// ── State
let token   = localStorage.getItem("cirs_token") || null;
let session = JSON.parse(localStorage.getItem("cirs_user") || "null");
let section = "dashboard";

/* 
   API HELPER
*/
async function api(endpoint, method = "GET", body = null, formData = false) {
  const opts = {
    method,
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
  };
  if (body && !formData) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  if (body && formData) {
    opts.body = body; // FormData object
  }
  try {
    const res  = await fetch(`${API}/${endpoint}`, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  } catch (err) {
    throw err;
  }
}

/* 
   PARTICLES CANVAS
 */
function initParticles() {
  const canvas = document.getElementById("particles-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  let W = canvas.width  = window.innerWidth;
  let H = canvas.height = window.innerHeight;
  window.addEventListener("resize", () => {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  });
  const pts = Array.from({ length: 60 }, () => ({
    x: Math.random() * W, y: Math.random() * H,
    r: Math.random() * 1.4 + 0.3,
    vx: (Math.random() - 0.5) * 0.3,
    vy: -Math.random() * 0.4 - 0.1,
    a: Math.random() * 0.5 + 0.1,
    c: ["#388bfd","#39d353","#bc8cff","#0dcaf0"][Math.floor(Math.random()*4)]
  }));
  function draw() {
    ctx.clearRect(0, 0, W, H);
    pts.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.c + Math.round(p.a * 255).toString(16).padStart(2,"0");
      ctx.fill();
      p.x += p.vx; p.y += p.vy;
      if (p.y < -5) { p.y = H + 5; p.x = Math.random() * W; }
      if (p.x < 0 || p.x > W) p.vx *= -1;
    });
    requestAnimationFrame(draw);
  }
  draw();
}

/*
   TOAST
*/
function toast(msg, type = "ok") {
  const c  = document.getElementById("toasts");
  if (!c) return;
  const t  = document.createElement("div");
  const ico = type === "ok" ? "✅" : type === "err" ? "❌" : "ℹ️";
  t.className = `toast toast-${type}`;
  t.innerHTML = `<span class="toast-ico">${ico}</span><span>${msg}</span>`;
  c.appendChild(t);
  setTimeout(() => { t.style.opacity = "0"; t.style.transform = "translateX(110%)"; t.style.transition = "all .3s"; setTimeout(() => t.remove(), 300); }, 3500);
}

/* ═══════════════════════════════════════
   AUTH HELPERS
═══════════════════════════════════════ */
function saveSession(data) {
  token   = data.token;
  session = data.user;
  localStorage.setItem("cirs_token", token);
  localStorage.setItem("cirs_user",  JSON.stringify(session));
}
function clearSession() {
  token = session = null;
  localStorage.removeItem("cirs_token");
  localStorage.removeItem("cirs_user");
}
function isAdmin()  { return session?.role === "admin"; }
function isCoord()  { return session?.role === "coordinator"; }
function canManage(){ return isAdmin() || isCoord(); }
function initials(name) { return (name || "?").split(" ").map(w=>w[0]).join("").slice(0,2).toUpperCase(); }

/* ═══════════════════════════════════════
   ROUTER — main render
═══════════════════════════════════════ */
function boot() {
  if (session && token) renderApp();
  else                   renderAuth("login");
}

/* ═══════════════════════════════════════
   AUTH — LOGIN / REGISTER
═══════════════════════════════════════ */
function renderAuth(mode = "login") {
  document.getElementById("app").innerHTML = `
    <canvas id="particles-canvas"></canvas>
    <div class="auth-wrap a1">
      <div class="auth-side">
        <div class="auth-tagline">
          Campus <span class="hi">Issues</span><br>
          Reporting<br>System
        </div>
        <p class="auth-desc">
          A centralized, transparent digital platform for reporting and resolving
          campus infrastructure issues — designed for CDGI Indore.
        </p>
        <div class="auth-feats">
          <div class="auth-feat"><div class="feat-ico">🎫</div> Auto-generated unique Ticket IDs</div>
          <div class="auth-feat"><div class="feat-ico">📡</div> Real-time status tracking & notifications</div>
          <div class="auth-feat"><div class="feat-ico">🔐</div> Role-based access: Student · Coordinator · Admin</div>
          <div class="auth-feat"><div class="feat-ico">📊</div> Analytics dashboard with live database data</div>
          <div class="auth-feat"><div class="feat-ico">🐍</div> Python Flask + SQLite/MySQL backend</div>
        </div>
      </div>
      <div class="auth-form-side">
        <div class="auth-form-box" id="auth-box">
          ${mode === "login" ? loginForm() : registerForm()}
        </div>
      </div>
    </div>
    <div class="toasts" id="toasts"></div>
  `;
  initParticles();
}

function loginForm() {
  return `
    <div style="margin-bottom:28px;">
      <div class="logo-mark" style="width:46px;height:46px;font-size:22px;margin-bottom:14px;">🏛️</div>
      <div class="auth-form-title">Welcome back</div>
      <p class="auth-form-sub">Sign in to your CDGI campus account</p>
    </div>
    <div id="auth-alert"></div>
    <div class="form-group">
      <label class="label">Email Address <span class="req">*</span></label>
      <div class="input-icon">
        <span class="ico">📧</span>
        <input id="l-email" class="input" type="email" placeholder="you@cdgi.edu.in" autocomplete="email">
      </div>
    </div>
    <div class="form-group">
      <label class="label">Password <span class="req">*</span></label>
      <div class="pass-wrap">
        <input id="l-pass" class="input" type="password" placeholder="••••••••" autocomplete="current-password">
        <button class="eye-btn" onclick="toggleEye('l-pass',this)" type="button">👁️</button>
      </div>
    </div>
    <button class="btn btn-primary btn-full btn-lg" id="login-btn" onclick="doLogin()">
      Sign In &nbsp;→
    </button>
    <div class="divider-text">or use demo account</div>
    <div style="display:grid;gap:7px;">
      <button class="btn btn-outline btn-sm" onclick="quickLogin('admin@cdgi.edu.in','admin123')">🔴 Admin — admin@cdgi.edu.in</button>
    </div>
    <p style="text-align:center;margin-top:20px;font-size:12.5px;color:var(--text-2);">
      No account? <a href="#" onclick="renderAuth('register')" style="color:var(--blue-light);font-weight:600;">Create one →</a>
    </p>
  `;
}

function registerForm() {
  return `
    <div style="margin-bottom:24px;">
      <div class="auth-form-title">Create Account</div>
      <p class="auth-form-sub">Register your CDGI campus profile</p>
    </div>
    <div id="auth-alert"></div>
    <div class="form-row">
      <div class="form-group">
        <label class="label">Full Name <span class="req">*</span></label>
        <input id="r-name" class="input" placeholder="Your full name">
      </div>
      <div class="form-group">
        <label class="label">Roll Number</label>
        <input id="r-roll" class="input" placeholder="0832CS231XXX">
      </div>
    </div>
    <div class="form-group">
      <label class="label">Email <span class="req">*</span></label>
      <input id="r-email" class="input" type="email" placeholder="you@cdgi.edu.in">
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="label">Password <span class="req">*</span></label>
        <div class="pass-wrap">
          <input id="r-pass" class="input" type="password" placeholder="Min 6 chars">
          <button class="eye-btn" onclick="toggleEye('r-pass',this)" type="button">👁️</button>
        </div>
      </div>
      <div class="form-group">
        <label class="label">Phone</label>
        <input id="r-phone" class="input" placeholder="10-digit number">
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="label">Department</label>
        <select id="r-dept" class="select">
          <option value="CSE">CSE</option><option value="IT">IT</option>
          <option value="EC">EC</option><option value="ME">ME</option>
          <option value="CE">Civil</option><option value="MBA">MBA</option>
        </select>
      </div>
      <div class="form-group">
        <label class="label">Role</label>
        <select id="r-role" class="select">
          <option value="student">Student</option>
          <option value="faculty">Faculty</option>
          <option value="staff">Staff</option>
        </select>
      </div>
    </div>
    <button class="btn btn-primary btn-full btn-lg" onclick="doRegister()">Create Account →</button>
    <p style="text-align:center;margin-top:18px;font-size:12.5px;color:var(--text-2);">
      Already registered? <a href="#" onclick="renderAuth('login')" style="color:var(--blue-light);font-weight:600;">Sign in →</a>
    </p>
  `;
}

async function doLogin() {
  const email = document.getElementById("l-email").value.trim();
  const pass  = document.getElementById("l-pass").value;
  const btn   = document.getElementById("login-btn");
  if (!email || !pass) { showAuthErr("Please fill all fields."); return; }
  btn.disabled = true;
  btn.innerHTML = `<span class="spin">⟳</span> Signing in…`;
  try {
    const data = await api("login", "POST", { email, password: pass });
    saveSession(data);
    renderApp();
  } catch (e) {
    showAuthErr(e.message);
    btn.disabled = false;
    btn.innerHTML = "Sign In &nbsp;→";
  }
}

async function doRegister() {
  const name  = document.getElementById("r-name").value.trim();
  const email = document.getElementById("r-email").value.trim();
  const pass  = document.getElementById("r-pass").value;
  const phone = document.getElementById("r-phone").value.trim();
  const dept  = document.getElementById("r-dept").value;
  const role  = document.getElementById("r-role").value;
  const roll  = document.getElementById("r-roll").value.trim();
  if (!name || !email || !pass) { showAuthErr("Name, email and password are required."); return; }
  if (pass.length < 6)          { showAuthErr("Password must be at least 6 characters."); return; }
  try {
    const data = await api("register", "POST", { name, email, password: pass, phone, dept, role, roll_no: roll });
    saveSession(data);
    renderApp();
    toast("Welcome to CIRS, " + name + "! 🎉", "ok");
  } catch (e) {
    showAuthErr(e.message);
  }
}

function quickLogin(email, pass) {
  document.getElementById("l-email").value = email;
  document.getElementById("l-pass").value  = pass;
  doLogin();
}

function showAuthErr(msg) {
  const el = document.getElementById("auth-alert");
  if (el) el.innerHTML = `<div class="alert alert-err"><span class="alert-ico">⚠️</span>${msg}</div>`;
}

function toggleEye(id, btn) {
  const inp = document.getElementById(id);
  inp.type  = inp.type === "password" ? "text" : "password";
  btn.textContent = inp.type === "password" ? "👁️" : "🙈";
}

/* ═══════════════════════════════════════
   MAIN APP SHELL
═══════════════════════════════════════ */
function renderApp() {
  if (!session) { renderAuth("login"); return; }
  const manage = canManage();
  document.getElementById("app").innerHTML = `
    <canvas id="particles-canvas"></canvas>
    <div class="shell">

      <!-- SIDEBAR -->
      <aside class="sidebar" id="sidebar">
        <div class="sidebar-head">
          <div class="logo">
            <div class="logo-mark">🏛️</div>
            <div class="logo-text">
              <div class="logo-name">CIRS</div>
              <div class="logo-sub">CDGI · Indore</div>
            </div>
          </div>
        </div>
        <nav class="nav">
          <div class="nav-group">
            <div class="nav-section-label">Main</div>
            <button class="nav-item active" data-s="dashboard" onclick="go('dashboard')">
              <span class="nav-icon">📊</span> Dashboard
            </button>
            <button class="nav-item" data-s="report" onclick="go('report')">
              <span class="nav-icon">✍️</span> Report Issue
            </button>
            <button class="nav-item" data-s="complaints" onclick="go('complaints')">
              <span class="nav-icon">🎫</span> My Complaints
            </button>
          </div>
          ${manage ? `
          <div class="nav-group">
            <div class="nav-section-label">Management</div>
            <button class="nav-item" data-s="manage" onclick="go('manage')">
              <span class="nav-icon">⚙️</span> ${isAdmin() ? "Admin Panel" : "Coordinator"}
              <span class="nav-badge" id="new-count" style="display:none">0</span>
            </button>
            ${isAdmin() ? `<button class="nav-item" data-s="users" onclick="go('users')">
              <span class="nav-icon">👥</span> Users
            </button>` : ""}
          </div>` : ""}
          <div class="nav-group">
            <div class="nav-section-label">Account</div>
            <button class="nav-item" data-s="profile" onclick="go('profile')">
              <span class="nav-icon">👤</span> Profile
            </button>
            <button class="nav-item" onclick="logout()">
              <span class="nav-icon">🚪</span> Sign Out
            </button>
          </div>
        </nav>
        <div class="sidebar-foot">
          <div class="user-card">
            <div class="avatar">${initials(session.name)}</div>
            <div class="user-info">
              <div class="u-name">${session.name}</div>
              <div class="u-role">${session.role} · ${session.dept}</div>
            </div>
          </div>
        </div>
      </aside>

      <!-- MAIN -->
      <main class="main">
        <header class="topbar">
          <div class="topbar-l">
            <button class="menu-btn" onclick="document.getElementById('sidebar').classList.toggle('open')">☰</button>
            <div>
              <div class="pg-title" id="pg-title">Dashboard</div>
              <div class="pg-crumb">CDGI / <span id="pg-crumb">Overview</span></div>
            </div>
          </div>
          <div class="topbar-r">
            <div style="position:relative;">
              <button class="icon-btn" id="notif-btn" onclick="toggleNotifDrop()">
                🔔 <span class="dot-badge hidden" id="notif-dot"></span>
              </button>
              <div class="notif-drop" id="notif-drop">
                <div class="notif-drop-head">
                  <span>Notifications</span>
                  <button onclick="markAllRead()">Mark all read</button>
                </div>
                <div id="notif-list"><div class="notif-empty">Loading…</div></div>
              </div>
            </div>
            <div class="avatar" style="cursor:pointer;" onclick="go('profile')" title="${session.name}">${initials(session.name)}</div>
          </div>
        </header>
        <div class="content" id="page-content"></div>
      </main>

    </div>
    <div class="overlay" id="overlay" onclick="closeModal()">
      <div class="modal" id="modal" onclick="event.stopPropagation()"></div>
    </div>
    <div class="toasts" id="toasts"></div>
  `;
  initParticles();
  go("dashboard");
  loadNotifications();
  // close notif on outside click
  document.addEventListener("click", e => {
    const drop = document.getElementById("notif-drop");
    const btn  = document.getElementById("notif-btn");
    if (drop && btn && !drop.contains(e.target) && !btn.contains(e.target)) drop.classList.remove("open");
  });
}

function go(s) {
  section = s;
  document.querySelectorAll(".nav-item").forEach(el => el.classList.toggle("active", el.dataset.s === s));
  const titles = { dashboard:"Dashboard", report:"Report Issue", complaints:"My Complaints", manage:"Admin Panel", users:"Users", profile:"Profile" };
  const el = document.getElementById("pg-title");
  if (el) el.textContent = titles[s] || s;
  const content = document.getElementById("page-content");
  if (!content) return;
  content.innerHTML = `<div style="text-align:center;padding:60px;color:var(--text-3);">Loading…</div>`;
  const map = { dashboard: renderDashboard, report: renderReport, complaints: renderComplaints, manage: renderManage, users: renderUsers, profile: renderProfile };
  if (map[s]) map[s](content);
}

function logout() {
  clearSession();
  renderAuth("login");
}

/* ═══════════════════════════════════════
   DASHBOARD
═══════════════════════════════════════ */
async function renderDashboard(el) {
  try {
    const stats = await api("stats");
    const recent = await api("complaints?page=1");
    const list  = (recent.data || []).slice(0, 6);

    // update new-count badge
    const badge = document.getElementById("new-count");
    if (badge && stats.new > 0) { badge.style.display = ""; badge.textContent = stats.new; }

    const cats = stats.categories || {};
    const maxCat = Math.max(...Object.values(cats), 1);
    const hr = new Date().getHours();
    const greet = hr < 12 ? "morning" : hr < 17 ? "afternoon" : "evening";

    el.innerHTML = `
      <div class="page-header a1">
        <h1>Good ${greet}, <span>${session.name.split(" ")[0]}</span> 👋</h1>
        <p>${new Date().toLocaleDateString("en-IN",{weekday:"long",day:"numeric",month:"long",year:"numeric"})} — Campus live data from database</p>
      </div>

      <div class="stats a2">
        <div class="stat s-blue">
          <div class="stat-top"><div class="stat-ico">🎫</div><span class="stat-delta up">Total</span></div>
          <div class="stat-val">${stats.total}</div>
          <div class="stat-label">Total Complaints</div>
          <div class="stat-strip"><div class="stat-strip-fill" style="width:100%"></div></div>
        </div>
        <div class="stat s-teal">
          <div class="stat-top"><div class="stat-ico">🆕</div><span class="stat-delta">${stats.new} pending</span></div>
          <div class="stat-val">${stats.new}</div>
          <div class="stat-label">New Issues</div>
          <div class="stat-strip"><div class="stat-strip-fill" style="width:${stats.total ? (stats.new/stats.total*100).toFixed(0) : 0}%"></div></div>
        </div>
        <div class="stat s-yel">
          <div class="stat-top"><div class="stat-ico">⏳</div><span class="stat-delta">${stats.in_progress} active</span></div>
          <div class="stat-val">${stats.in_progress}</div>
          <div class="stat-label">In Progress</div>
          <div class="stat-strip"><div class="stat-strip-fill" style="width:${stats.total ? (stats.in_progress/stats.total*100).toFixed(0) : 0}%"></div></div>
        </div>
        <div class="stat s-green">
          <div class="stat-top"><div class="stat-ico">✅</div><span class="stat-delta up">${stats.resolution_rate}% rate</span></div>
          <div class="stat-val">${stats.resolved}</div>
          <div class="stat-label">Resolved</div>
          <div class="stat-strip"><div class="stat-strip-fill" style="width:${stats.resolution_rate}%"></div></div>
        </div>
      </div>

      <div class="two-col a3">
        <div class="card">
          <div class="card-head"><span class="card-title">📈 Issues by Category</span><span class="text-sm text-2">Live data</span></div>
          <div class="card-body">
            ${Object.keys(cats).length ? `
            <div class="bar-chart">
              ${Object.entries(cats).map(([cat,cnt]) => `
                <div class="bar-wrap">
                  <span class="bar-num">${cnt}</span>
                  <div class="bar-col" style="height:${Math.round(cnt/maxCat*110)+10}px"></div>
                  <span class="bar-lbl">${cat.slice(0,5).toUpperCase()}</span>
                </div>
              `).join("")}
            </div>` : `<div class="tbl-empty">No complaints yet — be the first to report!</div>`}
          </div>
        </div>
        <div class="card">
          <div class="card-head"><span class="card-title">🚀 Quick Actions</span></div>
          <div class="card-body" style="display:flex;flex-direction:column;gap:10px;">
            <button class="btn btn-primary" onclick="go('report')" style="justify-content:flex-start;gap:12px;padding:14px 16px;">
              <span style="font-size:20px;">✍️</span>
              <div style="text-align:left;"><div>Report a New Issue</div><div style="font-size:11px;opacity:.7;font-weight:400;margin-top:2px;">Submit a campus complaint</div></div>
            </button>
            <button class="btn btn-outline" onclick="go('complaints')" style="justify-content:flex-start;gap:12px;padding:14px 16px;">
              <span style="font-size:20px;">🎫</span>
              <div style="text-align:left;"><div>Track My Complaints</div><div style="font-size:11px;opacity:.7;font-weight:400;margin-top:2px;">View real-time status</div></div>
            </button>
            ${canManage() ? `
            <button class="btn btn-outline" onclick="go('manage')" style="justify-content:flex-start;gap:12px;padding:14px 16px;">
              <span style="font-size:20px;">⚙️</span>
              <div style="text-align:left;"><div>Manage All Complaints</div><div style="font-size:11px;opacity:.7;font-weight:400;margin-top:2px;">${stats.new} new awaiting action</div></div>
            </button>` : ""}
          </div>
        </div>
      </div>

      <div class="card a4">
        <div class="card-head">
          <span class="card-title">🕐 Recent Activity</span>
          <button class="btn btn-outline btn-sm" onclick="go('complaints')">View All</button>
        </div>
        <div class="tbl-wrap">
          ${list.length ? `
          <table>
            <thead><tr><th>Ticket</th><th>Issue Title</th><th>Category</th><th>Priority</th><th>Status</th><th>Date</th><th></th></tr></thead>
            <tbody>
              ${list.map(c => `
                <tr>
                  <td><span class="mono" style="color:var(--blue-light);font-size:11.5px;">${c.ticket_id}</span></td>
                  <td style="font-weight:500;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${c.title}</td>
                  <td><span class="cpill c-${c.category}">${c.category}</span></td>
                  <td><span class="flex-c gap-8"><span class="pdot p-${c.priority}"></span>${c.priority}</span></td>
                  <td>${statusBadge(c.status)}</td>
                  <td class="text-sm text-2">${c.created_at}</td>
                  <td><button class="btn btn-ghost btn-sm" onclick="viewTicket('${c.ticket_id}')">View →</button></td>
                </tr>
              `).join("")}
            </tbody>
          </table>` : `
          <div class="tbl-empty">
            <div style="font-size:36px;margin-bottom:10px;">📭</div>
            <div class="fw-7">No complaints yet</div>
            <p style="margin-top:6px;">The database is empty. Submit the first campus complaint!</p>
            <button class="btn btn-primary" onclick="go('report')" style="margin-top:16px;">Report an Issue →</button>
          </div>`}
        </div>
      </div>
    `;
  } catch(e) {
    el.innerHTML = serverDownBanner();
  }
}

/* ═══════════════════════════════════════
   REPORT FORM
═══════════════════════════════════════ */
function renderReport(el) {
  el.innerHTML = `
    <div class="page-header a1">
      <h1>Report <span>New Issue</span></h1>
      <p>Submit a campus complaint — saved directly to database with a unique Ticket ID</p>
    </div>
    <div style="max-width:700px;">
      <div class="card a2">
        <div class="card-head"><span class="card-title">🎫 Complaint Details</span></div>
        <div class="card-body">
          <div id="report-alert"></div>
          <div class="form-group">
            <label class="label">Issue Title <span class="req">*</span></label>
            <input id="r-title" class="input" placeholder="e.g. Broken light in Lab-2, No water in Hostel Block B">
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="label">Category <span class="req">*</span></label>
              <select id="r-cat" class="select">
                <option value="">— Select category</option>
                <option value="hygiene">🧹 Hygiene / Cleanliness</option>
                <option value="electrical">⚡ Electrical / Power</option>
                <option value="transport">🚌 Transport</option>
                <option value="maintenance">🔧 Maintenance</option>
                <option value="water">💧 Water Supply</option>
                <option value="safety">🛡️ Safety / Security</option>
                <option value="admin">📋 Administrative</option>
              </select>
            </div>
            <div class="form-group">
              <label class="label">Priority <span class="req">*</span></label>
              <select id="r-priority" class="select">
                <option value="low">🟢 Low — Minor inconvenience</option>
                <option value="medium" selected>🟡 Medium — Affecting daily work</option>
                <option value="high">🔴 High — Urgent attention needed</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="label">Location / Block</label>
            <input id="r-location" class="input" placeholder="e.g. Main Block, 2nd Floor, Near Lab-204, Hostel Block B">
          </div>
          <div class="form-group">
            <label class="label">Detailed Description <span class="req">*</span></label>
            <textarea id="r-desc" class="textarea" rows="5" placeholder="Describe the issue: what happened, since when, how it's affecting you or others…"></textarea>
          </div>
          <div class="form-group">
            <label class="label">Attach Evidence Photo / Video (Optional)</label>
            <div class="file-zone" id="file-zone" onclick="document.getElementById('r-file').click()">
              <div class="file-zone-ico">📎</div>
              <div class="file-zone-txt"><strong>Click to browse</strong> or drag & drop</div>
              <div class="file-zone-hint">JPG · PNG · MP4 · PDF — max 16MB</div>
            </div>
            <input type="file" id="r-file" style="display:none" accept="image/*,video/*,.pdf" onchange="handleFile(event)">
            <div id="file-preview"></div>
          </div>
          <div style="display:flex;gap:10px;margin-top:6px;">
            <button class="btn btn-primary btn-lg" id="submit-btn" onclick="submitComplaint()" style="flex:1;">
              🚀 Submit Complaint
            </button>
            <button class="btn btn-outline btn-lg" onclick="go('dashboard')">Cancel</button>
          </div>
        </div>
      </div>

      <div class="card a3" style="margin-top:16px;">
        <div class="card-body">
          <p class="text-sm text-2" style="margin-bottom:14px;">Your complaint will go through this lifecycle:</p>
          <div class="tracker">
            ${["Submit","Assigned","In Progress","Resolved","Feedback"].map((l,i) => `
              <div class="t-step ${i===0?'active':''}">
                <div class="t-dot">${i===0?'1':i+1}</div>
                <div class="t-label">${l}</div>
              </div>
            `).join("")}
          </div>
          <p class="text-sm text-3" style="text-align:center;margin-top:10px;">You'll receive a notification at every status change.</p>
        </div>
      </div>
    </div>
  `;

  // drag-drop
  const zone = document.getElementById("file-zone");
  zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("over"); });
  zone.addEventListener("dragleave", () => zone.classList.remove("over"));
  zone.addEventListener("drop", e => {
    e.preventDefault(); zone.classList.remove("over");
    if (e.dataTransfer.files[0]) previewFile(e.dataTransfer.files[0]);
  });
}

function handleFile(e) { if (e.target.files[0]) previewFile(e.target.files[0]); }
function previewFile(file) {
  const el = document.getElementById("file-preview");
  if (!el) return;
  el.innerHTML = `
    <div class="file-preview">
      <span>📎</span>
      <span class="file-preview-name">${file.name}</span>
      <span class="file-preview-size">${(file.size/1024).toFixed(1)} KB</span>
      <button onclick="clearFile()" style="background:none;border:none;color:var(--text-3);font-size:18px;cursor:pointer;margin-left:auto;">×</button>
    </div>`;
  window._selectedFile = file;
}
function clearFile() {
  document.getElementById("file-preview").innerHTML = "";
  document.getElementById("r-file").value = "";
  window._selectedFile = null;
}

async function submitComplaint() {
  const title    = document.getElementById("r-title").value.trim();
  const category = document.getElementById("r-cat").value;
  const priority = document.getElementById("r-priority").value;
  const desc     = document.getElementById("r-desc").value.trim();
  const location = document.getElementById("r-location").value.trim();
  const alertEl  = document.getElementById("report-alert");
  const btn      = document.getElementById("submit-btn");

  if (!title || !category || !desc) {
    alertEl.innerHTML = `<div class="alert alert-err"><span class="alert-ico">⚠️</span>Title, category and description are required.</div>`;
    return;
  }

  btn.disabled = true;
  btn.innerHTML = `<span class="spin">⟳</span> Submitting…`;

  try {
    const fd = new FormData();
    fd.append("title",       title);
    fd.append("category",    category);
    fd.append("priority",    priority);
    fd.append("description", desc);
    fd.append("location",    location);
    if (window._selectedFile) fd.append("image", window._selectedFile);

    const res = await api("complaints", "POST", fd, true);
    toast(`✅ ${res.message}`, "ok");
    go("complaints");
  } catch(e) {
    alertEl.innerHTML = `<div class="alert alert-err"><span class="alert-ico">⚠️</span>${e.message}</div>`;
    btn.disabled = false;
    btn.innerHTML = "🚀 Submit Complaint";
  }
}

/* ═══════════════════════════════════════
   MY COMPLAINTS
═══════════════════════════════════════ */
async function renderComplaints(el) {
  try {
    const data = await api("complaints");
    const list = data.data || [];

    el.innerHTML = `
      <div class="page-header a1">
        <h1>My <span>Complaints</span></h1>
        <p>${list.length} total complaints — real-time from database</p>
      </div>

      <div class="flex-bc mb-20 a2" style="flex-wrap:wrap;gap:10px;">
        <div style="display:flex;gap:8px;flex-wrap:wrap;" id="filter-chips">
          ${["all","new","in-progress","resolved"].map(s => `
            <button class="btn btn-outline btn-sm ${s==="all"?"btn-primary":""}" onclick="filterChip(this,'${s}')" data-filter="${s}">
              ${s==="all"?"All ("+list.length+")":s==="new"?"New ("+list.filter(c=>c.status==="new").length+")":s==="in-progress"?"In Progress ("+list.filter(c=>c.status==="in-progress").length+")":"Resolved ("+list.filter(c=>c.status==="resolved").length+")"}
            </button>
          `).join("")}
        </div>
        <div class="input-icon" style="width:220px;">
          <span class="ico">🔍</span>
          <input class="input" placeholder="Search…" id="search-inp" oninput="searchTickets(this.value)">
        </div>
      </div>

      <div id="ticket-grid" class="tickets-grid a3">
        ${list.length ? list.map(c => ticketCard(c)).join("") : `
          <div class="card" style="padding:60px;text-align:center;">
            <div style="font-size:42px;margin-bottom:12px;">📭</div>
            <div class="fw-7" style="font-size:18px;">No Complaints Found</div>
            <p class="text-sm text-2" style="margin-top:8px;">The database is empty. Submit your first complaint!</p>
            <button class="btn btn-primary" onclick="go('report')" style="margin-top:16px;">Report an Issue →</button>
          </div>`}
      </div>
    `;
    window._allTickets = list;
  } catch(e) {
    el.innerHTML = serverDownBanner();
  }
}

function ticketCard(c) {
  return `
    <div class="tkt ${c.priority==="high"?"high":""}" data-status="${c.status}" data-title="${(c.title||"").toLowerCase()}" onclick="viewTicket('${c.ticket_id}')">
      <div class="flex-bc">
        <span class="tkt-id">${c.ticket_id}</span>
        ${statusBadge(c.status)}
      </div>
      <div class="tkt-ttl">${c.title}</div>
      <div class="tkt-meta">
        <span class="cpill c-${c.category}">${c.category}</span>
        <span class="flex-c gap-8"><span class="pdot p-${c.priority}"></span>${c.priority}</span>
        <span>📅 ${c.created_at}</span>
        ${c.assigned_to ? `<span>👤 ${c.assigned_to}</span>` : ""}
      </div>
      <div class="tkt-foot">
        <span class="tkt-desc">${c.description}</span>
        <button class="btn btn-outline btn-sm" onclick="event.stopPropagation();viewTicket('${c.ticket_id}')">Details →</button>
      </div>
    </div>`;
}

function filterChip(btn, status) {
  document.querySelectorAll("#filter-chips .btn").forEach(b => b.classList.remove("btn-primary"));
  btn.classList.add("btn-primary");
  document.querySelectorAll("#ticket-grid .tkt").forEach(el => {
    el.style.display = (status === "all" || el.dataset.status === status) ? "" : "none";
  });
}
function searchTickets(q) {
  document.querySelectorAll("#ticket-grid .tkt").forEach(el => {
    el.style.display = el.dataset.title?.includes(q.toLowerCase()) ? "" : "none";
  });
}

/* ═══════════════════════════════════════
   TICKET DETAIL MODAL
═══════════════════════════════════════ */
async function viewTicket(ticketId) {
  try {
    const c = await api(`complaints/${ticketId}`);
    const steps = ["new","in-progress","resolved"];
    const si    = steps.indexOf(c.status);

    openModal(`
      <div class="modal-head">
        <div>
          <div class="mono" style="font-size:10.5px;color:var(--blue-light);margin-bottom:4px;">${c.ticket_id}</div>
          <div class="modal-title">${c.title}</div>
        </div>
        <button class="modal-close" onclick="closeModal()">×</button>
      </div>
      <div class="modal-body">
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px;">
          ${statusBadge(c.status)}
          <span class="cpill c-${c.category}">${c.category}</span>
          <span class="flex-c gap-8 text-sm"><span class="pdot p-${c.priority}"></span>${c.priority} priority</span>
        </div>

        <div class="tracker" style="margin-bottom:20px;">
          ${["Submitted","Assigned","In Progress","Resolved","Feedback"].map((l,i)=>`
            <div class="t-step ${i<si+1?"done":i===si+1?"active":""}">
              <div class="t-dot">${i<si+1?"✓":i+1}</div>
              <div class="t-label">${l}</div>
            </div>`).join("")}
        </div>

        <div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--r-sm);padding:14px;margin-bottom:14px;">
          <div class="label" style="margin-bottom:6px;">Description</div>
          <p style="font-size:13.5px;line-height:1.7;">${c.description}</p>
        </div>

        ${c.location ? `<div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--r-sm);padding:12px;margin-bottom:14px;font-size:13px;">
          <span class="text-3">📍 Location: </span><span class="fw-7">${c.location}</span>
        </div>` : ""}

        ${c.image_path ? `<div style="margin-bottom:14px;">
          <img src="${c.image_path}" style="max-width:100%;border-radius:var(--r-sm);border:1px solid var(--border);" alt="Evidence">
        </div>` : ""}

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;">
          ${[["Reported By", c.user_name],["Department", c.dept],["Assigned To", c.assigned_to||"— Pending"],["Last Updated", c.updated_at||c.created_at],["Submitted", c.created_at],["Ticket ID", c.ticket_id]].map(([k,v])=>`
            <div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--r-sm);padding:11px;">
              <div class="label" style="margin-bottom:3px;">${k}</div>
              <div class="fw-7 text-sm">${v}</div>
            </div>`).join("")}
        </div>

        ${canManage() && c.status !== "resolved" ? `
        <div class="divider"></div>
        <div class="label">Admin Actions</div>
        <div style="display:grid;grid-template-columns:1fr auto;gap:8px;margin:10px 0;">
          <input id="assign-inp" class="input" placeholder="Assign to coordinator…" value="${c.assigned_to||""}">
          <button class="btn btn-primary" onclick="assignTicket('${c.ticket_id}')">Assign</button>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          ${c.status==="new"?`<button class="btn btn-outline btn-sm" onclick="updateTicketStatus('${c.ticket_id}','in-progress')">▶ Mark In Progress</button>`:""}
          <button class="btn btn-success btn-sm" onclick="updateTicketStatus('${c.ticket_id}','resolved')">✅ Mark Resolved</button>
          <button class="btn btn-danger btn-sm" onclick="deleteTicket('${c.ticket_id}')">🗑 Delete</button>
        </div>` : ""}

        ${c.status==="resolved" && c.user_id===session?.id && !c.feedback ? `
        <div class="divider"></div>
        <div class="label">Rate Resolution Quality</div>
        <div style="display:flex;gap:7px;margin-top:10px;flex-wrap:wrap;">
          ${[1,2,3,4,5].map(i=>`<button class="btn btn-outline btn-sm" onclick="submitFeedback('${c.ticket_id}',${i})" style="font-size:18px;padding:6px 14px;">${"⭐".repeat(i)}</button>`).join("")}
        </div>` : ""}

        ${c.feedback ? `<div class="alert alert-ok" style="margin-top:12px;"><span class="alert-ico">⭐</span>Feedback submitted: ${c.feedback}/5 — Thank you!</div>` : ""}
      </div>
    `);
  } catch(e) {
    toast("Failed to load ticket: " + e.message, "err");
  }
}

async function assignTicket(ticketId) {
  const name = document.getElementById("assign-inp").value.trim();
  if (!name) return;
  try {
    await api(`complaints/${ticketId}`, "PUT", { status: "in-progress", assigned_to: name });
    toast("Assigned successfully!", "ok");
    closeModal();
    go(section);
  } catch(e) { toast(e.message, "err"); }
}

async function updateTicketStatus(ticketId, status) {
  try {
    await api(`complaints/${ticketId}`, "PUT", { status });
    toast(`Status updated to: ${status}`, "ok");
    closeModal();
    go(section);
  } catch(e) { toast(e.message, "err"); }
}

async function deleteTicket(ticketId) {
  if (!confirm(`Delete ${ticketId}? This cannot be undone.`)) return;
  try {
    await api(`complaints/${ticketId}`, "DELETE");
    toast(`${ticketId} deleted`, "ok");
    closeModal();
    go(section);
  } catch(e) { toast(e.message, "err"); }
}

async function submitFeedback(ticketId, rating) {
  try {
    await api(`complaints/${ticketId}`, "PUT", { feedback: rating });
    toast("Feedback submitted! Thank you ⭐", "ok");
    closeModal();
    go(section);
  } catch(e) { toast(e.message, "err"); }
}

/* ═══════════════════════════════════════
   ADMIN / MANAGE
═══════════════════════════════════════ */
async function renderManage(el) {
  try {
    const data  = await api("complaints");
    const stats = await api("stats");
    const list  = data.data || [];

    el.innerHTML = `
      <div class="page-header a1">
        <h1>${isAdmin()?"Admin":"Coordinator"} <span>Control Panel</span></h1>
        <p>Manage all campus complaints from the real database</p>
      </div>

      <div class="stats a2" style="grid-template-columns:repeat(3,1fr);">
        ${[["new","🆕","New Issues","s-teal"],["in-progress","⏳","In Progress","s-yel"],["resolved","✅","Resolved","s-green"]].map(([s,ico,lbl,cls])=>`
          <div class="stat ${cls}">
            <div class="stat-top"><div class="stat-ico">${ico}</div></div>
            <div class="stat-val">${list.filter(c=>c.status===s).length}</div>
            <div class="stat-label">${lbl}</div>
          </div>`).join("")}
      </div>

      <div class="card a3">
        <div class="card-head">
          <span class="card-title">📋 All Complaints (${list.length})</span>
          <div style="display:flex;gap:8px;align-items:center;">
            <select class="select" style="padding:6px 10px;font-size:12px;width:auto;" onchange="filterTable(this.value)">
              <option value="all">All Status</option>
              <option value="new">New</option>
              <option value="in-progress">In Progress</option>
              <option value="resolved">Resolved</option>
            </select>
            <div class="input-icon" style="width:180px;">
              <span class="ico">🔍</span>
              <input class="input" style="padding:7px 12px 7px 34px;font-size:12px;" placeholder="Search…" oninput="filterTableSearch(this.value)">
            </div>
          </div>
        </div>
        <div class="tbl-wrap">
          <table id="admin-tbl">
            <thead>
              <tr><th>Ticket</th><th>Title</th><th>Reporter</th><th>Category</th><th>Priority</th><th>Status</th><th>Dept</th><th>Date</th><th>Actions</th></tr>
            </thead>
            <tbody>
              ${list.length ? list.map(c=>`
                <tr data-status="${c.status}" data-title="${(c.title||"").toLowerCase()}">
                  <td><span class="mono" style="color:var(--blue-light);font-size:11px;">${c.ticket_id}</span></td>
                  <td style="font-weight:500;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${c.title}">${c.title}</td>
                  <td class="text-sm text-2">${c.user_name}</td>
                  <td><span class="cpill c-${c.category}">${c.category}</span></td>
                  <td><span class="flex-c gap-8"><span class="pdot p-${c.priority}"></span>${c.priority}</span></td>
                  <td>${statusBadge(c.status)}</td>
                  <td class="text-sm text-2">${c.dept||"—"}</td>
                  <td class="text-sm text-2">${c.created_at}</td>
                  <td>
                    <div style="display:flex;gap:5px;">
                      <button class="btn btn-ghost btn-sm" onclick="viewTicket('${c.ticket_id}')">View</button>
                      ${c.status!=="resolved"?`<button class="btn btn-success btn-sm" onclick="updateTicketStatus('${c.ticket_id}','${c.status==="new"?"in-progress":"resolved"}')">${c.status==="new"?"▶":"✓"}</button>`:""}
                    </div>
                  </td>
                </tr>`).join("") : `<tr><td colspan="9" class="tbl-empty">No complaints in database yet.</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch(e) { el.innerHTML = serverDownBanner(); }
}

function filterTable(val) {
  document.querySelectorAll("#admin-tbl tbody tr[data-status]").forEach(r => {
    r.style.display = val==="all" || r.dataset.status===val ? "" : "none";
  });
}
function filterTableSearch(q) {
  document.querySelectorAll("#admin-tbl tbody tr[data-title]").forEach(r => {
    r.style.display = r.dataset.title?.includes(q.toLowerCase()) ? "" : "none";
  });
}

/* ═══════════════════════════════════════
   USERS (Admin only)
═══════════════════════════════════════ */
async function renderUsers(el) {
  try {
    const data = await api("users");
    const list = data.data || [];
    el.innerHTML = `
      <div class="page-header a1">
        <h1>Registered <span>Users</span></h1>
        <p>${list.length} users in database</p>
      </div>
      <div class="card a2">
        <div class="card-head"><span class="card-title">👥 All Users</span></div>
        <div class="tbl-wrap">
          <table>
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Dept</th><th>Roll No.</th><th>Phone</th><th>Joined</th><th>Actions</th></tr></thead>
            <tbody>
              ${list.map(u=>`
                <tr>
                  <td>
                    <div class="flex-c gap-8">
                      <div class="avatar" style="width:28px;height:28px;font-size:11px;">${initials(u.name)}</div>
                      <span class="fw-7">${u.name}</span>
                    </div>
                  </td>
                  <td class="text-sm text-2">${u.email}</td>
                  <td><span class="badge b-${u.role}">${u.role}</span></td>
                  <td class="text-sm">${u.dept||"—"}</td>
                  <td class="mono text-xs text-2">${u.roll_no||"—"}</td>
                  <td class="text-sm text-2">${u.phone||"—"}</td>
                  <td class="text-sm text-2">${u.created_at}</td>
                  <td>
                    <select class="select" style="padding:5px 8px;font-size:11px;width:auto;" onchange="changeRole(${u.id},this.value)">
                      <option ${u.role==="student"?"selected":""}>student</option>
                      <option ${u.role==="coordinator"?"selected":""}>coordinator</option>
                      <option ${u.role==="admin"?"selected":""}>admin</option>
                    </select>
                  </td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>
      </div>`;
  } catch(e) { el.innerHTML = serverDownBanner(); }
}

async function changeRole(userId, role) {
  try {
    await api(`users/${userId}/role`, "PUT", { role });
    toast(`Role updated to ${role}`, "ok");
  } catch(e) { toast(e.message, "err"); }
}

/* ═══════════════════════════════════════
   PROFILE
═══════════════════════════════════════ */
async function renderProfile(el) {
  try {
    const stats = await api("stats");
    el.innerHTML = `
      <div class="page-header a1"><h1>My <span>Profile</span></h1></div>
      <div class="two-col">
        <div>
          <div class="profile-hero a2">
            <div class="avatar lg" style="margin:0 auto;">${initials(session.name)}</div>
            <div class="profile-name">${session.name}</div>
            <div class="profile-email">${session.email}</div>
            <div style="margin-top:10px;"><span class="badge b-${session.role}">${session.role}</span></div>
            <div class="profile-stats">
              <div><div class="ps-val">${stats.total}</div><div class="ps-lbl">Submitted</div></div>
              <div><div class="ps-val">${stats.resolved}</div><div class="ps-lbl">Resolved</div></div>
              <div><div class="ps-val">${stats.in_progress}</div><div class="ps-lbl">Active</div></div>
            </div>
          </div>
          <div class="card a3" style="margin-top:16px;">
            <div class="card-body">
              <div style="display:grid;gap:8px;font-size:13px;">
                ${[["🎓 Department", session.dept],["📋 Roll Number", session.roll_no||"—"],["📱 Phone", session.phone||"—"],["🏫 Institution","CDGI, Indore"]].map(([k,v])=>`
                  <div class="flex-bc" style="padding:9px;background:var(--surface2);border-radius:var(--r-sm);">
                    <span class="text-2">${k}</span><span class="fw-7">${v}</span>
                  </div>`).join("")}
              </div>
            </div>
          </div>
        </div>
        <div class="card a2">
          <div class="card-head"><span class="card-title">✏️ Edit Profile</span></div>
          <div class="card-body">
            <div id="profile-alert"></div>
            <div class="form-group">
              <label class="label">Full Name</label>
              <input id="p-name" class="input" value="${session.name}">
            </div>
            <div class="form-group">
              <label class="label">Email <span style="color:var(--text-3);font-weight:400;">(cannot change)</span></label>
              <input class="input" value="${session.email}" disabled style="opacity:.5;">
            </div>
            <div class="form-group">
              <label class="label">Phone Number</label>
              <input id="p-phone" class="input" value="${session.phone||""}" placeholder="10-digit number">
            </div>
            <div class="divider"></div>
            <div class="form-group">
              <label class="label">New Password <span style="color:var(--text-3);font-weight:400;">(leave blank to keep)</span></label>
              <div class="pass-wrap">
                <input id="p-pass" class="input" type="password" placeholder="New password…">
                <button class="eye-btn" onclick="toggleEye('p-pass',this)" type="button">👁️</button>
              </div>
            </div>
            <button class="btn btn-primary" onclick="saveProfile()">💾 Save Changes</button>
          </div>
        </div>
      </div>`;
  } catch(e) { el.innerHTML = serverDownBanner(); }
}

async function saveProfile() {
  const name  = document.getElementById("p-name").value.trim();
  const phone = document.getElementById("p-phone").value.trim();
  const pass  = document.getElementById("p-pass").value;
  const body  = { name, phone };
  if (pass) body.password = pass;
  try {
    const res = await api("profile", "PUT", body);
    session = res.user;
    localStorage.setItem("cirs_user", JSON.stringify(session));
    document.getElementById("profile-alert").innerHTML = `<div class="alert alert-ok"><span class="alert-ico">✅</span>Profile updated successfully!</div>`;
    toast("Profile saved!", "ok");
  } catch(e) { toast(e.message, "err"); }
}

/* ═══════════════════════════════════════
   NOTIFICATIONS
═══════════════════════════════════════ */
async function loadNotifications() {
  try {
    const data = await api("notifications");
    const list = data.data || [];
    const unread = data.unread || 0;
    const dot  = document.getElementById("notif-dot");
    if (dot) dot.classList.toggle("hidden", unread === 0);
    const listEl = document.getElementById("notif-list");
    if (!listEl) return;
    listEl.innerHTML = list.length ? list.map(n=>`
      <div class="notif-item ${!n.is_read?"unread":""}">
        <div class="notif-msg">${n.message}</div>
        <div class="notif-time">${n.created_at}</div>
      </div>`).join("") : `<div class="notif-empty">No notifications yet</div>`;
  } catch(e) { /* silently ignore */ }
}

async function markAllRead() {
  try {
    await api("notifications/read-all", "PUT");
    const dot = document.getElementById("notif-dot");
    if (dot) dot.classList.add("hidden");
    document.querySelectorAll(".notif-item.unread").forEach(el => el.classList.remove("unread"));
    toast("All marked as read", "ok");
  } catch(e) { toast(e.message, "err"); }
}

function toggleNotifDrop() {
  document.getElementById("notif-drop").classList.toggle("open");
  loadNotifications();
}

/* ═══════════════════════════════════════
   MODAL
═══════════════════════════════════════ */
function openModal(html) {
  document.getElementById("modal").innerHTML = html;
  document.getElementById("overlay").classList.add("show");
}
function closeModal() {
  document.getElementById("overlay")?.classList.remove("show");
}

/* ═══════════════════════════════════════
   HELPERS
═══════════════════════════════════════ */
function statusBadge(s) {
  const map = { new:"b-new", "in-progress":"b-progress", resolved:"b-resolved" };
  const lbl = { new:"🆕 New", "in-progress":"⏳ In Progress", resolved:"✅ Resolved" };
  return `<span class="badge ${map[s]||"b-new"}">${lbl[s]||s}</span>`;
}

function serverDownBanner() {
  return `
    <div class="card" style="padding:48px;text-align:center;">
      <div style="font-size:48px;margin-bottom:16px;">⚠️</div>
      <div class="fw-7" style="font-size:20px;">Cannot connect to server</div>
      <p class="text-2" style="margin-top:10px;font-size:13.5px;max-width:400px;margin-left:auto;margin-right:auto;line-height:1.7;">
        The Python Flask server is not running.<br>
        Open a terminal, go to the <strong>backend/</strong> folder and run:<br>
      </p>
      <div style="background:var(--bg2);border:1px solid var(--border);border-radius:var(--r-sm);padding:14px 20px;display:inline-block;margin-top:14px;font-family:var(--mono);font-size:13px;color:var(--green);">
        pip install -r requirements.txt<br>python app.py
      </div>
      <p class="text-3" style="font-size:12px;margin-top:10px;">Then refresh this page.</p>
    </div>`;
}

/* ═══════════════════════════════════════
   INIT
═══════════════════════════════════════ */
window.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    const loader = document.getElementById("loader");
    if (loader) { loader.classList.add("done"); setTimeout(() => loader.remove(), 500); }
    boot();
  }, 1800);
});
