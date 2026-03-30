/**
 * CIRS v3 — All 6 enhancements
 * 1. CDGI logo everywhere + college photo on login
 * 2. Staff = limited menu (My Work only)
 * 3. Photo viewer for admin/coordinator/faculty
 * 4. Classic white loading screen with CDGI logo
 * 5. Faculty sees ALL complaints + can mark resolved
 * 6. Only admin can delete users
 */

const API = `${window.location.origin}/api`;
let token   = localStorage.getItem("cirs_token") || null;
let session = JSON.parse(localStorage.getItem("cirs_user") || "null");
let section = "dashboard";

// ── CDGI Logo SVG (matches AccSoft style) ──
const CDGI_LOGO = `🏛️`;

/* ══════════════════════════════
   API
══════════════════════════════ */
async function api(endpoint, method = "GET", body = null, formData = false) {
  const opts = { method, headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) } };
  if (body && !formData) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  if (body && formData)  { opts.body = body; }
  try {
    const res  = await fetch(`${API}/${endpoint}`, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `Error ${res.status}`);
    return data;
  } catch(e) { throw e; }
}

/* ══════════════════════════════
   TOAST
══════════════════════════════ */
function toast(msg, type = "ok") {
  const c = document.getElementById("toasts");
  if (!c) return;
  const t = document.createElement("div");
  t.className = `toast toast-${type}`;
  t.innerHTML = `<span class="toast-ico">${type==="ok"?"✅":type==="err"?"❌":"ℹ️"}</span><span>${msg}</span>`;
  c.appendChild(t);
  setTimeout(() => { t.style.opacity="0"; t.style.transform="translateX(110%)"; t.style.transition="all .3s"; setTimeout(()=>t.remove(),300); }, 3500);
}

/* ══════════════════════════════
   SESSION
══════════════════════════════ */
function saveSession(d) { token=d.token; session=d.user; localStorage.setItem("cirs_token",token); localStorage.setItem("cirs_user",JSON.stringify(session)); }
function clearSession()  { token=session=null; localStorage.removeItem("cirs_token"); localStorage.removeItem("cirs_user"); }

// Role helpers
function isAdmin()   { return session?.role === "admin"; }
function isCoord()   { return session?.role === "coordinator"; }
function isFaculty() { return session?.role === "faculty"; }
function isStaff()   { return session?.role === "staff"; }
function isStudent() { return session?.role === "student"; }
// Can manage = change status, priority
function canManage() { return ["admin","coordinator","faculty"].includes(session?.role); }
// Can see all complaints
function canViewAll(){ return ["admin","coordinator","faculty"].includes(session?.role); }
// Can delete users — ADMIN ONLY
function canDeleteUsers() { return isAdmin(); }

function initials(n) { return (n||"?").split(" ").map(w=>w[0]).join("").slice(0,2).toUpperCase(); }
function validatePhone(p) { return /^\d{10}$/.test(p); }

/* ══════════════════════════════
   BOOT
══════════════════════════════ */
function boot() {
  if (session && token) renderApp();
  else renderAuth("login");
}

/* ══════════════════════════════
   AUTH — CDGI PORTAL (matches screenshot)
══════════════════════════════ */
function renderAuth(mode = "login") {
  document.getElementById("app").innerHTML = `
    <div class="auth-page">
      <div class="auth-bg"></div>
      <div class="auth-card a1">
        <!-- Top bar like AccSoft -->
        <div class="auth-card-topbar">
          <div class="auth-topbar-icon">C</div>
          <div class="auth-topbar-title">CDGI Campus Issues Portal</div>
        </div>
        <!-- CDGI Logo Section -->
        <div class="auth-logo-section">
          <div class="auth-cdgi-logo">${CDGI_LOGO}</div>
          <div class="auth-cdgi-name">Chameli Devi Group of Institutions</div>
          <div class="auth-cdgi-sub">Indore (M.P.) 452020 · Est. 1994</div>
        </div>
        <!-- Form -->
        <div class="auth-form-section">
          <div class="auth-tabs">
            <button class="auth-tab ${mode==="login"?"active":""}" onclick="renderAuth('login')">Sign In</button>
            <button class="auth-tab ${mode==="register"?"active":""}" onclick="renderAuth('register')">Register</button>
          </div>
          <div id="auth-alert"></div>
          ${mode === "login" ? loginForm() : registerForm()}
        </div>
      </div>
    </div>
    <div class="toasts" id="toasts"></div>
  `;
}

function loginForm() {
  return `
    <div class="form-group">
      <label class="label">Email / User ID <span class="req">*</span></label>
      <div class="input-icon">
        <span class="ico">👤</span>
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
    <button class="btn btn-primary btn-full btn-lg" id="login-btn" onclick="doLogin()">Login »</button>
    <p style="text-align:center;margin-top:14px;font-size:13px;color:var(--text-2);">
      New user? <a href="#" onclick="renderAuth('register')" style="color:var(--blue);font-weight:600;">SignUp (New User)</a>
    </p>
  `;
}

function registerForm() {
  return `
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
        <label class="label">Phone (10 digits)</label>
        <input id="r-phone" class="input" placeholder="9876543210" maxlength="10"
          oninput="this.value=this.value.replace(/\D/g,'').slice(0,10)">
        <span class="field-err" id="phone-err">Must be exactly 10 digits</span>
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
    <p style="text-align:center;margin-top:14px;font-size:13px;color:var(--text-2);">
      Already registered? <a href="#" onclick="renderAuth('login')" style="color:var(--blue);font-weight:600;">Sign in</a>
    </p>
  `;
}

