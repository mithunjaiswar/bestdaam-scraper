function authorizeGitHubWorkflow() {
  return triggerFastUpdate_();
}

const SHEET_NAME = "Product Requests";
const ANALYTICS_SHEET_NAME = "Site Analytics";
const HEADERS = [
  "id",
  "requested_at",
  "query",
  "label",
  "source",
  "status",
  "attempts",
  "result_url",
  "completed_at",
];
const ANALYTICS_HEADERS = [
  "recorded_at",
  "event_name",
  "source",
  "path",
  "product_id",
  "product_name",
  "category",
  "store",
  "query",
  "value",
];

function setupProductRequests() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = spreadsheet.getSheetByName(SHEET_NAME);

  if (!sheet) {
    sheet = spreadsheet.insertSheet(SHEET_NAME);
  }

  if (sheet.getLastRow() === 0) {
    sheet.appendRow(HEADERS);
    sheet.setFrozenRows(1);
    sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight("bold");
    sheet.autoResizeColumns(1, HEADERS.length);
  }

  setupAnalyticsSheet_(spreadsheet);

  const properties = PropertiesService.getScriptProperties();

  if (!properties.getProperty("QUEUE_TOKEN")) {
    properties.setProperty("QUEUE_TOKEN", Utilities.getUuid());
  }

  return {
    sheet: spreadsheet.getUrl(),
    queueToken: properties.getProperty("QUEUE_TOKEN"),
  };
}

function doGet(event) {
  const params = event && event.parameter ? event.parameter : {};

  if (params.action !== "list" || !isAuthorized_(params.token)) {
    return json_({ success: 0, error: "Unauthorized" });
  }

  const sheet = getSheet_();
  const rows = sheet.getDataRange().getValues();
  const requests = [];

  for (let index = 1; index < rows.length; index += 1) {
    const row = rows[index];

    if (String(row[5] || "").toLowerCase() !== "pending") {
      continue;
    }

    requests.push({
      id: String(row[0] || ""),
      requested_at: formatDate_(row[1]),
      query: String(row[2] || ""),
      label: String(row[3] || ""),
      source: String(row[4] || ""),
      attempts: Number(row[6] || 0),
    });
  }

  return json_({ success: 1, data: requests.slice(0, 50) });
}

function doPost(event) {
  const params = event && event.parameter ? event.parameter : {};
  const action = String(params.action || "submit");

  if (action === "submit") {
    return submitRequest_(params);
  }

  if (action === "track") {
    return trackEvent_(params);
  }

  if (action === "update" && isAuthorized_(params.token)) {
    return updateRequest_(params);
  }

  return json_({ success: 0, error: "Unsupported action" });
}

function trackEvent_(params) {
  const allowedEvents = [
    "page_view",
    "search",
    "select_product",
    "store_click",
    "share",
  ];
  const eventName = clean_(params.event_name).slice(0, 50);
  const honeypot = clean_(params.website);

  if (honeypot || allowedEvents.indexOf(eventName) === -1) {
    return json_({ success: 0, error: "Invalid event" });
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);

  try {
    const sheet = getAnalyticsSheet_();
    sheet.appendRow([
      new Date(),
      eventName,
      clean_(params.source).slice(0, 100) || "direct",
      clean_(params.path).slice(0, 500),
      clean_(params.product_id).slice(0, 200),
      clean_(params.product_name).slice(0, 300),
      clean_(params.category).slice(0, 100),
      clean_(params.store).slice(0, 100),
      clean_(params.query).slice(0, 500),
      Number(params.value || 0),
    ]);

    return json_({ success: 1 });
  } finally {
    lock.releaseLock();
  }
}

function submitRequest_(params) {
  const query = clean_(params.query).slice(0, 500);
  const label = clean_(params.label).slice(0, 200);
  const source = clean_(params.source).slice(0, 100);
  const honeypot = clean_(params.website);

  if (honeypot || query.length < 3) {
    return json_({ success: 0, error: "Invalid request" });
  }

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);

  try {
    const sheet = getSheet_();
    const rows = sheet.getDataRange().getValues();
    const normalized = normalize_(query);

    for (let index = 1; index < rows.length; index += 1) {
      const existingQuery = normalize_(rows[index][2]);
      const status = String(rows[index][5] || "").toLowerCase();

      if (existingQuery === normalized && status === "pending") {
        return json_({
          success: 1,
          duplicate: true,
          id: String(rows[index][0] || ""),
        });
      }
    }

    const id = Utilities.getUuid();
    sheet.appendRow([
      id,
      new Date(),
      query,
      label || query,
      source || "bestdaam.in",
      "Pending",
      0,
      "",
      "",
    ]);

    const fastUpdate = triggerFastUpdate_();

    return json_({
      success: 1,
      id: id,
      update_triggered: fastUpdate.success,
    });
  } finally {
    lock.releaseLock();
  }
}

