/**
 * CIRS v6 Frontend
 * - Professional Service Unit Workflow
 * - Role-Based Dashboards (Student, Manager, Staff, HOD, Principal)
 * - 48-hour Escalation with SLA Timer
 * - Before/After photos
 * - Enhanced email notifications
 */
const API = `${window.location.origin}/api`;
let token   = localStorage.getItem("cirs_token") || null;
let session = JSON.parse(localStorage.getItem("cirs_user") || "null");
let section = "dashboard";



function showTooltip(e, title, val) {
  const t = document.getElementById("chart-tooltip");
  if (!t) return;
  t.innerHTML = `<div class="chart-tooltip-title">${title}</div><div class="chart-tooltip-val">${val} Complaints</div>`;
  t.className = "chart-tooltip show";
  t.style.left = (e.clientX + 15) + "px";
  t.style.top = (e.clientY - 40) + "px";
}

function showTableTooltip(e, id, title, category, status, reporter, desc, date) {
  const t = document.getElementById("chart-tooltip");
  if (!t) return;
  
  const shortDesc = desc && desc.length > 120 ? desc.substring(0, 120) + "..." : (desc || "No description provided.");
  
  t.innerHTML = `
    <div class="tt-head">
      <span class="tt-id">${id}</span>
      <span class="tt-status">${status}</span>
    </div>
    <div class="tt-title">${title}</div>
    <div class="tt-meta">
      <div class="tt-meta-item">
        <span class="tt-meta-lbl">Category:</span>
        <span class="tt-meta-val">${category}</span>
      </div>
      <div class="tt-meta-item">
        <span class="tt-meta-lbl">Reporter:</span>
        <span class="tt-meta-val">${reporter || 'Student/Faculty'}</span>
      </div>
      <div class="tt-meta-item">
        <span class="tt-meta-lbl">Date:</span>
        <span class="tt-meta-val" style="font-family: var(--mono); font-size: 11px;">${date || 'Recent'}</span>
      </div>
      <div style="margin-top: 6px; padding-top: 6px; border-top: 1px dashed rgba(255,255,255,0.1); font-size: 11.5px; color: #94a3b8; line-height: 1.4;">
        ${shortDesc}
      </div>
    </div>
  `;
  t.className = "chart-tooltip table-tooltip show";
  
  // Adjust position to stay within viewport
  const tooltipWidth = 300; // slightly wider for description
  let left = e.clientX + 15;
  if (left + tooltipWidth > window.innerWidth) {
    left = e.clientX - tooltipWidth - 15;
  }
  
  t.style.left = left + "px";
  t.style.top = (e.clientY + 15) + "px";
}

function hideTooltip() {
  const t = document.getElementById("chart-tooltip");
  if (t) t.className = "chart-tooltip";
}