async function doLogin() {
  const email = document.getElementById("l-email").value.trim();
  const pass  = document.getElementById("l-pass").value;
  const btn   = document.getElementById("login-btn");
  if (!email || !pass) { showAuthErr("Please fill all fields."); return; }
  btn.disabled = true; btn.innerHTML = `<span class="spin">⟳</span> Signing in…`;
  try {
    const d = await api("login","POST",{email, password:pass});
    saveSession(d); renderApp();
  } catch(e) {
    showAuthErr(e.message);
    btn.disabled = false; btn.innerHTML = "Login »";
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
  if (!name||!email||!pass) { showAuthErr("Name, email and password are required."); return; }
  if (pass.length < 6)      { showAuthErr("Password must be at least 6 characters."); return; }
  if (phone && !validatePhone(phone)) {
    document.getElementById("phone-err").classList.add("show");
    showAuthErr("Phone must be exactly 10 digits.");
    return;
  }
  document.getElementById("phone-err")?.classList.remove("show");
  try {
    const d = await api("register","POST",{name,email,password:pass,phone,dept,role,roll_no:roll});
    saveSession(d); renderApp();
    toast(`Welcome to CIRS, ${name}! 🎉`,"ok");
  } catch(e) { showAuthErr(e.message); }
}

function showAuthErr(msg) {
  const el = document.getElementById("auth-alert");
  if (el) el.innerHTML = `<div class="alert alert-err"><span class="alert-ico">⚠️</span>${msg}</div>`;
}
function toggleEye(id,btn) {
  const inp = document.getElementById(id);
  inp.type = inp.type==="password" ? "text" : "password";
  btn.textContent = inp.type==="password" ? "👁️" : "🙈";
}

/* ══════════════════════════════
   APP SHELL
══════════════════════════════ */
function renderApp() {
  if (!session) { renderAuth("login"); return; }

  // ── CHANGE 2: Staff sees limited menu ──
  const staffLimited = isStaff();

  document.getElementById("app").innerHTML = `
    <div class="sidebar-overlay" id="sidebar-overlay" onclick="closeSidebar()"></div>
    <div class="shell">
      <aside class="sidebar" id="sidebar">
        <div class="sidebar-head">
          <div class="sidebar-brand">
            <div class="sidebar-cdgi-logo">${CDGI_LOGO}</div>
            <div class="sidebar-brand-text">
              <div class="s-name">CDGI · CIRS</div>
              <div class="s-sub">Campus Portal</div>
            </div>
          </div>
        </div>
        <nav class="nav">
          ${staffLimited ? `
          <!-- Staff sees only My Work -->
          <div>
            <div class="nav-section-label">My Work</div>
            <button class="nav-item active" data-s="report" onclick="go('report')">
              <span class="nav-icon">✍️</span> Report Issue
            </button>
            <button class="nav-item" data-s="complaints" onclick="go('complaints')">
              <span class="nav-icon">🎫</span> My Complaints
            </button>
          </div>
          <div>
            <div class="nav-section-label">Account</div>
            <button class="nav-item" data-s="profile" onclick="go('profile')">
              <span class="nav-icon">👤</span> Profile
            </button>
            <button class="nav-item" onclick="logout()">
              <span class="nav-icon">🚪</span> Sign Out
            </button>
          </div>` : `
          <!-- Full menu for others -->
          <div>
            <div class="nav-section-label">Main Menu</div>
            <button class="nav-item active" data-s="dashboard" onclick="go('dashboard')">
              <span class="nav-icon">📊</span> Dashboard
            </button>
            <button class="nav-item" data-s="report" onclick="go('report')">
              <span class="nav-icon">✍️</span> Report Issue
            </button>
            <button class="nav-item" data-s="complaints" onclick="go('complaints')">
              <span class="nav-icon">🎫</span> ${canViewAll()?"All Complaints":"My Complaints"}
            </button>
          </div>
          ${canManage() ? `
          <div>
            <div class="nav-section-label">Management</div>
            <button class="nav-item" data-s="manage" onclick="go('manage')">
              <span class="nav-icon">⚙️</span> ${isAdmin()?"Admin Panel":isFaculty()?"Faculty Panel":"Coordinator"}
              <span class="nav-badge" id="new-count" style="display:none">0</span>
            </button>
            ${(isAdmin()||isCoord()) ? `<button class="nav-item" data-s="users" onclick="go('users')">
              <span class="nav-icon">👥</span> Users
            </button>` : ""}
          </div>` : ""}
          <div>
            <div class="nav-section-label">Account</div>
            <button class="nav-item" data-s="profile" onclick="go('profile')">
              <span class="nav-icon">👤</span> Profile
            </button>
            <button class="nav-item" onclick="logout()">
              <span class="nav-icon">🚪</span> Sign Out
            </button>
          </div>`}
        </nav>
        <div class="sidebar-foot">
          <div class="user-card" onclick="go('profile')">
            <div class="avatar">${initials(session.name)}</div>
            <div class="user-info">
              <div class="u-name">${session.name}</div>
              <div class="u-role">${session.role} · ${session.dept}</div>
            </div>
          </div>
        </div>
      </aside>

      <main class="main">
        <header class="topbar">
          <div class="topbar-l">
            <button class="menu-btn" onclick="toggleSidebar()">☰</button>
            <div>
              <div class="pg-title" id="pg-title">${staffLimited?"Report Issue":"Dashboard"}</div>
              <div class="pg-crumb">CDGI / <span id="pg-crumb">Campus Portal</span></div>
            </div>
          </div>
          <div class="topbar-r">
            <div style="position:relative;">
              <button class="icon-btn" id="notif-btn" onclick="toggleNotifDrop()">
                🔔<span class="dot-badge hidden" id="notif-dot"></span>
              </button>
              <div class="notif-drop" id="notif-drop">
                <div class="notif-drop-head">
                  <span>Notifications</span>
                  <button onclick="markAllRead()">Mark all read</button>
                </div>
                <div id="notif-list"><div class="notif-empty">Loading…</div></div>
              </div>
            </div>
            <!-- CDGI logo in topbar -->
            <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,var(--blue),var(--red-cdgi));display:flex;align-items:center;justify-content:center;font-size:16px;border:2px solid var(--border);" title="CDGI">🏛️</div>
            <div class="avatar" style="cursor:pointer;" onclick="go('profile')">${initials(session.name)}</div>
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

  // Default section
  if (staffLimited) go("report");
  else go("dashboard");

  loadNotifications();
  document.addEventListener("click", e => {
    const d=document.getElementById("notif-drop"), b=document.getElementById("notif-btn");
    if (d&&b&&!d.contains(e.target)&&!b.contains(e.target)) d.classList.remove("open");
  });
}

function toggleSidebar() {
  document.getElementById("sidebar")?.classList.toggle("open");
  document.getElementById("sidebar-overlay")?.classList.toggle("show");
}
function closeSidebar() {
  document.getElementById("sidebar")?.classList.remove("open");
  document.getElementById("sidebar-overlay")?.classList.remove("show");
}

function go(s) {
  section = s;
  document.querySelectorAll(".nav-item").forEach(el => el.classList.toggle("active", el.dataset.s===s));
  const titles = {dashboard:"Dashboard",report:"Report Issue",complaints:canViewAll()?"All Complaints":"My Complaints",manage:isAdmin()?"Admin Panel":isFaculty()?"Faculty Panel":"Coordinator Panel",users:"Users",profile:"Profile"};
  const pg = document.getElementById("pg-title");
  if (pg) pg.textContent = titles[s] || s;
  const content = document.getElementById("page-content");
  if (!content) return;
  content.innerHTML = `<div style="text-align:center;padding:60px;color:var(--text-3);">Loading…</div>`;
  closeSidebar();
  const map = {dashboard:renderDashboard, report:renderReport, complaints:renderComplaints, manage:renderManage, users:renderUsers, profile:renderProfile};
  if (map[s]) map[s](content);
}

function logout() { clearSession(); renderAuth("login"); }

/* ══════════════════════════════
   DASHBOARD
══════════════════════════════ */
async function renderDashboard(el) {
  try {
    const [stats, recent] = await Promise.all([api("stats"), api("complaints")]);
    const list  = (recent.data||[]).slice(0,6);
    const badge = document.getElementById("new-count");
    if (badge && stats.new > 0) { badge.style.display=""; badge.textContent=stats.new; }
    const cats   = stats.categories || {};
    const maxCat = Math.max(...Object.values(cats), 1);
    const hr = new Date().getHours();
    const greet = hr<12?"morning":hr<17?"afternoon":"evening";

    el.innerHTML = `
      <div class="page-header a1">
        <h1>Good ${greet}, <span>${session.name.split(" ")[0]}</span> 👋</h1>
        <p>${new Date().toLocaleDateString("en-IN",{weekday:"long",day:"numeric",month:"long",year:"numeric"})}</p>
      </div>
      <div class="stats a2">
        <div class="stat s-blue"><div class="stat-top"><div class="stat-ico">🎫</div><span class="stat-delta">Total</span></div><div class="stat-val">${stats.total}</div><div class="stat-label">Total Complaints</div><div class="stat-strip"><div class="stat-strip-fill" style="width:100%"></div></div></div>
        <div class="stat s-teal"><div class="stat-top"><div class="stat-ico">🆕</div><span class="stat-delta">${stats.new}</span></div><div class="stat-val">${stats.new}</div><div class="stat-label">New</div><div class="stat-strip"><div class="stat-strip-fill" style="width:${stats.total?(stats.new/stats.total*100).toFixed(0):0}%"></div></div></div>
        <div class="stat s-yel"><div class="stat-top"><div class="stat-ico">⏳</div><span class="stat-delta">${stats.in_progress}</span></div><div class="stat-val">${stats.in_progress}</div><div class="stat-label">In Progress</div><div class="stat-strip"><div class="stat-strip-fill" style="width:${stats.total?(stats.in_progress/stats.total*100).toFixed(0):0}%"></div></div></div>
        <div class="stat s-green"><div class="stat-top"><div class="stat-ico">✅</div><span class="stat-delta up">${stats.resolution_rate}%</span></div><div class="stat-val">${stats.resolved}</div><div class="stat-label">Resolved</div><div class="stat-strip"><div class="stat-strip-fill" style="width:${stats.resolution_rate}%"></div></div></div>
      </div>
      <div class="two-col a3">
        <div class="card">
          <div class="card-head"><span class="card-title">📈 By Category</span></div>
          <div class="card-body">
            ${Object.keys(cats).length ? `
            <div class="bar-chart">
              ${Object.entries(cats).map(([cat,cnt])=>`
                <div class="bar-wrap">
                  <span class="bar-num">${cnt}</span>
                  <div class="bar-col" style="height:${Math.round(cnt/maxCat*110)+10}px"></div>
                  <span class="bar-lbl">${cat.slice(0,5).toUpperCase()}</span>
                </div>`).join("")}
            </div>` : `<div class="tbl-empty">No data yet</div>`}
          </div>
        </div>
        <div class="card">
          <div class="card-head"><span class="card-title">🚀 Quick Actions</span></div>
          <div class="card-body" style="display:flex;flex-direction:column;gap:10px;">
            <button class="btn btn-primary" onclick="go('report')" style="justify-content:flex-start;gap:14px;padding:16px;">
              <span style="font-size:22px;">✍️</span>
              <div style="text-align:left;"><div>Report a New Issue</div><div style="font-size:12px;opacity:.75;font-weight:400;margin-top:2px;">Submit campus complaint</div></div>
            </button>
            <button class="btn btn-outline" onclick="go('complaints')" style="justify-content:flex-start;gap:14px;padding:16px;">
              <span style="font-size:22px;">🎫</span>
              <div style="text-align:left;"><div>${canViewAll()?"All Complaints":"My Complaints"}</div><div style="font-size:12px;opacity:.75;font-weight:400;margin-top:2px;">Track status in real-time</div></div>
            </button>
            ${canManage()?`<button class="btn btn-outline" onclick="go('manage')" style="justify-content:flex-start;gap:14px;padding:16px;">
              <span style="font-size:22px;">⚙️</span>
              <div style="text-align:left;"><div>Manage Panel</div><div style="font-size:12px;opacity:.75;font-weight:400;margin-top:2px;">${stats.new} new awaiting</div></div>
            </button>`:""}
          </div>
        </div>
      </div>
      <div class="card a4">
        <div class="card-head"><span class="card-title">🕐 Recent Activity</span><button class="btn btn-outline btn-sm" onclick="go('complaints')">View All</button></div>
        <div class="tbl-wrap">
          ${list.length ? `
          <table>
            <thead><tr><th>Ticket</th><th>Title</th><th>${canViewAll()?"Reporter":"Category"}</th><th>Status</th><th>Date</th><th></th></tr></thead>
            <tbody>
              ${list.map(c=>`
                <tr>
                  <td><span class="mono" style="color:var(--blue);font-size:12px;font-weight:700;">${c.ticket_id}</span></td>
                  <td style="font-weight:600;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${c.title}</td>
                  <td>${canViewAll()?`<span class="text-sm text-2">${c.user_name}</span>`:`<span class="cpill c-${c.category}">${c.category}</span>`}</td>
                  <td>${statusBadge(c.status)}</td>
                  <td class="text-sm text-2">${c.created_at}</td>
                  <td><button class="btn btn-ghost btn-sm" onclick="viewTicket('${c.ticket_id}')">View →</button></td>
                </tr>`).join("")}
            </tbody>
          </table>` : `
          <div class="tbl-empty">
            <div style="font-size:40px;margin-bottom:12px;">📭</div>
            <div class="fw-7">No complaints yet</div>
            <button class="btn btn-primary" onclick="go('report')" style="margin-top:14px;">Report an Issue →</button>
          </div>`}
        </div>
      </div>`;
  } catch(e) { el.innerHTML = serverDownBanner(); }
}

/* ══════════════════════════════
   REPORT FORM
══════════════════════════════ */
function renderReport(el) {
  el.innerHTML = `
    <div class="page-header a1">
      <h1>Report <span>New Issue</span></h1>
      <p>Submit a campus complaint — you'll receive an email confirmation</p>
    </div>
    <div style="max-width:720px;">
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
              <label class="label">Priority ${!canManage()?"<span style='color:var(--text-3);font-size:11px;font-weight:400;'>(set by admin)</span>":""}</label>
              ${canManage() ? `
              <select id="r-priority" class="select">
                <option value="low">🟢 Low</option>
                <option value="medium" selected>🟡 Medium</option>
                <option value="high">🔴 High — Urgent</option>
              </select>` : `
              <div class="input" style="background:var(--surface2);color:var(--text-3);cursor:not-allowed;">🟡 Medium — default</div>`}
            </div>
          </div>
          <div class="form-group">
            <label class="label">Location / Block</label>
            <input id="r-location" class="input" placeholder="e.g. Main Block, 2nd Floor, Near Lab-204, Hostel Block B">
          </div>
          <div class="form-group">
            <label class="label">Detailed Description <span class="req">*</span></label>
            <textarea id="r-desc" class="textarea" rows="5" placeholder="Describe the issue in detail — what happened, since when, how it is affecting you…"></textarea>
          </div>
          <div class="form-group">
            <label class="label">📸 Attach Evidence Photo / Video</label>
            <div class="file-zone" id="file-zone" onclick="document.getElementById('r-file').click()">
              <div class="file-zone-ico">📎</div>
              <div class="file-zone-txt"><strong>Click to browse</strong> or drag & drop</div>
              <div class="file-zone-hint">JPG · PNG · MP4 · PDF — max 16MB</div>
            </div>
            <input type="file" id="r-file" style="display:none" accept="image/*,video/*,.pdf" onchange="handleFile(event)">
            <div id="file-preview"></div>
          </div>
          <div style="display:flex;gap:10px;margin-top:8px;">
            <button class="btn btn-primary btn-lg" id="submit-btn" onclick="submitComplaint()" style="flex:1;">🚀 Submit Complaint</button>
            <button class="btn btn-outline btn-lg" onclick="go(isStaff()?'complaints':'dashboard')">Cancel</button>
          </div>
        </div>
      </div>
      <div class="card a3" style="margin-top:16px;">
        <div class="card-body">
          <p style="font-size:14px;color:var(--text-2);margin-bottom:14px;">Complaint lifecycle:</p>
          <div class="tracker">
            ${["Submit","Assigned","In Progress","Resolved","Feedback"].map((l,i)=>`
              <div class="t-step ${i===0?"active":""}">
                <div class="t-dot">${i===0?"1":i+1}</div>
                <div class="t-label">${l}</div>
              </div>`).join("")}
          </div>
          <p style="text-align:center;font-size:13px;color:var(--text-3);margin-top:10px;">📧 You'll receive email updates at every stage.</p>
        </div>
      </div>
    </div>`;

  const zone = document.getElementById("file-zone");
  zone.addEventListener("dragover", e=>{e.preventDefault();zone.classList.add("over");});
  zone.addEventListener("dragleave", ()=>zone.classList.remove("over"));
  zone.addEventListener("drop", e=>{e.preventDefault();zone.classList.remove("over");if(e.dataTransfer.files[0])previewFile(e.dataTransfer.files[0]);});
}

function handleFile(e) { if(e.target.files[0]) previewFile(e.target.files[0]); }
function previewFile(file) {
  const el = document.getElementById("file-preview");
  if (!el) return;
  el.innerHTML = `<div class="file-preview"><span>📎</span><span class="file-preview-name">${file.name}</span><span class="file-preview-size">${(file.size/1024).toFixed(1)} KB</span><button onclick="clearFile()" style="background:none;border:none;color:var(--text-3);font-size:20px;cursor:pointer;margin-left:auto;">×</button></div>`;
  window._selectedFile = file;
}
function clearFile() { document.getElementById("file-preview").innerHTML=""; document.getElementById("r-file").value=""; window._selectedFile=null; }

async function submitComplaint() {
  const title    = document.getElementById("r-title").value.trim();
  const category = document.getElementById("r-cat").value;
  const desc     = document.getElementById("r-desc").value.trim();
  const location = document.getElementById("r-location")?.value.trim()||"";
  const alertEl  = document.getElementById("report-alert");
  const btn      = document.getElementById("submit-btn");
  if (!title||!category||!desc) { alertEl.innerHTML=`<div class="alert alert-err"><span class="alert-ico">⚠️</span>Title, category and description required.</div>`; return; }
  btn.disabled=true; btn.innerHTML=`<span class="spin">⟳</span> Submitting…`;
  try {
    const fd = new FormData();
    fd.append("title",title); fd.append("category",category);
    fd.append("description",desc); fd.append("location",location);
    if (canManage()) { const pe=document.getElementById("r-priority"); if(pe) fd.append("priority",pe.value); }
    if (window._selectedFile) fd.append("image",window._selectedFile);
    const res = await api("complaints","POST",fd,true);
    toast(`✅ ${res.message}`,"ok");
    window._selectedFile=null;
    go("complaints");
  } catch(e) {
    alertEl.innerHTML=`<div class="alert alert-err"><span class="alert-ico">⚠️</span>${e.message}</div>`;
    btn.disabled=false; btn.innerHTML="🚀 Submit Complaint";
  }
}

/* ══════════════════════════════
   COMPLAINTS LIST
══════════════════════════════ */
async function renderComplaints(el) {
  try {
    const data = await api("complaints");
    const list = data.data||[];
    el.innerHTML = `
      <div class="page-header a1">
        <h1>${canViewAll()?"All":"My"} <span>Complaints</span></h1>
        <p>${list.length} total complaints — live from database</p>
      </div>
      <div class="flex-bc mb-20 a2" style="flex-wrap:wrap;gap:10px;">
        <div style="display:flex;gap:8px;flex-wrap:wrap;" id="filter-chips">
          ${["all","new","in-progress","resolved"].map(s=>`
            <button class="btn ${s==="all"?"btn-primary":"btn-outline"} btn-sm" onclick="filterChip(this,'${s}')" data-filter="${s}">
              ${s==="all"?"All ("+list.length+")":s==="new"?"🆕 New ("+list.filter(c=>c.status==="new").length+")":s==="in-progress"?"⏳ Active ("+list.filter(c=>c.status==="in-progress").length+")":"✅ Done ("+list.filter(c=>c.status==="resolved").length+")"}
            </button>`).join("")}
        </div>
        <div class="input-icon" style="width:220px;">
          <span class="ico">🔍</span>
          <input class="input" placeholder="Search…" id="search-inp" oninput="searchTickets(this.value)">
        </div>
      </div>
      <div id="ticket-grid" class="tickets-grid a3">
        ${list.length ? list.map(c=>ticketCard(c)).join("") : `
          <div class="card" style="padding:60px;text-align:center;">
            <div style="font-size:48px;margin-bottom:14px;">📭</div>
            <div class="fw-7" style="font-size:19px;">No Complaints Found</div>
            <p class="text-sm text-2" style="margin-top:8px;">Submit the first campus complaint!</p>
            <button class="btn btn-primary" onclick="go('report')" style="margin-top:16px;">Report an Issue →</button>
          </div>`}
      </div>`;
  } catch(e) { el.innerHTML = serverDownBanner(); }
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
        ${canViewAll()&&c.user_name?`<span>👤 ${c.user_name}</span>`:""}
        ${c.assigned_to?`<span>🔧 ${c.assigned_to}</span>`:""}
        ${c.image_path?`<span style="color:var(--blue);">📸 Photo</span>`:""}
      </div>
      <div class="tkt-foot">
        <span class="tkt-desc">${c.description}</span>
        <button class="btn btn-outline btn-sm" onclick="event.stopPropagation();viewTicket('${c.ticket_id}')">Details →</button>
      </div>
    </div>`;
}

function filterChip(btn, status) {
  document.querySelectorAll("#filter-chips .btn").forEach(b=>b.className="btn btn-outline btn-sm");
  btn.className="btn btn-primary btn-sm";
  document.querySelectorAll("#ticket-grid .tkt").forEach(el=>{
    el.style.display=(status==="all"||el.dataset.status===status)?"":"none";
  });
}
function searchTickets(q) {
  document.querySelectorAll("#ticket-grid .tkt").forEach(el=>{
    el.style.display=el.dataset.title?.includes(q.toLowerCase())?"":"none";
  });
}

/* ══════════════════════════════
   TICKET DETAIL MODAL (Change 3: Photo visible to faculty/admin/coord)
══════════════════════════════ */
async function viewTicket(ticketId) {
  try {
    const c  = await api(`complaints/${ticketId}`);
    const steps = ["new","in-progress","resolved"];
    const si    = steps.indexOf(c.status);

    // Photo section — visible to admin, coordinator, faculty
    const showPhoto = canViewAll() && c.image_path;
    const canSeePhoto = canViewAll();

    openModal(`
      <div class="modal-head">
        <div>
          <div class="mono" style="font-size:11px;color:var(--blue);margin-bottom:4px;font-weight:700;">${c.ticket_id}</div>
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

        <div class="tracker" style="margin-bottom:22px;">
          ${["Submitted","Assigned","In Progress","Resolved","Feedback"].map((l,i)=>`
            <div class="t-step ${i<si+1?"done":i===si+1?"active":""}">
              <div class="t-dot">${i<si+1?"✓":i+1}</div>
              <div class="t-label">${l}</div>
            </div>`).join("")}
        </div>

        <!-- Reporter Details — visible to admin/coord/faculty -->
        ${canViewAll() ? `
        <div class="reporter-card">
          <div class="reporter-card-title">👤 Reporter Information</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13.5px;">
            <div><span class="text-3">Name: </span><strong>${c.user_name||"—"}</strong></div>
            <div><span class="text-3">Email: </span><strong>${c.user_email||"—"}</strong></div>
            <div><span class="text-3">Dept: </span><strong>${c.user_dept||"—"}</strong></div>
            <div><span class="text-3">Roll No: </span><strong>${c.user_roll||"—"}</strong></div>
            <div><span class="text-3">Phone: </span><strong>${c.user_phone||"—"}</strong></div>
            <div><span class="text-3">Submitted: </span><strong>${c.created_at}</strong></div>
          </div>
        </div>` : ""}

        <div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--r-sm);padding:14px;margin-bottom:14px;">
          <div class="label" style="margin-bottom:6px;">Description</div>
          <p style="font-size:14.5px;line-height:1.75;">${c.description}</p>
        </div>

        ${c.location ? `
        <div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--r-sm);padding:12px;margin-bottom:14px;font-size:14px;">
          <span class="text-3">📍 Location: </span><strong>${c.location}</strong>
        </div>` : ""}

        <!-- CHANGE 3: Evidence Photo — visible to admin/coordinator/faculty -->
        ${c.image_path && canSeePhoto ? `
        <div style="margin-bottom:16px;">
          <div class="label" style="margin-bottom:8px;">📸 Evidence Photo</div>
          <img src="${c.image_path}" class="evidence-img"
            alt="Evidence submitted with complaint"
            onclick="window.open('${c.image_path}','_blank')"
            title="Click to view full size">
          <div class="img-caption">Click image to open full size · Submitted by ${c.user_name}</div>
        </div>` : c.image_path && !canSeePhoto ? `
        <div style="background:#fef3c7;border:1px solid #fde68a;border-radius:var(--r-sm);padding:12px;margin-bottom:14px;font-size:13px;color:#92400e;">
          📸 Evidence photo attached — visible to faculty, coordinator and admin only.
        </div>` : ""}

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;">
          ${[["Dept",c.dept||"—"],["Assigned To",c.assigned_to||"Pending"],["Last Updated",c.updated_at||c.created_at],["Ticket ID",c.ticket_id]].map(([k,v])=>`
            <div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--r-sm);padding:12px;">
              <div class="label" style="font-size:10px;margin-bottom:3px;">${k}</div>
              <div class="fw-7" style="font-size:14px;">${v}</div>
            </div>`).join("")}
        </div>

        <!-- CHANGE 5: Faculty can also manage complaints -->
        ${canManage() && c.status !== "resolved" ? `
        <div class="divider"></div>
        <div class="label" style="margin-bottom:10px;">${isFaculty()?"Faculty":"Admin / Coordinator"} Actions</div>
        <div style="display:grid;grid-template-columns:1fr auto;gap:8px;margin-bottom:10px;">
          <input id="assign-inp" class="input" placeholder="Assign to coordinator / staff…" value="${c.assigned_to||""}">
          <button class="btn btn-primary" onclick="assignTicket('${c.ticket_id}')">Assign</button>
        </div>
        ${(isAdmin()||isCoord()) ? `
        <div class="form-row" style="margin-bottom:10px;">
          <div class="form-group" style="margin-bottom:0;">
            <label class="label">Priority</label>
            <select id="modal-priority" class="select">
              <option value="low" ${c.priority==="low"?"selected":""}>🟢 Low</option>
              <option value="medium" ${c.priority==="medium"?"selected":""}>🟡 Medium</option>
              <option value="high" ${c.priority==="high"?"selected":""}>🔴 High</option>
            </select>
          </div>
          <div class="form-group" style="margin-bottom:0;display:flex;align-items:flex-end;">
            <button class="btn btn-outline btn-sm" onclick="updatePriority('${c.ticket_id}')" style="width:100%;height:44px;">Update Priority</button>
          </div>
        </div>` : ""}
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          ${c.status==="new"?`<button class="btn btn-outline btn-sm" onclick="updateTicketStatus('${c.ticket_id}','in-progress')">▶ Mark In Progress</button>`:""}
          <button class="btn btn-success btn-sm" onclick="updateTicketStatus('${c.ticket_id}','resolved')">✅ Mark Resolved</button>
          ${isAdmin()?`<button class="btn btn-danger btn-sm" onclick="deleteTicket('${c.ticket_id}')">🗑 Delete</button>`:""}
        </div>` : ""}

        ${canManage() && c.status === "resolved" ? `
        <div class="alert alert-ok" style="margin-top:12px;"><span class="alert-ico">✅</span>This complaint has been resolved${c.assigned_to?" by "+c.assigned_to:""}.</div>` : ""}

        ${c.status==="resolved" && c.user_id===session?.id && !c.feedback ? `
        <div class="divider"></div>
        <div class="label">Rate Resolution</div>
        <div style="display:flex;gap:7px;margin-top:10px;flex-wrap:wrap;">
          ${[1,2,3,4,5].map(i=>`<button class="btn btn-outline btn-sm" onclick="submitFeedback('${c.ticket_id}',${i})" style="font-size:20px;padding:8px 14px;">${"⭐".repeat(i)}</button>`).join("")}
        </div>` : ""}

        ${c.feedback ? `<div class="alert alert-ok" style="margin-top:12px;"><span class="alert-ico">⭐</span>Feedback: ${c.feedback}/5 — Thank you!</div>` : ""}
      </div>`);
  } catch(e) { toast("Failed to load: "+e.message,"err"); }
}

