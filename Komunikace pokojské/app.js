const STORAGE_KEY = "hotel-housekeeping-v2";
const OLD_STORAGE_KEY = "hotel-housekeeping-v1";
const SERVER_MODE = location.protocol === "http:" || location.protocol === "https:";
const SYNC_SERVER_PORT = "4173";
const SYNC_POLL_MS = 2000;
const MAX_PHOTO_FILE_BYTES = 20 * 1024 * 1024;
const APP_VERSION = "v.0.1.0";

const DEFAULT_PHOTO_TASKS = ["Postel", "Koupelna", "Podlaha", "Minibar"];
const DEFAULT_MINIBAR_ITEMS = ["Voda", "Cola", "Pivo", "Víno", "Čokoláda", "Oříšky", "Chipsy", "Jiné"];
const MONTH_NAMES = ["Leden", "Únor", "Březen", "Duben", "Květen", "Červen", "Červenec", "Srpen", "Září", "Říjen", "Listopad", "Prosinec"];

const state = loadState();
localStorage.removeItem("hotel-housekeeping-session");
localStorage.removeItem("hotel-housekeeping-remembered-session");
sessionStorage.removeItem("hotel-housekeeping-window-session");
state.sessionUserId = null;
let activeFilter = "all";
let currentUser = null;
let csrfToken = null;
let serverHydrated = false;
let pushTimer = null;
let focusedAssignmentId = null;
let syncBaseUrl = "";
let syncEvents = null;
let syncPollTimer = null;
let localSaveInProgress = false;
let pendingHydrate = false;
let syncWarningShown = false;
let lastSharedStateJson = "";
let stateEtag = "";
let selectedMinibarMonth = new Date().toISOString().slice(0, 7);
let selectedHistoryMonth = new Date().toISOString().slice(0, 7);
let activeRevisionFilter = "open";

const roleTabs = {
  admin: [{ id: "admin", label: "Admin" }, { id: "reception", label: "Recepce" }, { id: "history", label: "Historie" }, { id: "housekeeping", label: "Pokojská" }, { id: "minibar", label: "Minibar" }],
  reception: [{ id: "reception", label: "Recepce" }, { id: "history", label: "Historie" }, { id: "minibar", label: "Minibar" }],
  housekeeping: [{ id: "housekeeping", label: "Pokojská" }, { id: "revision", label: "Revize" }]
};

const views = {
  admin: document.querySelector("#adminView"),
  reception: document.querySelector("#receptionView"),
  housekeeping: document.querySelector("#housekeepingView"),
  revision: document.querySelector("#revisionView"),
  history: document.querySelector("#historyView"),
  minibar: document.querySelector("#minibarView"),
  settings: document.querySelector("#settingsView")
};

applyColorScheme("light");

document.querySelector("#todayLabel").textContent = new Intl.DateTimeFormat("cs-CZ", {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric"
}).format(new Date());

document.querySelector("#loginForm").addEventListener("submit", handleLogin);
document.querySelector("#settingsButton").addEventListener("click", () => switchView("settings"));
document.querySelector("#logoutButton").addEventListener("click", logout);
document.querySelector("#accountForm").addEventListener("submit", saveAccount);
document.querySelector("#cancelAccountEdit").addEventListener("click", clearAccountForm);
document.querySelector("#adminRoomForm").addEventListener("submit", addAdminRooms);
document.querySelector("#minibarItemForm").addEventListener("submit", addMinibarItem);
document.querySelector("#photoTaskForm").addEventListener("submit", addPhotoTask);
document.querySelector("#assignmentForm").addEventListener("submit", saveAssignment);
document.querySelector("#cancelAssignmentEdit").addEventListener("click", clearAssignmentForm);
document.querySelector("#additionalWorkForm").addEventListener("submit", addAdditionalWorkReport);
document.querySelector("#revisionTaskForm").addEventListener("submit", addRevisionTask);
document.querySelector("#openRevisionTaskDialog").addEventListener("click", () => document.querySelector("#revisionTaskDialog").showModal());
document.querySelector("#closeRevisionTaskDialog").addEventListener("click", () => document.querySelector("#revisionTaskDialog").close());
document.querySelector("#closeDetail").addEventListener("click", () => document.querySelector("#roomDetailDialog").close());

document.querySelectorAll(".filter").forEach((button) => {
  button.addEventListener("click", () => {
    activeFilter = button.dataset.filter;
    document.querySelectorAll(".filter").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    render();
  });
});

document.querySelectorAll(".revision-filter").forEach((button) => {
  button.addEventListener("click", () => {
    activeRevisionFilter = button.dataset.revisionFilter;
    document.querySelectorAll(".revision-filter").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    renderRevisionTasks();
  });
});

document.querySelector("#clearDone").addEventListener("click", () => {
  state.assignments.forEach((assignment) => {
    if (assignment.status === "Zkontrolováno") assignment.archived = true;
  });
  saveState();
  render();
});

document.querySelector("#resetWork").addEventListener("click", () => {
  if (!confirm("Opravdu vymazat denní práci včetně fotek?")) return;
  state.assignments = [];
  saveState();
  render();
});

document.querySelector("#clearMinibar").addEventListener("click", () => {
  if (!confirm("Opravdu vymazat tabulku minibaru?")) return;
  state.minibars = [];
  saveState();
  render();
});

document.querySelector("#sendLaundryEcho").addEventListener("click", sendLaundryEcho);
document.querySelector("#cancelLaundryEcho").addEventListener("click", cancelLaundryEcho);
document.querySelector("#exportPdf").addEventListener("click", exportMinibarPdf);
document.querySelector("#exportHistoryPdf").addEventListener("click", exportHistoryMonthlyPdf);
document.querySelector("#historyPrevMonth").addEventListener("click", () => shiftHistoryMonth(-1));
document.querySelector("#historyNextMonth").addEventListener("click", () => shiftHistoryMonth(1));
document.querySelector("#historyMonthSelect").addEventListener("change", updateHistoryMonthFromPicker);
document.querySelector("#historyYearSelect").addEventListener("change", updateHistoryMonthFromPicker);
document.querySelector("#minibarPrevMonth").addEventListener("click", () => shiftMinibarMonth(-1));
document.querySelector("#minibarNextMonth").addEventListener("click", () => shiftMinibarMonth(1));
document.querySelector("#minibarMonthSelect").addEventListener("change", updateMinibarMonthFromPicker);
document.querySelector("#minibarYearSelect").addEventListener("change", updateMinibarMonthFromPicker);
document.querySelector("#colorScheme").addEventListener("change", saveAccountColorScheme);
setupMinibarMonthPicker();
setupHistoryMonthPicker();

