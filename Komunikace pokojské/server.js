const http = require("http");
const fs = require("fs");
const path = require("path");
const os = require("os");
const crypto = require("crypto");

const root = __dirname;
const dataFile = path.join(root, "data.json");
const photoDir = path.join(root, "photos");
const port = Number(process.env.PORT) || 4173;
const host = "0.0.0.0";
const maxBodyBytes = Number(process.env.MAX_BODY_BYTES) || 35 * 1024 * 1024;
const maxPhotoBytes = Number(process.env.MAX_PHOTO_BYTES) || 6 * 1024 * 1024;
const sessionTtlMs = 12 * 60 * 60 * 1000;
const clients = new Set();
const sessions = new Map();
const loginAttempts = new Map();

const types = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml; charset=utf-8"
};

const defaultState = {
  users: [{ id: "admin", username: "admin", password: "061004", role: "admin" }],
  hotelRooms: ["101", "102", "103", "201", "202", "203"],
  minibarItems: ["Voda", "Cola", "Pivo", "Víno", "Čokoláda", "Oříšky", "Chipsy", "Jiné"],
  photoTasks: ["Postel", "Koupelna", "Podlaha", "Minibar"],
  assignments: [],
  minibars: [],
  history: [],
  revisionTasks: [],
  laundryTasks: [],
  sessionUserId: null
};

ensureDataFile();

const server = http.createServer((request, response) => {
  if (request.method === "OPTIONS") {
    response.writeHead(204, corsHeaders(request));
    response.end();
    return;
  }

  if (request.url === "/api/session" && request.method === "GET") {
    const session = getSession(request);
    const state = readState();
    const user = session ? state.users.find((item) => item.id === session.userId) : null;
    sendJson(request, response, { user: safeUser(user), csrfToken: session?.csrfToken || null });
    return;
  }

  if (request.url === "/api/login" && request.method === "POST") {
    handleLogin(request, response);
    return;
  }

  if (request.url === "/api/logout" && request.method === "POST") {
    const session = requireSession(request, response, { csrf: true });
    if (!session) return;
    sessions.delete(session.id);
    sendJson(request, response, { ok: true }, 200, clearSessionCookie());
    return;
  }

  if (request.url === "/api/state" && request.method === "GET") {
    const session = requireSession(request, response);
    if (!session) return;
    sendState(request, response, safeStateForClient(readState()));
    return;
  }

  if (request.url === "/api/photos" && request.method === "POST") {
    const session = requireSession(request, response, { csrf: true });
    if (!session) return;
    readBinaryBody(request, maxPhotoBytes, (error, buffer) => {
      if (error) {
        sendJson(request, response, { error: "Invalid photo upload" }, error.status || 400);
        return;
      }

      try {
        const contentType = String(request.headers["content-type"] || "");
        const saved = savePhotoBuffer(buffer, contentType);
        sendJson(request, response, { ok: true, src: saved.url, fullSrc: saved.url, bytes: saved.bytes });
      } catch (error) {
        sendJson(request, response, { error: error.message || "Invalid photo" }, 400);
      }
    });
    return;
  }

  if (request.url.startsWith("/api/photos/") && request.method === "GET") {
    const session = requireSession(request, response);
    if (!session) return;
    servePhoto(request, response);
    return;
  }

  if (request.url === "/api/state" && request.method === "POST") {
    const session = requireSession(request, response, { csrf: true });
    if (!session) return;
    readBody(request, (error, body) => {
      if (error) {
        sendJson(request, response, { error: "Invalid request" }, error.status || 400);
        return;
      }

      try {
        const currentState = readState();
        const currentUser = currentState.users.find((item) => item.id === session.userId);
        if (!currentUser) {
          sendJson(request, response, { error: "Unauthorized" }, 401, clearSessionCookie());
          return;
        }

        const incomingState = JSON.parse(body);
        const state = mergeStateForRole(currentState, incomingState, currentUser);
        writeState(state);
        broadcast({ type: "state-updated", updatedAt: new Date().toISOString() });
        sendJson(request, response, { ok: true });
      } catch (error) {
        sendJson(request, response, { error: error.message || "Invalid JSON" }, 400);
      }
    });
    return;
  }

  if (request.url === "/events" && request.method === "GET") {
    const session = requireSession(request, response);
    if (!session) return;
    response.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-store",
      Connection: "keep-alive",
      ...securityHeaders(),
      ...corsHeaders(request)
    });
    response.write(`retry: 2000\nevent: ready\ndata: ${JSON.stringify({ ok: true })}\n\n`);
    clients.add(response);
    const heartbeat = setInterval(() => {
      response.write(`event: ping\ndata: ${JSON.stringify({ at: new Date().toISOString() })}\n\n`);
    }, 15000);
    request.on("close", () => {
      clearInterval(heartbeat);
      clients.delete(response);
    });
    return;
  }

  serveStatic(request, response);
});