const getWavePath = (data) => {
  const maxTrend = Math.max(...data, 1);
  const width = 100;
  const height = 40;
  const step = width / (data.length - 1);
  const points = data.map((v, i) => ({
    x: i * step,
    y: height - (v / maxTrend * 25) - 8
  }));
  let d = `M${points[0].x} ${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const xc = (points[i].x + points[i+1].x) / 2;
    const yc = (points[i].y + points[i+1].y) / 2;
    d += ` Q ${points[i].x} ${points[i].y}, ${xc} ${yc}`;
  }
  d += ` T ${points[points.length-1].x} ${points[points.length-1].y}`;
  return d;
};

const getAreaPath = (data) => {
  const maxTrend = Math.max(...data, 1);
  const width = 100;
  const height = 40;
  const step = width / (data.length - 1);
  const points = data.map((v, i) => ({
    x: i * step,
    y: height - (v / maxTrend * 20) - 5
  }));
  let d = `M0 ${height} L${points[0].x} ${points[0].y}`;
  for (let i = 0; i < points.length - 1; i++) {
    const xc = (points[i].x + points[i+1].x) / 2;
    const yc = (points[i].y + points[i+1].y) / 2;
    d += ` Q ${points[i].x} ${points[i].y}, ${xc} ${yc}`;
  }
  d += ` T ${points[points.length-1].x} ${points[points.length-1].y}`;
  d += ` L${width} ${height} Z`;
  return d;
};

async function showGraphDetail(type) {
  const stats = await api("stats");
  if (!stats) return;
  
  const trends = stats.trends || [0,0,0,0,0,0,0];
  const maxTrend = Math.max(...trends, 1);
  const titles = { total: "Total Complaints", routed: "Routed Issues", progress: "Work in Progress", resolved: "Resolved Issues" };
  const colors = { total: "detail-blue", routed: "detail-orange", progress: "detail-purple", resolved: "detail-green" };
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const last7Days = Array.from({length: 7}, (_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (6 - i));
    return days[d.getDay()];
  });

  const html = `
    <div class="graph-detail-wrap ${colors[type] || ''}">
      <div class="graph-detail-header">
        <div>
          <div class="graph-detail-title">${titles[type]}</div>
          <div class="graph-detail-subtitle">In-depth analysis of campus reporting</div>
        </div>
        <button class="btn btn-outline btn-sm" onclick="closeModal()">Close</button>
      </div>
      
      <div class="large-chart-container" style="justify-content: center; align-items: center;">
        ${type === 'total' ? `
          <div style="display: flex; align-items: flex-end; gap: 15px; width: 100%; height: 100%;">
            ${trends.map((v, i) => `
              <div class="large-bar">
                <div class="large-bar-val">${v}</div>
                <div class="large-bar-fill" style="height: ${Math.max((v/maxTrend*100), 5)}%"></div>
                <div class="large-bar-label">${last7Days[i]}</div>
              </div>
            `).join("")}
          </div>
        ` : type === 'routed' || type === 'resolved' ? `
          <div style="width: 100%; height: 100%; display: flex; flex-direction: column;">
            <svg viewBox="0 0 100 40" style="width: 100%; height: 200px; fill: none; stroke: var(--wg-s, #3b82f6); stroke-width: 2;">
               ${type === 'resolved' ? `<path d="${getAreaPath(trends)}" fill="var(--wg-s)" style="opacity: 0.15; stroke:none;" />` : ''}
               <path d="${type === 'resolved' ? getAreaPath(trends).replace(' Z', '').replace('M0 40 L', 'M') : getWavePath(trends)}" stroke-width="1.5" />
            </svg>
            <div style="display: flex; justify-content: space-between; margin-top: 20px; padding: 0 10px;">
              ${last7Days.map(d => `<span style="font-size: 11px; font-weight: 600; color: var(--text-3);">${d}</span>`).join("")}
            </div>
          </div>
        ` : `
          <div style="position: relative; width: 220px; height: 220px;">
            <svg viewBox="0 0 100 100" style="transform: rotate(-90deg); width: 100%; height: 100%;">
              <circle cx="50" cy="50" r="45" fill="none" stroke="var(--surface2)" stroke-width="8" />
              <circle cx="50" cy="50" r="45" fill="none" stroke="var(--wg-s, #8b5cf6)" stroke-width="8" 
                stroke-dasharray="283" 
                stroke-dashoffset="${283 - (283 * (stats.total ? stats.in_progress/stats.total : 0))}"
                style="transition: stroke-dashoffset 1s ease; filter: drop-shadow(0 0 10px var(--wg-s));" />
            </svg>
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;">
              <div style="font-size: 48px; font-weight: 800;">${stats.in_progress}</div>
              <div style="font-size: 12px; font-weight: 700; color: var(--text-3); text-transform: uppercase;">Active</div>
            </div>
          </div>
        `}
      </div>

      <div class="detail-stats-grid">
        <div class="detail-stat-item">
          <div class="detail-stat-label">Total Count</div>
          <div class="detail-stat-val">${stats[type == 'total' ? 'total' : type == 'progress' ? 'in_progress' : type == 'resolved' ? 'resolved' : 'new'] || 0}</div>
        </div>
        <div class="detail-stat-item">
          <div class="detail-stat-label">Avg / Day</div>
          <div class="detail-stat-val">${(trends.reduce((a,b)=>a+b,0)/7).toFixed(1)}</div>
        </div>
        <div class="detail-stat-item">
          <div class="detail-stat-label">Efficiency Rate</div>
          <div class="detail-stat-val">${stats.resolution_rate || 0}%</div>
        </div>
      </div>
    </div>
  `;
  openModal(html, "lg");
}

async function api(endpoint, method="GET", body=null, formData=false) {
  const opts = { method, headers: { ...(token ? {Authorization:`Bearer ${token}`} : {}) } };
  if (body && !formData) { opts.headers["Content-Type"]="application/json"; opts.body=JSON.stringify(body); }
  if (body && formData) opts.body = body;
  try {
    const res = await fetch(`${API}/${endpoint}`, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `Error ${res.status}`);
    return data;
  } catch(e) { throw e; }
}

function toast(msg, type="ok") {
  const c = document.getElementById("toasts"); if (!c) return;
  const t = document.createElement("div");
  t.className = `toast toast-${type}`;
  t.innerHTML = `<span class="toast-ico">${type==="ok"?"✅":type==="err"?"❌":"ℹ️"}</span><span>${msg}</span>`;
  c.appendChild(t);
  setTimeout(()=>{t.style.opacity="0";t.style.transform="translateX(110%)";t.style.transition="all .3s";setTimeout(()=>t.remove(),300);},3500);
}

function saveSession(d){token=d.token;session=d.user;localStorage.setItem("cirs_token",token);localStorage.setItem("cirs_user",JSON.stringify(session));}
function clearSession(){token=session=null;localStorage.removeItem("cirs_token");localStorage.removeItem("cirs_user");}
function isAdmin(){return session?.role==="admin";}
function isCoord(){return session?.role==="coordinator";}
function isFaculty(){return session?.role==="faculty";}
function isStaff(){return session?.role==="staff";}
function isManager(){return session?.role==="service_unit_manager";}
function isHOD(){return session?.role==="hod";}
function isPrincipal(){return session?.role==="principal";}
function canReport(){return ["student","faculty"].includes(session?.role);}
function canManage(){return isManager();}
function canViewAll(){return ["admin","coordinator","service_unit_manager","hod","principal"].includes(session?.role);}
function canAssign(){return isManager();}
function canOpenUsers(){return ["admin","coordinator"].includes(session?.role);}
function canModifyStaff(){return ["admin","service_unit_manager"].includes(session?.role);}
function complaintNavLabel(){
  if (isPrincipal()) return "Unsolved Problems";
  if (isStaff()) return "My Assigned Issues";
  if (isManager()) return "Service Unit Complaints";
  if (isHOD()) return "Department Complaints";
  return canViewAll() ? "All Complaints" : "My Complaints";
}
function statusLabel(s){return ({"routed":"Routed","assigned":"Assigned","in-progress":"In Progress","resolved":"Resolved","escalated":"Escalated","closed":"Closed"}[s]||s);}
function initials(n){return(n||"?").split(" ").map(w=>w[0]).join("").slice(0,2).toUpperCase();}
function valPhone(p){return /^\d{10}$/.test(p);}

function boot(){
  if (session && token) renderApp();
  else renderAuth("login");
}

/* ══ AUTH ══════════════════════════════════════════════════ */
function renderAuth(mode="login"){
  document.getElementById("app").innerHTML=`
    <div class="auth-page">
      <div class="auth-bg"></div>
      <div class="auth-card a1">
        <div class="auth-card-topbar">
          <img src="images/logo.jpg" alt="CDGI logo" class="auth-topbar-logo">
          <div class="auth-topbar-title">CDGI Campus Issues Portal</div>
        </div>
        <div class="auth-logo-section">
          <div class="auth-cdgi-logo">
            <img src="images/logo.jpg" alt="CDGI logo">
          </div>
          <div class="auth-cdgi-name">Chameli Devi Group of Institutions</div>
          <div class="auth-cdgi-sub">Indore (M.P.)</div>
        </div>
        <div class="auth-form-section">
          <div class="auth-tabs">
            <button class="auth-tab ${mode==="login"?"active":""}" onclick="renderAuth('login')">Sign In</button>
            <button class="auth-tab ${mode==="register"?"active":""}" onclick="renderAuth('register')">Register</button>
          </div>
          <div id="auth-alert"></div>
          ${mode==="login" ? loginForm() : registerForm()}
        </div>
      </div>
    </div>
    <div class="toasts" id="toasts"></div>`;
}
function loginForm(){
  return `
    <div class="form-group">
      <label class="label">Email / User ID <span class="req">*</span></label>
      <div class="input-icon"><span class="ico">👤</span>
        <input id="l-email" class="input" type="email" placeholder="you@cdgi.edu.in" autocomplete="email">
      </div>
    </div>
    <div class="form-group">
      <label class="label">Password <span class="req">*</span></label>
      <div class="pass-wrap">
        <input id="l-pass" class="input" type="password" placeholder="••••••••">
        <button class="eye-btn" onclick="toggleEye('l-pass',this)" type="button">👁️</button>
      </div>
    </div>
    <button class="btn btn-primary btn-full btn-lg" id="login-btn" onclick="doLogin()">Login »</button>
    <div id="verify-section" style="display:none;margin-top:12px;text-align:center;background:#fef3c7;padding:12px;border-radius:8px;border:1px solid #fde68a;">
      <p style="font-size:13px;color:#92400e;margin-bottom:8px;">Email not verified. Check inbox or resend:</p>
      <button class="btn btn-outline btn-sm" onclick="resendVerify()">📧 Resend Verification</button>
    </div>
    <p style="text-align:center;margin-top:14px;font-size:13px;color:var(--text-2);">
      New user? <a href="#" onclick="renderAuth('register')" style="color:var(--blue);font-weight:600;">SignUp (New User)</a>
    </p>`;
}

function registerForm(){
  return `
    <div class="form-row">
      <div class="form-group"><label class="label">Full Name <span class="req">*</span></label><input id="r-name" class="input" placeholder="Your full name"></div>
      <div class="form-group"><label class="label">Roll Number</label><input id="r-roll" class="input" placeholder="0832CS231XXX"></div>
    </div>
    <div class="form-group"><label class="label">Email <span class="req">*</span></label><input id="r-email" class="input" type="email" placeholder="you@cdgi.edu.in"></div>
    <div class="form-row">
      <div class="form-group">
        <label class="label">Password <span class="req">*</span></label>
        <div class="pass-wrap"><input id="r-pass" class="input" type="password" placeholder="Min 6 chars"><button class="eye-btn" onclick="toggleEye('r-pass',this)" type="button">👁️</button></div>
      </div>
      <div class="form-group">
        <label class="label">Phone (10 digits)</label>
        <input id="r-phone" class="input" placeholder="9876543210" maxlength="10" oninput="this.value=this.value.replace(/\D/g,'').slice(0,10)">
        <span class="field-err" id="phone-err">Must be exactly 10 digits</span>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group"><label class="label">Department</label>
        <select id="r-dept" class="select"><option value="CSE">CSE</option><option value="IT">IT</option><option value="EC">EC</option><option value="ME">ME</option><option value="CE">Civil</option><option value="MBA">MBA</option></select>
      </div>
      <div class="form-group"><label class="label">Role</label>
        <select id="r-role" class="select"><option value="student">Student</option><option value="faculty">Faculty</option></select>
        <div style="font-size:12px;color:var(--text-2);margin-top:6px;">Staff accounts are created by managers.</div>
      </div>
    </div>
    <button class="btn btn-primary btn-full btn-lg" onclick="doRegister()">Create Account →</button>
    <p style="text-align:center;margin-top:14px;font-size:13px;color:var(--text-2);">Already registered? <a href="#" onclick="renderAuth('login')" style="color:var(--blue);font-weight:600;">Sign in</a></p>`;
}

async function doLogin(){
  const email=document.getElementById("l-email").value.trim();
  const pass=document.getElementById("l-pass").value;
  const btn=document.getElementById("login-btn");
  if (!email||!pass){showAuthErr("Please fill all fields.");return;}
  btn.disabled=true; btn.innerHTML=`<span class="spin">⟳</span> Signing in…`;
  try {
    const d=await api("login","POST",{email,password:pass});
    saveSession(d); renderApp();
  } catch(e) {
    showAuthErr(e.message);
    if (e.message.includes("verify")) {
      document.getElementById("verify-section").style.display="block";
      window._verifyEmail=email;
    }
    btn.disabled=false; btn.innerHTML="Login »";
  }
}

async function resendVerify(){
  const email=window._verifyEmail||document.getElementById("l-email").value.trim();
  if (!email){toast("Enter your email first","err");return;}
  try {
    const d=await api("resend-verify","POST",{email});
    toast(d.message || "Verification email sent.","ok");
  } catch(e){toast(e.message,"err");}
}

async function doRegister(){
  const name=document.getElementById("r-name").value.trim();
  const email=document.getElementById("r-email").value.trim();
  const pass=document.getElementById("r-pass").value;
  const phone=document.getElementById("r-phone").value.trim();
  const dept=document.getElementById("r-dept").value;
  const role=document.getElementById("r-role").value;
  const roll=document.getElementById("r-roll").value.trim();
  if (!name||!email||!pass){showAuthErr("Name, email and password required.");return;}
  if (pass.length<6){showAuthErr("Password must be at least 6 characters.");return;}
  if (phone&&!valPhone(phone)){document.getElementById("phone-err").classList.add("show");showAuthErr("Phone must be exactly 10 digits.");return;}
  document.getElementById("phone-err")?.classList.remove("show");
  try {
    const d=await api("register","POST",{name,email,password:pass,phone,dept,role,roll_no:roll});
    if (d.status==="pending_verification") {
      document.getElementById("auth-alert").innerHTML=`<div class="alert alert-info"><span class="alert-ico">📧</span><div><strong>Verification email sent</strong><br><span style="font-size:13px;">A verification link was sent to <strong>${email}</strong>. Click it to activate your account.</span></div></div>`;
    } else {
      saveSession(d); renderApp(); toast(`Welcome to CIRS, ${name}! 🎉`,"ok");
    }
  } catch(e){showAuthErr(e.message);}
}

function showAuthErr(msg){const el=document.getElementById("auth-alert");if(el)el.innerHTML=`<div class="alert alert-err"><span class="alert-ico">⚠️</span>${msg}</div>`;}
function toggleEye(id,btn){const inp=document.getElementById(id);inp.type=inp.type==="password"?"text":"password";btn.textContent=inp.type==="password"?"👁️":"🙈";}

/* ══ APP SHELL ══════════════════════════════════════════════ */
function renderApp(){
  if (!session){renderAuth("login");return;}
  const staffLimited=isStaff();
  const complaintSection=isPrincipal()?"unsolved":"complaints";
  const showReport=canReport();
  const showManage=canManage();
  const showUsers=canOpenUsers();
  const showStaffMembers=canModifyStaff();
  document.getElementById("app").innerHTML=`
    <div class="sidebar-overlay" id="sidebar-overlay" onclick="closeSidebar()"></div>
    <div class="shell">
      <aside class="sidebar" id="sidebar">
        <div class="sidebar-head">
          <div class="sidebar-brand" onclick="window.location.href='/'" style="cursor: pointer;" title="Go to Dashboard">
            <div class="sidebar-cdgi-logo">
              <img src="images/logo.jpg" alt="CDGI logo">
            </div>
            <div class="sidebar-brand-text"><div class="s-name">CDGI · CIRS</div><div class="s-sub">Campus Portal </div></div>
          </div>
          <button class="sidebar-collapse-btn" onclick="toggleSidebarCollapse()" title="Collapse Sidebar">
            <svg viewBox="0 0 24 24" width="20" height="20" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>
          </button>
        </div>
        <nav class="nav">
          ${staffLimited?`
          <div><div class="nav-section-label">My Work</div>
            <button class="nav-item active" data-s="dashboard" onclick="go('dashboard')"><span class="nav-icon">📊</span> Dashboard</button>
            <button class="nav-item" data-s="complaints" onclick="go('complaints')"><span class="nav-icon">📋</span> My Assigned Issues</button>
          </div>
          <div><div class="nav-section-label">Account</div>
            <button class="nav-item" data-s="profile" onclick="go('profile')"><span class="nav-icon">👤</span> Profile</button>
            <button class="nav-item" onclick="logout()"><span class="nav-icon">🚪</span> Sign Out</button>
          </div>`:`
          <div><div class="nav-section-label">Main Menu</div>
            <button class="nav-item active" data-s="dashboard" onclick="go('dashboard')"><span class="nav-icon">📊</span> Dashboard</button>
            ${showReport?`<button class="nav-item" data-s="report" onclick="go('report')"><span class="nav-icon">📝</span> Report Issue</button>`:""}
            <button class="nav-item" data-s="${complaintSection}" onclick="go('${complaintSection}')"><span class="nav-icon">📋</span> ${complaintNavLabel()}</button>
          </div>
          ${(showManage||showUsers||showStaffMembers)?`<div><div class="nav-section-label">Management</div>
            ${showManage?`<button class="nav-item" data-s="manage" onclick="go('manage')"><span class="nav-icon">⚙️</span> Manager Panel<span class="nav-badge" id="new-count" style="display:none">0</span></button>`:""}
            ${showStaffMembers?`<button class="nav-item" data-s="staff-members" onclick="go('staff-members')"><span class="nav-icon">👷</span> Modify Staff Members</button>`:""}
            ${showUsers?`<button class="nav-item" data-s="users" onclick="go('users')"><span class="nav-icon">👥</span> Users</button>`:""}
          </div>`:""}
          <div><div class="nav-section-label">Account</div>
            <button class="nav-item" data-s="profile" onclick="go('profile')"><span class="nav-icon">👤</span> Profile</button>
            <button class="nav-item" onclick="logout()"><span class="nav-icon">🚪</span> Sign Out</button>
          </div>`}
        </nav>
        <div class="sidebar-foot">
          <div class="user-card" onclick="go('profile')">
            <div class="avatar" style="overflow:hidden; display:flex; align-items:center; justify-content:center;">
              ${session.profile_image ? `<img src="${session.profile_image}" style="width:100%;height:100%;object-fit:cover;">` : initials(session.name)}
            </div>
            <div class="user-info"><div class="u-name">${session.name}</div><div class="u-role">${session.role} · ${session.dept}</div></div>
          </div>
        </div>
      </aside>
      <main class="main">
        <header class="topbar">
          <div class="topbar-l">
            <button class="menu-btn" onclick="toggleSidebar()">☰</button>
            <div><div class="pg-title" id="pg-title">Dashboard</div><div class="pg-crumb">CDGI / <span id="pg-crumb">Campus Portal</span></div></div>
          </div>
          <div class="topbar-r">
            <div class="topbar-college-brand">
              <img src="images/logo.jpg" alt="CDGI logo" class="topbar-college-logo">
              <div class="topbar-college-text">
                <span>CDGI</span>
                <small>Campus Portal</small>
              </div>
            </div>
            <div style="position:relative;">
              <button class="icon-btn" id="notif-btn" onclick="toggleNotifDrop()">🔔<span class="dot-badge hidden" id="notif-dot"></span></button>
              <div class="notif-drop" id="notif-drop">
                <div class="notif-drop-head"><span>Notifications</span><button onclick="markAllRead()">Mark all read</button></div>
                <div id="notif-list"><div class="notif-empty">Loading…</div></div>
              </div>
            </div>
            <div class="avatar" style="cursor:pointer; overflow:hidden; display:flex; align-items:center; justify-content:center;" onclick="go('profile')">
              ${session.profile_image ? `<img src="${session.profile_image}" style="width:100%;height:100%;object-fit:cover;">` : initials(session.name)}
            </div>
          </div>
        </header>
        <div class="content" id="page-content"></div>
      </main>
    </div>
    <div class="overlay" id="overlay" onclick="closeModal()"><div class="modal" id="modal" onclick="event.stopPropagation()"></div></div>
    <div class="toasts" id="toasts"></div>
    <div id="chart-tooltip" class="chart-tooltip"></div>`;
  
  if (localStorage.getItem('cirs_sidebar_collapsed') === 'true') {
    document.querySelector('.shell').classList.add('collapsed');
  }

  go("dashboard");
  loadNotifications();
  document.addEventListener("click",e=>{const d=document.getElementById("notif-drop"),b=document.getElementById("notif-btn");if(d&&b&&!d.contains(e.target)&&!b.contains(e.target))d.classList.remove("open");});
}

function toggleSidebar(){document.getElementById("sidebar")?.classList.toggle("open");document.getElementById("sidebar-overlay")?.classList.toggle("show");}
function closeSidebar(){document.getElementById("sidebar")?.classList.remove("open");document.getElementById("sidebar-overlay")?.classList.remove("show");}

function toggleSidebarCollapse() {
  const shell = document.querySelector('.shell');
  if (shell) {
    shell.classList.toggle('collapsed');
    // Save preference
    localStorage.setItem('cirs_sidebar_collapsed', shell.classList.contains('collapsed'));
  }
}

function go(s){
  section=s;
  document.querySelectorAll(".nav-item").forEach(el=>el.classList.toggle("active",el.dataset.s===s));
  const titles={dashboard:isStaff()?"Staff Dashboard":isManager()?"Manager Dashboard":isPrincipal()?"Principal Dashboard":isHOD()?"HOD Dashboard":"Dashboard",report:"Report Issue",complaints:complaintNavLabel(),unsolved:"Unsolved Problems",manage:"Manager Panel","staff-members":"Modify Staff Members",users:"Users",profile:"Profile"};
  const pg=document.getElementById("pg-title"); if(pg) pg.textContent=titles[s]||s;
  const content=document.getElementById("page-content"); if(!content) return;
  content.innerHTML=`<div style="text-align:center;padding:60px;color:var(--text-3);">Loading…</div>`;
  closeSidebar();
  const map={dashboard:renderDashboard,report:renderReport,complaints:renderComplaints,unsolved:renderUnsolved,manage:renderManage,"staff-members":renderStaffMembers,users:renderUsers,profile:renderProfile};
  if(map[s]) map[s](content);
}
function logout(){clearSession();renderAuth("login");}

/* ══ DASHBOARD ══════════════════════════════════════════════ */
async function renderDashboard(el){
  try {
    const complaintsEndpoint=isPrincipal()?"complaints?scope=principal-unsolved":"complaints";
    const [stats,recent]=await Promise.all([api("stats"),api(complaintsEndpoint)]);
    const list=(recent.data||[]).slice(0,6);
    const badge=document.getElementById("new-count");
    if(badge&&canManage()&&stats.new>0){badge.style.display="";badge.textContent=stats.new;}
    const cats=stats.categories||{}; const maxCat=Math.max(...Object.values(cats),1);
    const hr=new Date().getHours(); const greet=hr<12?"morning":hr<17?"afternoon":"evening";
    const quickActions = `
      <div class="quick-action-grid">
        ${canReport() ? `
          <div class="q-action-tile" onclick="go('report')">
            <div class="q-action-ico">➕</div>
            <div class="q-action-label">Report Issue</div>
          </div>
        ` : ""}
        <div class="q-action-tile" onclick="go('${isPrincipal() ? "unsolved" : "complaints"}')">
          <div class="q-action-ico">📋</div>
          <div class="q-action-label">${isPrincipal() ? "Unsolved" : "My Issues"}</div>
        </div>
        ${canModifyStaff() ? `
          <div class="q-action-tile" onclick="go('staff-members')">
            <div class="q-action-ico">👥</div>
            <div class="q-action-label">Staff</div>
          </div>
        ` : ""}
        ${canOpenUsers() ? `
          <div class="q-action-tile" onclick="go('users')">
            <div class="q-action-ico">🔑</div>
            <div class="q-action-label">Users</div>
          </div>
        ` : ""}
        <div class="q-action-tile" onclick="go('profile')">
          <div class="q-action-ico">👤</div>
          <div class="q-action-label">Profile</div>
        </div>
      </div>
    `;
    const trends = (stats.trends && stats.trends.some(v => v > 0)) ? stats.trends : [2, 5, 3, 8, 4, 6, 2];
    const maxTrend = Math.max(...trends, 1);
    
    const principalStats = `
      <div class="principal-grid a2">
        <!-- Card 1: Total (Bar Chart) -->
        <div class="widget-card w-blue" onclick="showGraphDetail('total')">
          <div class="widget-head">
            <div class="widget-label">Total Complaints</div>
            <div class="widget-sub">Past 7 Days</div>
          </div>
          <div class="widget-val">${stats.total}</div>
          <div class="widget-chart">
            ${trends.map(v => `<div class="w-bar"><div class="w-bar-fill" style="height: ${Math.max((v/maxTrend*100), 10)}%"></div></div>`).join("")}
          </div>
        </div>

        <!-- Card 2: Routed (Line Wave) -->
        <div class="widget-card w-orange" onclick="showGraphDetail('routed')">
          <div class="widget-head">
            <div class="widget-label">Routed Issues</div>
            <div class="widget-sub">Trend Analysis</div>
          </div>
          <div class="widget-val">${stats.pending_assignment ?? stats.new ?? 0}</div>
          <div class="widget-wave">
            <svg class="wave-svg" viewBox="0 0 100 40">
              <path d="${getWavePath(trends)}" />
            </svg>
          </div>
        </div>

        <!-- Card 3: In Progress (Gauge) -->
        <div class="widget-card w-purple" onclick="showGraphDetail('progress')">
          <div class="widget-head">
            <div class="widget-label">In Progress</div>
            <div class="widget-sub">Live Workload</div>
          </div>
          <div style="display: flex; align-items: flex-end; justify-content: space-between;">
            <div class="widget-val">${stats.in_progress}</div>
            <div class="widget-gauge">
              <svg class="gauge-svg" viewBox="0 0 100 100">
                <circle class="gauge-bg" cx="50" cy="50" r="40" />
                <circle class="gauge-fill" cx="50" cy="50" r="40" style="stroke-dashoffset: ${157 - (157 * (stats.total ? stats.in_progress/stats.total : 0))}" />
              </svg>
            </div>
          </div>
        </div>

        <!-- Card 4: Resolved (Success Rate) -->
        <div class="widget-card w-green" onclick="showGraphDetail('resolved')">
          <div class="widget-head">
            <div class="widget-label">Resolved</div>
            <div class="widget-sub">Service Quality</div>
          </div>
          <div class="widget-val">${stats.resolved}</div>
          <div class="widget-delta up">↑ ${stats.resolution_rate}% success</div>
          <div class="widget-wave">
            <svg class="wave-svg" viewBox="0 0 100 40">
              <path d="${getAreaPath(trends)}" fill="var(--wg-s)" style="opacity: 0.2;" />
              <path d="${getAreaPath(trends).replace(' Z', '').replace('M0 40 L', 'M')}" fill="none" stroke="var(--wg-s)" stroke-width="1" />
            </svg>
          </div>
        </div>
      </div>
    `;

    el.innerHTML=`
      <div class="page-header a1"><h1>Good ${greet}, <span>${session.name.split(" ")[0]}</span></h1><p>${new Date().toLocaleDateString("en-IN",{weekday:"long",day:"numeric",month:"long",year:"numeric"})}</p></div>
      ${principalStats}
      <div class="two-col a3">
        <div class="card">
          <div class="card-head"><span class="card-title">Analytics by Category</span></div>
          <div class="card-body" style="padding: 30px 20px;">
            ${Object.keys(cats).length ? `
              <div style="height: 150px; display: flex; align-items: flex-end; gap: 12px;">
                ${(() => {
                  const catColors = [
                    { s: "#3b82f6", g: "linear-gradient(135deg, #3b82f6, #1d4ed8)" },
                    { s: "#10b981", g: "linear-gradient(135deg, #10b981, #059669)" },
                    { s: "#f59e0b", g: "linear-gradient(135deg, #f59e0b, #d97706)" },
                    { s: "#a855f7", g: "linear-gradient(135deg, #a855f7, #7c3aed)" },
                    { s: "#ef4444", g: "linear-gradient(135deg, #ef4444, #b91c1c)" },
                    { s: "#06b6d4", g: "linear-gradient(135deg, #06b6d4, #0891b2)" }
                  ];
                  return Object.entries(cats).map(([cat, cnt], i) => {
                    const color = catColors[i % catColors.length];
                    const h = (cnt/maxCat*100);
                    return `
                      <div class="cat-dot-wrap">
                        <div class="cat-dot-val">${cnt}</div>
                        <div class="cat-dot-track">
                          <div class="cat-dot-line" style="height: ${h}%"></div>
                          <div class="cat-dot" 
                            style="background: ${color.g}; box-shadow: 0 0 15px ${color.s}; bottom: ${h}%; position: absolute; margin-bottom: -7px;"
                            onmouseenter="showTooltip(event, '${cat}', '${cnt}')"
                            onmousemove="showTooltip(event, '${cat}', '${cnt}')"
                            onmouseleave="hideTooltip()"
                          ></div>
                        </div>
                        <div class="cat-dot-label" title="${cat}">${cat}</div>
                      </div>
                    `;
                  }).join("");
                })()}
              </div>
            ` : `<div class="tbl-empty">No data yet</div>`}
          </div>
        </div>
        <div class="card">
          <div class="card-head"><span class="card-title">Quick Actions</span></div>
          <div class="card-body" style="display:flex;flex-direction:column;gap:10px;">
            ${quickActions}
          </div>
        </div>
      </div>
      <div class="card a4">
        <div class="card-head"><span class="card-title">Recent Activity</span><button class="btn btn-outline btn-sm" onclick="go('${isPrincipal()?"unsolved":"complaints"}')">View All</button></div>
        <div class="tbl-wrap">
          ${list.length?`<table style="font-size: 14.5px;">
            <thead><tr><th>Ticket</th><th>Title</th><th>${canViewAll()?"Reporter":"Category"}</th><th>Status</th><th>Photos</th><th>Date</th><th></th></tr></thead>
            <tbody>
              ${list.map(c=>`<tr style="transition: background 0.2s; cursor: pointer;" 
                onmouseenter="showTableTooltip(event, '${c.ticket_id}', '${(c.title||'').replace(/'/g,"\\'")}', '${c.category||'General'}', '${c.status}', '${(c.user_name||'').replace(/'/g,"\\'")}', '${(c.description||'').replace(/'/g,"\\'")}', '${c.created_at}')" 
                onmousemove="showTableTooltip(event, '${c.ticket_id}', '${(c.title||'').replace(/'/g,"\\'")}', '${c.category||'General'}', '${c.status}', '${(c.user_name||'').replace(/'/g,"\\'")}', '${(c.description||'').replace(/'/g,"\\'")}', '${c.created_at}')" 
                onmouseleave="hideTooltip()"
                onclick="viewTicket('${c.ticket_id}')"
              >
                <td style="padding: 16px 12px;"><span class="mono" style="color:var(--blue);font-size:13px;font-weight:800;">${c.ticket_id}</span></td>
                <td style="font-weight:600;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding: 16px 12px;">${c.title}</td>
                <td style="padding: 16px 12px;">${canViewAll()?`<span style="font-size:13px;color:var(--text-2);font-weight:500;">${c.user_name}</span>`:`<span class="cpill c-${c.category}" style="font-size:12px;padding:4px 10px;">${c.category}</span>`}</td>
                <td style="padding: 16px 12px;">${statusBadge(c.status)}</td>
                <td style="white-space:nowrap;padding: 16px 12px;">${c.image_before?'<span style="color:var(--blue);font-size:12px;font-weight:700;">Before</span>':"—"} ${c.image_after?'<span style="color:var(--green);font-size:12px;font-weight:700;">After</span>':""}</td>
                <td style="font-size:13px;color:var(--text-2);padding: 16px 12px;">${c.created_at}</td>
                <td style="padding: 16px 12px;"><button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); viewTicket('${c.ticket_id}')">View →</button></td>
              </tr>`).join("")}
            </tbody>
          </table>`:`<div class="tbl-empty"><div style="font-size:40px;margin-bottom:12px;">📭</div><div class="fw-7">No complaints yet</div>${canReport()?`<button class="btn btn-primary" onclick="go('report')" style="margin-top:14px;">Report an Issue</button>`:""}</div>`}
        </div>
      </div>`;
  } catch(e){el.innerHTML=serverDownBanner();}
}

/* ══ REPORT FORM ════════════════════════════════════════════ */
function renderReport(el){
  if(!canReport()){
    el.innerHTML=`<div class="card" style="padding:36px;"><div class="fw-7" style="font-size:20px;color:var(--text-1);">Report Issue is available only for students and faculty.</div></div>`;
    return;
  }
  el.innerHTML=`
    <div class="page-header a1"><h1>Report <span>Issue</span></h1><p>Submit a campus complaint — 📧 email confirmation will be sent automatically</p></div>
    <div style="max-width:720px;">
      <div class="card a2">
        <div class="card-head"><span class="card-title">🎫 Complaint Details</span></div>
        <div class="card-body">
          <div id="report-alert"></div>
          <div class="form-group"><label class="label">Issue Title <span class="req">*</span></label><input id="r-title" class="input" placeholder="e.g. Broken light in Lab-2, No water in Hostel Block B"></div>
          <div class="form-row">
            <div class="form-group"><label class="label">Category <span class="req">*</span></label>
              <select id="r-cat" class="select"><option value="">— Loading categories…</option></select>
            </div>
          </div>
          <div class="form-group"><label class="label">Location / Block</label><input id="r-location" class="input" placeholder="e.g. Main Block, 2nd Floor, Near Lab-204"></div>
          <div class="form-group"><label class="label">Detailed Description <span class="req">*</span></label><textarea id="r-desc" class="textarea" rows="4" placeholder="Describe the issue in detail…"></textarea></div>
          <div class="form-group">
            <label class="label">📸 Before Photo — Evidence of Issue (Optional)</label>
            <div class="file-zone" id="file-zone" onclick="document.getElementById('r-file').click()">
              <div class="file-zone-ico">📷</div>
              <div class="file-zone-txt"><strong>Click to browse</strong> or drag & drop</div>
              <div class="file-zone-hint">Upload photo/video showing the issue · JPG·PNG·MP4 · max 32MB</div>
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
          <p style="font-size:14px;color:var(--text-2);margin-bottom:14px;font-weight:600;">📧 Email Notification Flow:</p>
          <div style="display:grid;gap:8px;font-size:13px;">
            <div style="display:flex;align-items:center;gap:10px;padding:10px;background:var(--surface2);border-radius:8px;border-left:3px solid var(--blue);">
              <span style="font-size:18px;">1️⃣</span><div><strong>You submit complaint</strong><br><span style="color:var(--text-3);">→ Auto email sent: "Complaint Routed"</span></div>
            </div>
            <div style="display:flex;align-items:center;gap:10px;padding:10px;background:var(--surface2);border-radius:8px;border-left:3px solid var(--yellow);">
              <span style="font-size:18px;">2️⃣</span><div><strong>Service Unit Manager assigns to staff</strong><br><span style="color:var(--text-3);">→ Auto email: "Issue Assigned to You"</span></div>
            </div>
            <div style="display:flex;align-items:center;gap:10px;padding:10px;background:var(--surface2);border-radius:8px;border-left:3px solid var(--orange);">
              <span style="font-size:18px;">3️⃣</span><div><strong>Staff marks In Progress or Resolved</strong><br><span style="color:var(--text-3);">→ Auto email: "Status Update"</span></div>
            </div>
            <div style="display:flex;align-items:center;gap:10px;padding:10px;background:var(--surface2);border-radius:8px;border-left:3px solid var(--green);">
              <span style="font-size:18px;">4️⃣</span><div><strong>Staff uploads After Photo → Resolved</strong><br><span style="color:var(--text-3);">→ Auto email: "Issue Resolved" + After photo</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>`;
  loadCategories();
  const zone=document.getElementById("file-zone");
  zone.addEventListener("dragover",e=>{e.preventDefault();zone.classList.add("over");});
  zone.addEventListener("dragleave",()=>zone.classList.remove("over"));
  zone.addEventListener("drop",e=>{e.preventDefault();zone.classList.remove("over");if(e.dataTransfer.files[0])previewFile(e.dataTransfer.files[0]);});
}

async function loadCategories(){
  try {
    const res = await api("categories");
    const options = res.data.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
    document.getElementById("r-cat").innerHTML = `<option value="">— Select Category</option>${options}`;
  } catch(e) {
    document.getElementById("r-cat").innerHTML = `<option value="">Failed to load categories</option>`;
  }
}

function handleFile(e){if(e.target.files[0])previewFile(e.target.files[0]);}
function previewFile(file){
  const el=document.getElementById("file-preview"); if(!el) return;
  const isImg=file.type.startsWith("image/");
  let preview=isImg?`<img src="${URL.createObjectURL(file)}" style="max-width:100%;max-height:200px;border-radius:8px;border:2px solid var(--border);margin-top:8px;display:block;">`:"";
  el.innerHTML=`<div class="file-preview"><span>📎</span><span class="file-preview-name">${file.name}</span><span class="file-preview-size">${(file.size/1024).toFixed(1)} KB</span><button onclick="clearFile()" style="background:none;border:none;color:var(--text-3);font-size:20px;cursor:pointer;margin-left:auto;">×</button></div>${preview}`;
  window._selectedFile=file;
}
function clearFile(){document.getElementById("file-preview").innerHTML="";document.getElementById("r-file").value="";window._selectedFile=null;}

async function submitComplaint(){
  const title=document.getElementById("r-title").value.trim();
  const category=document.getElementById("r-cat").value;
  const desc=document.getElementById("r-desc").value.trim();
  const location=document.getElementById("r-location")?.value.trim()||"";
  const alertEl=document.getElementById("report-alert");
  const btn=document.getElementById("submit-btn");
  if(!title||!category||!desc){alertEl.innerHTML=`<div class="alert alert-err"><span class="alert-ico">⚠️</span>Title, category and description required.</div>`;return;}
  btn.disabled=true; btn.innerHTML=`<span class="spin">⟳</span> Submitting…`;
  try {
    const fd=new FormData();
    fd.append("title",title); fd.append("category_id",category);
    fd.append("description",desc); fd.append("location",location);
    if(window._selectedFile)fd.append("image",window._selectedFile);
    const res=await api("complaints","POST",fd,true);
    toast(`✅ ${res.message}`,"ok");
    window._selectedFile=null; go("complaints");
  } catch(e){
    alertEl.innerHTML=`<div class="alert alert-err"><span class="alert-ico">⚠️</span>${e.message}</div>`;
    btn.disabled=false; btn.innerHTML="🚀 Submit Complaint";
  }
}

/* ══ COMPLAINTS LIST ════════════════════════════════════════ */
async function renderComplaints(el){
  try {
    const data=await api("complaints"); const list=data.data||[];
    const statusDefs=[
      ["all",`All (${list.length})`],
      ["routed",`Routed (${list.filter(c=>c.status==="routed").length})`],
      ["assigned",`Assigned (${list.filter(c=>c.status==="assigned").length})`],
      ["in-progress",`In Progress (${list.filter(c=>c.status==="in-progress").length})`],
      ["resolved",`Resolved (${list.filter(c=>c.status==="resolved").length})`],
      ["escalated",`Escalated (${list.filter(c=>c.status==="escalated").length})`]
    ].filter(([key])=>key==="all"||list.some(c=>c.status===key));
    el.innerHTML=`
      <div class="page-header a1"><h1>${complaintNavLabel()}</h1><p>${list.length} total · Live from database</p></div>
      <div class="flex-bc mb-20 a2" style="flex-wrap:wrap;gap:10px;">
        <div style="display:flex;gap:8px;flex-wrap:wrap;" id="filter-chips">
          ${statusDefs.map(([s,label],index)=>`<button class="btn ${index===0?"btn-primary":"btn-outline"} btn-sm" onclick="filterChip(this,'${s}')">${label}</button>`).join("")}
        </div>
        <div class="input-icon" style="width:220px;"><span class="ico">🔍</span><input class="input" placeholder="Search…" id="search-inp" oninput="searchTickets(this.value)"></div>
      </div>
      <div id="ticket-grid" class="tickets-grid a3">
        ${list.length?list.map(c=>ticketCard(c)).join(""):`<div class="card" style="padding:60px;text-align:center;"><div style="font-size:48px;margin-bottom:14px;">📭</div><div class="fw-7" style="font-size:19px;">No Complaints Yet</div>${canReport()?`<button class="btn btn-primary" onclick="go('report')" style="margin-top:16px;">Report an Issue</button>`:""}</div>`}
      </div>`;
  } catch(e){el.innerHTML=serverDownBanner();}
}

function ticketCard(c){
  return `<div class="tkt" data-status="${c.status}" data-title="${(c.title||"").toLowerCase()}" onclick="viewTicket('${c.ticket_id}')">
    <div class="flex-bc"><span class="tkt-id">${c.ticket_id}</span>${statusBadge(c.status)}</div>
    <div class="tkt-ttl">${c.title}</div>
    <div class="tkt-meta">
      <span class="cpill c-${c.category}">${c.category}</span>
      <span>📅 ${c.created_at.split(" ")[0]}</span>
      ${canViewAll()&&c.user_name?`<span>👤 ${c.user_name}</span>`:""}
      ${c.service_unit_name?`<span>🏢 ${c.service_unit_name}</span>`:""}
      ${isHOD()&&c.reporter_academic_department?`<span>🎓 ${c.reporter_academic_department}</span>`:""}
      ${c.image_before?`<span style="color:var(--blue);font-size:11px;font-weight:700;">📸 Before</span>`:""}
      ${c.image_after?`<span style="color:var(--green);font-size:11px;font-weight:700;">📸 After</span>`:""}
    </div>
    <div class="tkt-foot"><span class="tkt-desc">${c.description.slice(0,80)}${c.description.length>80?"...":""}</span><button class="btn btn-outline btn-sm" onclick="event.stopPropagation();viewTicket('${c.ticket_id}')">Details →</button></div>
  </div>`;
}

async function renderUnsolved(el){
  try {
    const data=await api("complaints?scope=principal-unsolved");
    const list=data.data||[];
    el.innerHTML = `
      <div class="page-header a1">
        <h1>Unsolved <span>Problems</span></h1>
        <p>Issues across all departments that have exceeded the 48-hour resolution window</p>
      </div>
      
      ${list.length ? `
        <div class="unsolved-grid a2">
          ${list.map(c => `
            <div class="unsolved-card">
              <div class="unsolved-card-header">
                <div class="unsolved-id">${c.ticket_id}</div>
                <div class="unsolved-time">
                  <span style="font-size:14px;">🚨</span> ESCALATED
                </div>
              </div>
              
              <div class="unsolved-title">${c.title}</div>
              
              <div class="unsolved-meta">
                <div class="unsolved-meta-item">
                  <div class="unsolved-meta-ico">🏢</div>
                  <div><strong>${c.service_unit_name || "Unassigned Unit"}</strong></div>
                </div>
                <div class="unsolved-meta-item">
                  <div class="unsolved-meta-ico">👨‍💼</div>
                  <div>Manager: <strong>${c.assigned_manager_name || "Pending"}</strong></div>
                </div>
                <div class="unsolved-meta-item">
                  <div class="unsolved-meta-ico">👤</div>
                  <div>Reporter: <strong>${c.user_name}</strong></div>
                </div>
              </div>
              
              <div class="unsolved-footer">
                <button class="btn btn-primary btn-sm btn-full" onclick="viewTicket('${c.ticket_id}')">Take Action</button>
                <button class="btn btn-outline btn-sm" onclick="viewTicket('${c.ticket_id}')">Details</button>
              </div>
            </div>
          `).join("")}
        </div>
      ` : `
        <div class="card a2" style="padding:60px; text-align:center;">
          <div style="font-size:50px; margin-bottom:20px;">✅</div>
          <div class="fw-7" style="font-size:22px; color:var(--text-1);">All systems normal!</div>
          <p class="text-3" style="margin-top:10px;">There are no unsolved problems requiring your immediate attention.</p>
        </div>
      `}
    `;
  } catch(e){el.innerHTML=serverDownBanner();}
}

function filterChip(btn,status){document.querySelectorAll("#filter-chips .btn").forEach(b=>b.className="btn btn-outline btn-sm");btn.className="btn btn-primary btn-sm";document.querySelectorAll("#ticket-grid .tkt").forEach(el=>{el.style.display=(status==="all"||el.dataset.status===status)?"":"none";});}
function searchTickets(q){document.querySelectorAll("#ticket-grid .tkt").forEach(el=>{el.style.display=el.dataset.title?.includes(q.toLowerCase())?"":"none";});}

/* ══ TICKET DETAIL MODAL ════════════════════════════════════ */
async function viewTicket(ticketId){
  try {
    const c=await api(`complaints/${ticketId}`);
    const steps=["routed","assigned","in-progress","resolved"]; const si=Math.max(steps.indexOf(c.status),0);

    const photoSection=()=>{
      const issueImages = c.issue_images || [];
      const resolutionImages = c.resolution_images || [];
      let html = "";
      if(issueImages.length){
        html += `<div style="margin-bottom:16px;"><div class="label" style="margin-bottom:8px;">📸 Student Uploaded Photos</div><div class="image-grid">${issueImages.map(img=>`<img src="${img.image_url}" class="evidence-img evidence-thumb" onclick="window.open('${img.image_url}','_blank')">`).join('')}</div></div>`;
      }
      if(resolutionImages.length){
        html += `<div style="margin-bottom:16px;"><div class="label" style="margin-bottom:8px;color:var(--green);">✅ Staff Resolution Photos</div><div class="image-grid">${resolutionImages.map(img=>`<img src="${img.image_url}" class="evidence-img evidence-thumb" style="border-color:#bbf7d0;" onclick="window.open('${img.image_url}','_blank')">`).join('')}</div></div>`;
      }
      if(isStaff() && c.assigned_staff_id===session?.id && c.status!=="resolved"){
        html += `<div style="margin-bottom:16px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:var(--r);padding:14px;"><div class="label" style="margin-bottom:8px;color:var(--green);">Upload Fixed-Work Photos</div><p style="font-size:13px;color:var(--text-2);margin-bottom:10px;">Upload one or more proof images. This will mark the issue as resolved.</p><div class="file-zone" id="after-zone" onclick="document.getElementById('after-file').click()" style="padding:16px;"><div class="file-zone-ico" style="font-size:22px;">📷</div><div class="file-zone-txt" style="font-size:12px;"><strong>Click to upload</strong> fixed-work photos</div></div><input type="file" id="after-file" style="display:none" accept="image/*" multiple onchange="handleAfterFile(event,'${c.ticket_id}')"><div id="after-preview"></div><button class="btn btn-success btn-sm" id="upload-after-btn" style="display:none;margin-top:8px;width:100%;" onclick="uploadAfterPhoto('${c.ticket_id}')">Upload & Mark Resolved</button></div>`;
      }
      return html;
    };

    openModal(`
      <div class="modal-head">
        <div><div class="mono" style="font-size:11px;color:var(--blue);margin-bottom:4px;font-weight:700;">${c.ticket_id}</div><div class="modal-title">${c.title}</div></div>
        <button class="modal-close" onclick="closeModal()">×</button>
      </div>
      <div class="modal-body">
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:18px;">${statusBadge(c.status)}<span class="cpill c-${c.category}">${c.category}</span></div>
        <div class="tracker" style="margin-bottom:20px;">
          ${["Routed","Assigned","In Progress","Resolved"].map((l,i)=>`<div class="t-step ${i<si+1?"done":i===si+1?"active":""}"><div class="t-dot">${i<si+1?"✓":i+1}</div><div class="t-label">${l}</div></div>`).join("")}
        </div>
        ${canViewAll()?`<div class="reporter-card"><div class="reporter-card-title">Reporter Information</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px;"><div><span class="text-3">Name: </span><strong>${c.user_name||"—"}</strong></div><div><span class="text-3">Email: </span><strong>${c.user_email||"—"}</strong></div><div><span class="text-3">Academic Department: </span><strong>${c.reporter_academic_department||c.user_dept||"—"}</strong></div><div><span class="text-3">Roll No: </span><strong>${c.user_roll||"—"}</strong></div><div><span class="text-3">Phone: </span><strong>${c.user_phone||"—"}</strong></div><div><span class="text-3">Submitted: </span><strong>${c.created_at}</strong></div></div></div>`:""}
        ${c.can_view_student_photo&&c.image_before?`<div class="reporter-card"><div class="reporter-card-title">📷 Student Complaint Photo</div><div style="margin-top:10px;"><img src="${c.image_before}" alt="Complaint photo" style="width:100%;max-height:420px;object-fit:cover;border-radius:14px;border:1px solid var(--line);box-shadow:var(--shadow-sm);"></div></div>`:""}
        <div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--r-sm);padding:14px;margin-bottom:14px;">
          <div class="label" style="margin-bottom:6px;">Description</div>
          <p style="font-size:14px;line-height:1.75;">${c.description}</p>
        </div>
        ${c.location?`<div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--r-sm);padding:11px;margin-bottom:14px;font-size:14px;"><span class="text-3">📍 Location: </span><strong>${c.location}</strong></div>`:""}
        ${photoSection()}
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;">
          ${[["Service Unit",c.service_unit_name||c.dept||"—"],["Assigned Manager",c.assigned_manager_name||"—"],["Assigned Staff",c.assigned_staff_name||"Pending"],["Resolved By",c.resolved_by||"—"],["Academic Department",c.reporter_academic_department||c.user_dept||"—"],["Last Updated",c.updated_at||c.created_at]].map(([k,v])=>`<div style="background:var(--surface2);border:1px solid var(--border);border-radius:var(--r-sm);padding:11px;"><div class="label" style="font-size:10px;margin-bottom:3px;">${k}</div><div class="fw-7" style="font-size:13.5px;">${v}</div></div>`).join("")}
        </div>
        ${canAssign()&&c.status!=="resolved"?`
        <div class="divider"></div>
        <div class="label" style="margin-bottom:10px;">Assign to Staff</div>
        <div style="display:grid;grid-template-columns:1fr auto;gap:8px;margin-bottom:10px;">
          <select id="assign-staff-select" class="select"><option value="">Select staff member</option></select>
          <button class="btn btn-primary" onclick="assignTicket('${c.ticket_id}')">Assign</button>
        </div>`:""}
        ${isStaff()&&c.assigned_staff_id===session?.id&&c.status!=="resolved"?`
        <div class="divider"></div>
        <div class="label" style="margin-bottom:10px;">Work Progress</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          ${c.status!=="in-progress"?`<button class="btn btn-outline btn-sm" onclick="updateTicketStatus('${c.ticket_id}','in-progress')">Mark In Progress</button>`:""}
        </div>`:""}
        ${isAdmin()?`<div class="divider"></div><div style="display:flex;justify-content:flex-end;"><button class="btn btn-danger btn-sm" onclick="deleteTicket('${c.ticket_id}')">Delete</button></div>`:""}
        ${c.status==="resolved"&&c.user_id===session?.id&&!c.feedback?`
        <div class="divider"></div><div class="label">⭐ Rate Resolution Quality</div>
        <div style="display:flex;gap:7px;margin-top:10px;flex-wrap:wrap;">
          ${[1,2,3,4,5].map(i=>`<button class="btn btn-outline btn-sm" onclick="submitFeedback('${c.ticket_id}',${i})" style="font-size:20px;padding:8px 14px;">${"⭐".repeat(i)}</button>`).join("")}
        </div>`:""}
        ${c.feedback?`<div class="alert alert-ok" style="margin-top:12px;"><span class="alert-ico">⭐</span>Feedback: ${c.feedback}/5 — Thank you!</div>`:""}
      </div>`);
    if (canAssign()) loadStaffOptions(c.assigned_staff_id);
  } catch(e){toast("Failed: "+e.message,"err");}
}

function handleAfterFile(e, ticketId){
  const files=[...(e.target.files||[])]; if(!files.length) return;
  const preview=document.getElementById("after-preview");
  if(preview){
    preview.innerHTML=files.map(file=>`<div class="file-preview" style="margin-top:8px;"><span>📷</span><span class="file-preview-name">${file.name}</span><span class="file-preview-size">${(file.size/1024).toFixed(1)} KB</span></div>`).join("");
  }
  const btn=document.getElementById("upload-after-btn");
  if(btn) btn.style.display="";
  window._afterFiles=files;
}

async function uploadAfterPhoto(ticketId){
  if(!window._afterFiles||!window._afterFiles.length){toast("Please select photo first","err");return;}
  const btn=document.getElementById("upload-after-btn");
  btn.disabled=true; btn.innerHTML=`<span class="spin">⟳</span> Uploading…`;
  try {
    const fd=new FormData(); window._afterFiles.forEach(file=>fd.append("images",file));
    const res=await fetch(`${API}/complaints/${ticketId}/after-photo`,{method:"POST",headers:{Authorization:`Bearer ${token}`},body:fd});
    const data=await res.json();
    if(!res.ok) throw new Error(data.error);
    toast("✅ "+data.message,"ok");
    window._afterFiles=null; closeModal(); setTimeout(() => window.location.reload(), 1000);
  } catch(e){toast(e.message,"err");btn.disabled=false;btn.innerHTML="Upload & Mark Resolved";}
}

async function assignTicket(tid){
  const staffId=document.getElementById("assign-staff-select")?.value;
  if(!staffId){toast("Select staff member first","err");return;}
  try{const d=await api(`complaints/${tid}/assign`,"POST",{assigned_staff_id:Number(staffId)});toast(d.message||"Assigned successfully.","ok");closeModal();setTimeout(() => window.location.reload(), 1000);}
  catch(e){toast(e.message,"err");}
}

async function loadStaffOptions(selectedId=null){
  const select=document.getElementById("assign-staff-select");
  if(!select) return;
  try{
    const res=await api("staff/options");
    if (!res.data || res.data.length === 0) {
      select.innerHTML=`<option value="">No staff found for this unit</option>`;
      return;
    }
    const options=(res.data||[]).map(s=>`<option value="${s.id}" ${Number(selectedId)===Number(s.id)?"selected":""}>${s.name} · ${s.dept||s.email||""}</option>`).join("");
    select.innerHTML=`<option value="">Select staff member</option>${options}`;
  }catch(e){ 
    console.error("Failed to load staff:", e.message);
    select.innerHTML=`<option value="">Failed to load staff</option>`; 
  }
}
async function updateTicketStatus(tid,status){
  try{await api(`complaints/${tid}`,"PUT",{status});toast(`Status → ${status}`,"ok");closeModal();setTimeout(() => window.location.reload(), 1000);}
  catch(e){toast(e.message,"err");}
}
async function deleteTicket(tid){
  if(!confirm(`Delete ${tid}? Cannot undo.`)) return;
  try{await api(`complaints/${tid}`,"DELETE");toast(`${tid} deleted`,"ok");closeModal();setTimeout(() => window.location.reload(), 1000);}
  catch(e){toast(e.message,"err");}
}
async function submitFeedback(tid,rating){
  try{await api(`complaints/${tid}`,"PUT",{feedback:rating});toast("Feedback submitted! ⭐","ok");closeModal();setTimeout(() => window.location.reload(), 1000);}
  catch(e){toast(e.message,"err");}
}

/* ══ MANAGE PANEL ══════════════════════════════════════════ */
async function renderManage(el){
  if(!canManage()){
    el.innerHTML=`<div class="card" style="padding:36px;"><div class="fw-7" style="font-size:20px;color:var(--text-1);">Manager Panel is available only for service unit managers.</div></div>`;
    return;
  }
  try {
    const [data,stats]=await Promise.all([api("complaints"),api("stats")]);
    const list=data.data||[];
    el.innerHTML=`
      <div class="page-header a1"><h1>Manager <span>Panel</span></h1><p>Review routed complaints for your service unit and assign them to staff</p></div>
      <div class="stats a2" style="grid-template-columns:repeat(4,1fr);">
        ${[["routed","🔀","Routed","s-teal"],["assigned","📌","Assigned","s-blue"],["in-progress","⏳","In Progress","s-yel"],["resolved","✅","Resolved","s-green"]].map(([s,ico,lbl,cls])=>`<div class="stat ${cls}"><div class="stat-top"><div class="stat-ico">${ico}</div></div><div class="stat-val">${list.filter(c=>c.status===s).length}</div><div class="stat-label">${lbl}</div></div>`).join("")}
      </div>
      <div class="card a3">
        <div class="card-head"><span class="card-title">Service Unit Issues (${list.length})</span>
          <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
            <select class="select" style="padding:7px 10px;font-size:13px;width:auto;" onchange="filterTable(this.value)"><option value="all">All Status</option><option value="routed">Routed</option><option value="assigned">Assigned</option><option value="in-progress">In Progress</option><option value="resolved">Resolved</option></select>
            <div class="input-icon" style="width:180px;"><span class="ico">🔍</span><input class="input" style="padding:7px 12px 7px 36px;font-size:13px;" placeholder="Search…" oninput="filterTableSearch(this.value)"></div>
          </div>
        </div>
        <div class="tbl-wrap">
          <table id="admin-tbl">
            <thead><tr><th>Ticket</th><th>Title</th><th>Reporter</th><th>Category</th><th>Status</th><th>Complaint Photo</th><th>Resolution Photo</th><th>Date</th><th>Actions</th></tr></thead>
            <tbody>
              ${list.length?list.map(c=>`
                <tr data-status="${c.status}" data-title="${(c.title||"").toLowerCase()}">
                  <td><span class="mono" style="color:var(--blue);font-size:12px;font-weight:700;">${c.ticket_id}</span></td>
                  <td style="font-weight:600;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${c.title}">${c.title}</td>
                  <td class="text-sm text-2">${c.user_name}</td>
                  <td><span class="cpill c-${c.category}">${c.category}</span></td>
                  <td>${statusBadge(c.status)}</td>
                  <td>${c.image_before?`<a href="${c.image_before}" target="_blank" class="btn btn-outline btn-sm" style="font-size:11px;padding:4px 8px;">📸 View</a>`:`<span class="text-3 text-xs">—</span>`}</td>
                  <td>${c.image_after?`<a href="${c.image_after}" target="_blank" class="btn btn-success btn-sm" style="font-size:11px;padding:4px 8px;">✅ View</a>`:`<span class="text-3 text-xs">—</span>`}</td>
                  <td class="text-sm text-2">${c.created_at}</td>
                  <td><div style="display:flex;gap:4px;">
                    <button class="btn btn-ghost btn-sm" onclick="viewTicket('${c.ticket_id}')">View</button>
                    ${c.status!=="resolved"?`<button class="btn btn-primary btn-sm" onclick="viewTicket('${c.ticket_id}')">Assign</button>`:""}
                  </div></td>
                </tr>`).join(""):`<tr><td colspan="9" class="tbl-empty">No complaints yet.</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>`;
  } catch(e){el.innerHTML=serverDownBanner();}
}