async function assignTicket(tid) {
  const name = document.getElementById("assign-inp").value.trim();
  if (!name) { toast("Enter name first","err"); return; }
  try { await api(`complaints/${tid}`,"PUT",{status:"in-progress",assigned_to:name}); toast("Assigned! Email sent.","ok"); closeModal(); go(section); }
  catch(e) { toast(e.message,"err"); }
}
async function updateTicketStatus(tid, status) {
  try { await api(`complaints/${tid}`,"PUT",{status}); toast(`Status → ${status}`,"ok"); closeModal(); go(section); }
  catch(e) { toast(e.message,"err"); }
}
async function updatePriority(tid) {
  const priority = document.getElementById("modal-priority").value;
  try { await api(`complaints/${tid}`,"PUT",{priority}); toast(`Priority → ${priority}`,"ok"); closeModal(); go(section); }
  catch(e) { toast(e.message,"err"); }
}
async function deleteTicket(tid) {
  if (!confirm(`Delete ${tid}? Cannot undo.`)) return;
  try { await api(`complaints/${tid}`,"DELETE"); toast(`${tid} deleted`,"ok"); closeModal(); go(section); }
  catch(e) { toast(e.message,"err"); }
}
async function submitFeedback(tid, rating) {
  try { await api(`complaints/${tid}`,"PUT",{feedback:rating}); toast("Feedback submitted! ⭐","ok"); closeModal(); go(section); }
  catch(e) { toast(e.message,"err"); }
}