server.listen(port, host, () => {
  const localIps = getLocalIps();
  console.log(`Aplikace běží na http://127.0.0.1:${port}`);
  localIps.forEach((ip) => console.log(`Pro ostatní zařízení ve stejné síti: http://${ip}:${port}`));
});

function handleLogin(request, response) {
  const ip = request.socket.remoteAddress || "unknown";
  if (isRateLimited(ip)) {
    sendJson(request, response, { error: "Too many login attempts" }, 429);
    return;
  }

  readBody(request, (error, body) => {
    if (error) {
      sendJson(request, response, { error: "Invalid request" }, error.status || 400);
      return;
    }

    try {
      const { username, password } = JSON.parse(body);
      const state = readState();
      const user = state.users.find((item) => item.username === String(username || "").trim());
      if (!user || !verifyPassword(password || "", user.passwordHash)) {
        registerFailedLogin(ip);
        sendJson(request, response, { error: "Invalid credentials" }, 401);
        return;
      }

      loginAttempts.delete(ip);
      const session = createSession(user.id);
      sendJson(request, response, {
        ok: true,
        user: safeUser(user),
        csrfToken: session.csrfToken
      }, 200, sessionCookie(session.id));
    } catch {
      sendJson(request, response, { error: "Invalid JSON" }, 400);
    }
  });
}

function serveStatic(request, response) {
  if (request.method !== "GET" && request.method !== "HEAD") {
    response.writeHead(405, { Allow: "GET, HEAD", ...securityHeaders() });
    response.end("Method not allowed");
    return;
  }

  let requestedPath;
  try {
    requestedPath = decodeURIComponent(request.url.split("?")[0]);
  } catch {
    response.writeHead(400, securityHeaders());
    response.end("Bad request");
    return;
  }

  const cleanPath = requestedPath === "/" ? "index.html" : requestedPath.replace(/^\/+/, "");
  const filePath = path.normalize(path.join(root, cleanPath));
  const rootPath = root.endsWith(path.sep) ? root : `${root}${path.sep}`;
  const photoPath = photoDir.endsWith(path.sep) ? photoDir : `${photoDir}${path.sep}`;
  const basename = path.basename(filePath);

  if (
    (!filePath.startsWith(rootPath) && filePath !== root)
    || filePath === photoDir
    || filePath.startsWith(photoPath)
    || basename === "data.json"
    || basename.startsWith(".")
  ) {
    response.writeHead(403, securityHeaders());
    response.end("Forbidden");
    return;
  }

  fs.readFile(filePath, (error, data) => {
    if (error) {
      response.writeHead(404, securityHeaders());
      response.end("Not found");
      return;
    }

    const cacheControl = filePath.endsWith("index.html") ? "no-store" : "public, max-age=300";
    response.writeHead(200, {
      "Content-Type": types[path.extname(filePath)] || "application/octet-stream",
      "Cache-Control": cacheControl,
      ...securityHeaders()
    });
    if (request.method === "HEAD") {
      response.end();
      return;
    }
    response.end(data);
  });
}