function filterTable(val){document.querySelectorAll("#admin-tbl tbody tr[data-status]").forEach(r=>{r.style.display=val==="all"||r.dataset.status===val?"":"none";});}
function filterTableSearch(q){document.querySelectorAll("#admin-tbl tbody tr[data-title]").forEach(r=>{r.style.display=r.dataset.title?.includes(q.toLowerCase())?"":"none";});}

/* == STAFF MEMBERS ========================================= */
async function renderStaffMembers(el){
  if(!canModifyStaff()){
    el.innerHTML=`<div class="card" style="padding:36px;"><div class="fw-7" style="font-size:20px;color:var(--text-1);">Staff management is available only for managers and admin.</div></div>`;
    return;
  }
  try {
    const [staffRes, unitsRes]=await Promise.all([api("staff-members"),api("service-units")]);
    const staff=staffRes.data||[];
    const units=unitsRes.data||[];
    const unitOptions=units.map(u=>`<option value="${u.id}">${u.name}</option>`).join("");
    el.innerHTML=`
      <div class="page-header a1"><h1>Modify <span>Staff Members</span></h1><p>${isAdmin()?"Create and manage staff accounts for every service unit":"Create and manage staff accounts under your service unit"}</p></div>
      <div class="two-col a2">
        <div class="card">
          <div class="card-head"><span class="card-title">Add Staff Member</span></div>
          <div class="card-body">
            <div id="staff-alert"></div>
            <div class="form-group"><label class="label">Full Name <span class="req">*</span></label><input id="staff-name" class="input" placeholder="Staff full name"></div>
            <div class="form-group"><label class="label">Email <span class="req">*</span></label><input id="staff-email" class="input" type="email" placeholder="staff@cdgi.edu.in"></div>
            <div class="form-row">
              <div class="form-group"><label class="label">Phone</label><input id="staff-phone" class="input" maxlength="10" placeholder="10-digit number" oninput="this.value=this.value.replace(/\\D/g,'').slice(0,10)"></div>
              <div class="form-group"><label class="label">Department / Skill</label><input id="staff-dept" class="input" placeholder="Electrical, Plumbing, IT"></div>
            </div>
            ${isAdmin()?`<div class="form-group"><label class="label">Service Unit <span class="req">*</span></label><select id="staff-unit" class="select"><option value="">Select service unit</option>${unitOptions}</select></div>`:`<input id="staff-unit" type="hidden" value="${session.service_unit_id||""}">`}
            <div class="form-group"><label class="label">Temporary Password <span class="req">*</span></label><input id="staff-pass" class="input" type="password" placeholder="Minimum 6 characters"></div>
            <button class="btn btn-primary btn-full" onclick="createStaffMember()">Add Staff Member</button>
          </div>
        </div>
        <div class="card">
          <div class="card-head"><span class="card-title">Staff Summary</span></div>
          <div class="card-body">
            <div class="stats" style="grid-template-columns:repeat(3,1fr);gap:10px;">
              <div class="stat s-blue"><div class="stat-val">${staff.length}</div><div class="stat-label">Total Staff</div></div>
              <div class="stat s-yel"><div class="stat-val">${staff.reduce((sum,s)=>sum+(s.active_count||0),0)}</div><div class="stat-label">Active Issues</div></div>
              <div class="stat s-green"><div class="stat-val">${units.length}</div><div class="stat-label">Service Units</div></div>
            </div>
          </div>
        </div>
      </div>
      <div class="card a3" style="margin-top:16px;">
        <div class="card-head"><span class="card-title">Staff Details (${staff.length})</span></div>
        <div class="tbl-wrap"><table>
          <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Department</th><th>Service Unit</th><th>Assigned</th><th>Active</th><th>Joined</th><th>Actions</th></tr></thead>
          <tbody>${staff.length?staff.map(s=>staffRow(s, unitOptions)).join(""):`<tr><td colspan="9" class="tbl-empty">No staff members added yet.</td></tr>`}</tbody>
        </table></div>
      </div>`;
  } catch(e){el.innerHTML=serverDownBanner();}
}