/* ══════════════════════════════
   MANAGE PANEL
══════════════════════════════ */
async function renderManage(el) {
  try {
    const [data, stats] = await Promise.all([api("complaints"), api("stats")]);
    const list = data.data||[];
    el.innerHTML = `
      <div class="page-header a1">
        <h1>${isAdmin()?"Admin":isFaculty()?"Faculty":"Coordinator"} <span>Panel</span></h1>
        <p>Manage all campus complaints</p>
      </div>
      <div class="stats a2" style="grid-template-columns:repeat(3,1fr);">
        ${[["new","🆕","New","s-teal"],["in-progress","⏳","In Progress","s-yel"],["resolved","✅","Resolved","s-green"]].map(([s,ico,lbl,cls])=>`
          <div class="stat ${cls}"><div class="stat-top"><div class="stat-ico">${ico}</div></div><div class="stat-val">${list.filter(c=>c.status===s).length}</div><div class="stat-label">${lbl}</div></div>`).join("")}
      </div>
      <div class="card a3">
        <div class="card-head">
          <span class="card-title">📋 All Complaints (${list.length})</span>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            <select class="select" style="padding:7px 10px;font-size:13px;width:auto;" onchange="filterTable(this.value)">
              <option value="all">All Status</option>
              <option value="new">New</option>
              <option value="in-progress">In Progress</option>
              <option value="resolved">Resolved</option>
            </select>
            <div class="input-icon" style="width:180px;">
              <span class="ico">🔍</span>
              <input class="input" style="padding:7px 12px 7px 36px;font-size:13px;" placeholder="Search…" oninput="filterTableSearch(this.value)">
            </div>
          </div>
        </div>
        <div class="tbl-wrap">
          <table id="admin-tbl">
            <thead>
              <tr><th>Ticket</th><th>Title</th><th>Reporter</th><th>Category</th><th>Priority</th><th>Status</th><th>Photo</th><th>Date</th><th>Actions</th></tr>
            </thead>
            <tbody>
              ${list.length ? list.map(c=>`
                <tr data-status="${c.status}" data-title="${(c.title||"").toLowerCase()}">
                  <td><span class="mono" style="color:var(--blue);font-size:12px;font-weight:700;">${c.ticket_id}</span></td>
                  <td style="font-weight:600;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${c.title}">${c.title}</td>
                  <td class="text-sm text-2">${c.user_name}</td>
                  <td><span class="cpill c-${c.category}">${c.category}</span></td>
                  <td><span class="flex-c gap-8"><span class="pdot p-${c.priority}"></span>${c.priority}</span></td>
                  <td>${statusBadge(c.status)}</td>
                  <td>${c.image_path?`<a href="${c.image_path}" target="_blank" class="btn btn-outline btn-sm" style="font-size:12px;">📸 View</a>`:`<span class="text-3 text-xs">None</span>`}</td>
                  <td class="text-sm text-2">${c.created_at}</td>
                  <td>
                    <div style="display:flex;gap:5px;">
                      <button class="btn btn-ghost btn-sm" onclick="viewTicket('${c.ticket_id}')">View</button>
                      ${c.status!=="resolved"?`<button class="btn btn-success btn-sm" onclick="updateTicketStatus('${c.ticket_id}','${c.status==="new"?"in-progress":"resolved"}')">${c.status==="new"?"▶":"✓"}</button>`:""}
                    </div>
                  </td>
                </tr>`).join("") : `<tr><td colspan="9" class="tbl-empty">No complaints yet.</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>`;
  } catch(e) { el.innerHTML = serverDownBanner(); }
}

function filterTable(val) { document.querySelectorAll("#admin-tbl tbody tr[data-status]").forEach(r=>{r.style.display=val==="all"||r.dataset.status===val?"":"none";}); }
function filterTableSearch(q) { document.querySelectorAll("#admin-tbl tbody tr[data-title]").forEach(r=>{r.style.display=r.dataset.title?.includes(q.toLowerCase())?"":"none";}); }

/* ══════════════════════════════
   USERS — Change 6: Only admin can delete
══════════════════════════════ */
async function renderUsers(el) {
  try {
    const data = await api("users");
    const list = data.data||[];
    el.innerHTML = `
      <div class="page-header a1">
        <h1>Registered <span>Users</span></h1>
        <p>${list.length} users · ${isAdmin()?"Admin: you can delete users":"Coordinator: view only"}</p>
      </div>
      <div class="card a2">
        <div class="card-head"><span class="card-title">👥 All Users</span></div>
        <div class="tbl-wrap">
          <table>
            <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Dept</th><th>Roll No.</th><th>Phone</th><th>Joined</th><th>Actions</th></tr></thead>
            <tbody>
              ${list.map(u=>`
                <tr>
                  <td><div class="flex-c gap-8"><div class="avatar" style="width:30px;height:30px;font-size:11px;flex-shrink:0;">${initials(u.name)}</div><span class="fw-7">${u.name}</span></div></td>
                  <td class="text-sm text-2">${u.email}</td>
                  <td><span class="badge b-${u.role}">${u.role}</span></td>
                  <td class="text-sm">${u.dept||"—"}</td>
                  <td class="mono text-xs text-2">${u.roll_no||"—"}</td>
                  <td class="text-sm text-2">${u.phone||"—"}</td>
                  <td class="text-sm text-2">${u.created_at}</td>
                  <td>
                    <div style="display:flex;gap:6px;align-items:center;">
                      ${isAdmin() ? `
                      <select class="select" style="padding:5px 8px;font-size:12px;width:auto;" onchange="changeRole(${u.id},this.value)">
                        <option ${u.role==="student"?"selected":""} value="student">student</option>
                        <option ${u.role==="faculty"?"selected":""} value="faculty">faculty</option>
                        <option ${u.role==="staff"?"selected":""} value="staff">staff</option>
                        <option ${u.role==="coordinator"?"selected":""} value="coordinator">coordinator</option>
                        <option ${u.role==="admin"?"selected":""} value="admin">admin</option>
                      </select>
                      <button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id},'${u.name}')" title="Delete user" style="padding:5px 10px;">🗑</button>
                      ` : `<span class="text-xs text-2">${u.role}</span>`}
                    </div>
                  </td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>
      </div>
      ${isAdmin() ? `<div class="alert alert-info" style="margin-top:12px;"><span class="alert-ico">ℹ️</span>Only Admin can delete users. Deleting a user is permanent and cannot be undone.</div>` : ""}
    `;
  } catch(e) { el.innerHTML = serverDownBanner(); }
}