function sendJson(request, response, data, status = 200, extraHeaders = {}) {
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    ...securityHeaders(),
    ...corsHeaders(request),
    ...extraHeaders
  });
  response.end(JSON.stringify(data));
}

function sendState(request, response, data) {
  const body = JSON.stringify(data);
  const etag = makeEtag(body);
  if (request.headers["if-none-match"] === etag) {
    response.writeHead(304, {
      ETag: etag,
      "Cache-Control": "no-store",
      ...securityHeaders(),
      ...corsHeaders(request)
    });
    response.end();
    return;
  }

  response.writeHead(200, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    ETag: etag,
    ...securityHeaders(),
    ...corsHeaders(request)
  });
  response.end(body);
}

function corsHeaders(request) {
  const origin = request.headers.origin;
  const allowedOrigin = origin && isAllowedOrigin(origin) ? origin : "";
  return {
    ...(allowedOrigin ? { "Access-Control-Allow-Origin": allowedOrigin, Vary: "Origin" } : {}),
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, X-CSRF-Token"
  };
}

function isAllowedOrigin(origin) {
  try {
    const url = new URL(origin);
    return ["127.0.0.1", "localhost"].includes(url.hostname) || getLocalIps().includes(url.hostname);
  } catch {
    return false;
  }
}

function securityHeaders() {
  return {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "Permissions-Policy": "camera=(self), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; connect-src 'self' http://127.0.0.1:* http://localhost:* http://192.168.0.0/16 http://10.0.0.0/8 http://172.16.0.0/12; object-src 'none'; base-uri 'self'; form-action 'self'"
  };
}

function readBody(request, callback) {
  let body = "";
  let done = false;
  request.on("data", (chunk) => {
    body += chunk;
    if (body.length > maxBodyBytes && !done) {
      done = true;
      callback({ status: 413, message: "Request body too large" });
      request.destroy();
    }
  });
  request.on("end", () => {
    if (!done) callback(null, body);
  });
  request.on("error", (error) => {
    if (!done) callback(error);
  });
}

function readBinaryBody(request, limit, callback) {
  const chunks = [];
  let size = 0;
  let done = false;
  request.on("data", (chunk) => {
    size += chunk.length;
    if (size > limit && !done) {
      done = true;
      callback({ status: 413, message: "Request body too large" });
      request.destroy();
      return;
    }
    chunks.push(chunk);
  });
  request.on("end", () => {
    if (!done) callback(null, Buffer.concat(chunks));
  });
  request.on("error", (error) => {
    if (!done) callback(error);
  });
}

function broadcast(message) {
  const payload = `event: message\ndata: ${JSON.stringify(message)}\n\n`;
  clients.forEach((client) => {
    try {
      client.write(payload);
    } catch {
      clients.delete(client);
    }
  });
}

function ensureDataFile() {
  fs.mkdirSync(photoDir, { recursive: true, mode: 0o700 });
  if (!fs.existsSync(dataFile)) {
    writeState(defaultState);
    return;
  }
  writeState(readState());
}

function readState() {
  try {
    return normalizeState(JSON.parse(fs.readFileSync(dataFile, "utf8")));
  } catch {
    try {
      fs.copyFileSync(dataFile, path.join(root, `data.corrupt-${Date.now()}.json`));
    } catch {
      // If the broken file cannot be backed up, keep the server available with defaults.
    }
    const recovered = normalizeState(defaultState);
    writeState(recovered);
    return recovered;
  }
}

