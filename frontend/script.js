// Auto-detect API base: use localStorage, or detect environment
const getDefaultApiBase = () => {
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    // If localhost/127.0.0.1, use local backend; otherwise use Render backend
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      return "http://127.0.0.1:8000/api";
    }
    // Production: use Render backend
    return "https://leadflow-hsyp.onrender.com/api";
  }
  return "http://127.0.0.1:8000/api";
};

const API_BASE = localStorage.getItem("crm_api_base") || getDefaultApiBase();
const TOKEN_KEY = "crm_token";
const BOOKMARKS_KEY = "crm_bookmarked_leads";
const DASHBOARD_SETTINGS_KEY = "crm_dashboard_settings";

const getPage = () => document.body.dataset.page;
const setMessage = (text, isError = false) => {
  const el = document.getElementById("message");
  if (!el) {
    return;
  }
  el.textContent = text;
  el.classList.toggle("error", isError);
};

const getToken = () => localStorage.getItem(TOKEN_KEY);
const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
const clearToken = () => localStorage.removeItem(TOKEN_KEY);

async function apiFetch(path, options = {}) {
  const apiBase = localStorage.getItem("crm_api_base") || API_BASE;
  const token = getToken();
  const isFormData = (typeof FormData !== "undefined") && (options.body instanceof FormData);
  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers || {}),
  };

  if (token) {
    headers.Authorization = `Token ${token}`;
  }

  let response;
  try {
    response = await fetch(`${apiBase}${path}`, {
      ...options,
      headers,
    });
  } catch (_error) {
    throw new Error("Cannot reach backend. Make sure Django server is running on http://127.0.0.1:8000.");
  }

  let payload = {};
  try {
    payload = await response.json();
  } catch (_error) {
    payload = {};
  }

  if (!response.ok) {
    const msg = payload.detail || "Request failed. Please try again.";
    throw new Error(msg);
  }

  return payload;
}

function initContactPage() {
  const form = document.getElementById("lead-form");
  if (!form) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("");

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    if (!data.name || !data.email || !data.phone || !data.source) {
      setMessage("All fields are required.", true);
      return;
    }

    try {
      await apiFetch("/leads/", {
        method: "POST",
        body: JSON.stringify(data),
      });
      form.reset();
      setMessage("Lead submitted successfully.");
    } catch (error) {
      if (error.message.includes("Cannot reach backend")) {
        setMessage(`${error.message} If your API uses another URL, run localStorage.setItem('crm_api_base', 'http://your-host/api') and refresh.`, true);
        return;
      }
      setMessage(error.message, true);
    }
  });
}

function initLoginPage() {
  const form = document.getElementById("login-form");
  if (!form) {
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("");

    const formData = new FormData(form);
    const credentials = Object.fromEntries(formData.entries());

    if (!credentials.username || !credentials.password) {
      setMessage("Username and password are required.", true);
      return;
    }

    try {
      const result = await apiFetch("/auth/login/", {
        method: "POST",
        body: JSON.stringify(credentials),
      });
      setToken(result.token);
      window.location.href = "dashboard.html";
    } catch (error) {
      setMessage(error.message, true);
    }
  });
}