async function changeRole(uid, role) {
  try { await api(`users/${uid}/role`,"PUT",{role}); toast(`Role → ${role}`,"ok"); }
  catch(e) { toast(e.message,"err"); }
}

async function deleteUser(uid, name) {
  if (!isAdmin()) { toast("Only admin can delete users","err"); return; }
  if (!confirm(`DELETE user "${name}"?\n\nThis is PERMANENT and cannot be undone.`)) return;
  try {
    await api(`users/${uid}`,"DELETE");
    toast(`User ${name} deleted`,"ok");
    go("users");
  } catch(e) { toast(e.message,"err"); }
}

/* ══════════════════════════════
   PROFILE
══════════════════════════════ */
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
              ${[["🎓 Department",session.dept],["📋 Roll Number",session.roll_no||"—"],["📱 Phone",session.phone||"—"],["🏫 Institution","CDGI, Indore"]].map(([k,v])=>`
                <div class="flex-bc" style="padding:10px;background:var(--surface2);border-radius:var(--r-sm);margin-bottom:8px;font-size:14px;">
                  <span class="text-2">${k}</span><span class="fw-7">${v}</span>
                </div>`).join("")}
            </div>
          </div>
        </div>
        <div class="card a2">
          <div class="card-head"><span class="card-title">✏️ Edit Profile</span></div>
          <div class="card-body">
            <div id="profile-alert"></div>
            <div class="form-group"><label class="label">Full Name</label><input id="p-name" class="input" value="${session.name}"></div>
            <div class="form-group"><label class="label">Email (cannot change)</label><input class="input" value="${session.email}" disabled style="opacity:.5;"></div>
            <div class="form-group">
              <label class="label">Phone (10 digits)</label>
              <input id="p-phone" class="input" value="${session.phone||""}" placeholder="10-digit number" maxlength="10" oninput="this.value=this.value.replace(/\D/g,'').slice(0,10)">
              <span class="field-err" id="profile-phone-err">Must be exactly 10 digits</span>
            </div>
            <div class="divider"></div>
            <div class="form-group">
              <label class="label">New Password (leave blank to keep)</label>
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
  if (phone && !validatePhone(phone)) { document.getElementById("profile-phone-err").classList.add("show"); toast("Phone must be 10 digits","err"); return; }
  document.getElementById("profile-phone-err")?.classList.remove("show");
  try {
    const body = {name, phone};
    if (pass) body.password = pass;
    const res = await api("profile","PUT",body);
    session = res.user; localStorage.setItem("cirs_user",JSON.stringify(session));
    document.getElementById("profile-alert").innerHTML=`<div class="alert alert-ok"><span class="alert-ico">✅</span>Profile updated!</div>`;
    toast("Profile saved!","ok");
  } catch(e) { toast(e.message,"err"); }
}