function staffRow(s, unitOptions){
  return `<tr>
    <td><div class="flex-c gap-8"><div class="avatar" style="width:30px;height:30px;font-size:11px;flex-shrink:0;">${initials(s.name)}</div><span class="fw-7">${s.name}</span></div></td>
    <td class="text-sm text-2">${s.email}</td>
    <td class="text-sm">${s.phone||"—"}</td>
    <td class="text-sm">${s.dept||"—"}</td>
    <td class="text-sm">${s.service_unit_name||"—"}</td>
    <td><span class="badge b-admin">${s.assigned_count||0}</span></td>
    <td><span class="badge ${s.active_count?"b-progress":"b-resolved"}">${s.active_count||0}</span></td>
    <td class="text-sm text-2">${s.created_at||"—"}</td>
    <td><div style="display:flex;gap:6px;flex-wrap:wrap;">
      <button class="btn btn-outline btn-sm" onclick="openEditStaff(${s.id}, '${String(s.name).replace(/'/g,"\\'")}', '${String(s.phone||"").replace(/'/g,"\\'")}', '${String(s.dept||"").replace(/'/g,"\\'")}', ${s.service_unit_id||0})">Edit</button>
      <button class="btn btn-danger btn-sm" onclick="deleteStaffMember(${s.id}, '${String(s.name).replace(/'/g,"\\'")}')">Delete</button>
    </div></td>
  </tr>`;
}