async function handleLogin(event) {
  event.preventDefault();
  const username = document.querySelector("#loginUsername").value.trim();
  const password = document.querySelector("#loginPassword").value;
  const loginError = document.querySelector("#loginError");

  if (SERVER_MODE) {
    if (!syncBaseUrl) syncBaseUrl = await findSyncServer();
    if (syncBaseUrl === null) {
      loginError.textContent = "Synchronizační server není dostupný. Spusťte node server.js.";
      return;
    }

    try {
      const response = await fetch(`${syncBaseUrl}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, password })
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        loginError.textContent = response.status === 429
          ? "Příliš mnoho pokusů. Zkuste to za chvíli."
          : "Špatné jméno nebo heslo.";
        return;
      }

      currentUser = result.user;
      csrfToken = result.csrfToken;
      state.sessionUserId = currentUser?.id || null;
      applyColorScheme(getUserColorScheme(currentUser));
      event.target.reset();
      loginError.textContent = "";
      await hydrateFromServer(true);
      renderShell();
      await connectLiveServer();
      return;
    } catch {
      loginError.textContent = "Přihlášení se nepodařilo. Zkontrolujte server a síť.";
      return;
    }
  }

  const user = state.users.find((item) => item.username === username && item.password === password);

  if (!user) {
    loginError.textContent = "Špatné jméno nebo heslo.";
    return;
  }

  currentUser = user;
  state.sessionUserId = user.id;
  applyColorScheme(getUserColorScheme(user));
  saveState();
  event.target.reset();
  loginError.textContent = "";
  renderShell();
  await connectLiveServer();
}

async function logout() {
  if (SERVER_MODE && syncBaseUrl !== null && csrfToken) {
    try {
      await fetch(`${syncBaseUrl}/api/logout`, {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken },
        credentials: "include"
      });
    } catch {
      // Local logout still clears the visible session if the server is unreachable.
    }
  }
  currentUser = null;
  csrfToken = null;
  state.sessionUserId = null;
  stopLiveSync();
  applyColorScheme("light");
  sessionStorage.removeItem("hotel-housekeeping-window-session");
  localStorage.removeItem("hotel-housekeeping-remembered-session");
  localStorage.removeItem("hotel-housekeeping-session");
  saveStateToBrowserCache();
  renderShell();
}

function renderShell() {
  document.querySelector("#loginScreen").classList.toggle("hidden", Boolean(currentUser));
  document.querySelector("#appShell").classList.toggle("hidden", !currentUser);

  if (!currentUser) return;

  applyColorScheme(getUserColorScheme(currentUser));
  document.querySelector("#currentUserLabel").textContent = `${currentUser.username} (${roleLabel(currentUser.role)})`;
  renderSyncStatus();
  renderTabs();
  render();
}

function renderTabs() {
  const container = document.querySelector("#tabs");
  container.innerHTML = "";
  const tabs = roleTabs[currentUser.role] || [];
  const currentActive = document.querySelector(".view.active")?.id.replace("View", "");
  const allowedActive = tabs.some((tab) => tab.id === currentActive) ? currentActive : tabs[0]?.id;

  tabs.forEach((tab) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tab";
    button.dataset.view = tab.id;
    button.textContent = tab.label;
    button.classList.toggle("active", tab.id === allowedActive);
    button.addEventListener("click", () => switchView(tab.id));
    container.append(button);
  });

  switchView(allowedActive, false);
}

function switchView(viewName, rerender = true) {
  const tabs = roleTabs[currentUser?.role] || [];
  const isTabView = tabs.some((tab) => tab.id === viewName);
  if (!isTabView && viewName !== "settings") return;

  Object.entries(views).forEach(([name, view]) => {
    view.classList.toggle("active", name === viewName);
  });
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.view === viewName);
  });
  document.querySelector("#settingsButton").classList.toggle("active", viewName === "settings");
  if (rerender) render();
}

function render() {
  if (!currentUser) return;

  if (currentUser.role === "admin") renderAdmin();
  if (currentUser.role === "admin" || currentUser.role === "reception") renderAssignmentOptions();

  const activeAssignments = state.assignments
    .filter((assignment) => !assignment.archived)
    .sort((a, b) => Number(a.roomNumber) - Number(b.roomNumber));
  const filteredAssignments = activeFilter === "all"
    ? activeAssignments
    : activeAssignments.filter((assignment) => assignment.status === activeFilter);

  renderMetrics(activeAssignments);
  renderLaundryControl();
  renderLaundryAlert();
  renderRoomList(document.querySelector("#receptionRooms"), filteredAssignments, "reception");
  renderRoomList(
    document.querySelector("#housekeepingRooms"),
    activeAssignments.filter((assignment) => assignment.status !== "Hotovo" && assignment.status !== "Zkontrolováno"),
    "housekeeping"
  );
  renderHousekeepingFocus(activeAssignments);
  renderAdditionalWorkReports();
  renderRevisionTasks();
  renderHistory();
  renderMinibars();
  renderSettings();
}

function renderAdmin() {
  renderAccounts();
  renderAdminRooms();
  renderAdminMinibarItems();
  renderAdminPhotoTasks();
}

function renderAccounts() {
  const container = document.querySelector("#accountsList");
  container.innerHTML = "";

  state.users.forEach((user) => {
    const row = document.createElement("div");
    row.className = "list-row";
    const text = document.createElement("div");
    text.innerHTML = `<strong></strong><span></span>`;
    text.querySelector("strong").textContent = user.username;
    text.querySelector("span").textContent = roleLabel(user.role);

    const actions = document.createElement("div");
    actions.className = "row-actions";
    actions.append(makeButton("Upravit", "", () => editAccount(user.id)));
    if (user.id !== "admin") {
      actions.append(makeButton("Smazat", "danger", () => deleteAccount(user.id)));
    }

    row.append(text, actions);
    container.append(row);
  });
}

function renderAdminRooms() {
  const container = document.querySelector("#adminRoomsList");
  container.innerHTML = "";

  state.hotelRooms
    .slice()
    .sort((a, b) => Number(a) - Number(b))
    .forEach((room) => {
      container.append(chip(room, () => {
        state.hotelRooms = state.hotelRooms.filter((item) => item !== room);
        saveState();
        render();
      }));
    });
}

function renderAdminMinibarItems() {
  const container = document.querySelector("#adminMinibarList");
  container.innerHTML = "";

  state.minibarItems.forEach((item) => {
    container.append(chip(item, () => {
      state.minibarItems = state.minibarItems.filter((value) => value !== item);
      saveState();
      render();
    }));
  });
}

function renderAdminPhotoTasks() {
  const container = document.querySelector("#adminPhotoTasksList");
  container.innerHTML = "";

  state.photoTasks.forEach((item) => {
    container.append(chip(item, () => {
      state.photoTasks = state.photoTasks.filter((value) => value !== item);
      saveState();
      render();
    }));
  });
}

function renderSettings() {
  const version = document.querySelector("#settingsVersion");
  const userLabel = document.querySelector("#settingsCurrentUser");
  const colorScheme = document.querySelector("#colorScheme");
  if (!version || !userLabel || !colorScheme || !currentUser) return;

  version.textContent = APP_VERSION;
  userLabel.textContent = `${currentUser.username} (${roleLabel(currentUser.role)})`;
  colorScheme.value = getUserColorScheme(currentUser);
}

function saveAccountColorScheme(event) {
  if (!currentUser) return;
  const colorScheme = normalizeColorScheme(event.target.value);
  const user = state.users.find((item) => item.id === currentUser.id);
  if (user) user.colorScheme = colorScheme;
  currentUser.colorScheme = colorScheme;
  applyColorScheme(colorScheme);
  saveState();
  renderSettings();
}

function renderAssignmentOptions() {
  const roomChecks = document.querySelector("#assignmentRooms");
  const selectedRooms = new Set([...roomChecks.querySelectorAll("input:checked")].map((input) => input.value));
  roomChecks.innerHTML = "";
  state.hotelRooms
    .slice()
    .sort((a, b) => Number(a) - Number(b))
    .forEach((room) => {
      const label = document.createElement("label");
      label.className = "room-check";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = room;
      input.checked = selectedRooms.has(room);
      label.append(input, document.createTextNode(`Pokoj ${room}`));
      roomChecks.append(label);
    });

  const checks = document.querySelector("#requiredPhotoChecks");
  const selectedPhotoTasks = new Set([...checks.querySelectorAll("input:checked")].map((input) => input.value));
  checks.innerHTML = "";
  state.photoTasks.forEach((task) => {
    const label = document.createElement("label");
    label.className = "checkbox-line";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = task;
    input.checked = selectedPhotoTasks.has(task);
    label.append(input, document.createTextNode(task));
    checks.append(label);
  });
}

function saveAccount(event) {
  event.preventDefault();
  const id = document.querySelector("#accountId").value;
  const username = document.querySelector("#accountUsername").value.trim();
  const password = document.querySelector("#accountPassword").value;
  const role = document.querySelector("#accountRole").value;

  if (!username || (!id && !password)) return;
  const duplicate = state.users.find((user) => user.username === username && user.id !== id);
  if (duplicate) {
    alert("Toto jméno už existuje.");
    return;
  }

  if (id) {
    const user = state.users.find((item) => item.id === id);
    if (user) {
      Object.assign(user, { username, role });
      if (password) user.password = password;
    }
  } else {
    state.users.push({ id: createId(), username, password, role });
  }

  clearAccountForm();
  warnWhenSavingWithoutSync();
  saveState();
  render();
}

function editAccount(id) {
  const user = state.users.find((item) => item.id === id);
  if (!user) return;
  document.querySelector("#accountId").value = user.id;
  document.querySelector("#accountUsername").value = user.username;
  document.querySelector("#accountPassword").value = "";
  document.querySelector("#accountRole").value = user.role;
}

function clearAccountForm() {
  document.querySelector("#accountForm").reset();
  document.querySelector("#accountId").value = "";
}

function deleteAccount(id) {
  if (!confirm("Opravdu smazat tento účet?")) return;
  state.users = state.users.filter((user) => user.id !== id);
  saveState();
  render();
}

function addAdminRooms(event) {
  event.preventDefault();
  const rooms = parseRooms(document.querySelector("#adminRoomNumbers").value);
  state.hotelRooms = unique([...state.hotelRooms, ...rooms]).sort((a, b) => Number(a) - Number(b));
  event.target.reset();
  saveState();
  render();
}

function addMinibarItem(event) {
  event.preventDefault();
  const value = document.querySelector("#minibarItemName").value.trim();
  if (!value) return;
  state.minibarItems = unique([...state.minibarItems, value]);
  event.target.reset();
  saveState();
  render();
}

function addPhotoTask(event) {
  event.preventDefault();
  const value = document.querySelector("#photoTaskName").value.trim();
  if (!value) return;
  state.photoTasks = unique([...state.photoTasks, value]);
  event.target.reset();
  saveState();
  render();
}

function saveAssignment(event) {
  event.preventDefault();
  const id = document.querySelector("#assignmentId").value;
  const rooms = [...document.querySelectorAll("#assignmentRooms input:checked")].map((input) => input.value);
  if (!rooms.length) {
    alert("Vyberte alespoň jeden pokoj.");
    return;
  }
  if (id && rooms.length > 1) {
    alert("Při úpravě vyberte jen jeden pokoj.");
    return;
  }

  const checkedTasks = [...document.querySelectorAll("#requiredPhotoChecks input:checked")].map((input) => input.value);
  const customTasks = parseCustomPhotoTasks(document.querySelector("#customPhotoTask").value);
  const requiredPhotos = unique([...checkedTasks, ...customTasks]);

  const base = {
    workType: document.querySelector("#workType").value,
    priority: document.querySelector("#priority").value,
    note: document.querySelector("#note").value.trim(),
    requiredPhotos,
    updatedAt: now()
  };

  if (id) {
    const assignment = state.assignments.find((item) => item.id === id);
    if (!assignment) {
      alert("Úkol už neexistuje.");
      clearAssignmentForm();
      render();
      return;
    }

    Object.assign(assignment, base, { roomNumber: rooms[0] });
    assignment.photos = (assignment.photos || []).filter((photo) => requiredPhotos.includes(photo.task) || photo.voluntary);
    clearAssignmentForm();
    saveState();
    render();
    return;
  }

  rooms.forEach((roomNumber) => {
    const existing = state.assignments.find((item) => item.roomNumber === roomNumber && !item.archived);
    if (existing) {
      Object.assign(existing, base);
      existing.photos = (existing.photos || []).filter((photo) => requiredPhotos.includes(photo.task) || photo.voluntary);
      return;
    }

    state.assignments.push({
      id: createId(),
      roomNumber,
      status: "Čeká",
      createdAt: now(),
      startedAt: null,
      finishedAt: null,
      durationSeconds: null,
      housekeeperId: null,
      housekeeperName: "",
      housekeeperNote: "",
      photos: [],
      minibars: [],
      extraTasks: [],
      archived: false,
      ...base
    });
  });

  clearAssignmentForm();
  saveState();
  render();
}

function parseCustomPhotoTasks(value) {
  return unique(value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean));
}

function editAssignment(id) {
  const assignment = state.assignments.find((item) => item.id === id);
  if (!assignment) return;

  document.querySelector("#assignmentForm").reset();
  document.querySelector("#assignmentId").value = assignment.id;
  document.querySelector("#assignmentFormTitle").textContent = "Upravit úklid";
  document.querySelector("#assignmentSubmit").textContent = "Uložit úpravy";
  document.querySelector("#cancelAssignmentEdit").classList.remove("hidden");
  document.querySelector("#workType").value = assignment.workType;
  document.querySelector("#priority").value = assignment.priority;
  document.querySelector("#note").value = assignment.note || "";

  renderAssignmentOptions();
  setCheckedValues("#assignmentRooms", [assignment.roomNumber]);
  setCheckedValues("#requiredPhotoChecks", (assignment.requiredPhotos || []).filter((task) => state.photoTasks.includes(task)));

  const customTasks = (assignment.requiredPhotos || []).filter((task) => !state.photoTasks.includes(task));
  document.querySelector("#customPhotoTask").value = customTasks.join(", ");
  document.querySelector("#assignmentForm").scrollIntoView({ behavior: "smooth", block: "start" });
}

function setCheckedValues(selector, values) {
  const selected = new Set(values);
  document.querySelectorAll(`${selector} input`).forEach((input) => {
    input.checked = selected.has(input.value);
  });
}

function clearAssignmentForm() {
  document.querySelector("#assignmentForm").reset();
  document.querySelector("#assignmentId").value = "";
  document.querySelector("#assignmentFormTitle").textContent = "Zadat úklid";
  document.querySelector("#assignmentSubmit").textContent = "Přidat do denního seznamu";
  document.querySelector("#cancelAssignmentEdit").classList.add("hidden");
  renderAssignmentOptions();
}

function renderMetrics(assignments) {
  document.querySelector("#summaryText").textContent = `${assignments.length} pokojů`;
  document.querySelector("#metricOpen").textContent = assignments.filter((item) => item.status === "Čeká").length;
  document.querySelector("#metricProgress").textContent = assignments.filter((item) => item.status === "Uklízí se" || item.status === "Pozastaveno").length;
  document.querySelector("#metricDone").textContent = assignments.filter((item) => item.status === "Hotovo" || item.status === "Zkontrolováno").length;
}

function sendLaundryEcho() {
  const active = activeLaundryTask();
  if (active) return;
  state.laundryTasks = [
    ...(state.laundryTasks || []),
    {
      id: createId(),
      status: "open",
      createdAt: now(),
      acceptedAt: null,
      acceptedById: null,
      acceptedByName: "",
      completedAt: null,
      photos: []
    }
  ];
  saveState();
  render();
}

function cancelLaundryEcho() {
  const active = activeLaundryTask();
  if (!active || !confirm("Opravdu zrušit aktivní echo prádelny?")) return;
  active.status = "cancelled";
  active.cancelledAt = now();
  saveState();
  render();
}

function renderLaundryControl() {
  const statusText = document.querySelector("#laundryStatusText");
  const sendButton = document.querySelector("#sendLaundryEcho");
  const cancelButton = document.querySelector("#cancelLaundryEcho");
  if (!statusText || !sendButton || !cancelButton) return;

  const active = activeLaundryTask();
  sendButton.disabled = Boolean(active);
  cancelButton.classList.toggle("hidden", !active);
  if (!active) {
    statusText.textContent = "Bez aktivního echa";
    return;
  }

  if (active.status === "accepted") {
    statusText.textContent = `Převzala: ${active.acceptedByName || "pokojská"}`;
    return;
  }

  statusText.textContent = "Dorazila prádelna";
}

function renderLaundryAlert() {
  const container = document.querySelector("#laundryAlert");
  if (!container) return;
  container.innerHTML = "";
  const active = activeLaundryTask();
  if (!active) return;

  const alert = document.createElement("section");
  alert.className = "laundry-alert";
  const mark = document.createElement("div");
  mark.className = "laundry-alert-mark";
  mark.textContent = "!";

  const content = document.createElement("div");
  const title = document.createElement("h2");
  title.textContent = "Dorazila prádelna";
  const text = document.createElement("p");
  text.textContent = active.status === "accepted"
    ? `Prádlo převzala ${active.acceptedByName || "pokojská"}. Dokončení vyžaduje fotku skříně.`
    : "Recepce poslala echo. Převezměte prádlo a po uložení vyfoťte skříň.";
  content.append(title, text);

  const actions = document.createElement("div");
  actions.className = "laundry-alert-actions";
  if (active.status === "open") {
    actions.append(makeButton("Převzít prádlo", "primary", () => acceptLaundryTask(active.id)));
  } else if (active.acceptedById === currentUser?.id) {
    actions.append(laundryPhotoInput(active));
  } else {
    const info = document.createElement("span");
    info.className = "hint";
    info.textContent = "Úkol už je převzatý jinou pokojskou.";
    actions.append(info);
  }

  alert.append(mark, content, actions);
  container.append(alert);
}

function acceptLaundryTask(id) {
  const task = (state.laundryTasks || []).find((item) => item.id === id);
  if (!task || task.status !== "open" || !currentUser) return;
  task.status = "accepted";
  task.acceptedAt = now();
  task.acceptedById = currentUser.id;
  task.acceptedByName = currentUser.username;
  saveState();
  render();
}

function laundryPhotoInput(task) {
  const label = document.createElement("label");
  label.className = "laundry-photo-input";
  label.textContent = "Foto skříně s prádlem";
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.addEventListener("change", async () => {
    if (!input.files.length) return;
    input.disabled = true;
    localSaveInProgress = true;
    try {
      const photoData = await fileToPhotoData(input.files[0]);
      task.status = "done";
      task.completedAt = now();
      task.photos = [{ id: createId(), task: "Skříň s prádlem", src: photoData.thumb, fullSrc: photoData.full, createdAt: now() }];
      addHistoryRecord({
        type: "laundry",
        id: task.id,
        status: "Hotovo",
        createdAt: task.createdAt,
        acceptedAt: task.acceptedAt,
        finishedAt: task.completedAt,
        completedAt: task.completedAt,
        housekeeperId: task.acceptedById || currentUser?.id || null,
        housekeeperName: task.acceptedByName || currentUser?.username || "",
        photos: task.photos
      }, { skipSave: true });
      saveState();
      render();
    } catch (error) {
      localSaveInProgress = false;
      input.disabled = false;
      alert(error.message || "Fotku skříně se nepodařilo uložit. Zkuste to prosím znovu.");
    }
  });
  label.append(input);
  return label;
}

function renderRoomList(container, assignments, mode) {
  container.innerHTML = "";

  if (!assignments.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = mode === "housekeeping" ? "Zatím tu nejsou žádné pokoje k úklidu." : "Zatím tu nejsou žádné pokoje.";
    container.append(empty);
    return;
  }

  assignments.forEach((assignment) => {
    const card = document.querySelector("#roomCardTemplate").content.firstElementChild.cloneNode(true);
    card.querySelector(".room-number").textContent = `Pokoj ${assignment.roomNumber}`;
    card.querySelector(".work-type").textContent = assignment.workType;
    const status = card.querySelector(".status");
    status.textContent = assignment.status;
    status.classList.add(statusClass(assignment.status));
    card.querySelector(".note").textContent = assignment.note || "Bez poznámky.";
    card.querySelector(".requirements").append(requirementsList(assignment));
    card.querySelector(".requirements").append(extraTasksList(assignment, mode));
    card.querySelector(".card-meta").append(...metaLines(assignment));

    const actions = card.querySelector(".actions");
    if (mode === "reception") renderReceptionActions(actions, assignment);
    if (mode === "housekeeping") renderHousekeepingActions(actions, assignment);

    if (mode === "reception" && (assignment.status === "Hotovo" || assignment.status === "Zkontrolováno")) {
      card.classList.add("openable");
      card.title = "Dvojklikem otevřít detail pokoje";
      card.addEventListener("dblclick", () => openRoomDetail(assignment));
    }

    container.append(card);
  });
}

function renderHousekeepingFocus(assignments) {
  const appShell = document.querySelector("#appShell");
  const list = document.querySelector("#housekeepingRooms");
  const detail = document.querySelector("#housekeepingDetail");
  const assignment = assignments.find((item) => item.id === focusedAssignmentId && (item.status === "Uklízí se" || item.status === "Pozastaveno"));

  detail.innerHTML = "";
  appShell.classList.toggle("housekeeping-focus-mode", Boolean(assignment) && currentUser?.role === "housekeeping");
  list.classList.toggle("hidden", Boolean(assignment));
  detail.classList.toggle("hidden", !assignment);

  if (!assignment) return;

  const header = document.createElement("div");
  header.className = "focused-head";
  const title = document.createElement("div");
  title.innerHTML = `<p class="eyebrow">Aktuální úklid</p><h2></h2>`;
  title.querySelector("h2").textContent = `Pokoj ${assignment.roomNumber}`;
  const back = makeButton("Zpět na seznam", "", () => {
    focusedAssignmentId = null;
    render();
  });
  header.append(title, back);

  const card = document.querySelector("#roomCardTemplate").content.firstElementChild.cloneNode(true);
  card.classList.add("focused-card");
  card.querySelector(".room-number").textContent = `Pokoj ${assignment.roomNumber}`;
  card.querySelector(".work-type").textContent = assignment.workType;
  const status = card.querySelector(".status");
  status.textContent = assignment.status;
  status.classList.add(statusClass(assignment.status));
  card.querySelector(".note").textContent = assignment.note || "Bez poznámky.";
  card.querySelector(".requirements").append(requirementsList(assignment));
  card.querySelector(".requirements").append(extraTasksList(assignment, "housekeeping"));
  card.querySelector(".card-meta").append(...metaLines(assignment));
  renderHousekeepingActions(card.querySelector(".actions"), assignment);

  detail.append(header, card);
}

function addAdditionalWorkReport(event) {
  event.preventDefault();
  const textInput = document.querySelector("#additionalWorkText");
  const text = textInput.value.trim();
  if (!text || !currentUser) return;

  addHistoryRecord({
    type: "additionalWork",
    id: createId(),
    text,
    createdAt: now(),
    finishedAt: now(),
    housekeeperId: currentUser.id,
    housekeeperName: currentUser.username
  });
  event.target.reset();
  render();
}

function renderAdditionalWorkReports() {
  const container = document.querySelector("#additionalWorkList");
  if (!container) return;
  container.innerHTML = "";

  const today = historyDateKey(now());
  const records = (state.history || [])
    .filter((record) => record.type === "additionalWork")
    .filter((record) => record.housekeeperId === currentUser?.id)
    .filter((record) => historyDateKey(record.finishedAt || record.savedAt || record.createdAt) === today)
    .sort((a, b) => new Date(b.finishedAt || b.savedAt || b.createdAt) - new Date(a.finishedAt || a.savedAt || a.createdAt));

  if (!records.length) {
    const empty = document.createElement("div");
    empty.className = "empty compact-empty";
    empty.textContent = "Dnes zatím není zapsaná žádná dodatková práce.";
    container.append(empty);
    return;
  }

  records.forEach((record) => {
    const row = document.createElement("article");
    row.className = "additional-work-row";
    const text = document.createElement("p");
    text.textContent = record.text;
    const time = document.createElement("span");
    time.textContent = formatDateTime(record.finishedAt || record.savedAt || record.createdAt);
    row.append(text, time);
    container.append(row);
  });
}

function renderReceptionActions(actions, assignment) {
  actions.append(photoGrid(assignment));
  if (assignment.housekeeperNote) {
    const note = document.createElement("p");
    note.className = "housekeeper-note";
    note.textContent = `Poznámka pokojské: ${assignment.housekeeperNote}`;
    actions.append(note);
  }

  const row = document.createElement("div");
  row.className = "action-row";
  row.append(
    makeButton("Upravit zadání", "", () => editAssignment(assignment.id)),
    makeButton("Vrátit k úklidu", "", () => updateAssignment(assignment.id, { status: "Uklízí se", finishedAt: null, durationSeconds: null })),
    makeButton("Zkontrolováno", "primary", () => updateAssignment(assignment.id, { status: "Zkontrolováno" }))
  );
  actions.append(row);
  actions.append(makeButton("Smazat úkol", "danger", () => deleteAssignment(assignment.id)));
}

function renderHousekeepingActions(actions, assignment) {
  if (assignment.status === "Čeká") {
    actions.append(makeButton("Začít úklid", "primary", () => startCleaning(assignment.id)));
    actions.append(disabledHint("Po zahájení se otevře detail jen tohoto pokoje."));
    return;
  }

  if (assignment.status === "Pozastaveno") {
    actions.append(makeButton("Pokračovat v úklidu", "primary", () => resumeCleaning(assignment.id)));
    actions.append(disabledHint("Úklid je pozastavený. Recepce to vidí u pokoje."));
    return;
  }

  actions.append(extraTaskForm(assignment));
  assignment.requiredPhotos.forEach((task) => {
    actions.append(photoInput(assignment, task));
  });
  actions.append(voluntaryPhotoInput(assignment));

  actions.append(noteInput(assignment));
  actions.append(minibarForm(assignment));
  actions.append(photoGrid(assignment));

  const finishButton = makeButton("Ukončit úklid", "primary", () => finishCleaning(assignment.id));
  const complete = isAssignmentComplete(assignment);
  finishButton.disabled = !complete;
  const row = document.createElement("div");
  row.className = "action-row";
  row.append(makeButton("Pozastavit úklid", "", () => pauseCleaning(assignment.id)), finishButton);
  actions.append(row);

  if (!complete) {
    actions.append(disabledHint("Úklid nejde ukončit, dokud nejsou vložené všechny povinné fotky."));
  }
}

function requirementsList(assignment) {
  const wrapper = document.createElement("div");
  wrapper.className = "requirement-list";
  if (!assignment.requiredPhotos.length) {
    const item = document.createElement("span");
    item.className = "done";
    item.textContent = "Fotky nejsou povinné";
    wrapper.append(item);
    return wrapper;
  }
  assignment.requiredPhotos.forEach((task) => {
    const item = document.createElement("span");
    const done = assignment.photos.some((photo) => photo.task === task);
    item.className = done ? "done" : "";
    item.textContent = `${done ? "Hotovo" : "Čeká"}: ${task}`;
    wrapper.append(item);
  });
  return wrapper;
}

function extraTasksList(assignment, mode) {
  const wrapper = document.createElement("div");
  wrapper.className = "extra-task-list";
  const tasks = assignment.extraTasks || [];
  if (!tasks.length) return wrapper;

  const title = document.createElement("h3");
  title.textContent = "Dodatkové úkoly bez času";
  wrapper.append(title);

  tasks.forEach((task) => {
    const label = document.createElement(mode === "housekeeping" ? "label" : "div");
    label.className = "extra-task";
    const text = document.createElement("span");
    text.textContent = task.text;

    if (mode === "housekeeping") {
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = Boolean(task.done);
      checkbox.addEventListener("change", () => toggleExtraTask(assignment.id, task.id, checkbox.checked));
      label.append(checkbox, text);
    } else {
      const badge = document.createElement("strong");
      badge.textContent = task.done ? "Hotovo" : "Zapsáno";
      label.append(badge, text);
    }

    wrapper.append(label);
  });

  return wrapper;
}

function extraTaskForm(assignment) {
  const form = document.createElement("form");
  form.className = "extra-task-form";
  const label = document.createElement("label");
  label.textContent = "Dopsat práci navíc";
  const input = document.createElement("input");
  input.placeholder = "Například vyčištěná skvrna, uklizený balkon, opravená drobnost";
  label.append(input);
  const button = document.createElement("button");
  button.type = "submit";
  button.textContent = "Přidat";
  form.append(label, button);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    assignment.extraTasks = [...(assignment.extraTasks || []), createExtraTask(text)];
    assignment.updatedAt = now();
    saveState();
    render();
  });
  return form;
}

function metaLines(assignment) {
  const lines = [
    `Priorita: ${assignment.priority}`,
    `Aktualizováno: ${formatDateTime(assignment.updatedAt)}`
  ];
  if (assignment.startedAt) lines.push(`Začátek: ${formatDateTime(assignment.startedAt)}`);
  if (assignment.status === "Pozastaveno" && assignment.pauseStartedAt) lines.push(`Pozastaveno od: ${formatDateTime(assignment.pauseStartedAt)}`);
  if (assignment.finishedAt) lines.push(`Konec: ${formatDateTime(assignment.finishedAt)}`);
  if (assignment.startedAt && !assignment.finishedAt && assignment.status !== "Pozastaveno") lines.push(`Čas běží: ${formatDuration(cleaningSecondsSoFar(assignment))}`);
  if (assignment.startedAt && !assignment.finishedAt && assignment.status === "Pozastaveno") lines.push(`Odpracováno: ${formatDuration(cleaningSecondsSoFar(assignment))}`);
  if (assignment.durationSeconds !== null) lines.push(`Doba úklidu: ${formatDuration(assignment.durationSeconds)}`);

  return lines.map((line) => {
    const span = document.createElement("span");
    span.textContent = line;
    return span;
  });
}

function startCleaning(id) {
  focusedAssignmentId = id;
  updateAssignment(id, {
    status: "Uklízí se",
    startedAt: now(),
    finishedAt: null,
    durationSeconds: null,
    pausedSeconds: 0,
    pauseStartedAt: null,
    housekeeperId: currentUser?.id || null,
    housekeeperName: currentUser?.username || ""
  });
}

function pauseCleaning(id) {
  focusedAssignmentId = null;
  updateAssignment(id, { status: "Pozastaveno", pauseStartedAt: now() });
}

function resumeCleaning(id) {
  const assignment = state.assignments.find((item) => item.id === id);
  if (!assignment) return;
  focusedAssignmentId = id;
  const pausedSeconds = (assignment.pausedSeconds || 0) + (assignment.pauseStartedAt ? secondsBetween(assignment.pauseStartedAt, now()) : 0);
  updateAssignment(id, { status: "Uklízí se", pausedSeconds, pauseStartedAt: null });
}

function finishCleaning(id) {
  const assignment = state.assignments.find((item) => item.id === id);
  if (!assignment || !isAssignmentComplete(assignment)) return;
  const finishedAt = now();
  const durationSeconds = cleaningDurationAtFinish(assignment, finishedAt);
  updateAssignment(id, {
    status: "Hotovo",
    finishedAt,
    durationSeconds,
    pauseStartedAt: null
  });
  addHistoryRecord({ ...assignment, status: "Hotovo", finishedAt, durationSeconds, pauseStartedAt: null });
  focusedAssignmentId = null;
}

function isAssignmentComplete(assignment) {
  return Boolean(assignment.startedAt) && assignment.requiredPhotos.every((task) => assignment.photos.some((photo) => photo.task === task));
}

function photoInput(assignment, task) {
  const label = document.createElement("label");
  label.textContent = `Foto: ${task}`;
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.addEventListener("change", async () => {
    if (!input.files.length) return;
    input.disabled = true;
    localSaveInProgress = true;
    try {
      const photoData = await fileToPhotoData(input.files[0]);
      assignment.photos = assignment.photos.filter((photo) => photo.task !== task);
      assignment.photos.push({ id: createId(), task, src: photoData.thumb, fullSrc: photoData.full, createdAt: now() });
      assignment.updatedAt = now();
      saveState();
      render();
    } catch (error) {
      localSaveInProgress = false;
      alert(error.message || "Fotku se nepodařilo zpracovat. Zkuste ji prosím vyfotit znovu.");
      input.disabled = false;
    }
  });
  label.append(input);
  return label;
}

function voluntaryPhotoInput(assignment) {
  const label = document.createElement("label");
  label.textContent = "Dobrovolná fotka";
  const taskInput = document.createElement("input");
  taskInput.placeholder = "Popis fotky, např. závada, flek, rozbité vybavení";
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = "image/*";
  fileInput.addEventListener("change", async () => {
    if (!fileInput.files.length) return;
    fileInput.disabled = true;
    localSaveInProgress = true;
    try {
      const task = taskInput.value.trim() || "Dobrovolná kontrola";
      const photoData = await fileToPhotoData(fileInput.files[0]);
      assignment.photos.push({ id: createId(), task, src: photoData.thumb, fullSrc: photoData.full, voluntary: true, createdAt: now() });
      assignment.updatedAt = now();
      saveState();
      render();
    } catch (error) {
      localSaveInProgress = false;
      alert(error.message || "Fotku se nepodařilo zpracovat. Zkuste ji prosím vyfotit znovu.");
      fileInput.disabled = false;
    }
  });
  label.append(taskInput, fileInput);
  return label;
}

function addRevisionTask(event) {
  event.preventDefault();
  const location = document.querySelector("#revisionLocation").value.trim();
  const text = document.querySelector("#revisionText").value.trim();
  if (!location || !text) return;

  state.revisionTasks = [
    ...(state.revisionTasks || []),
    {
      id: createId(),
      location,
      text,
      status: "open",
      createdAt: now(),
      completedAt: null,
      completedById: null,
      completedByName: "",
      note: "",
      photos: []
    }
  ];
  event.target.reset();
  document.querySelector("#revisionTaskDialog").close();
  activeRevisionFilter = "open";
  document.querySelectorAll(".revision-filter").forEach((item) => item.classList.toggle("active", item.dataset.revisionFilter === "open"));
  saveState();
  render();
}

function renderRevisionTasks() {
  const container = document.querySelector("#revisionTasks");
  if (!container) return;
  container.innerHTML = "";
  const tasks = state.revisionTasks || [];
  const openCount = tasks.filter((task) => task.status !== "done").length;
  const doneCount = tasks.filter((task) => task.status === "done").length;
  document.querySelector("#revisionSummary").textContent = `${openCount} ke splnění / ${doneCount} splněno`;

  const visible = tasks
    .filter((task) => activeRevisionFilter === "done" ? task.status === "done" : task.status !== "done")
    .sort((a, b) => activeRevisionFilter === "done"
      ? new Date(b.completedAt || b.createdAt) - new Date(a.completedAt || a.createdAt)
      : new Date(a.createdAt) - new Date(b.createdAt));

  if (!visible.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = activeRevisionFilter === "done" ? "Zatím nejsou splněné žádné revize." : "Zatím nejsou žádné revize ke splnění.";
    container.append(empty);
    return;
  }

  visible.forEach((task) => container.append(revisionTaskCard(task)));
}

function revisionTaskCard(task) {
  const card = document.createElement("article");
  card.className = "revision-card";

  const head = document.createElement("div");
  head.className = "room-card-head";
  const title = document.createElement("div");
  const location = document.createElement("span");
  location.className = "room-number";
  location.textContent = task.location;
  const created = document.createElement("span");
  created.className = "badge";
  created.textContent = `Zadáno ${formatDateTime(task.createdAt)}`;
  title.append(location, created);
  const status = document.createElement("span");
  status.className = `status ${task.status === "done" ? "zkontrolovano" : "ceka"}`;
  status.textContent = task.status === "done" ? "Splněno" : "Ke splnění";
  head.append(title, status);

  const text = document.createElement("p");
  text.className = "note";
  text.textContent = task.text;
  card.append(head, text);

  if (task.status === "done") {
    const meta = document.createElement("div");
    meta.className = "card-meta";
    [`Splnila: ${task.completedByName || "nezapsáno"}`, `Dokončeno: ${formatDateTime(task.completedAt)}`].forEach((line) => {
      const item = document.createElement("span");
      item.textContent = line;
      meta.append(item);
    });
    card.append(meta);
    if (task.note) {
      const note = document.createElement("p");
      note.className = "housekeeper-note";
      note.textContent = task.note;
      card.append(note);
    }
    card.append(revisionPhotoGrid(task));
    return card;
  }

  const details = document.createElement("details");
  details.className = "revision-complete";
  const summary = document.createElement("summary");
  summary.textContent = "Udělat úkol";
  details.append(summary, revisionCompleteForm(task));
  card.append(details);
  return card;
}

function revisionCompleteForm(task) {
  const form = document.createElement("form");
  form.className = "revision-complete-form";
  const noteLabel = document.createElement("label");
  noteLabel.textContent = "Poznámka";
  const note = document.createElement("textarea");
  note.name = "note";
  note.rows = 3;
  note.placeholder = "Co bylo hotové, co zůstává, upřesnění...";
  noteLabel.append(note);

  const photoLabel = document.createElement("label");
  photoLabel.textContent = "Fotky";
  const photos = document.createElement("input");
  photos.name = "photos";
  photos.type = "file";
  photos.accept = "image/*";
  photos.multiple = true;
  photoLabel.append(photos);

  const submit = document.createElement("button");
  submit.type = "submit";
  submit.className = "primary";
  submit.textContent = "Splnit úkol";
  form.append(noteLabel, photoLabel, submit);
  form.addEventListener("submit", (event) => completeRevisionTask(event, task.id));
  return form;
}

async function completeRevisionTask(event, taskId) {
  event.preventDefault();
  const task = (state.revisionTasks || []).find((item) => item.id === taskId);
  if (!task || task.status === "done") return;
  const form = event.currentTarget;
  const submit = form.querySelector("button[type='submit']");
  submit.disabled = true;
  localSaveInProgress = true;
  try {
    const files = [...form.querySelector("input[type='file']").files];
    const photos = [];
    for (const file of files) {
      const photoData = await fileToPhotoData(file);
      photos.push({ id: createId(), task: task.location, src: photoData.thumb, fullSrc: photoData.full, createdAt: now() });
    }
    task.status = "done";
    task.completedAt = now();
    task.completedById = currentUser?.id || null;
    task.completedByName = currentUser?.username || "";
    task.note = form.querySelector("textarea").value.trim();
    task.photos = photos;
    saveState();
    activeRevisionFilter = "done";
    document.querySelectorAll(".revision-filter").forEach((item) => item.classList.toggle("active", item.dataset.revisionFilter === "done"));
    render();
  } catch (error) {
    localSaveInProgress = false;
    submit.disabled = false;
    alert(error.message || "Revizi se nepodařilo uložit. Zkuste to prosím znovu.");
  }
}

function revisionPhotoGrid(task) {
  const grid = document.createElement("div");
  grid.className = "photo-grid";
  if (!task.photos?.length) {
    const empty = document.createElement("span");
    empty.className = "hint";
    empty.textContent = "Bez fotek";
    grid.append(empty);
    return grid;
  }

  task.photos.forEach((photo) => {
    const figure = document.createElement("figure");
    const image = document.createElement("img");
    const caption = document.createElement("figcaption");
    image.src = resolveMediaUrl(photo.src);
    image.alt = `Revize ${task.location}`;
    caption.textContent = formatDateTime(photo.createdAt);
    figure.append(image, caption);
    grid.append(figure);
  });
  return grid;
}

function minibarForm(assignment) {
  const wrapper = document.createElement("details");
  wrapper.className = "minibar-panel";
  const used = state.minibars.filter((entry) => entry.assignmentId === assignment.id);
  const summary = document.createElement("summary");
  summary.innerHTML = `<span>Minibar</span><strong></strong>`;
  summary.querySelector("strong").textContent = used.length ? `${used.length} zapsáno` : "nic zapsáno";
  wrapper.append(summary);

  const form = document.createElement("form");
  form.className = "minibar-checks";
  state.minibarItems.forEach((item) => {
    const existing = state.minibars.find((entry) => entry.assignmentId === assignment.id && entry.item === item);
    const label = document.createElement("label");
    label.className = "minibar-check";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = item;
    checkbox.checked = Boolean(existing);
    label.append(checkbox, document.createTextNode(item));
    form.append(label);
  });

  const save = document.createElement("button");
  save.className = "primary";
  save.type = "submit";
  save.textContent = "Zapsat minibar";
  form.append(save);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const checkedItems = [...form.querySelectorAll("input:checked")].map((input) => input.value);
    saveMinibarChecklist(assignment, checkedItems);
  });
  wrapper.append(form);

  if (used.length) {
    const list = document.createElement("div");
    list.className = "minibar-used";
    used.forEach((entry) => {
      const item = document.createElement("span");
      item.textContent = `${entry.item}: ${entry.quantity}`;
      list.append(item);
    });
    wrapper.append(list);
  }

  return wrapper;
}

function saveMinibarChecklist(assignment, checkedItems) {
  state.minibars = state.minibars.filter((entry) => entry.assignmentId !== assignment.id || checkedItems.includes(entry.item));
  checkedItems.forEach((item) => {
    const existing = state.minibars.find((entry) => entry.assignmentId === assignment.id && entry.item === item);
    if (existing) {
      existing.quantity = 1;
      existing.updatedAt = now();
    } else {
      state.minibars.push({
        id: createId(),
        assignmentId: assignment.id,
        roomNumber: assignment.roomNumber,
        item,
        quantity: 1,
        note: "",
        createdAt: now(),
        updatedAt: now()
      });
    }
  });

  assignment.updatedAt = now();
  saveState();
  render();
}

function noteInput(assignment) {
  const label = document.createElement("label");
  label.textContent = "Poznámka od pokojské";
  const input = document.createElement("textarea");
  input.rows = 3;
  input.value = assignment.housekeeperNote || "";
  input.placeholder = "Například závada, chybí ručníky, host je na pokoji...";
  input.addEventListener("change", () => {
    updateAssignment(assignment.id, { housekeeperNote: input.value.trim() });
  });
  label.append(input);
  return label;
}

function photoGrid(assignment) {
  const grid = document.createElement("div");
  grid.className = "photo-grid";
  if (!assignment.photos.length) {
    const empty = document.createElement("span");
    empty.className = "hint";
    empty.textContent = "Bez fotek";
    grid.append(empty);
    return grid;
  }

  assignment.photos.forEach((photo) => {
    const figure = document.createElement("figure");
    const image = document.createElement("img");
    const caption = document.createElement("figcaption");
    image.src = resolveMediaUrl(photo.src);
    image.alt = `Foto ${photo.task} pokoj ${assignment.roomNumber}`;
    caption.textContent = photo.task;
    figure.append(image, caption);
    grid.append(figure);
  });
  return grid;
}

function openRoomDetail(assignment) {
  const dialog = document.querySelector("#roomDetailDialog");
  document.querySelector("#detailTitle").textContent = `Pokoj ${assignment.roomNumber}`;
  document.querySelector("#detailEyebrow").textContent = assignment.historyId ? "Historie úklidu" : "Detail hotového pokoje";
  const body = document.querySelector("#detailBody");
  body.innerHTML = "";

  const meta = document.createElement("div");
  meta.className = "detail-meta";
  metaLines(assignment).forEach((line) => meta.append(line));
  const housekeeper = document.createElement("span");
  housekeeper.textContent = `Pokojská: ${assignment.housekeeperName || "nezapsáno"}`;
  meta.append(housekeeper);
  body.append(meta);

  if (assignment.housekeeperNote) {
    const note = document.createElement("p");
    note.className = "housekeeper-note";
    note.textContent = `Poznámka pokojské: ${assignment.housekeeperNote}`;
    body.append(note);
  }

  body.append(requirementsList(assignment));
  body.append(extraTasksList(assignment, "reception"));

  const photos = document.createElement("div");
  photos.className = "detail-photos";
  if (!assignment.photos.length) {
    const empty = document.createElement("p");
    empty.className = "hint";
    empty.textContent = "Pokoj nemá fotky.";
    photos.append(empty);
  }
  assignment.photos.forEach((photo) => {
    const figure = document.createElement("figure");
    const image = document.createElement("img");
    const caption = document.createElement("figcaption");
    image.src = resolveMediaUrl(photo.fullSrc || photo.src);
    image.alt = `Foto ${photo.task} pokoj ${assignment.roomNumber}`;
    caption.textContent = photo.task;
    figure.append(image, caption);
    photos.append(figure);
  });
  body.append(photos);

  dialog.showModal();
}

function renderMinibars() {
  const tbody = document.querySelector("#minibarRows");
  tbody.innerHTML = "";
  document.querySelector("#clearMinibar").classList.toggle("hidden", currentUser?.role !== "admin");

  updateMinibarMonthPicker();
  const rows = groupedMinibarRows(selectedMinibarMonth);

  if (!rows.length) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 3;
    cell.textContent = "Zatím nejsou zapsané žádné minibary.";
    row.append(cell);
    tbody.append(row);
    return;
  }

  rows.forEach((item) => {
      const row = document.createElement("tr");
      [item.roomNumber, formatDateOnly(item.createdAt), item.itemsText].forEach((value) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      });
      tbody.append(row);
  });
}

function renderHistory() {
  const container = document.querySelector("#historyRooms");
  container.innerHTML = "";
  updateHistoryMonthPicker();
  const records = (state.history || []).slice().sort((a, b) => new Date(b.finishedAt || b.savedAt || b.createdAt) - new Date(a.finishedAt || a.savedAt || a.createdAt));

  if (!records.length) {
    const empty = document.createElement("div");
    empty.className = "empty";
    empty.textContent = "Historie je zatím prázdná.";
    container.append(empty);
    return;
  }

  const table = document.createElement("table");
  table.innerHTML = `
    <thead>
      <tr>
        <th>Datum</th>
        <th>Pokojská</th>
        <th>Pokoje / práce</th>
        <th>Detail</th>
      </tr>
    </thead>
    <tbody></tbody>
  `;
  const tbody = table.querySelector("tbody");

  groupHistoryRecords(records).forEach((group) => {
    const row = document.createElement("tr");
    const dateCell = document.createElement("td");
    const userCell = document.createElement("td");
    const roomsCell = document.createElement("td");
    const detailCell = document.createElement("td");
    const button = makeButton("Zobrazit detaily", "primary", () => openHistoryGroupDetail(group));

    dateCell.textContent = group.label;
    userCell.textContent = group.housekeeperName;
    roomsCell.textContent = historyGroupSummary(group.records);
    detailCell.append(button);
    row.append(dateCell, userCell, roomsCell, detailCell);
    tbody.append(row);
  });

  container.append(table);
}

function addHistoryRecord(assignment, options = {}) {
  const copy = JSON.parse(JSON.stringify(assignment));
  copy.historyId = createId();
  copy.savedAt = now();
  state.history = [copy, ...(state.history || [])];
  if (!options.skipSave) saveState();
}

function historyGroupSummary(records) {
  const rooms = records.filter((record) => !record.type).map((record) => record.roomNumber).filter(Boolean);
  const additionalCount = records.filter((record) => record.type === "additionalWork").length;
  const laundryCount = records.filter((record) => record.type === "laundry").length;
  const parts = [];
  if (rooms.length) parts.push(rooms.join(", "));
  if (additionalCount) parts.push(`${additionalCount} ${additionalWorkCountLabel(additionalCount)}`);
  if (laundryCount) parts.push(`${laundryCount}x prádelna`);
  return parts.join(" + ") || "Bez pokojů";
}

function additionalWorkCountLabel(count) {
  if (count === 1) return "dodatková práce";
  if (count > 1 && count < 5) return "dodatkové práce";
  return "dodatkových prací";
}

function groupHistoryRecords(records) {
  const groups = new Map();
  records.forEach((record) => {
    const key = `${historyDateKey(record.finishedAt || record.savedAt || record.createdAt)}::${record.housekeeperName || "nezapsáno"}`;
    if (!groups.has(key)) {
      groups.set(key, {
        key,
        label: formatDateOnly(record.finishedAt || record.savedAt || record.createdAt),
        housekeeperName: record.housekeeperName || "nezapsáno",
        records: []
      });
    }
    groups.get(key).records.push(record);
  });

  return [...groups.values()].sort((a, b) => new Date(b.records[0].finishedAt || b.records[0].createdAt) - new Date(a.records[0].finishedAt || a.records[0].createdAt));
}

function openHistoryGroupDetail(group) {
  const dialog = document.querySelector("#roomDetailDialog");
  document.querySelector("#detailEyebrow").textContent = "Historie úklidu";
  document.querySelector("#detailTitle").textContent = `${group.label} - ${group.housekeeperName}`;
  const body = document.querySelector("#detailBody");
  body.innerHTML = "";

  group.records.forEach((record) => {
    const section = document.createElement("section");
    section.className = "history-detail-room";
    const title = document.createElement("h3");
    if (record.type === "laundry") {
      title.textContent = "Prádelna";
      section.append(title);

      const meta = document.createElement("div");
      meta.className = "detail-meta";
      [
        `Pokojská: ${record.housekeeperName || "nezapsáno"}`,
        `Převzato: ${record.acceptedAt ? formatDateTime(record.acceptedAt) : "nezapsáno"}`,
        `Dokončeno: ${formatDateTime(record.finishedAt || record.completedAt || record.savedAt || record.createdAt)}`,
        `Stav: ${record.status || "Hotovo"}`
      ].forEach((line) => {
        const item = document.createElement("span");
        item.textContent = line;
        meta.append(item);
      });
      section.append(meta);

      section.append(photoGrid({ ...record, roomNumber: "prádelna", photos: record.photos || [] }));
      section.append(historyCheckActions(record));
      body.append(section);
      return;
    }

    if (record.type === "additionalWork") {
      title.textContent = "Dodatková práce";
      section.append(title);

      const meta = document.createElement("div");
      meta.className = "detail-meta";
      const finished = document.createElement("span");
      finished.textContent = `Zapsáno: ${formatDateTime(record.finishedAt || record.savedAt || record.createdAt)}`;
      meta.append(finished);
      section.append(meta);

      const note = document.createElement("p");
      note.className = "housekeeper-note";
      note.textContent = record.text || "Bez popisu.";
      section.append(note);
      section.append(historyCheckActions(record));
      body.append(section);
      return;
    }

    title.textContent = `Pokoj ${record.roomNumber}`;
    section.append(title);

    const meta = document.createElement("div");
    meta.className = "detail-meta";
    metaLines(record).forEach((line) => meta.append(line));
    section.append(meta);

    if (record.note) {
      const note = document.createElement("p");
      note.className = "housekeeper-note";
      note.textContent = `Zadání recepce: ${record.note}`;
      section.append(note);
    }

    if (record.housekeeperNote) {
      const note = document.createElement("p");
      note.className = "housekeeper-note";
      note.textContent = `Poznámka pokojské: ${record.housekeeperNote}`;
      section.append(note);
    }

    section.append(requirementsList(record));
    section.append(extraTasksList(record, "reception"));
    section.append(photoGrid(record));
    section.append(historyCheckActions(record));
    if (currentUser?.role === "admin") {
      section.append(historyEditForm(record));
    }
    body.append(section);
  });

  dialog.showModal();
}

function historyCheckActions(record) {
  const wrapper = document.createElement("div");
  wrapper.className = "history-check-actions";
  if (record.status === "Zkontrolováno") {
    const checked = document.createElement("span");
    checked.className = "status zkontrolovano";
    checked.textContent = "Zkontrolováno";
    wrapper.append(checked);
    return wrapper;
  }

  if (currentUser?.role !== "admin" && currentUser?.role !== "reception") return wrapper;
  wrapper.append(makeButton("Zkontrolováno", "primary", () => checkHistoryRecord(record)));
  return wrapper;
}

function checkHistoryRecord(record) {
  const target = findHistoryRecord(record);
  if (!target) return;
  target.status = "Zkontrolováno";
  target.checkedAt = now();
  target.checkedById = currentUser?.id || null;
  target.checkedByName = currentUser?.username || "";
  saveState();
  render();
  document.querySelector("#roomDetailDialog").close();
}

function historyEditForm(record) {
  const details = document.createElement("details");
  details.className = "history-edit";
  const summary = document.createElement("summary");
  summary.textContent = "Upravit historii";
  details.append(summary);

  const form = document.createElement("form");
  form.className = "history-edit-form";
  form.append(
    fieldInput("Pokoj", "roomNumber", record.roomNumber || ""),
    fieldInput("Datum dokončení", "finishedAt", toDateTimeLocal(record.finishedAt || record.savedAt || record.createdAt), "datetime-local"),
    fieldInput("Pokojská", "housekeeperName", record.housekeeperName || ""),
    fieldSelect("Stav", "status", ["Hotovo", "Zkontrolováno"], record.status || "Hotovo"),
    fieldSelect("Typ práce", "workType", ["Příjezd", "Odjezd", "Průběh", "Jiné úkoly"], record.workType || "Odjezd"),
    fieldTextarea("Zadání recepce", "note", record.note || ""),
    fieldTextarea("Poznámka pokojské", "housekeeperNote", record.housekeeperNote || "")
  );

  const actions = document.createElement("div");
  actions.className = "action-row";
  const save = document.createElement("button");
  save.type = "submit";
  save.className = "primary";
  save.textContent = "Uložit historii";
  actions.append(save, makeButton("Smazat z historie", "danger", () => deleteHistoryRecord(record)));
  form.append(actions);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    saveHistoryRecord(record, form);
  });
  details.append(form);
  return details;
}

function fieldInput(labelText, name, value, type = "text") {
  const label = document.createElement("label");
  label.textContent = labelText;
  const input = document.createElement("input");
  input.name = name;
  input.type = type;
  input.value = value;
  label.append(input);
  return label;
}

function fieldSelect(labelText, name, values, selected) {
  const label = document.createElement("label");
  label.textContent = labelText;
  const select = document.createElement("select");
  select.name = name;
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    option.selected = value === selected;
    select.append(option);
  });
  label.append(select);
  return label;
}

function fieldTextarea(labelText, name, value) {
  const label = document.createElement("label");
  label.textContent = labelText;
  const textarea = document.createElement("textarea");
  textarea.name = name;
  textarea.rows = 3;
  textarea.value = value;
  label.append(textarea);
  return label;
}

function saveHistoryRecord(record, form) {
  const target = findHistoryRecord(record);
  if (!target) return;
  const formData = new FormData(form);
  const finishedAt = fromDateTimeLocal(formData.get("finishedAt")) || target.finishedAt || target.savedAt || now();
  Object.assign(target, {
    roomNumber: String(formData.get("roomNumber") || "").trim() || target.roomNumber,
    finishedAt,
    savedAt: target.savedAt || finishedAt,
    updatedAt: now(),
    housekeeperName: String(formData.get("housekeeperName") || "").trim(),
    status: String(formData.get("status") || target.status),
    workType: String(formData.get("workType") || target.workType),
    note: String(formData.get("note") || "").trim(),
    housekeeperNote: String(formData.get("housekeeperNote") || "").trim()
  });
  saveState();
  render();
  document.querySelector("#roomDetailDialog").close();
}

function deleteHistoryRecord(record) {
  if (!confirm("Opravdu smazat tento záznam historie?")) return;
  const id = historyRecordKey(record);
  state.history = (state.history || []).filter((item) => historyRecordKey(item) !== id);
  saveState();
  render();
  document.querySelector("#roomDetailDialog").close();
}

function findHistoryRecord(record) {
  const id = historyRecordKey(record);
  return (state.history || []).find((item) => historyRecordKey(item) === id);
}

function historyRecordKey(record) {
  return record.historyId || `${record.id || ""}::${record.savedAt || record.finishedAt || record.createdAt || ""}`;
}

function groupedMinibarRows(month) {
  const normalizedMonth = month || new Date().toISOString().slice(0, 7);
  const groups = new Map();
  state.minibars
    .filter((item) => !normalizedMonth || String(item.createdAt || "").slice(0, 7) === normalizedMonth)
    .forEach((item) => {
      const dateKey = historyDateKey(item.createdAt || now());
      const key = `${dateKey}::${item.roomNumber || ""}::${item.assignmentId || ""}`;
      if (!groups.has(key)) {
        groups.set(key, {
          key,
          createdAt: item.createdAt || now(),
          roomNumber: item.roomNumber || "",
          items: []
        });
      }
      groups.get(key).items.push(`${item.item}${item.quantity && Number(item.quantity) !== 1 ? ` (${item.quantity}x)` : ""}`);
    });

  return [...groups.values()]
    .map((item) => ({ ...item, itemsText: item.items.join(", ") }))
    .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt) || String(a.roomNumber).localeCompare(String(b.roomNumber), "cs"));
}

function setupMinibarMonthPicker() {
  setupMonthPicker("#minibarMonthSelect", "#minibarYearSelect");
  updateMinibarMonthPicker();
}

function setupHistoryMonthPicker() {
  setupMonthPicker("#historyMonthSelect", "#historyYearSelect");
  updateHistoryMonthPicker();
}

function setupMonthPicker(monthSelector, yearSelector) {
  const monthSelect = document.querySelector(monthSelector);
  const yearSelect = document.querySelector(yearSelector);
  monthSelect.innerHTML = "";
  yearSelect.innerHTML = "";

  MONTH_NAMES.forEach((label, index) => {
    const option = document.createElement("option");
    option.value = String(index + 1).padStart(2, "0");
    option.textContent = label;
    monthSelect.append(option);
  });

  const currentYear = new Date().getFullYear();
  for (let year = currentYear - 3; year <= currentYear + 2; year += 1) {
    const option = document.createElement("option");
    option.value = String(year);
    option.textContent = String(year);
    yearSelect.append(option);
  }

}

function updateMinibarMonthPicker() {
  const [year, month] = selectedMinibarMonth.split("-");
  const monthSelect = document.querySelector("#minibarMonthSelect");
  const yearSelect = document.querySelector("#minibarYearSelect");
  ensureYearOption(yearSelect, year);
  monthSelect.value = month;
  yearSelect.value = year;
}

function updateHistoryMonthPicker() {
  const [year, month] = selectedHistoryMonth.split("-");
  const monthSelect = document.querySelector("#historyMonthSelect");
  const yearSelect = document.querySelector("#historyYearSelect");
  ensureYearOption(yearSelect, year);
  monthSelect.value = month;
  yearSelect.value = year;
}

function updateMinibarMonthFromPicker() {
  const month = document.querySelector("#minibarMonthSelect").value;
  const year = document.querySelector("#minibarYearSelect").value;
  selectedMinibarMonth = `${year}-${month}`;
  renderMinibars();
}

function updateHistoryMonthFromPicker() {
  const month = document.querySelector("#historyMonthSelect").value;
  const year = document.querySelector("#historyYearSelect").value;
  selectedHistoryMonth = `${year}-${month}`;
  renderHistory();
}

function shiftMinibarMonth(offset) {
  const [year, month] = selectedMinibarMonth.split("-").map(Number);
  const date = new Date(year, month - 1 + offset, 1);
  selectedMinibarMonth = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
  renderMinibars();
}

function shiftHistoryMonth(offset) {
  const [year, month] = selectedHistoryMonth.split("-").map(Number);
  const date = new Date(year, month - 1 + offset, 1);
  selectedHistoryMonth = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
  renderHistory();
}

function ensureYearOption(yearSelect, year) {
  if ([...yearSelect.options].some((option) => option.value === String(year))) return;
  const option = document.createElement("option");
  option.value = String(year);
  option.textContent = String(year);
  yearSelect.append(option);
  [...yearSelect.options]
    .sort((a, b) => Number(a.value) - Number(b.value))
    .forEach((item) => yearSelect.append(item));
}

function exportMinibarPdf() {
  const month = selectedMinibarMonth;
  const rows = groupedMinibarRows(month);
  const report = window.open("", "_blank");
  if (!report) {
    alert("Prohlížeč zablokoval otevření exportu. Povolte prosím vyskakovací okna pro tuto aplikaci.");
    return;
  }

  report.document.write(`<!doctype html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <title>Minibary ${escapeHtml(month)}</title>
  <style>
    body { font-family: Arial, sans-serif; color: #1e2726; margin: 28px; }
    h1 { margin: 0 0 4px; font-size: 24px; }
    p { margin: 0 0 18px; color: #687370; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #dfe5df; padding: 8px; text-align: left; vertical-align: top; }
    th { background: #eef4f1; }
    @media print { body { margin: 16mm; } button { display: none; } }
  </style>
</head>
<body>
  <button onclick="window.print()">Uložit jako PDF</button>
  <h1>Minibary</h1>
  <p>Měsíc: ${escapeHtml(formatMonthLabel(month))}</p>
  <table>
    <thead><tr><th>Pokoj</th><th>Datum</th><th>Položky</th></tr></thead>
    <tbody>
      ${rows.length ? rows.map((row) => `<tr><td>${escapeHtml(row.roomNumber)}</td><td>${escapeHtml(formatDateOnly(row.createdAt))}</td><td>${escapeHtml(row.itemsText)}</td></tr>`).join("") : '<tr><td colspan="3">Žádné záznamy.</td></tr>'}
    </tbody>
  </table>
</body>
</html>`);
  report.document.close();
  report.focus();
  report.print();
}

function exportHistoryMonthlyPdf() {
  const month = selectedHistoryMonth || new Date().toISOString().slice(0, 7);
  const rows = historyMonthlyReportRows(month);
  const report = window.open("", "_blank");
  if (!report) {
    alert("Prohlížeč zablokoval otevření exportu. Povolte prosím vyskakovací okna pro tuto aplikaci.");
    return;
  }

  report.document.write(`<!doctype html>
<html lang="cs">
<head>
  <meta charset="utf-8">
  <title>Historie ${escapeHtml(month)}</title>
  <style>
    body { font-family: Arial, sans-serif; color: #1e2726; margin: 28px; }
    h1 { margin: 0 0 4px; font-size: 24px; }
    p { margin: 0 0 18px; color: #687370; }
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #dfe5df; padding: 8px; text-align: left; vertical-align: top; }
    th { background: #eef4f1; }
    @media print { body { margin: 16mm; } button { display: none; } }
  </style>
</head>
<body>
  <button onclick="window.print()">Uložit jako PDF</button>
  <h1>Měsíční report historie</h1>
  <p>Měsíc: ${escapeHtml(formatMonthLabel(month))}</p>
  <table>
    <thead>
      <tr>
        <th>Pokojská</th>
        <th>Dní práce</th>
        <th>Pokojů celkem</th>
        <th>Převzetí prádelny</th>
      </tr>
    </thead>
    <tbody>
      ${rows.length ? rows.map((row) => `<tr><td>${escapeHtml(row.housekeeperName)}</td><td>${row.workDays}</td><td>${row.roomsCleaned}</td><td>${row.laundryCount}</td></tr>`).join("") : '<tr><td colspan="4">Žádné záznamy.</td></tr>'}
    </tbody>
  </table>
</body>
</html>`);
  report.document.close();
  report.focus();
  report.print();
}

function historyMonthlyReportRows(month) {
  const summary = new Map();
  (state.history || [])
    .filter((record) => String(record.finishedAt || record.savedAt || record.createdAt || "").slice(0, 7) === month)
    .forEach((record) => {
      const name = record.housekeeperName || "nezapsáno";
      if (!summary.has(name)) {
        summary.set(name, { housekeeperName: name, days: new Set(), roomsCleaned: 0, laundryCount: 0 });
      }
      const item = summary.get(name);
      item.days.add(historyDateKey(record.finishedAt || record.savedAt || record.createdAt));
      if (!record.type && record.roomNumber) item.roomsCleaned += 1;
      if (record.type === "laundry") item.laundryCount += 1;
    });

  return [...summary.values()]
    .map((item) => ({ ...item, workDays: item.days.size }))
    .sort((a, b) => a.housekeeperName.localeCompare(b.housekeeperName, "cs"));
}

function updateAssignment(id, changes) {
  const assignment = state.assignments.find((item) => item.id === id);
  if (!assignment) return;
  Object.assign(assignment, changes, { updatedAt: now() });
  saveState();
  render();
}

function activeLaundryTask() {
  return (state.laundryTasks || [])
    .slice()
    .sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))
    .find((task) => task.status === "open" || task.status === "accepted") || null;
}

function deleteAssignment(id) {
  if (!confirm("Opravdu smazat tento úkol?")) return;
  state.assignments = state.assignments.filter((item) => item.id !== id);
  saveState();
  render();
}

function toggleExtraTask(assignmentId, taskId, done) {
  const assignment = state.assignments.find((item) => item.id === assignmentId);
  const task = assignment?.extraTasks?.find((item) => item.id === taskId);
  if (!task) return;
  task.done = done;
  task.doneAt = done ? now() : null;
  assignment.updatedAt = now();
  saveState();
  render();
}

function createExtraTask(text) {
  return {
    id: createId(),
    text,
    source: "Pokojská",
    done: false,
    createdAt: now(),
    doneAt: null
  };
}

function makeButton(text, className, handler) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = text;
  if (className) button.className = className;
  button.addEventListener("click", handler);
  return button;
}

function disabledHint(text) {
  const paragraph = document.createElement("p");
  paragraph.className = "hint";
  paragraph.textContent = text;
  return paragraph;
}

function chip(text, onRemove) {
  const wrapper = document.createElement("span");
  wrapper.className = "chip";
  const label = document.createElement("span");
  label.textContent = text;
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "x";
  button.addEventListener("click", onRemove);
  wrapper.append(label, button);
  return wrapper;
}

function parseRooms(value) {
  return value
    .split(",")
    .flatMap((part) => {
      const trimmed = part.trim();
      if (!trimmed) return [];
      const range = trimmed.match(/^(\d+)\s*-\s*(\d+)$/);
      if (!range) return [trimmed];
      const start = Number(range[1]);
      const end = Number(range[2]);
      const min = Math.min(start, end);
      const max = Math.max(start, end);
      return Array.from({ length: max - min + 1 }, (_, index) => String(min + index));
    })
    .filter(Boolean);
}

function unique(values) {
  return [...new Set(values.map((value) => String(value).trim()).filter(Boolean))];
}

function statusClass(status) {
  return status.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replaceAll(" ", "-");
}

async function fileToPhotoData(file) {
  if (file.size > MAX_PHOTO_FILE_BYTES) {
    throw new Error("Fotka je větší než 20 MB. Vyfoťte ji prosím znovu v menší velikosti nebo vyberte menší soubor.");
  }

  const source = await readFile(file);
  const image = await loadImage(source);
  const maxSide = 1400;
  const scale = Math.min(1, maxSide / Math.max(image.width, image.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(image.width * scale);
  canvas.height = Math.round(image.height * scale);
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Canvas is not available");
  context.drawImage(image, 0, 0, canvas.width, canvas.height);
  const blob = await canvasToBlob(canvas, "image/jpeg", 0.72);

  if (SERVER_MODE && syncBaseUrl !== null && currentUser && csrfToken) {
    const uploaded = await uploadPhoto(blob);
    return {
      thumb: uploaded.src,
      full: uploaded.fullSrc || uploaded.src
    };
  }

  const compressed = await blobToDataUrl(blob);
  return {
    thumb: compressed,
    full: compressed
  };
}

function canvasToBlob(canvas, type, quality) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error("Fotku se nepodařilo zkomprimovat."));
    }, type, quality);
  });
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

async function uploadPhoto(blob) {
  const response = await fetch(`${syncBaseUrl}/api/photos`, {
    method: "POST",
    headers: {
      "Content-Type": blob.type || "image/jpeg",
      "X-CSRF-Token": csrfToken || ""
    },
    credentials: "include",
    body: blob
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(result.error || "Fotku se nepodařilo nahrát na server.");
  return result;
}

function resolveMediaUrl(value) {
  if (!value || typeof value !== "string") return "";
  if (value.startsWith("/api/") && syncBaseUrl) return `${syncBaseUrl}${value}`;
  return value;
}

function readFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = src;
  });
}

function secondsBetween(start, end) {
  return Math.max(0, Math.round((new Date(end) - new Date(start)) / 1000));
}

function cleaningSecondsSoFar(assignment) {
  if (!assignment.startedAt) return 0;
  const end = assignment.status === "Pozastaveno" && assignment.pauseStartedAt ? assignment.pauseStartedAt : now();
  return Math.max(0, secondsBetween(assignment.startedAt, end) - (assignment.pausedSeconds || 0));
}

function cleaningDurationAtFinish(assignment, finishedAt) {
  const pausedSeconds = (assignment.pausedSeconds || 0)
    + (assignment.status === "Pozastaveno" && assignment.pauseStartedAt ? secondsBetween(assignment.pauseStartedAt, finishedAt) : 0);
  return Math.max(0, secondsBetween(assignment.startedAt, finishedAt) - pausedSeconds);
}

function formatDuration(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes} min ${String(seconds).padStart(2, "0")} s`;
}

function historyDateKey(value) {
  const date = new Date(value);
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0")
  ].join("-");
}

function formatDateOnly(value) {
  return new Intl.DateTimeFormat("cs-CZ", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  }).format(new Date(value));
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat("cs-CZ", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  }).format(new Date(value));
}

function formatMonthLabel(value) {
  const [year, month] = String(value || "").split("-");
  if (!year || !month) return value || "";
  return new Intl.DateTimeFormat("cs-CZ", { month: "long", year: "numeric" }).format(new Date(Number(year), Number(month) - 1, 1));
}

function toDateTimeLocal(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function fromDateTimeLocal(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "" : date.toISOString();
}

function roleLabel(role) {
  return { admin: "Admin", reception: "Recepční", housekeeping: "Pokojská" }[role] || role;
}

function normalizeColorScheme(value) {
  return value === "dark" ? "dark" : "light";
}

function getUserColorScheme(user) {
  return normalizeColorScheme(user?.colorScheme);
}

function applyColorScheme(value) {
  document.body.dataset.theme = normalizeColorScheme(value);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[char]);
}

function createId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  const random = globalThis.crypto?.getRandomValues
    ? Array.from(globalThis.crypto.getRandomValues(new Uint32Array(4)), (value) => value.toString(16).padStart(8, "0")).join("")
    : Math.random().toString(16).slice(2) + Math.random().toString(16).slice(2);
  return `id-${Date.now().toString(36)}-${random}`;
}

function now() {
  return new Date().toISOString();
}

function saveState() {
  saveStateToBrowserCache();
  pushStateToServer();
}

async function connectLiveServer() {
  if (!SERVER_MODE) return;

  stopLiveSync();
  syncBaseUrl = await findSyncServer();
  if (syncBaseUrl === null) {
    renderSyncStatus();
    return;
  }

  if (!currentUser) {
    renderSyncStatus();
    return;
  }

  await hydrateFromServer();
  if (!serverHydrated) {
    renderSyncStatus();
    startSyncPolling();
    return;
  }

  syncEvents = new EventSource(`${syncBaseUrl}/events`, { withCredentials: true });
  syncEvents.addEventListener("message", async () => {
    await hydrateFromServer();
  });
  syncEvents.onerror = () => {
    serverHydrated = false;
    renderSyncStatus();
    document.querySelector("#currentUserLabel").textContent = currentUser
      ? `${currentUser.username} (${roleLabel(currentUser.role)}) - spojení se obnovuje`
      : "";
  };

  startSyncPolling();
}

function stopLiveSync() {
  if (syncEvents) {
    syncEvents.close();
    syncEvents = null;
  }
  clearInterval(syncPollTimer);
  syncPollTimer = null;
}

async function hydrateFromServer(force = false) {
  if (syncBaseUrl === null) return;
  if (shouldDeferHydrate(force)) {
    pendingHydrate = true;
    return;
  }

  try {
    const uiSnapshot = captureTransientUiState();
    const headers = stateEtag ? { "If-None-Match": stateEtag } : {};
    const response = await fetch(`${syncBaseUrl}/api/state`, { cache: "no-store", credentials: "include", headers });
    if (response.status === 401) {
      currentUser = null;
      csrfToken = null;
      renderShell();
      return;
    }
    if (response.status === 304) {
      serverHydrated = true;
      renderSyncStatus();
      return;
    }
    if (!response.ok) return;
    stateEtag = response.headers.get("ETag") || stateEtag;
    const serverState = normalizeState(await response.json());
    const serverStateJson = sharedStateJson(serverState);
    if (serverHydrated && serverStateJson === lastSharedStateJson) {
      serverHydrated = true;
      renderSyncStatus();
      return;
    }

    Object.assign(state, serverState);
    state.sessionUserId = currentUser?.id || null;
    currentUser = state.sessionUserId ? state.users.find((user) => user.id === state.sessionUserId) || currentUser : null;
    applyColorScheme(getUserColorScheme(currentUser));
    saveStateToBrowserCache();
    serverHydrated = true;
    lastSharedStateJson = serverStateJson;
    renderSyncStatus();
    renderShell();
    restoreTransientUiState(uiSnapshot);
  } catch {
    serverHydrated = false;
    renderSyncStatus();
  }
}

function shouldDeferHydrate(force) {
  if (localSaveInProgress && !force) return true;
  return hasPendingFileInput();
}

function hasPendingFileInput() {
  return [...document.querySelectorAll("input[type='file']")].some((input) => input.files?.length);
}

function captureTransientUiState() {
  return {
    activeView: document.querySelector(".view.active")?.id || "",
    focusedAssignmentId,
    activeElementId: document.activeElement?.id || "",
    assignment: captureAssignmentFormState(),
    additionalWorkText: document.querySelector("#additionalWorkText")?.value || "",
    revisionLocation: document.querySelector("#revisionLocation")?.value || "",
    revisionText: document.querySelector("#revisionText")?.value || "",
    colorScheme: document.querySelector("#colorScheme")?.value || ""
  };
}

function captureAssignmentFormState() {
  const form = document.querySelector("#assignmentForm");
  if (!form) return null;
  return {
    id: document.querySelector("#assignmentId")?.value || "",
    title: document.querySelector("#assignmentFormTitle")?.textContent || "Zadat úklid",
    submit: document.querySelector("#assignmentSubmit")?.textContent || "Přidat do denního seznamu",
    cancelHidden: document.querySelector("#cancelAssignmentEdit")?.classList.contains("hidden") ?? true,
    rooms: checkedValues("#assignmentRooms"),
    photoTasks: checkedValues("#requiredPhotoChecks"),
    workType: document.querySelector("#workType")?.value || "",
    priority: document.querySelector("#priority")?.value || "",
    customPhotoTask: document.querySelector("#customPhotoTask")?.value || "",
    note: document.querySelector("#note")?.value || ""
  };
}

function checkedValues(selector) {
  return [...document.querySelectorAll(`${selector} input:checked`)].map((input) => input.value);
}

function restoreTransientUiState(snapshot) {
  if (!snapshot) return;
  focusedAssignmentId = snapshot.focusedAssignmentId || focusedAssignmentId;
  restoreAssignmentFormState(snapshot.assignment);
  restoreInputValue("#additionalWorkText", snapshot.additionalWorkText);
  restoreInputValue("#revisionLocation", snapshot.revisionLocation);
  restoreInputValue("#revisionText", snapshot.revisionText);
  restoreInputValue("#colorScheme", snapshot.colorScheme);
  restoreFocus(snapshot.activeElementId);
}

function restoreAssignmentFormState(snapshot) {
  if (!snapshot) return;
  restoreInputValue("#assignmentId", snapshot.id);
  restoreInputValue("#workType", snapshot.workType);
  restoreInputValue("#priority", snapshot.priority);
  restoreInputValue("#customPhotoTask", snapshot.customPhotoTask);
  restoreInputValue("#note", snapshot.note);
  setText("#assignmentFormTitle", snapshot.title);
  setText("#assignmentSubmit", snapshot.submit);
  document.querySelector("#cancelAssignmentEdit")?.classList.toggle("hidden", snapshot.cancelHidden);
  setCheckedValues("#assignmentRooms", snapshot.rooms);
  setCheckedValues("#requiredPhotoChecks", snapshot.photoTasks);
}

function restoreInputValue(selector, value) {
  const input = document.querySelector(selector);
  if (input && value !== undefined) input.value = value;
}

function setText(selector, value) {
  const element = document.querySelector(selector);
  if (element) element.textContent = value;
}

function restoreFocus(id) {
  if (!id) return;
  const escaped = globalThis.CSS?.escape ? CSS.escape(id) : id.replace(/[^a-zA-Z0-9_-]/g, "");
  const element = document.querySelector(`#${escaped}`);
  if (element && typeof element.focus === "function") element.focus({ preventScroll: true });
}

function pushStateToServer() {
  if (!SERVER_MODE || syncBaseUrl === null || !currentUser) {
    localSaveInProgress = false;
    return;
  }
  localSaveInProgress = true;
  clearTimeout(pushTimer);
  pushTimer = setTimeout(async () => {
    const sharedState = JSON.parse(JSON.stringify(state));
    sharedState.sessionUserId = null;
    const body = JSON.stringify(sharedState);
    try {
      const response = await fetch(`${syncBaseUrl}/api/state`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken || "" },
        credentials: "include",
        body
      });
      if (response.status === 401 || response.status === 403) {
        currentUser = null;
        csrfToken = null;
        renderShell();
        throw new Error("Session expired");
      }
      if (!response.ok) throw new Error("State save failed");
      stateEtag = response.headers.get("ETag") || "";
      serverHydrated = true;
      lastSharedStateJson = sharedStateJson(sharedState);
      renderSyncStatus();
    } catch {
      serverHydrated = false;
      renderSyncStatus();
    } finally {
      localSaveInProgress = false;
      if (pendingHydrate) {
        pendingHydrate = false;
        await hydrateFromServer(true);
      }
    }
  }, 120);
}

async function findSyncServer() {
  for (const baseUrl of syncServerCandidates()) {
    try {
      const response = await fetch(`${baseUrl}/api/session`, { cache: "no-store", credentials: "include" });
      if (!response.ok) continue;
      const session = await response.clone().json();
      currentUser = session.user || currentUser;
      csrfToken = session.csrfToken || csrfToken;
      state.sessionUserId = currentUser?.id || null;
      return baseUrl;
    } catch {
      // Live Server usually needs the shared backend on port 4173.
    }
  }
  return null;
}

function syncServerCandidates() {
  const candidates = [""];
  const explicitUrl = new URLSearchParams(location.search).get("sync");
  if (explicitUrl) {
    try {
      const url = new URL(explicitUrl);
      const localHosts = [location.hostname, "127.0.0.1", "localhost"];
      if (localHosts.includes(url.hostname) || /^10\.|^192\.168\.|^172\.(1[6-9]|2\d|3[0-1])\./.test(url.hostname)) {
        candidates.push(explicitUrl.replace(/\/$/, ""));
      }
    } catch {
      // Ignore malformed sync URLs.
    }
  }

  if (location.hostname && location.port !== SYNC_SERVER_PORT) {
    candidates.push(`${location.protocol}//${location.hostname}:${SYNC_SERVER_PORT}`);
  }

  return [...new Set(candidates)];
}

function renderSyncStatus() {
  const status = document.querySelector("#syncStatus");
  if (!status) return;

  const online = SERVER_MODE && serverHydrated && syncBaseUrl !== null;
  status.classList.toggle("online", online);
  status.classList.toggle("offline", !online);
  status.textContent = online
    ? "Synchronizace zapnutá"
    : "Ukládá se jen na tomto zařízení";
}

function sharedStateJson(value) {
  const sharedState = JSON.parse(JSON.stringify(value));
  sharedState.sessionUserId = null;
  return JSON.stringify(sharedState);
}

function saveStateToBrowserCache() {
  try {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(browserCacheState()));
  } catch {
    if (!SERVER_MODE) {
      alert("Data jsou příliš velká pro úložiště prohlížeče. Pokud používáte fotky, spusťte aplikaci přes server.");
    }
  }
}

function browserCacheState() {
  if (!SERVER_MODE) return state;

  const copy = JSON.parse(JSON.stringify(state));
  copy.users = (copy.users || []).map((user) => ({ id: user.id, username: user.username, role: user.role }));
  copy.assignments = (copy.assignments || []).map(stripPhotoData);
  copy.history = (copy.history || []).map(stripPhotoData);
  copy.revisionTasks = (copy.revisionTasks || []).map(stripPhotoData);
  copy.laundryTasks = (copy.laundryTasks || []).map(stripPhotoData);
  copy.sessionUserId = null;
  return copy;
}

function stripPhotoData(assignment) {
  return {
    ...assignment,
    photos: (assignment.photos || []).map((photo) => ({
      ...photo,
      src: "",
      fullSrc: ""
    }))
  };
}

function startSyncPolling() {
  clearInterval(syncPollTimer);
  syncPollTimer = setInterval(() => {
    hydrateFromServer();
  }, SYNC_POLL_MS);
}

function warnWhenSavingWithoutSync() {
  if (!SERVER_MODE || serverHydrated || syncWarningShown) return;
  syncWarningShown = true;
  alert("Synchronizační server není připojený. Změna se uloží jen na tomto zařízení. Pro sdílení mezi zařízeními spusťte také: node server.js");
}

function loadState() {
  const fallback = {
    users: [{ id: "admin", username: "admin", password: "061004", role: "admin" }],
    hotelRooms: ["101", "102", "103", "201", "202", "203"],
    minibarItems: DEFAULT_MINIBAR_ITEMS,
    photoTasks: DEFAULT_PHOTO_TASKS,
    assignments: [],
    minibars: [],
    history: [],
    revisionTasks: [],
    laundryTasks: [],
    sessionUserId: null
  };

  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (stored) return normalizeState(stored);

    const old = JSON.parse(localStorage.getItem(OLD_STORAGE_KEY));
    if (old) {
      fallback.assignments = (old.rooms || []).map((room) => ({
        id: room.id || createId(),
        roomNumber: room.number,
        workType: normalizeTextValue(room.workType || "Jiné úkoly"),
        priority: normalizeTextValue(room.priority || "Normální"),
        note: room.note || "",
        status: room.status === "Hotovo" ? "Hotovo" : "Čeká",
        requiredPhotos: DEFAULT_PHOTO_TASKS.slice(0, 2),
        photos: (room.photos || []).map((photo, index) => ({ ...photo, id: createId(), task: DEFAULT_PHOTO_TASKS[index] || "Kontrola" })),
        createdAt: room.createdAt || now(),
        updatedAt: room.updatedAt || now(),
        startedAt: null,
        finishedAt: null,
        durationSeconds: null,
        pausedSeconds: 0,
        pauseStartedAt: null,
        housekeeperId: null,
        housekeeperName: "",
        housekeeperNote: room.housekeeperNote || "",
        extraTasks: [],
        archived: Boolean(room.archived)
      }));
      fallback.minibars = old.minibars || [];
    }
  } catch {
    return fallback;
  }

  return normalizeState(fallback);
}

function normalizeState(value) {
  return {
    users: (value.users?.length ? value.users : [{ id: "admin", username: "admin", password: "061004", role: "admin" }]).map(normalizeUser),
    hotelRooms: value.hotelRooms?.length ? value.hotelRooms : ["101", "102", "103", "201", "202", "203"],
    minibarItems: normalizeTextList(value.minibarItems?.length ? value.minibarItems : DEFAULT_MINIBAR_ITEMS),
    photoTasks: normalizeTextList(value.photoTasks?.length ? value.photoTasks : DEFAULT_PHOTO_TASKS),
    assignments: (value.assignments || []).map(normalizeAssignment),
    minibars: dedupeMinibars(value.minibars || []),
    history: (value.history || []).map(normalizeHistoryRecord),
    revisionTasks: (value.revisionTasks || []).map(normalizeRevisionTask),
    laundryTasks: (value.laundryTasks || []).map(normalizeLaundryTask),
    sessionUserId: value.sessionUserId || null
  };
}

function normalizeHistoryRecord(record) {
  if (record?.type === "additionalWork") return normalizeAdditionalWorkRecord(record);
  if (record?.type === "laundry") return normalizeLaundryHistoryRecord(record);
  return normalizeAssignment(record || {});
}

function normalizeAdditionalWorkRecord(record) {
  return {
    ...record,
    type: "additionalWork",
    id: record.id || createId(),
    historyId: record.historyId || createId(),
    text: normalizeTextValue(record.text || ""),
    createdAt: record.createdAt || record.finishedAt || record.savedAt || now(),
    finishedAt: record.finishedAt || record.savedAt || record.createdAt || now(),
    savedAt: record.savedAt || record.finishedAt || record.createdAt || now(),
    housekeeperId: record.housekeeperId || null,
    housekeeperName: record.housekeeperName || ""
  };
}

function normalizeLaundryHistoryRecord(record) {
  return {
    ...record,
    type: "laundry",
    id: record.id || createId(),
    historyId: record.historyId || createId(),
    status: normalizeStatus(record.status || "Hotovo"),
    createdAt: record.createdAt || record.finishedAt || record.savedAt || now(),
    acceptedAt: record.acceptedAt || null,
    finishedAt: record.finishedAt || record.completedAt || record.savedAt || record.createdAt || now(),
    completedAt: record.completedAt || record.finishedAt || record.savedAt || record.createdAt || now(),
    savedAt: record.savedAt || record.finishedAt || record.completedAt || record.createdAt || now(),
    housekeeperId: record.housekeeperId || record.acceptedById || null,
    housekeeperName: record.housekeeperName || record.acceptedByName || "",
    photos: (record.photos || []).map((photo) => ({ ...photo, fullSrc: photo.fullSrc || photo.src }))
  };
}

function normalizeUser(user) {
  return {
    ...user,
    id: user.id || createId(),
    username: normalizeTextValue(user.username || ""),
    role: ["admin", "reception", "housekeeping"].includes(user.role) ? user.role : "housekeeping",
    colorScheme: normalizeColorScheme(user.colorScheme)
  };
}

function normalizeRevisionTask(task) {
  return {
    id: task.id || createId(),
    location: normalizeTextValue(task.location || ""),
    text: normalizeTextValue(task.text || ""),
    status: task.status === "done" ? "done" : "open",
    createdAt: task.createdAt || now(),
    completedAt: task.completedAt || null,
    completedById: task.completedById || null,
    completedByName: task.completedByName || "",
    note: task.note || "",
    photos: (task.photos || []).map((photo) => ({ ...photo, fullSrc: photo.fullSrc || photo.src }))
  };
}

function normalizeLaundryTask(task) {
  const status = ["open", "accepted", "done", "cancelled"].includes(task.status) ? task.status : "open";
  return {
    id: task.id || createId(),
    status,
    createdAt: task.createdAt || now(),
    acceptedAt: task.acceptedAt || null,
    acceptedById: task.acceptedById || null,
    acceptedByName: task.acceptedByName || "",
    completedAt: task.completedAt || null,
    cancelledAt: task.cancelledAt || null,
    photos: (task.photos || []).map((photo) => ({ ...photo, fullSrc: photo.fullSrc || photo.src }))
  };
}

function normalizeAssignment(assignment) {
  return {
    ...assignment,
    workType: normalizeTextValue(assignment.workType || "Jiné úkoly"),
    priority: normalizeTextValue(assignment.priority || "Normální"),
    status: normalizeStatus(assignment.status),
    requiredPhotos: normalizeTextList(assignment.requiredPhotos || []),
    photos: (assignment.photos || []).map((photo) => ({ ...photo, fullSrc: photo.fullSrc || photo.src })),
    extraTasks: (assignment.extraTasks || []).map((task) => ({ ...task, source: normalizeTextValue(task.source || "") })),
    housekeeperId: assignment.housekeeperId || null,
    housekeeperName: assignment.housekeeperName || "",
    pausedSeconds: assignment.pausedSeconds || 0,
    pauseStartedAt: assignment.pauseStartedAt || null
  };
}

function normalizeTextList(values) {
  return values.map(normalizeTextValue);
}

function normalizeStatus(status) {
  return normalizeTextValue(status || "Čeká");
}

function normalizeTextValue(value) {
  const map = {
    Ceka: "Čeká",
    "Uklizi se": "Uklízí se",
    Zkontrolovano: "Zkontrolováno",
    Pokojska: "Pokojská",
    Recepcni: "Recepční",
    Vino: "Víno",
    Cokolada: "Čokoláda",
    Orisky: "Oříšky",
    Jine: "Jiné",
    "Jine ukoly": "Jiné úkoly",
    "Jiné ukoly": "Jiné úkoly",
    Normalni: "Normální"
  };
  return map[value] || value;
}

function dedupeMinibars(items) {
  const map = new Map();
  items.forEach((item) => {
    const key = `${item.assignmentId || ""}::${item.item}`;
    map.set(key, item);
  });
  return [...map.values()];
}

renderShell();
connectLiveServer();