function initDashboardPage() {
  if (!getToken()) {
    window.location.href = "login.html";
    return;
  }

  // Sidebar navigation
  const navButtons = Array.from(document.querySelectorAll(".sidebar-item[data-target]"));
  const setActiveNav = (button) => {
    navButtons.forEach((b) => b.classList.remove("active"));
    if (button) {
      button.classList.add("active");
    }
  };

  navButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = btn.getAttribute("data-target");
      if (!target) {
        return;
      }
      const el = document.querySelector(target);
      if (!el) {
        setMessage("Section not found.", true);
        return;
      }
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      setActiveNav(btn);
      localStorage.setItem("crm_last_nav", target);
    });
  });

  const lastNav = localStorage.getItem("crm_last_nav");
  if (lastNav) {
    const lastBtn = navButtons.find((b) => b.getAttribute("data-target") === lastNav);
    if (lastBtn) {
      setActiveNav(lastBtn);
    }
  }

  // Sidebar resize (persisted)
  const resizer = document.getElementById("sidebar-resizer");
  if (resizer) {
    const KEY = "crm_sidebar_width";
    const MIN = 220;
    const MAX = 420;

    const clamp = (value) => Math.max(MIN, Math.min(MAX, value));
    const applyWidth = (widthPx) => {
      document.documentElement.style.setProperty("--sidebar-width", `${widthPx}px`);
    };

    const saved = parseInt(localStorage.getItem(KEY) || "", 10);
    if (!Number.isNaN(saved)) {
      applyWidth(clamp(saved));
    }

    let startX = 0;
    let startWidth = 0;

    const onMove = (e) => {
      const dx = e.clientX - startX;
      const next = clamp(startWidth + dx);
      applyWidth(next);
    };

    const onUp = () => {
      document.body.classList.remove("sidebar-resizing");
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);

      const computed = getComputedStyle(document.documentElement).getPropertyValue("--sidebar-width").trim();
      const px = parseInt(computed.replace("px", ""), 10);
      if (!Number.isNaN(px)) {
        localStorage.setItem(KEY, String(px));
      }
    };

    resizer.addEventListener("mousedown", (e) => {
      e.preventDefault();
      document.body.classList.add("sidebar-resizing");
      startX = e.clientX;
      startWidth = document.querySelector(".sidebar")?.getBoundingClientRect().width || 280;
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    });
  }

  const leadsBody = document.getElementById("leads-body");
  const pager = document.getElementById("pager");
  const searchInput = document.getElementById("search-input");
  const statusFilter = document.getElementById("status-filter");
  const sourceFilter = document.getElementById("source-filter");
  const priorityFilter = document.getElementById("priority-filter");
  const assigneeFilter = document.getElementById("assignee-filter");
  const bookmarkedOnly = document.getElementById("bookmarked-only");
  const dateFrom = document.getElementById("date-from");
  const dateTo = document.getElementById("date-to");
  const applyFilters = document.getElementById("apply-filters");
  const exportCsvBtn = document.getElementById("export-csv");
  const refreshAnalyticsBtn = document.getElementById("refresh-analytics");
  const logoutBtn = document.getElementById("logout-btn");

  // Settings (API base)
  const settingsForm = document.getElementById("settings-form");
  const apiBaseInput = document.getElementById("api-base-input");
  const chartDaysInput = document.getElementById("chart-days-input");
  const currencyModeInput = document.getElementById("currency-mode-input");
  const settingsBookmarkedDefault = document.getElementById("settings-bookmarked-default");

  const tasksBody = document.getElementById("tasks-body");
  const refreshTasksBtn = document.getElementById("refresh-tasks");
  const taskMeta = document.getElementById("task-meta");

  const sourceList = document.getElementById("source-list");
  const dailyList = document.getElementById("daily-list");
  const trafficLineChart = document.getElementById("traffic-line-chart");
  const sourceDonut = document.getElementById("source-donut");
  const sourceLegend = document.getElementById("source-legend");
  const bookmarkList = document.getElementById("bookmark-list");
  const bookmarkMeta = document.getElementById("bookmark-meta");

  let nextPageUrl = null;
  let prevPageUrl = null;

  let users = [];
  let lastVisibleLeads = [];
  let trafficChartInstance = null;

  const getDashboardSettings = () => {
    const defaults = {
      chartDays: 7,
      currencyMode: "off",
      bookmarkedOnlyDefault: false,
    };
    try {
      const parsed = JSON.parse(localStorage.getItem(DASHBOARD_SETTINGS_KEY) || "{}");
      return {
        chartDays: [7, 14, 30].includes(Number(parsed.chartDays)) ? Number(parsed.chartDays) : defaults.chartDays,
        currencyMode: parsed.currencyMode === "on" ? "on" : defaults.currencyMode,
        bookmarkedOnlyDefault: Boolean(parsed.bookmarkedOnlyDefault),
      };
    } catch (_error) {
      return defaults;
    }
  };

  let dashboardSettings = getDashboardSettings();

  if (apiBaseInput) {
    apiBaseInput.value = localStorage.getItem("crm_api_base") || API_BASE;
  }
  if (chartDaysInput) {
    chartDaysInput.value = String(dashboardSettings.chartDays);
  }
  if (currencyModeInput) {
    currencyModeInput.value = dashboardSettings.currencyMode;
  }
  if (settingsBookmarkedDefault) {
    settingsBookmarkedDefault.checked = dashboardSettings.bookmarkedOnlyDefault;
  }
  if (bookmarkedOnly) {
    bookmarkedOnly.checked = dashboardSettings.bookmarkedOnlyDefault;
  }

  if (settingsForm && apiBaseInput) {
    settingsForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const next = apiBaseInput.value.trim().replace(/\/$/, "");
      if (!next) {
        setMessage("API Base URL is required.", true);
        return;
      }

      localStorage.setItem("crm_api_base", next);
      dashboardSettings = {
        chartDays: Number(chartDaysInput?.value || 7),
        currencyMode: currencyModeInput?.value === "on" ? "on" : "off",
        bookmarkedOnlyDefault: Boolean(settingsBookmarkedDefault?.checked),
      };
      localStorage.setItem(DASHBOARD_SETTINGS_KEY, JSON.stringify(dashboardSettings));

      if (bookmarkedOnly) {
        bookmarkedOnly.checked = dashboardSettings.bookmarkedOnlyDefault;
      }

      await updateAnalytics();
      await loadLeads();
      setMessage("Dashboard settings saved and applied.");
    });
  }

  const getBookmarks = () => {
    try {
      const raw = localStorage.getItem(BOOKMARKS_KEY);
      const ids = raw ? JSON.parse(raw) : [];
      return new Set(Array.isArray(ids) ? ids.map((id) => Number(id)) : []);
    } catch (_error) {
      return new Set();
    }
  };

  const saveBookmarks = (set) => {
    localStorage.setItem(BOOKMARKS_KEY, JSON.stringify(Array.from(set)));
  };

  const toggleBookmark = (id) => {
    const bookmarks = getBookmarks();
    if (bookmarks.has(Number(id))) {
      bookmarks.delete(Number(id));
    } else {
      bookmarks.add(Number(id));
    }
    saveBookmarks(bookmarks);
    return bookmarks;
  };

  const renderBarList = (container, rows) => {
    if (!container) {
      return;
    }
    container.innerHTML = "";

    if (!rows.length) {
      const empty = document.createElement("li");
      empty.textContent = "No data";
      container.appendChild(empty);
      return;
    }

    const max = Math.max(...rows.map((r) => r.value), 1);
    rows.forEach((row) => {
      const li = document.createElement("li");
      const width = Math.max(6, Math.round((row.value / max) * 100));
      li.innerHTML = `
        <div class="graph-top"><span>${row.label}</span><strong>${row.value}</strong></div>
        <div class="graph-bar"><span style="width:${width}%"></span></div>
      `;
      container.appendChild(li);
    });
  };

  const renderSourceDonut = (sourceItems) => {
    if (!sourceDonut || !sourceLegend) {
      return;
    }

    const palette = ["#7c3aed", "#ec4899", "#06b6d4", "#22c55e", "#f59e0b", "#64748b"];
    const top = (sourceItems || []).slice(0, 6);
    const total = top.reduce((sum, item) => sum + Number(item.count || 0), 0);

    if (!top.length || total === 0) {
      sourceDonut.style.background = "conic-gradient(#e2e8f0 100%)";
      sourceLegend.innerHTML = "<li><span class='label'>No source data</span><span class='value'>0</span></li>";
      return;
    }

    let start = 0;
    const segments = [];
    sourceLegend.innerHTML = "";

    top.forEach((item, index) => {
      const value = Number(item.count || 0);
      const percent = (value / total) * 100;
      const end = start + percent;
      const color = palette[index % palette.length];
      segments.push(`${color} ${start}% ${end}%`);
      start = end;

      const li = document.createElement("li");
      li.innerHTML = `<span class="label">${item.source || "(unknown)"}</span><span class="value">${value}</span>`;
      li.style.borderLeft = `4px solid ${color}`;
      sourceLegend.appendChild(li);
    });

    sourceDonut.style.background = `conic-gradient(${segments.join(",")})`;
  };

  const renderTrafficLineChart = (stats) => {
    if (!trafficLineChart || typeof Chart === "undefined") {
      return;
    }

    const daysWindow = Number(dashboardSettings.chartDays || 7);
    const daily = (stats.leads_daily || []).slice(-daysWindow);
    if (!daily.length) {
      if (trafficChartInstance) {
        trafficChartInstance.destroy();
        trafficChartInstance = null;
      }
      return;
    }

    const labels = daily.map((item) => {
      const parsed = new Date(item.day);
      if (Number.isNaN(parsed.getTime())) {
        return item.day;
      }
      return parsed.toLocaleString("en-US", { month: "short" });
    });

    const salesSeries = daily.map((item) => Number(item.count || 0));
    const engagementFactor = Math.max(0.35, Math.min(0.9, Number(stats.contacted || 0) / Math.max(Number(stats.total || 1), 1)));
    const orderSeries = daily.map((item, index) => {
      const current = Number(item.count || 0);
      const prev = Number(daily[Math.max(index - 1, 0)].count || 0);
      const next = Number(daily[Math.min(index + 1, daily.length - 1)].count || 0);
      return Math.max(0, Math.round(((prev + current + next) / 3) * engagementFactor));
    });

    const ctx = trafficLineChart.getContext("2d");
    const salesGradient = ctx.createLinearGradient(0, 0, 0, 260);
    salesGradient.addColorStop(0, "rgba(109, 40, 217, 0.35)");
    salesGradient.addColorStop(1, "rgba(109, 40, 217, 0.03)");

    const orderGradient = ctx.createLinearGradient(0, 0, 0, 260);
    orderGradient.addColorStop(0, "rgba(236, 72, 153, 0.35)");
    orderGradient.addColorStop(1, "rgba(236, 72, 153, 0.03)");

    if (trafficChartInstance) {
      trafficChartInstance.destroy();
    }

    trafficChartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [
          {
            label: "Sale",
            data: salesSeries,
            borderColor: "#6d28d9",
            backgroundColor: salesGradient,
            fill: true,
            tension: 0.38,
            pointRadius: 3,
            pointHoverRadius: 5,
            borderWidth: 2,
          },
          {
            label: "Order",
            data: orderSeries,
            borderColor: "#ec4899",
            backgroundColor: orderGradient,
            fill: true,
            tension: 0.38,
            pointRadius: 3,
            pointHoverRadius: 5,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "index",
          intersect: false,
        },
        plugins: {
          legend: {
            position: "top",
            align: "end",
            labels: {
              usePointStyle: true,
              boxWidth: 8,
              color: "#475569",
            },
          },
          tooltip: {
            backgroundColor: "#ffffff",
            borderColor: "#e2e8f0",
            borderWidth: 1,
            titleColor: "#0f172a",
            bodyColor: "#334155",
            displayColors: false,
            callbacks: {
              label: (context) => `${context.dataset.label} : ${context.parsed.y}`,
            },
          },
        },
        scales: {
          x: {
            grid: {
              color: "rgba(148, 163, 184, 0.12)",
              drawBorder: false,
            },
            ticks: {
              color: "#64748b",
            },
          },
          y: {
            beginAtZero: true,
            grid: {
              color: "rgba(148, 163, 184, 0.14)",
              drawBorder: false,
            },
            ticks: {
              color: "#64748b",
              callback: (value) => {
                if (dashboardSettings.currencyMode !== "on") {
                  return value;
                }
                const numeric = Number(value || 0);
                return `$${numeric}K`;
              },
            },
          },
        },
      },
    });
  };

  const refreshBookmarkPanel = (leadsForPanel = []) => {
    if (!bookmarkList || !bookmarkMeta) {
      return;
    }

    const bookmarks = getBookmarks();
    bookmarkMeta.textContent = `${bookmarks.size} bookmarked`;
    bookmarkList.innerHTML = "";

    if (!bookmarks.size) {
      bookmarkList.innerHTML = "<span class='panel-meta'>Bookmark leads to pin them here.</span>";
      return;
    }

    const matched = leadsForPanel.filter((lead) => bookmarks.has(Number(lead.id))).slice(0, 12);
    if (!matched.length) {
      bookmarkList.innerHTML = "<span class='panel-meta'>Bookmarked leads are on other pages or filters.</span>";
      return;
    }

    matched.forEach((lead) => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "bookmark-chip";
      chip.textContent = `${lead.name} (${lead.status})`;
      chip.addEventListener("click", () => {
        searchInput.value = lead.name;
        loadLeads();
      });
      bookmarkList.appendChild(chip);
    });
  };

  const exportVisibleLeadsAsCsv = () => {
    const rows = lastVisibleLeads;
    if (!rows.length) {
      setMessage("No leads to export.", true);
      return;
    }

    const header = ["id", "name", "email", "phone", "source", "status", "priority", "assigned_to", "created_at"];
    const csvRows = [header.join(",")];
    rows.forEach((lead) => {
      const line = [
        lead.id,
        lead.name,
        lead.email,
        lead.phone,
        lead.source,
        lead.status,
        lead.priority,
        lead.assigned_to || "",
        lead.created_at,
      ].map((value) => `"${String(value ?? "").replace(/"/g, '""')}"`);
      csvRows.push(line.join(","));
    });

    const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `crm_leads_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    setMessage("CSV exported.");
  };

  const updateAnalytics = async () => {
    try {
      const stats = await apiFetch("/leads/analytics/");
      document.getElementById("stat-total").textContent = stats.total;
      document.getElementById("stat-new").textContent = stats.new;
      document.getElementById("stat-contacted").textContent = stats.contacted;
      document.getElementById("stat-qualified").textContent = stats.qualified;
      document.getElementById("stat-converted").textContent = stats.converted;
      document.getElementById("stat-rate").textContent = `${stats.conversion_rate}%`;

      if (sourceList) {
        sourceList.innerHTML = "";
        (stats.by_source || []).slice(0, 10).forEach((item) => {
          const li = document.createElement("li");
          li.innerHTML = `<span class="label">${item.source || "(unknown)"}</span><span class="value">${item.count}</span>`;
          sourceList.appendChild(li);
        });
      }

      if (dailyList) {
        dailyList.innerHTML = "";
        (stats.leads_daily || []).slice(-10).forEach((item) => {
          const li = document.createElement("li");
          li.innerHTML = `<span class="label">${item.day}</span><span class="value">${item.count}</span>`;
          dailyList.appendChild(li);
        });
      }

      const trafficRows = (stats.leads_daily || []).slice(-14).map((item) => ({
        label: item.day,
        value: Number(item.count || 0),
      }));
      if (!trafficRows.length && dailyList) {
        dailyList.innerHTML = "";
      }

      renderTrafficLineChart(stats);

      renderSourceDonut(stats.by_source || []);
    } catch (error) {
      setMessage(error.message, true);
    }
  };

  const loadUsers = async () => {
    try {
      const result = await apiFetch("/users/");
      // ReadOnlyModelViewSet is paginated by default; handle both shapes.
      users = Array.isArray(result) ? result : (result.results || []);

      if (assigneeFilter) {
        const current = assigneeFilter.value;
        assigneeFilter.innerHTML = `<option value="">All assignees</option>`;
        users.forEach((u) => {
          const opt = document.createElement("option");
          opt.value = String(u.id);
          opt.textContent = u.username;
          assigneeFilter.appendChild(opt);
        });
        assigneeFilter.value = current;
      }
    } catch (_error) {
      users = [];
    }
  };

  const userOptionsHtml = (selectedId) => {
    const options = [`<option value="">Unassigned</option>`];
    users.forEach((u) => {
      const sel = String(selectedId || "") === String(u.id) ? "selected" : "";
      options.push(`<option value="${u.id}" ${sel}>${u.username}</option>`);
    });
    return options.join("");
  };

  const rowTemplate = (lead) => {
    const tr = document.createElement("tr");
    const bookmarked = getBookmarks().has(Number(lead.id));
    if (lead.status === "new") {
      tr.classList.add("new-lead");
    }

    tr.innerHTML = `
      <td>${lead.name}</td>
      <td>${lead.email}</td>
      <td>${lead.phone}</td>
      <td>${lead.source}</td>
      <td>
        <select data-role="status">
          <option value="new" ${lead.status === "new" ? "selected" : ""}>new</option>
          <option value="contacted" ${lead.status === "contacted" ? "selected" : ""}>contacted</option>
          <option value="qualified" ${lead.status === "qualified" ? "selected" : ""}>qualified</option>
          <option value="converted" ${lead.status === "converted" ? "selected" : ""}>converted</option>
        </select>
      </td>
      <td>
        <select data-role="priority">
          <option value="high" ${lead.priority === "high" ? "selected" : ""}>high</option>
          <option value="medium" ${lead.priority === "medium" ? "selected" : ""}>medium</option>
          <option value="low" ${lead.priority === "low" ? "selected" : ""}>low</option>
        </select>
      </td>
      <td>
        <select data-role="assignee">${userOptionsHtml(lead.assigned_to)}</select>
      </td>
      <td class="notes-cell">
        <textarea data-role="notes" placeholder="Add notes...">${lead.notes || ""}</textarea>
      </td>
      <td>${new Date(lead.created_at).toLocaleString()}</td>
      <td class="actions">
        <button data-role="bookmark" class="outline bookmark-btn ${bookmarked ? "active" : ""}">${bookmarked ? "Bookmarked" : "Bookmark"}</button>
        <button data-role="save">Save</button>
        <button data-role="task" class="outline">Add Task</button>
        <button data-role="attach" class="outline">Attach</button>
        <button data-role="delete" class="danger">Delete</button>
      </td>
    `;

    tr.querySelector("[data-role='save']").addEventListener("click", async () => {
      const status = tr.querySelector("[data-role='status']").value;
      const priority = tr.querySelector("[data-role='priority']").value;
      const assigned_to = tr.querySelector("[data-role='assignee']").value || null;
      const notes = tr.querySelector("[data-role='notes']").value;

      try {
        await apiFetch(`/leads/${lead.id}/`, {
          method: "PATCH",
          body: JSON.stringify({ status, priority, assigned_to, notes }),
        });
        setMessage("Lead updated.");
        await loadLeads();
        await updateAnalytics();
      } catch (error) {
        setMessage(error.message, true);
      }
    });

    tr.querySelector("[data-role='bookmark']").addEventListener("click", async () => {
      toggleBookmark(lead.id);
      await loadLeads();
      refreshBookmarkPanel(lastVisibleLeads);
      setMessage("Bookmark updated.");
    });

    tr.querySelector("[data-role='task']").addEventListener("click", async () => {
      const due = window.prompt("Due date/time (YYYY-MM-DDTHH:MM)", "");
      if (!due) {
        return;
      }
      const taskType = (window.prompt("Task type (call/email/meeting)", "call") || "call").toLowerCase();
      try {
        await apiFetch(`/tasks/`, {
          method: "POST",
          body: JSON.stringify({ lead: lead.id, task_type: taskType, due_at: due }),
        });
        setMessage("Task created.");
        await loadTasks();
      } catch (error) {
        setMessage(error.message, true);
      }
    });

    tr.querySelector("[data-role='attach']").addEventListener("click", async () => {
      const input = document.createElement("input");
      input.type = "file";
      input.accept = "*/*";
      input.addEventListener("change", async () => {
        const file = input.files && input.files[0];
        if (!file) {
          return;
        }
        const form = new FormData();
        form.append("file", file);
        try {
          await apiFetch(`/leads/${lead.id}/attachments/`, {
            method: "POST",
            body: form,
          });
          setMessage("Attachment uploaded.");
        } catch (error) {
          setMessage(error.message, true);
        }
      });
      input.click();
    });

    tr.querySelector("[data-role='delete']").addEventListener("click", async () => {
      const confirmed = window.confirm("Delete this lead?");
      if (!confirmed) {
        return;
      }

      try {
        await apiFetch(`/leads/${lead.id}/`, { method: "DELETE" });
        setMessage("Lead deleted.");
        await loadLeads();
        await updateAnalytics();
      } catch (error) {
        setMessage(error.message, true);
      }
    });

    return tr;
  };

  const drawPager = (next, previous, onNavigate) => {
    pager.innerHTML = "";

    const prevBtn = document.createElement("button");
    prevBtn.textContent = "Previous";
    prevBtn.disabled = !previous;
    prevBtn.className = "outline";
    prevBtn.addEventListener("click", () => previous && onNavigate(previous));

    const nextBtn = document.createElement("button");
    nextBtn.textContent = "Next";
    nextBtn.disabled = !next;
    nextBtn.className = "outline";
    nextBtn.addEventListener("click", () => next && onNavigate(next));

    pager.appendChild(prevBtn);
    pager.appendChild(nextBtn);
  };

  const buildQuery = () => {
    const params = new URLSearchParams();
    params.append("ordering", "-created_at");

    const search = searchInput.value.trim();
    const status = statusFilter.value;
    const source = sourceFilter.value;
    const priority = priorityFilter ? priorityFilter.value : "";
    const assignee = assigneeFilter ? assigneeFilter.value : "";
    const from = dateFrom ? dateFrom.value : "";
    const to = dateTo ? dateTo.value : "";

    if (search) {
      params.append("search", search);
    }
    if (status) {
      params.append("status", status);
    }
    if (priority) {
      params.append("priority", priority);
    }
    if (source) {
      params.append("source", source);
    }
    if (assignee) {
      params.append("assigned_to", assignee);
    }
    if (from) {
      params.append("created_at__gte", `${from}T00:00:00`);
    }
    if (to) {
      params.append("created_at__lte", `${to}T23:59:59`);
    }

    return params.toString();
  };

  const taskRowTemplate = (task) => {
    const tr = document.createElement("tr");
    const dueText = task.due_at ? new Date(task.due_at).toLocaleString() : "";
    tr.innerHTML = `
      <td>${dueText}</td>
      <td>${task.task_type}</td>
      <td>${task.lead_name || task.lead}</td>
      <td>${task.assigned_to_username || ""}</td>
      <td>${task.status}</td>
      <td class="actions">
        <button data-role="done" class="outline" ${task.status === "completed" ? "disabled" : ""}>Complete</button>
      </td>
    `;

    tr.querySelector("[data-role='done']").addEventListener("click", async () => {
      try {
        await apiFetch(`/tasks/${task.id}/`, {
          method: "PATCH",
          body: JSON.stringify({ status: "completed" }),
        });
        setMessage("Task completed.");
        await loadTasks();
      } catch (error) {
        setMessage(error.message, true);
      }
    });

    return tr;
  };

  const loadTasks = async () => {
    if (!tasksBody) {
      return;
    }
    try {
      const notif = await apiFetch("/tasks/notifications/");
      const dueToday = notif.due_today || [];
      const overdue = notif.overdue || 0;

      tasksBody.innerHTML = "";
      dueToday.forEach((t) => tasksBody.appendChild(taskRowTemplate(t)));

      if (taskMeta) {
        taskMeta.textContent = `${dueToday.length} due today • ${overdue} overdue`;
      }
    } catch (error) {
      if (taskMeta) {
        taskMeta.textContent = "Unable to load tasks";
      }
    }
  };

  const normalizePathFromAbsolute = (absoluteOrPath) => {
    if (!absoluteOrPath) {
      return "/leads/?ordering=-created_at";
    }

    if (absoluteOrPath.startsWith("http")) {
      const url = new URL(absoluteOrPath);
      return `${url.pathname.replace("/api", "")}${url.search}`;
    }

    return absoluteOrPath;
  };

  const loadLeads = async (path = null) => {
    setMessage("");

    const endpoint = path || `/leads/?${buildQuery()}`;

    try {
      const result = await apiFetch(endpoint);
      leadsBody.innerHTML = "";

      const bookmarks = getBookmarks();
      const rawLeads = result.results || [];
      const visibleLeads = bookmarkedOnly && bookmarkedOnly.checked
        ? rawLeads.filter((lead) => bookmarks.has(Number(lead.id)))
        : rawLeads;

      lastVisibleLeads = visibleLeads;

      visibleLeads.forEach((lead) => {
        leadsBody.appendChild(rowTemplate(lead));
      });

      if (!visibleLeads.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = "<td colspan='10'>No leads match the current filters.</td>";
        leadsBody.appendChild(tr);
      }

      refreshBookmarkPanel(rawLeads);

      nextPageUrl = normalizePathFromAbsolute(result.next);
      prevPageUrl = normalizePathFromAbsolute(result.previous);
      drawPager(nextPageUrl, prevPageUrl, loadLeads);
    } catch (error) {
      if (error.message.toLowerCase().includes("credentials") || error.message.toLowerCase().includes("token")) {
        clearToken();
        window.location.href = "login.html";
        return;
      }
      setMessage(error.message, true);
    }
  };

  applyFilters.addEventListener("click", async () => {
    await loadLeads();
  });

  if (bookmarkedOnly) {
    bookmarkedOnly.addEventListener("change", async () => {
      await loadLeads();
    });
  }

  if (exportCsvBtn) {
    exportCsvBtn.addEventListener("click", () => {
      exportVisibleLeadsAsCsv();
    });
  }

  if (refreshAnalyticsBtn) {
    refreshAnalyticsBtn.addEventListener("click", async () => {
      await updateAnalytics();
      setMessage("Analytics refreshed.");
    });
  }

  const resetFiltersBtn = document.getElementById("reset-filters");
  if (resetFiltersBtn) {
    resetFiltersBtn.addEventListener("click", async () => {
      searchInput.value = "";
      statusFilter.value = "";
      sourceFilter.value = "";
      if (priorityFilter) {
        priorityFilter.value = "";
      }
      if (assigneeFilter) {
        assigneeFilter.value = "";
      }
      if (dateFrom) {
        dateFrom.value = "";
      }
      if (dateTo) {
        dateTo.value = "";
      }
      if (bookmarkedOnly) {
        bookmarkedOnly.checked = false;
      }
      await loadLeads();
    });
  }

  if (refreshTasksBtn) {
    refreshTasksBtn.addEventListener("click", async () => {
      await loadTasks();
    });
  }

  logoutBtn.addEventListener("click", async () => {
    try {
      await apiFetch("/auth/logout/", { method: "POST", body: JSON.stringify({}) });
    } catch (_error) {
      // Token may already be invalid; continue local logout.
    }
    clearToken();
    window.location.href = "login.html";
  });

  (async () => {
    await loadUsers();
    await loadLeads();
    await updateAnalytics();
    await loadTasks();
  })();
}

document.addEventListener("DOMContentLoaded", () => {
  const page = getPage();
  if (page === "contact") {
    initContactPage();
  } else if (page === "login") {
    initLoginPage();
  } else if (page === "dashboard") {
    initDashboardPage();
  }
});