async function createStaffMember(){
  const body={
    name:document.getElementById("staff-name")?.value.trim(),
    email:document.getElementById("staff-email")?.value.trim(),
    phone:document.getElementById("staff-phone")?.value.trim(),
    dept:document.getElementById("staff-dept")?.value.trim(),
    service_unit_id:Number(document.getElementById("staff-unit")?.value||0),
    password:document.getElementById("staff-pass")?.value
  };
  const alertEl=document.getElementById("staff-alert");
  if(!body.name||!body.email||!body.password){alertEl.innerHTML=`<div class="alert alert-err"><span class="alert-ico">⚠️</span>Name, email and password required.</div>`;return;}
  if(isAdmin()&&!body.service_unit_id){alertEl.innerHTML=`<div class="alert alert-err"><span class="alert-ico">⚠️</span>Select service unit.</div>`;return;}
  try{
    const res=await api("staff-members","POST",body);
    toast(res.message||"Staff member added","ok");
    go("staff-members");
  }catch(e){alertEl.innerHTML=`<div class="alert alert-err"><span class="alert-ico">⚠️</span>${e.message}</div>`;}
}

function openEditStaff(id, name, phone, dept, serviceUnitId){
  openModal(`
    <div class="modal-head"><div class="modal-title">Edit Staff Member</div><button class="modal-close" onclick="closeModal()">×</button></div>
    <div class="modal-body">
      <div class="form-group"><label class="label">Full Name</label><input id="edit-staff-name" class="input" value="${name}"></div>
      <div class="form-row">
        <div class="form-group"><label class="label">Phone</label><input id="edit-staff-phone" class="input" value="${phone}" maxlength="10" oninput="this.value=this.value.replace(/\\D/g,'').slice(0,10)"></div>
        <div class="form-group"><label class="label">Department / Skill</label><input id="edit-staff-dept" class="input" value="${dept}"></div>
      </div>
      ${isAdmin()?`<div class="form-group"><label class="label">Service Unit ID</label><input id="edit-staff-unit" class="input" type="number" value="${serviceUnitId||""}"></div>`:""}
      <div class="form-group"><label class="label">New Password</label><input id="edit-staff-pass" class="input" type="password" placeholder="Leave blank to keep old password"></div>
      <button class="btn btn-primary btn-full" onclick="saveStaffMember(${id})">Save Changes</button>
    </div>`);
}