function writeState(state) {
  const normalized = normalizeState(state);
  const tempFile = path.join(root, `.data.${process.pid}.${Date.now()}.tmp`);
  const fd = fs.openSync(tempFile, "w", 0o600);
  try {
    fs.writeFileSync(fd, JSON.stringify(normalized, null, 2), "utf8");
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
  fs.renameSync(tempFile, dataFile);
}

function normalizeState(value) {
  const fallbackUsers = defaultState.users.map(normalizeUser);
  return {
    users: Array.isArray(value.users) && value.users.length ? value.users.map(normalizeUser) : fallbackUsers,
    hotelRooms: normalizeTextList(value.hotelRooms?.length ? value.hotelRooms : defaultState.hotelRooms),
    minibarItems: normalizeTextList(value.minibarItems?.length ? value.minibarItems : defaultState.minibarItems),
    photoTasks: normalizeTextList(value.photoTasks?.length ? value.photoTasks : defaultState.photoTasks),
    assignments: Array.isArray(value.assignments) ? value.assignments.map(normalizeAssignmentStorage) : [],
    minibars: Array.isArray(value.minibars) ? value.minibars : [],
    history: Array.isArray(value.history) ? value.history.map(normalizeAssignmentStorage) : [],
    revisionTasks: Array.isArray(value.revisionTasks) ? value.revisionTasks.map(normalizeRevisionTaskStorage) : [],
    laundryTasks: Array.isArray(value.laundryTasks) ? value.laundryTasks.map(normalizeLaundryTaskStorage) : [],
    sessionUserId: null
  };
}

function normalizeLaundryTaskStorage(task) {
  return {
    ...task,
    status: ["open", "accepted", "done", "cancelled"].includes(task.status) ? task.status : "open",
    photos: (task.photos || []).map(normalizePhotoStorage)
  };
}

function normalizeRevisionTaskStorage(task) {
  return {
    ...task,
    status: task.status === "done" ? "done" : "open",
    photos: (task.photos || []).map(normalizePhotoStorage)
  };
}

function normalizeAssignmentStorage(assignment) {
  return {
    ...assignment,
    photos: (assignment.photos || []).map(normalizePhotoStorage)
  };
}

function normalizePhotoStorage(photo) {
  const src = externalizePhotoValue(photo.src || photo.fullSrc);
  const fullSrc = externalizePhotoValue(photo.fullSrc || photo.src) || src;
  return {
    ...photo,
    src,
    fullSrc
  };
}

function externalizePhotoValue(value) {
  if (!value || typeof value !== "string") return "";
  if (!value.startsWith("data:image/")) return value;
  const saved = saveDataUrlPhoto(value);
  return saved.url;
}

function normalizeUser(user) {
  const id = normalizeText(user.id || crypto.randomUUID()).slice(0, 80);
  const username = normalizeText(user.username || "").slice(0, 80);
  const role = ["admin", "reception", "housekeeping"].includes(user.role) ? user.role : "housekeeping";
  const colorScheme = user.colorScheme === "dark" ? "dark" : "light";
  const passwordHash = user.passwordHash || hashPassword(String(user.password || crypto.randomBytes(18).toString("base64")));
  return { id, username, passwordHash, role, colorScheme };
}

function mergeStateForRole(currentState, incomingState, currentUser) {
  const normalizedIncoming = normalizeState(incomingState);
  if (currentUser.role === "admin") {
    return {
      ...normalizedIncoming,
      users: mergeUsers(currentState.users, incomingState.users)
    };
  }
  return {
    ...normalizedIncoming,
    users: mergeCurrentUserPreferences(currentState.users, incomingState.users, currentUser.id),
    hotelRooms: currentState.hotelRooms,
    minibarItems: currentState.minibarItems,
    photoTasks: currentState.photoTasks
  };
}

function mergeUsers(currentUsers, incomingUsers) {
  const currentById = new Map(currentUsers.map((user) => [user.id, user]));
  const seenUsernames = new Set();
  return (Array.isArray(incomingUsers) ? incomingUsers : currentUsers).map((incoming) => {
    const id = normalizeText(incoming.id || crypto.randomUUID()).slice(0, 80);
    const current = currentById.get(id);
    const username = normalizeText(incoming.username || current?.username || "").slice(0, 80);
    const usernameKey = username.toLowerCase();
    if (!username || seenUsernames.has(usernameKey)) throw new Error("Invalid user list");
    seenUsernames.add(usernameKey);

    const role = ["admin", "reception", "housekeeping"].includes(incoming.role) ? incoming.role : current?.role || "housekeeping";
    const colorScheme = incoming.colorScheme === "dark" || (!incoming.colorScheme && current?.colorScheme === "dark") ? "dark" : "light";
    const passwordHash = incoming.password
      ? hashPassword(String(incoming.password))
      : incoming.passwordHash || current?.passwordHash;
    if (!passwordHash) throw new Error("Missing password for user");
    return { id, username, role, passwordHash, colorScheme };
  });
}

function mergeCurrentUserPreferences(currentUsers, incomingUsers, currentUserId) {
  const incoming = Array.isArray(incomingUsers)
    ? incomingUsers.find((user) => user.id === currentUserId)
    : null;
  return currentUsers.map((user) => {
    if (user.id !== currentUserId) return user;
    const colorScheme = incoming?.colorScheme === "dark" || (!incoming?.colorScheme && user.colorScheme === "dark") ? "dark" : "light";
    return { ...user, colorScheme };
  });
}

function safeStateForClient(state) {
  return {
    ...state,
    users: state.users.map(safeUser),
    sessionUserId: null
  };
}

function saveDataUrlPhoto(value) {
  const match = value.match(/^data:(image\/(?:jpeg|jpg|png|webp));base64,([a-z0-9+/=\s]+)$/i);
  if (!match) throw new Error("Invalid photo data");
  return savePhotoBuffer(Buffer.from(match[2].replace(/\s/g, ""), "base64"), match[1]);
}

function savePhotoBuffer(buffer, contentType) {
  const type = normalizeImageType(contentType, buffer);
  if (!type) throw new Error("Unsupported photo type");
  if (!buffer.length || buffer.length > maxPhotoBytes) throw new Error("Photo is too large");

  const hash = crypto.createHash("sha256").update(buffer).digest("hex");
  const filename = `${hash}.${type.ext}`;
  const filePath = path.join(photoDir, filename);
  if (!fs.existsSync(filePath)) {
    const fd = fs.openSync(filePath, "w", 0o600);
    try {
      fs.writeFileSync(fd, buffer);
      fs.fsyncSync(fd);
    } finally {
      fs.closeSync(fd);
    }
  }

  return { filename, url: `/api/photos/${filename}`, bytes: buffer.length };
}

function normalizeImageType(contentType, buffer) {
  const type = String(contentType || "").split(";")[0].trim().toLowerCase();
  if (type === "image/jpeg" || type === "image/jpg") return { mime: "image/jpeg", ext: "jpg" };
  if (type === "image/png") return { mime: "image/png", ext: "png" };
  if (type === "image/webp") return { mime: "image/webp", ext: "webp" };
  if (buffer[0] === 0xff && buffer[1] === 0xd8) return { mime: "image/jpeg", ext: "jpg" };
  if (buffer.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) return { mime: "image/png", ext: "png" };
  if (buffer.subarray(0, 4).toString("ascii") === "RIFF" && buffer.subarray(8, 12).toString("ascii") === "WEBP") return { mime: "image/webp", ext: "webp" };
  return null;
}

function servePhoto(request, response) {
  const filename = path.basename(decodeURIComponent(request.url.split("?")[0].replace("/api/photos/", "")));
  if (!/^[a-f0-9]{64}\.(jpg|png|webp)$/.test(filename)) {
    sendJson(request, response, { error: "Not found" }, 404);
    return;
  }

  const filePath = path.join(photoDir, filename);
  fs.readFile(filePath, (error, data) => {
    if (error) {
      sendJson(request, response, { error: "Not found" }, 404);
      return;
    }
    const ext = path.extname(filename);
    response.writeHead(200, {
      "Content-Type": ext === ".png" ? "image/png" : ext === ".webp" ? "image/webp" : "image/jpeg",
      "Cache-Control": "private, max-age=86400",
      ...securityHeaders(),
      ...corsHeaders(request)
    });
    response.end(data);
  });
}

function safeUser(user) {
  if (!user) return null;
  return { id: user.id, username: user.username, role: user.role, colorScheme: user.colorScheme || "light" };
}

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString("base64url");
  const iterations = 210000;
  const hash = crypto.pbkdf2Sync(String(password), salt, iterations, 32, "sha256").toString("base64url");
  return `pbkdf2-sha256$${iterations}$${salt}$${hash}`;
}