function triggerFastUpdate_() {
  const properties = PropertiesService.getScriptProperties();
  const token = properties.getProperty("GITHUB_WORKFLOW_TOKEN");

  if (!token) {
    console.log("GITHUB_WORKFLOW_TOKEN missing; request remains queued.");
    return { success: false, error: "Token missing" };
  }

  const repository =
    properties.getProperty("GITHUB_REPOSITORY") ||
    "mithunjaiswar/bestdaam-price";
  const workflow =
    properties.getProperty("GITHUB_WORKFLOW_FILE") ||
    "instant-product-requests.yml";
  const ref =
    properties.getProperty("GITHUB_WORKFLOW_REF") ||
    "claude/india-price-comparison-zb7xou";
  const endpoint =
    "https://api.github.com/repos/" +
    repository +
    "/actions/workflows/" +
    workflow +
    "/dispatches";

  try {
    const response = UrlFetchApp.fetch(endpoint, {
      method: "post",
      contentType: "application/json",
      headers: {
        Authorization: "Bearer " + token,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      payload: JSON.stringify({ ref: ref }),
      muteHttpExceptions: true,
    });
    const status = response.getResponseCode();

    if (status === 204) {
      return { success: true };
    }

    console.log(
      "GitHub workflow trigger failed: " +
        status +
        " " +
        response.getContentText()
    );
    return { success: false, error: "GitHub status " + status };
  } catch (error) {
    console.log("GitHub workflow trigger failed: " + error);
    return { success: false, error: String(error) };
  }
}

function updateRequest_(params) {
  const id = clean_(params.id);
  const status = clean_(params.status) || "Pending";
  const resultUrl = clean_(params.result_url);
  const sheet = getSheet_();
  const rows = sheet.getDataRange().getValues();

  for (let index = 1; index < rows.length; index += 1) {
    if (String(rows[index][0] || "") !== id) {
      continue;
    }

    const rowNumber = index + 1;
    const attempts = Number(rows[index][6] || 0) + 1;

    sheet.getRange(rowNumber, 6).setValue(status);
    sheet.getRange(rowNumber, 7).setValue(attempts);
    sheet.getRange(rowNumber, 8).setValue(resultUrl);
    sheet
      .getRange(rowNumber, 9)
      .setValue(status === "Added" ? new Date() : "");

    return json_({ success: 1, id: id, status: status });
  }

  return json_({ success: 0, error: "Request not found" });
}

function getSheet_() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = spreadsheet.getSheetByName(SHEET_NAME);

  if (!sheet) {
    setupProductRequests();
    sheet = spreadsheet.getSheetByName(SHEET_NAME);
  }

  return sheet;
}

function setupAnalyticsSheet_(spreadsheet) {
  let sheet = spreadsheet.getSheetByName(ANALYTICS_SHEET_NAME);

  if (!sheet) {
    sheet = spreadsheet.insertSheet(ANALYTICS_SHEET_NAME);
  }

  if (sheet.getLastRow() === 0) {
    sheet.appendRow(ANALYTICS_HEADERS);
    sheet.setFrozenRows(1);
    sheet
      .getRange(1, 1, 1, ANALYTICS_HEADERS.length)
      .setFontWeight("bold");
    sheet.autoResizeColumns(1, ANALYTICS_HEADERS.length);
  }

  return sheet;
}

function getAnalyticsSheet_() {
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  return setupAnalyticsSheet_(spreadsheet);
}

function isAuthorized_(token) {
  const expected = PropertiesService.getScriptProperties().getProperty(
    "QUEUE_TOKEN"
  );
  return Boolean(expected && token && expected === String(token));
}

function clean_(value) {
  return String(value || "").trim().replace(/\s+/g, " ");
}

function normalize_(value) {
  return clean_(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function formatDate_(value) {
  if (!value) {
    return "";
  }

  return Utilities.formatDate(
    new Date(value),
    Session.getScriptTimeZone(),
    "yyyy-MM-dd HH:mm:ss"
  );
}

function json_(value) {
  return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(
    ContentService.MimeType.JSON
  );
}