async function saveStaffMember(id){
  const body={
    name:document.getElementById("edit-staff-name")?.value.trim(),
    phone:document.getElementById("edit-staff-phone")?.value.trim(),
    dept:document.getElementById("edit-staff-dept")?.value.trim(),
    password:document.getElementById("edit-staff-pass")?.value
  };
  const unit=document.getElementById("edit-staff-unit")?.value;
  if(unit) body.service_unit_id=Number(unit);
  try{
    const res=await api(`staff-members/${id}`,"PUT",body);
    toast(res.message||"Staff member updated","ok");
    closeModal(); go("staff-members");
  }catch(e){toast(e.message,"err");}
}

async function deleteStaffMember(id,name){
  if(!confirm(`Delete staff member "${name}"?\n\nActive assigned issues will return to Routed.`)) return;
  try{
    const res=await api(`staff-members/${id}`,"DELETE");
    toast(res.message||"Staff member deleted","ok");
    go("staff-members");
  }catch(e){toast(e.message,"err");}
}

/* ══ USERS ══════════════════════════════════════════════════ */
async function renderUsers(el){
  try {
    const data=await api("users"); const list=data.data||[];
    el.innerHTML=`
      <div class="page-header a1"><h1>Registered <span>Users</span></h1><p>${list.length} users ${isAdmin()?"· Admin: you can delete users":""}</p></div>
      <div class="card a2">
        <div class="card-head"><span class="card-title">👥 All Users</span></div>
        <div class="tbl-wrap"><table>
          <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Dept</th><th>Verified</th><th>Joined</th><th>Actions</th></tr></thead>
          <tbody>${list.map(u=>`<tr>
            <td><div class="flex-c gap-8"><div class="avatar" style="width:30px;height:30px;font-size:11px;flex-shrink:0;">${initials(u.name)}</div><span class="fw-7">${u.name}</span></div></td>
            <td class="text-sm text-2">${u.email}</td>
            <td><span class="badge b-${u.role}">${u.role}</span></td>
            <td class="text-sm">${u.dept||"—"}</td>
            <td>${u.is_verified?'<span style="color:var(--green);font-size:13px;font-weight:700;">✅ Yes</span>':'<span style="color:var(--yellow);font-size:12px;">⚠️ Pending</span>'}</td>
            <td class="text-sm text-2">${u.created_at}</td>
            <td><div style="display:flex;gap:6px;align-items:center;">
              ${isAdmin()?`<select class="select" style="padding:5px 8px;font-size:12px;width:auto;" onchange="changeRole(${u.id},this.value)"><option ${u.role==="student"?"selected":""} value="student">student</option><option ${u.role==="faculty"?"selected":""} value="faculty">faculty</option><option ${u.role==="staff"?"selected":""} value="staff">staff</option><option ${u.role==="coordinator"?"selected":""} value="coordinator">coordinator</option><option ${u.role==="admin"?"selected":""} value="admin">admin</option></select><button class="btn btn-danger btn-sm" onclick="deleteUser(${u.id},'${u.name}')" title="Delete" style="padding:5px 10px;">🗑</button>`:`<span class="text-xs text-2">${u.role}</span>`}
            </div></td>
          </tr>`).join("")}</tbody>
        </table></div>
      </div>`;
  } catch(e){el.innerHTML=serverDownBanner();}
}