function verifyPassword(password, stored) {
  if (!stored) return false;
  const [algorithm, iterations, salt, hash] = String(stored).split("$");
  if (algorithm !== "pbkdf2-sha256" || !iterations || !salt || !hash) return false;
  const candidate = crypto.pbkdf2Sync(String(password), salt, Number(iterations), 32, "sha256").toString("base64url");
  return timingSafeEqual(candidate, hash);
}

function timingSafeEqual(a, b) {
  const aBuffer = Buffer.from(String(a));
  const bBuffer = Buffer.from(String(b));
  return aBuffer.length === bBuffer.length && crypto.timingSafeEqual(aBuffer, bBuffer);
}

function createSession(userId) {
  const session = {
    id: crypto.randomBytes(32).toString("base64url"),
    csrfToken: crypto.randomBytes(24).toString("base64url"),
    userId,
    expiresAt: Date.now() + sessionTtlMs
  };
  sessions.set(session.id, session);
  cleanupSessions();
  return session;
}

function getSession(request) {
  const id = parseCookies(request.headers.cookie || "").hem_session;
  const session = id ? sessions.get(id) : null;
  if (!session || session.expiresAt < Date.now()) {
    if (id) sessions.delete(id);
    return null;
  }
  session.expiresAt = Date.now() + sessionTtlMs;
  return session;
}