/* ══════════════════════════════
   NOTIFICATIONS
══════════════════════════════ */
async function loadNotifications() {
  try {
    const data  = await api("notifications");
    const list  = data.data||[];
    const unread = data.unread||0;
    const dot = document.getElementById("notif-dot");
    if (dot) dot.classList.toggle("hidden", unread===0);
    const listEl = document.getElementById("notif-list");
    if (!listEl) return;
    listEl.innerHTML = list.length
      ? list.map(n=>`<div class="notif-item ${!n.is_read?"unread":""}"><div class="notif-msg">${n.message}</div><div class="notif-time">${n.created_at}</div></div>`).join("")
      : `<div class="notif-empty">No notifications yet</div>`;
  } catch(e) { /* silent */ }
}
async function markAllRead() {
  try { await api("notifications/read-all","PUT"); document.getElementById("notif-dot")?.classList.add("hidden"); document.querySelectorAll(".notif-item.unread").forEach(el=>el.classList.remove("unread")); toast("All read","ok"); }
  catch(e) { toast(e.message,"err"); }
}
function toggleNotifDrop() { document.getElementById("notif-drop").classList.toggle("open"); loadNotifications(); }

/* ══════════════════════════════
   MODAL
══════════════════════════════ */
function openModal(html) { document.getElementById("modal").innerHTML=html; document.getElementById("overlay").classList.add("show"); }
function closeModal() { document.getElementById("overlay")?.classList.remove("show"); }

/* ══════════════════════════════
   HELPERS
══════════════════════════════ */
function statusBadge(s) {
  const m={new:"b-new","in-progress":"b-progress",resolved:"b-resolved"};
  const l={new:"🆕 New","in-progress":"⏳ In Progress",resolved:"✅ Resolved"};
  return `<span class="badge ${m[s]||"b-new"}">${l[s]||s}</span>`;
}
function serverDownBanner() {
  return `<div class="card" style="padding:52px;text-align:center;">
    <div style="font-size:52px;margin-bottom:16px;">⚠️</div>
    <div class="fw-7" style="font-size:21px;">Server Not Running</div>
    <p class="text-2" style="margin-top:10px;font-size:14px;">Run: <code style="background:var(--bg2);padding:2px 8px;border-radius:4px;">cd backend && python app.py</code></p>
  </div>`;
}

/* ══════════════════════════════
   INIT
══════════════════════════════ */
window.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    const loader = document.getElementById("loader");
    if (loader) { loader.classList.add("done"); setTimeout(()=>loader.remove(),500); }
    boot();
  }, 2000);
});