async function changeRole(uid,role){try{await api(`users/${uid}/role`,"PUT",{role});toast(`Role → ${role}`,"ok");}catch(e){toast(e.message,"err");}}
async function deleteUser(uid,name){
  if(!isAdmin()){toast("Only admin can delete users","err");return;}
  if(!confirm(`DELETE user "${name}"?\n\nPermanent and cannot be undone.`)) return;
  try{await api(`users/${uid}`,"DELETE");toast(`User ${name} deleted`,"ok");go("users");}
  catch(e){toast(e.message,"err");}
}

/* ══ PROFILE ════════════════════════════════════════════════ */
async function renderProfile(el){
  try {
    const stats=await api("stats");
    el.innerHTML=`
      <div class="page-header a1" style="display:flex; justify-content:space-between; align-items:center;">
        <div><h1>My <span>Profile</span></h1></div>
        <button class="btn btn-outline" id="edit-profile-btn" onclick="toggleEditProfile()" style="display:none; gap:6px; font-weight:600;"><span style="font-size:16px;">✏️</span> Edit Profile</button>
      </div>
      <div class="profile-layout" id="profile-layout">
        <div class="profile-left">
          <div class="profile-hero a2" style="background: #efeef5; border-radius: 24px; padding: 30px; position: relative; text-align: center; border: none; box-shadow: 0 10px 30px rgba(0,0,0,0.05);">
            <!-- Settings Icon (Toggle Edit) -->
            <button id="edit-profile-floating-btn" onclick="toggleEditProfile()" style="position: absolute; top: 20px; right: 20px; background: none; border: none; font-size: 20px; color: #7c3aed; cursor: pointer; padding: 4px; transition: transform 0.2s;">⚙️</button>
            
            <!-- Avatar -->
            <div style="width: 110px; height: 110px; border-radius: 50%; overflow: hidden; margin: 0 auto 16px auto; box-shadow: 0 8px 20px rgba(0,0,0,0.15); border: 3px solid #fff; position: relative; cursor: pointer;" onclick="document.getElementById('profile-img-upload').click()">
              ${session.profile_image 
                 ? `<img src="${session.profile_image}" alt="Avatar" style="width: 100%; height: 100%; object-fit: cover;">`
                 : `<div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: var(--blue-gl); color: var(--blue); font-size: 40px; font-weight: 700;">${initials(session.name)}</div>`
              }
              <div style="position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.5); color: white; font-size: 10px; padding: 4px 0; text-align: center; text-transform: uppercase; font-weight: 700; opacity: 0; transition: opacity 0.2s;" onmouseover="this.style.opacity=1" onmouseout="this.style.opacity=0">Upload</div>
            </div>
            <input type="file" id="profile-img-upload" style="display:none" accept="image/*" onchange="uploadProfileImage(event)">
            
            <!-- Name & Title -->
            <h2 style="font-size: 22px; font-weight: 800; color: #1e293b; margin: 0 0 4px 0; letter-spacing: -0.5px;">${session.name}</h2>
            <div style="font-size: 14px; color: #64748b; font-weight: 500; margin-bottom: 24px;">${session.email}</div>
            
            <!-- Badges -->
            <div style="margin-bottom: 24px; display: flex; gap: 8px; justify-content: center;">
              <span class="badge b-${session.role}" style="font-size: 11px;">${session.role.toUpperCase()}</span>
              ${session.is_verified?'<span style="background:#dcfce7;color:#166534;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700;">✅ Verified</span>':''}
            </div>
            
            <!-- Stats as Social-like Buttons -->
            <div style="display: flex; flex-direction: column; gap: 12px;">
              <div class="stat-btn stat-btn-sub">
                <span class="stat-btn-ico">📄</span>
                <span class="stat-btn-lbl">Submitted Complaints</span>
                <span class="stat-btn-val">${stats.total}</span>
              </div>
              <div class="stat-btn stat-btn-res">
                <span class="stat-btn-ico">✅</span>
                <span class="stat-btn-lbl">Resolved Issues</span>
                <span class="stat-btn-val">${stats.resolved}</span>
              </div>
              <div class="stat-btn stat-btn-act">
                <span class="stat-btn-ico">⏳</span>
                <span class="stat-btn-lbl">Active & Pending</span>
                <span class="stat-btn-val">${stats.in_progress}</span>
              </div>
            </div>
          </div>
          <div class="card a3" style="margin-top:16px;">
            <div class="card-body">
              ${[["🎓 Department",session.dept],["📋 Roll Number",session.roll_no||"—"],["📱 Phone",session.phone||"—"],["🏫 Institution","CDGI, Indore"]].map(([k,v])=>`<div class="flex-bc" style="padding:10px;background:var(--surface2);border-radius:var(--r-sm);margin-bottom:8px;font-size:14px;"><span class="text-2">${k}</span><span class="fw-7">${v}</span></div>`).join("")}
            </div>
          </div>
        </div>
        <div class="profile-right" id="profile-edit-panel">
          <div class="card" style="height: 100%; display: flex; flex-direction: column;">
            <div class="card-head" style="display:flex; justify-content:space-between; align-items:center;">
              <span class="card-title">✏️ Edit Profile</span>
              <button class="btn btn-ghost btn-sm" onclick="toggleEditProfile()" style="padding:4px 8px; font-size:16px;">✕</button>
            </div>
            <div class="card-body" style="flex: 1; display:flex; flex-direction:column;">
              <div id="profile-alert"></div>
              <div class="form-group"><label class="label">Full Name</label><input id="p-name" class="input" value="${session.name}"></div>
              <div class="form-group"><label class="label">Email (cannot change)</label><input class="input" value="${session.email}" disabled style="opacity:.5;"></div>
              <div class="form-group">
                <label class="label">Phone (10 digits)</label>
                <input id="p-phone" class="input" value="${session.phone||""}" placeholder="10-digit number" maxlength="10" oninput="this.value=this.value.replace(/\\D/g,'').slice(0,10)">
                <span class="field-err" id="profile-phone-err">Must be exactly 10 digits</span>
              </div>
              <div class="divider"></div>
              <div class="form-group"><label class="label">New Password (leave blank to keep)</label>
                <div class="pass-wrap"><input id="p-pass" class="input" type="password" placeholder="New password…"><button class="eye-btn" onclick="toggleEye('p-pass',this)" type="button">👁️</button></div>
              </div>
              <div style="margin-top:auto; padding-top:20px;">
                <button class="btn btn-primary btn-full" onclick="saveProfile()" style="padding:12px; font-size:15px; border-radius:10px;">💾 Save Changes</button>
              </div>
            </div>
          </div>
        </div>
      </div>`;
  } catch(e){el.innerHTML=serverDownBanner();}
}

async function saveProfile(){
  const name=document.getElementById("p-name").value.trim();
  const phone=document.getElementById("p-phone").value.trim();
  const pass=document.getElementById("p-pass").value;
  if(phone&&!valPhone(phone)){document.getElementById("profile-phone-err").classList.add("show");toast("Phone must be 10 digits","err");return;}
  document.getElementById("profile-phone-err")?.classList.remove("show");
  try {
    const body={name,phone}; if(pass) body.password=pass;
    const res=await api("profile","PUT",body);
    session=res.user; localStorage.setItem("cirs_user",JSON.stringify(session));
    document.getElementById("profile-alert").innerHTML=`<div class="alert alert-ok"><span class="alert-ico">✅</span>Profile updated!</div>`;
    toast("Profile saved!","ok");
  } catch(e){toast(e.message,"err");}
}

function toggleEditProfile() {
  const layout = document.getElementById("profile-layout");
  const topBtn = document.getElementById("edit-profile-btn");
  const floatBtn = document.getElementById("edit-profile-floating-btn");
  
  if (layout) {
    layout.classList.toggle("editing");
    const isEditing = layout.classList.contains("editing");
    
    if (topBtn) topBtn.style.display = isEditing ? "none" : "flex";
    if (floatBtn) floatBtn.style.display = isEditing ? "none" : "inline-block";
  }
}

async function uploadProfileImage(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  const formData = new FormData();
  formData.append("image", file);
  
  try {
    const res = await api("profile/image", "POST", formData, true);
    session = res.user;
    localStorage.setItem("cirs_user", JSON.stringify(session));
    toast("Profile image updated!", "ok");
    go('profile'); // Re-render profile page
  } catch(e) {
    toast(e.message, "err");
  }
}

/* ══ NOTIFICATIONS ══════════════════════════════════════════ */
async function loadNotifications(){
  try {
    const data=await api("notifications"); const list=data.data||[]; const unread=data.unread||0;
    const dot=document.getElementById("notif-dot"); if(dot) dot.classList.toggle("hidden",unread===0);
    const listEl=document.getElementById("notif-list"); if(!listEl) return;
    listEl.innerHTML=list.length?list.map(n=>`<div class="notif-item ${!n.is_read?"unread":""}"><div class="notif-msg">${n.message}</div><div class="notif-time">${n.created_at}</div></div>`).join(""):`<div class="notif-empty">No notifications yet</div>`;
  } catch(e){}
}
async function markAllRead(){
  try{await api("notifications/read-all","PUT");document.getElementById("notif-dot")?.classList.add("hidden");document.querySelectorAll(".notif-item.unread").forEach(el=>el.classList.remove("unread"));toast("All read","ok");}
  catch(e){toast(e.message,"err");}
}
function toggleNotifDrop(){document.getElementById("notif-drop").classList.toggle("open");loadNotifications();}

/* ══ MODAL ══════════════════════════════════════════════════ */
function openModal(html){document.getElementById("modal").innerHTML=html;document.getElementById("overlay").classList.add("show");}
function closeModal(){document.getElementById("overlay")?.classList.remove("show");window._afterFiles=null;}

/* ══ HELPERS ════════════════════════════════════════════════ */
function statusBadge(s){const m={"routed":"b-routed",assigned:"b-admin","in-progress":"b-progress",resolved:"b-resolved","escalated":"b-escalated",closed:"b-closed"};const l={"routed":"Routed","assigned":"Assigned","in-progress":"In Progress","resolved":"Resolved","escalated":"Escalated","closed":"Closed"};return `<span class="badge ${m[s]||"b-new"}">${l[s]||s}</span>`;}
function serverDownBanner(){return `<div class="card" style="padding:52px;text-align:center;"><div style="font-size:52px;margin-bottom:16px;">⚠️</div><div class="fw-7" style="font-size:21px;">Server Not Running</div><p class="text-2" style="margin-top:10px;font-size:14px;">Run: <code style="background:var(--bg2);padding:2px 8px;border-radius:4px;">cd backend && python app.py</code></p></div>`;}

window.addEventListener("DOMContentLoaded",()=>{
  setTimeout(()=>{const loader=document.getElementById("loader");if(loader){loader.classList.add("done");setTimeout(()=>loader.remove(),500);}boot();},2000);
});