function requireSession(request, response, options = {}) {
  const session = getSession(request);
  if (!session) {
    sendJson(request, response, { error: "Unauthorized" }, 401, clearSessionCookie());
    return null;
  }
  if (options.csrf && request.headers["x-csrf-token"] !== session.csrfToken) {
    sendJson(request, response, { error: "Invalid CSRF token" }, 403);
    return null;
  }
  return session;
}

function parseCookies(header) {
  return header.split(";").reduce((cookies, pair) => {
    const index = pair.indexOf("=");
    if (index === -1) return cookies;
    cookies[pair.slice(0, index).trim()] = decodeURIComponent(pair.slice(index + 1).trim());
    return cookies;
  }, {});
}

function sessionCookie(sessionId) {
  const secure = process.env.COOKIE_SECURE === "1" ? "; Secure" : "";
  return { "Set-Cookie": `hem_session=${encodeURIComponent(sessionId)}; HttpOnly; SameSite=Lax; Path=/; Max-Age=${Math.floor(sessionTtlMs / 1000)}${secure}` };
}

function clearSessionCookie() {
  return { "Set-Cookie": "hem_session=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0" };
}

function makeEtag(value) {
  return `"${crypto.createHash("sha256").update(value).digest("base64url")}"`;
}

function cleanupSessions() {
  const now = Date.now();
  sessions.forEach((session, id) => {
    if (session.expiresAt < now) sessions.delete(id);
  });
}

function isRateLimited(key) {
  const record = loginAttempts.get(key);
  return Boolean(record && record.count >= 8 && record.resetAt > Date.now());
}

function registerFailedLogin(key) {
  const now = Date.now();
  const record = loginAttempts.get(key);
  if (!record || record.resetAt < now) {
    loginAttempts.set(key, { count: 1, resetAt: now + 10 * 60 * 1000 });
    return;
  }
  record.count += 1;
}

function normalizeTextList(values) {
  return [...new Set((values || []).map(normalizeText).filter(Boolean))];
}

function normalizeText(value) {
  return String(value || "").trim();
}

function getLocalIps() {
  return Object.values(os.networkInterfaces())
    .flat()
    .filter((item) => item && item.family === "IPv4" && !item.internal)
    .map((item) => item.address);
}
