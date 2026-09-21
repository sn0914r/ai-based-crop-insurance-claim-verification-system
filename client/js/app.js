/**
 * Main Application Logic for Crop Insurance Client Interface
 */

// Intercept Live Server WebSocket reloads triggered by backend database and file writes
(function () {
  if (typeof window === "undefined" || !window.WebSocket) return;
  const OrigWebSocket = window.WebSocket;
  window.WebSocket = function (url, protocols) {
    const socket = protocols
      ? new OrigWebSocket(url, protocols)
      : new OrigWebSocket(url);
    let userOnMessage = null;
    try {
      Object.defineProperty(socket, "onmessage", {
        get() {
          return userOnMessage;
        },
        set(fn) {
          userOnMessage = function (e) {
            if (e && e.data === "reload") {
              const results = document.getElementById("resultsContainer");
              if (
                window.__claimInProgress ||
                (results && results.classList.contains("visible"))
              ) {
                console.warn(
                  "[LiveServer] Prevented automatic page reload caused by backend database/uploads update.",
                );
                return;
              }
            }
            if (typeof fn === "function") fn.apply(this, arguments);
          };
        },
        configurable: true,
      });
    } catch (err) {
      console.warn("Could not wrap WebSocket onmessage:", err);
    }
    return socket;
  };
  window.WebSocket.prototype = OrigWebSocket.prototype;
})();

document.addEventListener("DOMContentLoaded", () => {
  // Global State
  const state = {
    currentImageBase64: null,
    currentClaimId: null,
    isSubmitting: false,
    pendingPayload: null,
  };

  // DOM Elements
  const tabs = document.querySelectorAll(".tab-button");
  const panes = document.querySelectorAll(".tab-pane");
  const healthBadge = document.getElementById("healthStatusBadge");
  const healthText = document.getElementById("healthStatusText");
  const btnSettings = document.getElementById("btnSettings");
  const settingsModal = document.getElementById("settingsModal");
  const btnCloseSettings = document.getElementById("btnCloseSettings");
  const btnSaveSettings = document.getElementById("btnSaveSettings");
  const inputApiUrl = document.getElementById("inputApiUrl");
  const toastContainer = document.getElementById("toastContainer");

  // Form Elements
  const claimForm = document.getElementById("claimForm");
  const btnSubmit = document.getElementById("btnSubmit");
  const rangeDamage = document.getElementById("claimedDamage");
  const rangeValue = document.getElementById("claimedDamageValue");
  const claimedDamageInput = document.getElementById("claimedDamageInput");
  const inputLatitude = document.getElementById("latitude");
  const inputLongitude = document.getElementById("longitude");

  // Location & Inline Map Elements
  const btnUseCurrentLocation = document.getElementById(
    "btnUseCurrentLocation",
  );
  const btnSelectOnMap = document.getElementById("btnSelectOnMap");
  const btnEnterManually = document.getElementById("btnEnterManually");
  const locationDisplayText = document.getElementById("locationDisplayText");
  const btnToggleAdvancedGeo = document.getElementById("btnToggleAdvancedGeo");
  const advancedGeoIcon = document.getElementById("advancedGeoIcon");
  const advancedGeoFields = document.getElementById("advancedGeoFields");

  // Inline Map Workbench Elements
  const farmMapSection = document.getElementById("farmMapSection");
  const btnToggleMarking = document.getElementById("btnToggleMarking");
  const markingIcon = document.getElementById("markingIcon");
  const markingStatusText = document.getElementById("markingStatusText");
  const fieldMapContainer = document.getElementById("fieldMap");
  const btnSamplePolygon = document.getElementById("btnSamplePolygon");
  const btnClearPolygon = document.getElementById("btnClearPolygon");
  const mapSearchName = document.getElementById("mapSearchName");
  const btnSearchName = document.getElementById("btnSearchName");
  const mapSearchLat = document.getElementById("mapSearchLat");
  const mapSearchLon = document.getElementById("mapSearchLon");
  const btnGoCoords = document.getElementById("btnGoCoords");
  const calcAreaHectares = document.getElementById("calcAreaHectares");
  const calcVertexCount = document.getElementById("calcVertexCount");
  const calcCentroidCoords = document.getElementById("calcCentroidCoords");
  const btnSubmitBottom = document.getElementById("btnSubmitBottom");

  // Review Modal Elements
  const reviewClaimModal = document.getElementById("reviewClaimModal");
  const btnCloseReview = document.getElementById("btnCloseReview");
  const btnEditClaim = document.getElementById("btnEditClaim");
  const btnConfirmSubmitClaim = document.getElementById(
    "btnConfirmSubmitClaim",
  );
  const reviewFarmerId = document.getElementById("reviewFarmerId");
  const reviewCropType = document.getElementById("reviewCropType");
  const reviewLossDate = document.getElementById("reviewLossDate");
  const reviewClaimedDamage = document.getElementById("reviewClaimedDamage");
  const reviewPhotoPreview = document.getElementById("reviewPhotoPreview");
  const reviewPhotoMeta = document.getElementById("reviewPhotoMeta");
  const reviewCoordinates = document.getElementById("reviewCoordinates");

  // Dropzone Elements
  const dropzone = document.getElementById("imageDropzone");
  const fileInput = document.getElementById("imageFileInput");
  const previewWrapper = document.getElementById("previewWrapper");
  const previewImg = document.getElementById("previewImg");
  const previewMeta = document.getElementById("previewMeta");
  const btnRemoveImage = document.getElementById("btnRemoveImage");
  const sampleCardsContainer = document.getElementById("sampleCardsContainer");

  // Results Elements
  const resultsContainer = document.getElementById("resultsContainer");
  const decisionHero = document.getElementById("decisionHero");
  const resultDecisionTitle = document.getElementById("resultDecisionTitle");
  const resultDecisionDesc = document.getElementById("resultDecisionDesc");
  const resultClaimId = document.getElementById("resultClaimId");
  const resultDamageScore = document.getElementById("resultDamageScore");
  const resultDamageBar = document.getElementById("resultDamageBar");
  const resultPredictedClass = document.getElementById("resultPredictedClass");
  const resultConfidence = document.getElementById("resultConfidence");
  const resultConfidenceBar = document.getElementById("resultConfidenceBar");
  const resultFraudScore = document.getElementById("resultFraudScore");
  const resultFraudBar = document.getElementById("resultFraudBar");
  const resultRiskLevel = document.getElementById("resultRiskLevel");
  const resultWeatherConsistency = document.getElementById(
    "resultWeatherConsistency",
  );
  const resultWeatherBar = document.getElementById("resultWeatherBar");
  const resultInsightsList = document.getElementById("resultInsightsList");
  const executiveSummaryBox = document.getElementById("executiveSummaryBox");
  const execSummaryVerdict = document.getElementById("execSummaryVerdict");
  const execSummaryText = document.getElementById("execSummaryText");
  const evidenceChecklistContainer = document.getElementById(
    "evidenceChecklistContainer",
  );
  const btnToggleTechnicalShap = document.getElementById(
    "btnToggleTechnicalShap",
  );
  const technicalShapDrawer = document.getElementById("technicalShapDrawer");
  const jsonAccordionHeader = document.getElementById("jsonAccordionHeader");
  const jsonAccordionContent = document.getElementById("jsonAccordionContent");
  const jsonRawOutput = document.getElementById("jsonRawOutput");

  // Lookup & Audit Elements
  const inputSearchClaimId = document.getElementById("inputSearchClaimId");
  const btnSearchClaim = document.getElementById("btnSearchClaim");
  const btnRefreshClaimsHistory = document.getElementById(
    "btnRefreshClaimsHistory",
  );
  const btnClearClaimsHistory = document.getElementById(
    "btnClearClaimsHistory",
  );
  const claimsCountBadge = document.getElementById("claimsCountBadge");
  const claimsHistoryTableBody = document.getElementById(
    "claimsHistoryTableBody",
  );
  const dossierDetailsContainer = document.getElementById(
    "dossierDetailsContainer",
  );
  const timelineSectionWrapper = document.getElementById(
    "timelineSectionWrapper",
  );
  const btnToggleAuditTrail = document.getElementById("btnToggleAuditTrail");
  const auditTrailDrawer = document.getElementById("auditTrailDrawer");
  const caretAuditTrail = document.getElementById("caretAuditTrail");
  const auditEventCountBadge = document.getElementById("auditEventCountBadge");
  const lookupStatusAlert = document.getElementById("lookupStatusAlert");
  const claimDossierHeader = document.getElementById("claimDossierHeader");
  const auditTimeline = document.getElementById("auditTimeline");
  const recentClaimsContainer = document.getElementById(
    "recentClaimsContainer",
  );

  // -------------------------------------------------------------
  // Toast Notifications (Phosphor Vector Icons & Architectural Pill)
  // -------------------------------------------------------------
  function showToast(message, type = "info", duration = 4000) {
    if (!toastContainer) return;
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    let iconClass = "ph-bold ph-info";
    if (type === "success") iconClass = "ph-bold ph-check";
    if (type === "error") iconClass = "ph-bold ph-x";
    if (type === "warning") iconClass = "ph-bold ph-warning";

    toast.innerHTML = `
      <div class="toast-icon-wrapper">
        <i class="${iconClass}"></i>
      </div>
      <div class="toast-content">
        <span class="toast-message">${message}</span>
      </div>
      <button type="button" class="toast-close" aria-label="Dismiss">
        <i class="ph ph-x"></i>
      </button>
    `;
    toastContainer.appendChild(toast);

    const closeBtn = toast.querySelector(".toast-close");
    const dismissTimer = setTimeout(() => dismissToast(toast), duration);

    closeBtn?.addEventListener("click", (e) => {
      e.stopPropagation();
      clearTimeout(dismissTimer);
      dismissToast(toast);
    });

    toast.addEventListener("click", () => {
      clearTimeout(dismissTimer);
      dismissToast(toast);
    });
  }

  function dismissToast(toast) {
    toast.classList.add("toast-dismissing");
    setTimeout(() => toast.remove(), 260);
  }

  // -------------------------------------------------------------
  // Health Monitor
  // -------------------------------------------------------------
  async function updateHealth() {
    const res = await window.ApiClient.checkHealth();
    if (res.ok && res.data && (res.data.success || res.data.status === "ok")) {
      healthBadge.className = "health-status-badge online";
      healthText.textContent = "System Active";
    } else {
      healthBadge.className = "health-status-badge offline";
      healthText.textContent = "System Offline";
    }
  }

  // Initial check & interval
  updateHealth();
  setInterval(updateHealth, 15000);

  // -------------------------------------------------------------
  // Tab Navigation
  // -------------------------------------------------------------
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const targetId = tab.getAttribute("data-tab");
      tabs.forEach((t) => t.classList.remove("active"));
      panes.forEach((p) => p.classList.remove("active"));

      tab.classList.add("active");
      document.getElementById(targetId)?.classList.add("active");

      if (targetId === "tabLookup") {
        loadClaimsHistory();
      }
    });
  });

  // -------------------------------------------------------------
  // Settings Modal (Internal Developer / Admin Mode)
  // -------------------------------------------------------------
  const btnOpenDeveloperSettings = document.getElementById(
    "btnOpenDeveloperSettings",
  );
  btnOpenDeveloperSettings?.addEventListener("click", () => {
    inputApiUrl.value = window.AppConfig.getApiBaseUrl();
    settingsModal.classList.add("open");
  });

  btnSettings?.addEventListener("click", () => {
    inputApiUrl.value = window.AppConfig.getApiBaseUrl();
    settingsModal.classList.add("open");
  });

  btnCloseSettings?.addEventListener("click", () => {
    settingsModal.classList.remove("open");
  });

  settingsModal?.addEventListener("click", (e) => {
    if (e.target === settingsModal) {
      settingsModal.classList.remove("open");
    }
  });

  btnSaveSettings?.addEventListener("click", () => {
    const newUrl = inputApiUrl.value;
    window.AppConfig.setApiBaseUrl(newUrl);
    settingsModal.classList.remove("open");
    showToast(`Settings updated & saved successfully`, "success");
    updateHealth();
  });

  // -------------------------------------------------------------
  // Form Controls (Slider, Field Location, Map Picker & Coordinates)
  // -------------------------------------------------------------
  rangeDamage?.addEventListener("input", (e) => {
    if (claimedDamageInput) claimedDamageInput.value = e.target.value;
    if (rangeValue) rangeValue.textContent = `${e.target.value}%`;
  });

  claimedDamageInput?.addEventListener("input", (e) => {
    const raw = e.target.value;
    if (raw === "") return;
    let val = parseFloat(raw);
    if (!isNaN(val)) {
      if (val > 100) val = 100;
      if (val < 0) val = 0;
      if (rangeDamage) rangeDamage.value = val;
      if (rangeValue) rangeValue.textContent = `${val}%`;
    }
  });

  claimedDamageInput?.addEventListener("blur", (e) => {
    let val = parseFloat(e.target.value);
    if (isNaN(val) || val < 0) val = 0;
    if (val > 100) val = 100;
    e.target.value = val;
    if (rangeDamage) rangeDamage.value = val;
    if (rangeValue) rangeValue.textContent = `${val}%`;
  });

  // Coordinate Formatting & Status Pill Helpers
  function formatCoordinates(lat, lng) {
    const numLat = parseFloat(lat);
    const numLng = parseFloat(lng);
    if (isNaN(numLat) || isNaN(numLng)) {
      return "Coordinates not set";
    }
    const latDir = numLat >= 0 ? "N" : "S";
    const lngDir = numLng >= 0 ? "E" : "W";
    return `${Math.abs(numLat).toFixed(4)}° ${latDir}, ${Math.abs(numLng).toFixed(4)}° ${lngDir}`;
  }

  function updateLocationDisplay(lat, lng, prefix = "Plot location") {
    if (!locationDisplayText) return;
    const formatted = formatCoordinates(lat, lng);
    locationDisplayText.textContent = `${prefix}: ${formatted}`;
  }

  // Use Current Location (Device GPS)
  btnUseCurrentLocation?.addEventListener("click", () => {
    if (!navigator.geolocation) {
      showToast("Geolocation is not supported by your browser", "error");
      return;
    }
    const originalContent = btnUseCurrentLocation.innerHTML;
    btnUseCurrentLocation.innerHTML =
      '<i class="ph-bold ph-spinner ph-spin"></i><span>Acquiring GPS...</span>';
    btnUseCurrentLocation.disabled = true;

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        btnUseCurrentLocation.innerHTML = originalContent;
        btnUseCurrentLocation.disabled = false;
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        if (inputLatitude) inputLatitude.value = lat.toFixed(4);
        if (inputLongitude) inputLongitude.value = lng.toFixed(4);
        updateLocationDisplay(lat, lng, "Current location");
        showToast("Plot location acquired from GPS", "success");
      },
      (err) => {
        btnUseCurrentLocation.innerHTML = originalContent;
        btnUseCurrentLocation.disabled = false;
        showToast(`Could not acquire location: ${err.message}`, "error");
      },
      { timeout: 10000, enableHighAccuracy: true },
    );
  });

  // Toggle Manual Coordinates & Advanced Details
  function toggleManualInputs(forceState = null) {
    if (!advancedGeoFields) return;
    const isHidden =
      advancedGeoFields.style.display === "none" ||
      !advancedGeoFields.style.display;
    const shouldOpen = forceState !== null ? forceState : isHidden;

    if (shouldOpen) {
      advancedGeoFields.style.display = "block";
      btnToggleAdvancedGeo?.setAttribute("aria-expanded", "true");
      advancedGeoIcon?.classList.remove("ph-caret-right");
      advancedGeoIcon?.classList.add("ph-caret-down");
      btnEnterManually?.classList.add("active");
      inputLatitude?.focus();
    } else {
      advancedGeoFields.style.display = "none";
      btnToggleAdvancedGeo?.setAttribute("aria-expanded", "false");
      advancedGeoIcon?.classList.remove("ph-caret-down");
      advancedGeoIcon?.classList.add("ph-caret-right");
      btnEnterManually?.classList.remove("active");
    }
  }

  btnToggleAdvancedGeo?.addEventListener("click", () => {
    toggleManualInputs();
  });

  btnEnterManually?.addEventListener("click", () => {
    toggleManualInputs();
  });

  // Sync Location Pill When Coordinates Are Manually Edited
  function handleManualCoordinateChange() {
    if (inputLatitude && inputLongitude) {
      updateLocationDisplay(
        inputLatitude.value,
        inputLongitude.value,
        "Custom plot",
      );
    }
  }

  inputLatitude?.addEventListener("input", handleManualCoordinateChange);
  inputLongitude?.addEventListener("input", handleManualCoordinateChange);

  // -------------------------------------------------------------
  // Inline Interactive Field Map Workbench (Leaflet, Satellite & Polygon Drawing)
  // -------------------------------------------------------------
  let leafletMap = null;
  let fieldPolygon = null;
  let fieldBoundary = []; // Array of [lat, lng]
  let vertexMarkers = [];
  let centroidMarker = null;
  let isMarkingActive = false;

  // Calculate spherical polygon area in hectares
  function calculatePolygonAreaHectares(coords) {
    if (!coords || coords.length < 3) return 0;
    const R = 6378137; // Earth radius in meters
    let area = 0;
    const len = coords.length;
    for (let i = 0; i < len; i++) {
      const p1 = coords[i];
      const p2 = coords[(i + 1) % len];
      const lat1 = (p1[0] * Math.PI) / 180;
      const lat2 = (p2[0] * Math.PI) / 180;
      const lonDiff = ((p2[1] - p1[1]) * Math.PI) / 180;
      area += lonDiff * (2 + Math.sin(lat1) + Math.sin(lat2));
    }
    area = Math.abs((area * R * R) / 4.0);
    return area / 10000; // 1 hectare = 10,000 sq meters
  }

  // Calculate centroid from boundary coordinates
  function calculateCentroid(coords) {
    if (!coords || coords.length === 0) return null;
    let sumLat = 0;
    let sumLng = 0;
    coords.forEach((pt) => {
      sumLat += pt[0];
      sumLng += pt[1];
    });
    return [sumLat / coords.length, sumLng / coords.length];
  }

  // Update real-time stats strip and coordinate form inputs
  function updateBoundaryStats() {
    const count = fieldBoundary.length;
    if (calcVertexCount) {
      calcVertexCount.textContent = count === 1 ? "1 point" : `${count} points`;
    }

    if (count >= 3) {
      const areaHa = calculatePolygonAreaHectares(fieldBoundary);
      if (calcAreaHectares) {
        calcAreaHectares.textContent = `${areaHa.toFixed(2)} ha`;
      }
      const centroid = calculateCentroid(fieldBoundary);
      if (centroid) {
        if (calcCentroidCoords) {
          calcCentroidCoords.textContent = formatCoordinates(
            centroid[0],
            centroid[1],
          );
        }
        if (inputLatitude) inputLatitude.value = centroid[0].toFixed(4);
        if (inputLongitude) inputLongitude.value = centroid[1].toFixed(4);
        updateLocationDisplay(centroid[0], centroid[1], "Polygon plot");
      }
    } else if (count === 1 || count === 2) {
      if (calcAreaHectares) calcAreaHectares.textContent = "0.00 ha";
      const lastPt = fieldBoundary[fieldBoundary.length - 1];
      if (calcCentroidCoords) {
        calcCentroidCoords.textContent = formatCoordinates(
          lastPt[0],
          lastPt[1],
        );
      }
      if (inputLatitude) inputLatitude.value = lastPt[0].toFixed(4);
      if (inputLongitude) inputLongitude.value = lastPt[1].toFixed(4);
      updateLocationDisplay(lastPt[0], lastPt[1], "Plot point");
    } else {
      if (calcAreaHectares) calcAreaHectares.textContent = "0.00 ha";
      const curLat = parseFloat(inputLatitude?.value) || 16.513;
      const curLng = parseFloat(inputLongitude?.value) || 80.6235;
      if (calcCentroidCoords) {
        calcCentroidCoords.textContent = formatCoordinates(curLat, curLng);
      }
    }
  }

  // Redraw polygon & vertex markers on the map
  function redrawMapLayers() {
    if (!leafletMap) return;

    // Clear previous polygon
    if (fieldPolygon) {
      leafletMap.removeLayer(fieldPolygon);
      fieldPolygon = null;
    }

    // Clear previous markers
    vertexMarkers.forEach((m) => leafletMap.removeLayer(m));
    vertexMarkers = [];

    // Render vertex dots
    fieldBoundary.forEach((pt, idx) => {
      const marker = L.circleMarker([pt[0], pt[1]], {
        radius: 6,
        color: "#a3e635",
        fillColor: "#0a1f18",
        fillOpacity: 0.9,
        weight: 2,
      }).addTo(leafletMap);

      marker.bindTooltip(`Vertex ${idx + 1}`, {
        permanent: false,
        direction: "top",
      });
      vertexMarkers.push(marker);
    });

    // Render polygon if 3 or more points
    if (fieldBoundary.length >= 3) {
      fieldPolygon = L.polygon(fieldBoundary, {
        color: "#a3e635",
        fillColor: "#a3e635",
        fillOpacity: 0.28,
        weight: 2.5,
      }).addTo(leafletMap);
    } else if (fieldBoundary.length === 2) {
      fieldPolygon = L.polyline(fieldBoundary, {
        color: "#a3e635",
        weight: 2,
        dashArray: "4, 6",
      }).addTo(leafletMap);
    }

    updateBoundaryStats();
  }

  // Set boundary from external coordinates (e.g. preset or sample farm)
  function drawPolygonOnMap(coords, autoFit = false) {
    if (!Array.isArray(coords) || coords.length === 0) return;
    fieldBoundary = coords.map((pt) => [parseFloat(pt[0]), parseFloat(pt[1])]);
    redrawMapLayers();

    if (autoFit && leafletMap && fieldBoundary.length > 0) {
      if (fieldPolygon) {
        leafletMap.fitBounds(fieldPolygon.getBounds(), { padding: [35, 35] });
      } else {
        leafletMap.setView(fieldBoundary[0], 15);
      }
    }
  }

  // Clear boundary
  function clearBoundary(silent = false) {
    fieldBoundary = [];
    if (fieldPolygon && leafletMap) {
      leafletMap.removeLayer(fieldPolygon);
      fieldPolygon = null;
    }
    vertexMarkers.forEach((m) => leafletMap?.removeLayer(m));
    vertexMarkers = [];
    if (centroidMarker && leafletMap) {
      leafletMap.removeLayer(centroidMarker);
      centroidMarker = null;
    }
    updateBoundaryStats();
    if (!silent) {
      showToast(
        "Boundary cleared. Click on map to plot field vertices.",
        "info",
      );
    }
  }

  btnClearPolygon?.addEventListener("click", () => clearBoundary(false));

  // Toggle Marking Mode (Activate / Deactivate)
  function setMarkingMode(active) {
    isMarkingActive = active;
    if (isMarkingActive) {
      btnToggleMarking?.classList.add("marking-active");
      if (markingIcon) markingIcon.className = "ph-bold ph-pause";
      if (markingStatusText)
        markingStatusText.textContent = "Deactivate Marking";
      fieldMapContainer?.classList.add("marking-cursor");
      showToast(
        "Marking mode active: Click anywhere on the map to plot boundary vertices",
        "info",
        3500,
      );
    } else {
      btnToggleMarking?.classList.remove("marking-active");
      if (markingIcon) markingIcon.className = "ph-bold ph-pencil-simple-line";
      if (markingStatusText) markingStatusText.textContent = "Activate Marking";
      fieldMapContainer?.classList.remove("marking-cursor");
    }
  }

  btnToggleMarking?.addEventListener("click", () => {
    setMarkingMode(!isMarkingActive);
    if (!isMarkingActive) {
      showToast(
        "Marking deactivated: Map clicks will now pan and zoom freely",
        "info",
        3000,
      );
    }
  });

  // Default Sample Farm Polygon (Budameru, Andhra Pradesh, 1.51 ha, 6 vertices)
  const SAMPLE_ANDHRA_POLYGON = [
    [16.52295, 80.7586],
    [16.52208, 80.75988],
    [16.52048, 80.75918],
    [16.52118, 80.75798],
    [16.52158, 80.75818],
    [16.52188, 80.7583],
  ];

  btnSamplePolygon?.addEventListener("click", () => {
    drawPolygonOnMap(SAMPLE_ANDHRA_POLYGON, true);
    if (mapSearchName) mapSearchName.value = "Budameru";
    if (mapSearchLat) mapSearchLat.value = "16.5189";
    if (mapSearchLon) mapSearchLon.value = "80.7594";
    showToast(
      "Loaded Budameru farm boundary (Andhra Pradesh, 1.51 ha)",
      "success",
    );
  });

  // Initialize Leaflet Map in Inline Container
  function initInlineMap() {
    const mapContainer = document.getElementById("fieldMap");
    if (!mapContainer || typeof L === "undefined") return;

    // Default to Budameru, Andhra Pradesh center
    const curLat = parseFloat(inputLatitude?.value) || 16.5217;
    const curLng = parseFloat(inputLongitude?.value) || 80.7587;

    leafletMap = L.map("fieldMap", {
      center: [curLat, curLng],
      zoom: 16,
      zoomControl: true,
    });

    // Base Layers
    const satelliteLayer = L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      {
        maxZoom: 19,
        attribution:
          "Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
      },
    ).addTo(leafletMap);

    const osmLayer = L.tileLayer(
      "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
      },
    );

    // Layer Toggle Control
    L.control
      .layers(
        { "Satellite View": satelliteLayer, "Street Map": osmLayer },
        null,
        { position: "topright" },
      )
      .addTo(leafletMap);

    // Click on map to plot polygon vertices (only when marking mode is activated)
    leafletMap.on("click", (e) => {
      if (!isMarkingActive) {
        return;
      }
      const lat = parseFloat(e.latlng.lat.toFixed(5));
      const lng = parseFloat(e.latlng.lng.toFixed(5));
      fieldBoundary.push([lat, lng]);
      redrawMapLayers();

      if (fieldBoundary.length === 1) {
        showToast(
          "Vertex 1 added. Click more points around your field to enclose the polygon.",
          "info",
          3000,
        );
      } else if (fieldBoundary.length === 3) {
        showToast(
          "Enclosed farm polygon created. Area calculated automatically.",
          "success",
          3000,
        );
      }
    });

    // Make drawPolygonOnMap accessible globally for presets
    window.drawPolygonOnMap = drawPolygonOnMap;

    // Load Budameru 1.51 ha farm plot as the default on map load
    drawPolygonOnMap(SAMPLE_ANDHRA_POLYGON, false);
    if (mapSearchName && !mapSearchName.value) mapSearchName.value = "Budameru";
    if (mapSearchLat && !mapSearchLat.value) mapSearchLat.value = "16.5189";
    if (mapSearchLon && !mapSearchLon.value) mapSearchLon.value = "80.7594";
    if (inputLatitude) inputLatitude.value = "16.5217";
    if (inputLongitude) inputLongitude.value = "80.7587";
    updateLocationDisplay(16.5217, 80.7587, "Budameru, Andhra Pradesh");

    setTimeout(() => {
      leafletMap.invalidateSize();
      if (fieldPolygon) {
        leafletMap.fitBounds(fieldPolygon.getBounds(), { padding: [50, 50] });
      }
    }, 250);
  }

  // Name-Based Location Search (OpenStreetMap Nominatim)
  async function performNameSearch() {
    const query = (mapSearchName?.value || "").trim();
    if (!query) {
      showToast(
        "Please enter a location name or district to search",
        "warning",
      );
      mapSearchName?.focus();
      return;
    }

    const originalBtn = btnSearchName?.innerHTML;
    if (btnSearchName) {
      btnSearchName.innerHTML =
        '<i class="ph-bold ph-spinner ph-spin"></i> <span>Searching...</span>';
      btnSearchName.disabled = true;
    }

    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(query)}`;
      const res = await fetch(url, { headers: { "Accept-Language": "en" } });
      const results = await res.json();

      if (results && results.length > 0) {
        const item = results[0];
        const lat = parseFloat(item.lat);
        const lon = parseFloat(item.lon);

        if (leafletMap) {
          leafletMap.flyTo([lat, lon], 14, { duration: 1.2 });
        }

        if (inputLatitude) inputLatitude.value = lat.toFixed(4);
        if (inputLongitude) inputLongitude.value = lon.toFixed(4);
        if (mapSearchLat) mapSearchLat.value = lat.toFixed(4);
        if (mapSearchLon) mapSearchLon.value = lon.toFixed(4);

        updateLocationDisplay(lat, lon, "Searched location");
        if (calcCentroidCoords)
          calcCentroidCoords.textContent = formatCoordinates(lat, lon);

        const shortName = item.display_name.split(",").slice(0, 2).join(",");
        showToast(`Located "${shortName}" & navigated map`, "success");
      } else {
        showToast(`No locations found matching "${query}"`, "error");
      }
    } catch (err) {
      showToast(`Location search failed: ${err.message}`, "error");
    } finally {
      if (btnSearchName) {
        btnSearchName.innerHTML = originalBtn || "<span>Find Place</span>";
        btnSearchName.disabled = false;
      }
    }
  }

  btnSearchName?.addEventListener("click", performNameSearch);
  mapSearchName?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      performNameSearch();
    }
  });

  // Coordinates-Based GPS Search (Lat/Lon)
  function performCoordsSearch() {
    const rawLat = mapSearchLat?.value;
    const rawLon = mapSearchLon?.value;

    const lat = parseFloat(rawLat);
    const lon = parseFloat(rawLon);

    if (isNaN(lat) || lat < -90 || lat > 90) {
      showToast("Please enter a valid Latitude between -90 and 90", "error");
      mapSearchLat?.focus();
      return;
    }
    if (isNaN(lon) || lon < -180 || lon > 180) {
      showToast("Please enter a valid Longitude between -180 and 180", "error");
      mapSearchLon?.focus();
      return;
    }

    if (leafletMap) {
      leafletMap.flyTo([lat, lon], 15, { duration: 1.2 });
    }

    if (inputLatitude) inputLatitude.value = lat.toFixed(4);
    if (inputLongitude) inputLongitude.value = lon.toFixed(4);

    updateLocationDisplay(lat, lon, "GPS plot");
    if (calcCentroidCoords)
      calcCentroidCoords.textContent = formatCoordinates(lat, lon);
    showToast(`Navigated map to ${formatCoordinates(lat, lon)}`, "success");
  }

  btnGoCoords?.addEventListener("click", performCoordsSearch);
  mapSearchLat?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      performCoordsSearch();
    }
  });
  mapSearchLon?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      performCoordsSearch();
    }
  });

  // Select On Map Button Smoothly Scrolls to Map Section
  btnSelectOnMap?.addEventListener("click", () => {
    if (farmMapSection) {
      farmMapSection.scrollIntoView({ behavior: "smooth", block: "center" });
      farmMapSection.style.boxShadow = "0 0 0 2px var(--color-primary)";
      setTimeout(() => {
        farmMapSection.style.boxShadow = "";
      }, 1800);
      setTimeout(() => {
        leafletMap?.invalidateSize();
      }, 300);
    }
  });

  // Submit Claim Button at Bottom of Form / Map Section
  btnSubmitBottom?.addEventListener("click", () => {
    if (claimForm) {
      if (typeof claimForm.requestSubmit === "function") {
        claimForm.requestSubmit();
      } else {
        btnSubmit?.click();
      }
    }
  });

  // Initialize inline map on page load
  initInlineMap();

  // Initial display sync
  if (inputLatitude && inputLongitude) {
    updateLocationDisplay(
      inputLatitude.value,
      inputLongitude.value,
      "Plot location",
    );
  }

  // Set default loss date to today
  const inputLossDate = document.getElementById("lossDate");
  if (inputLossDate && !inputLossDate.value) {
    inputLossDate.value = new Date().toISOString().split("T")[0];
  }

  // -------------------------------------------------------------
  // Image Upload Handling
  // -------------------------------------------------------------
  function setImage(base64Url, filename = "Uploaded Image") {
    state.currentImageBase64 = base64Url;
    previewImg.src = base64Url;
    previewMeta.textContent = filename;
    previewWrapper.classList.add("has-image");
    dropzone.style.display = "none";
  }

  function clearImage() {
    state.currentImageBase64 = null;
    previewImg.src = "";
    previewWrapper.classList.remove("has-image");
    dropzone.style.display = "block";
    if (fileInput) fileInput.value = "";
  }

  btnRemoveImage?.addEventListener("click", clearImage);

  dropzone?.addEventListener("click", () => fileInput.click());

  dropzone?.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone?.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone?.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  });

  fileInput?.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  });

  function handleFile(file) {
    if (!file.type.startsWith("image/")) {
      showToast("Please upload a valid image file (JPEG, PNG, WEBP)", "error");
      return;
    }
    if (file.size > 15 * 1024 * 1024) {
      showToast("File size must be under 15MB", "error");
      return;
    }
    const reader = new FileReader();
    reader.onload = (event) => {
      setImage(
        event.target.result,
        `${file.name} (${(file.size / 1024).toFixed(1)} KB)`,
      );
      showToast("Crop image loaded successfully", "info");
    };
    reader.readAsDataURL(file);
  }

  // -------------------------------------------------------------
  // Sample Presets Loader
  // -------------------------------------------------------------
  function renderSamplePresets() {
    if (!sampleCardsContainer || !window.SamplePresets) return;
    sampleCardsContainer.innerHTML = "";

    window.SamplePresets.forEach((sample) => {
      const card = document.createElement("div");
      card.className = "sample-card";
      card.innerHTML = `
        <img class="sample-thumbnail" src="${sample.imagePath || sample.dataUrl}" alt="${sample.title}" />
        <div class="sample-body">
          <div class="sample-name">
            <span>${sample.title}</span>
            <i class="ph ph-arrow-up-right"></i>
          </div>
          <div class="sample-desc">${sample.description}</div>
        </div>
      `;

      card.addEventListener("click", async () => {
        // Populate Form
        document.getElementById("farmerId").value = sample.formData.farmerId;
        document.getElementById("cropType").value = sample.formData.cropType;
        document.getElementById("claimedDamage").value =
          sample.formData.claimedDamage;
        if (claimedDamageInput)
          claimedDamageInput.value = sample.formData.claimedDamage;
        if (rangeValue)
          rangeValue.textContent = `${sample.formData.claimedDamage}%`;
        document.getElementById("latitude").value = sample.formData.latitude;
        document.getElementById("longitude").value = sample.formData.longitude;
        updateLocationDisplay(
          sample.formData.latitude,
          sample.formData.longitude,
          "Plot location",
        );
        document.getElementById("lossDate").value = sample.formData.lossDate;
        document.getElementById("rainfall").value = sample.formData.rainfall;
        document.getElementById("temperature").value =
          sample.formData.temperature;
        document.getElementById("droughtIndex").value =
          sample.formData.droughtIndex;
        document.getElementById("historicalYield").value =
          sample.formData.historicalYield;
        document.getElementById("claimFrequency").value =
          sample.formData.claimFrequency;

        // Ensure Base64 Data URL is ready
        let dataUrl = sample.dataUrl;
        if (!dataUrl && sample.imagePath && window.loadAssetAsDataUrl) {
          dataUrl = await window.loadAssetAsDataUrl(sample.imagePath);
          sample.dataUrl = dataUrl;
        }

        if (
          sample.formData.fieldBoundary &&
          typeof window.drawPolygonOnMap === "function"
        ) {
          window.drawPolygonOnMap(sample.formData.fieldBoundary, true);
        } else if (
          sample.formData.latitude &&
          sample.formData.longitude &&
          leafletMap
        ) {
          leafletMap.flyTo(
            [sample.formData.latitude, sample.formData.longitude],
            15,
          );
        }

        if (dataUrl) {
          setImage(dataUrl, `Field Photo: ${sample.filename || sample.title}`);
          showToast(
            `Loaded "${sample.title}" real field photo & scenario`,
            "success",
          );
        } else {
          showToast(`Loaded "${sample.title}" scenario`, "info");
        }
      });

      sampleCardsContainer.appendChild(card);
    });
  }

  renderSamplePresets();

  // -------------------------------------------------------------
  // Form Submission
  // -------------------------------------------------------------
  // Review Modal Helpers
  function openReviewModal(payload) {
    if (!reviewClaimModal) return;

    state.pendingPayload = payload;

    if (reviewFarmerId)
      reviewFarmerId.textContent = payload.farmerId || "Not specified";
    if (reviewCropType) reviewCropType.textContent = payload.cropType;
    if (reviewLossDate)
      reviewLossDate.textContent =
        payload.lossDate || new Date().toISOString().split("T")[0];
    if (reviewClaimedDamage)
      reviewClaimedDamage.textContent = `${payload.claimedDamage}%`;
    if (reviewPhotoPreview)
      reviewPhotoPreview.src = state.currentImageBase64 || "";
    if (reviewPhotoMeta)
      reviewPhotoMeta.textContent =
        previewMeta?.textContent || "Field photo attached";

    if (reviewCoordinates) {
      if (payload.fieldBoundary && payload.fieldBoundary.length >= 3) {
        const areaStr = payload.fieldAreaHectares
          ? ` (${payload.fieldAreaHectares} ha)`
          : "";
        reviewCoordinates.textContent = `${formatCoordinates(payload.latitude, payload.longitude)} [${payload.fieldBoundary.length}-pt polygon${areaStr}]`;
      } else if (payload.latitude && payload.longitude) {
        reviewCoordinates.textContent = formatCoordinates(
          payload.latitude,
          payload.longitude,
        );
      } else {
        reviewCoordinates.textContent = "Auto GPS (Default)";
      }
    }

    reviewClaimModal.classList.add("open");
  }

  function closeReviewModal() {
    if (!reviewClaimModal) return;
    reviewClaimModal.classList.remove("open");
  }

  btnCloseReview?.addEventListener("click", closeReviewModal);
  btnEditClaim?.addEventListener("click", closeReviewModal);
  reviewClaimModal?.addEventListener("click", (e) => {
    if (e.target === reviewClaimModal) closeReviewModal();
  });

  claimForm?.addEventListener("submit", (e) => {
    e.preventDefault();

    if (!state.currentImageBase64) {
      showToast(
        "Please upload or select a crop photo before reviewing your claim",
        "error",
      );
      dropzone.scrollIntoView({ behavior: "smooth" });
      return;
    }

    const payload = {
      farmerId: document.getElementById("farmerId").value.trim(),
      cropType: document.getElementById("cropType").value,
      claimedDamage: parseFloat(document.getElementById("claimedDamage").value),
      image: state.currentImageBase64,
      allowDuplicateImages: true,
    };

    const lat = document.getElementById("latitude").value;
    if (lat !== "") payload.latitude = parseFloat(lat);

    const lon = document.getElementById("longitude").value;
    if (lon !== "") payload.longitude = parseFloat(lon);

    // Attached Field Boundary Polygon & Area in Hectares
    if (fieldBoundary && fieldBoundary.length >= 3) {
      payload.fieldBoundary = fieldBoundary;
      const areaHa = calculatePolygonAreaHectares(fieldBoundary);
      payload.fieldAreaHectares = parseFloat(areaHa.toFixed(2));
    }

    const lossDate = document.getElementById("lossDate").value;
    if (lossDate) {
      payload.lossDate = lossDate;
      payload.incidentDate = lossDate;
    }

    const rain = document.getElementById("rainfall").value;
    if (rain !== "") payload.rainfall = parseFloat(rain);

    const temp = document.getElementById("temperature").value;
    if (temp !== "") payload.temperature = parseFloat(temp);

    const drought = document.getElementById("droughtIndex").value;
    if (drought !== "") payload.droughtIndex = parseFloat(drought);

    const histYield = document.getElementById("historicalYield").value;
    if (histYield) payload.historicalYield = histYield;

    const freq = document.getElementById("claimFrequency").value;
    if (freq !== "") payload.claimFrequency = parseInt(freq, 10);

    openReviewModal(payload);
  });

  // Final Submission from Review Screen
  btnConfirmSubmitClaim?.addEventListener("click", async (e) => {
    if (e && typeof e.preventDefault === "function") e.preventDefault();
    if (!state.pendingPayload) return;
    const payload = state.pendingPayload;
    window.__claimInProgress = true;

    // UI Loading state on confirmation button
    const originalContent = btnConfirmSubmitClaim.innerHTML;
    btnConfirmSubmitClaim.disabled = true;
    btnConfirmSubmitClaim.innerHTML = `<div class="spinner"></div> <span>Submitting & Evaluating...</span>`;

    try {
      console.log(
        "[CLAIM SUBMIT] Sending payload to ApiClient.submitClaim:",
        payload,
      );
      showToast(
        "Verifying claim with crop imagery & weather records...",
        "info",
        4000,
      );
      const res = await window.ApiClient.submitClaim(payload);
      console.log("[CLAIM SUBMIT] Received response:", res);

      closeReviewModal();

      const claimData = res && res.data ? res.data : res;
      if (claimData && claimData.claimId) {
        const claimId = claimData.claimId;
        if (claimData.status === "QUEUED") {
          showToast(
            `Claim ${claimId} queued! Stream worker is evaluating...`,
            "info",
            4000,
          );
          displayQueuedState(claimId);
          await pollForAssessment(claimId, payload.cropType);
        } else {
          showToast(
            `Claim ${claimId} assessed: ${claimData.decision || "PROCESSED"}`,
            "success",
          );
          displayAssessmentResults(claimData);
          saveRecentClaim(
            claimId,
            claimData.decision || "PROCESSED",
            payload.cropType,
          );
        }
      }
    } catch (err) {
      console.error("[CLAIM SUBMIT ERROR]:", err);
      showToast(`Submission failed: ${err.message}`, "error", 6000);
    } finally {
      btnConfirmSubmitClaim.disabled = false;
      btnConfirmSubmitClaim.innerHTML = originalContent;
      if (btnSubmit) {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = `<span>Review claim</span> <i class="ph-bold ph-arrow-right"></i>`;
      }
      if (btnSubmitBottom) {
        btnSubmitBottom.disabled = false;
      }
      setTimeout(() => {
        window.__claimInProgress = false;
      }, 5000);
    }
  });

  function displayQueuedState(claimId) {
    resultsContainer.classList.add("visible");
    decisionHero.className = "decision-hero decision-REVIEW";
    resultDecisionTitle.innerHTML =
      '<div style="display:flex;align-items:center;gap:0.75rem"><div class="spinner"></div> <span>EVALUATING IN STREAM...</span></div>';
    resultClaimId.textContent = `ID: ${claimId}`;
    resultDecisionDesc.textContent =
      "Task dispatched to Redis Streams. Python ML worker is running MobileNetV2 vision assessment, XGBoost fraud scoring, and SHAP explainability.";
    resultDamageScore.textContent = "...%";
    resultDamageBar.style.width = "20%";
    if (resultConfidence) resultConfidence.textContent = "AI Confidence: ...%";
    if (resultConfidenceBar) resultConfidenceBar.style.width = "20%";
    resultFraudScore.textContent = "...";
    resultFraudBar.style.width = "20%";
    resultWeatherConsistency.textContent = "...%";
    resultWeatherBar.style.width = "20%";
    resultInsightsList.innerHTML =
      '<div class="insight-card"><div class="insight-card-title"><i class="ph ph-hourglass"></i> Task Queued</div><div class="insight-card-text">Waiting for webhook notification from Python ML worker...</div></div>';
    resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function pollForAssessment(claimId, cropType) {
    const maxAttempts = 25;
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      await new Promise((r) => setTimeout(r, 1500));
      try {
        const claimRes = await window.ApiClient.getClaim(claimId);
        if (claimRes && claimRes.data) {
          const claim = claimRes.data;
          const isFinished =
            claim.status !== "QUEUED" && claim.status !== "EVALUATING";
          if (isFinished || claim.decision || claim.visualAssessment) {
            displayAssessmentResults(claim);
            saveRecentClaim(
              claimId,
              claim.decision || claim.status || "REVIEW",
              cropType,
            );
            showToast(
              `Claim ${claimId} finalized: ${claim.decision || claim.status}`,
              "success",
            );
            return;
          }
        }
      } catch (pollErr) {
        console.warn("Poll attempt error:", pollErr);
      }
    }
    showToast(
      `Claim ${claimId} evaluation taking longer than expected. You can check status in Claim Tracker.`,
      "warning",
      6000,
    );
  }

  // -------------------------------------------------------------
  // Display Results
  // -------------------------------------------------------------
  function displayAssessmentResults(data) {
    resultsContainer.classList.add("visible");

    // Hero Decision Banner
    const decision = data.decision || "REVIEW";
    decisionHero.className = `decision-hero decision-${decision}`;
    const decisionIcon =
      decision === "APPROVED"
        ? '<i class="ph-bold ph-check-circle"></i>'
        : decision === "REJECTED"
          ? '<i class="ph-bold ph-x-circle"></i>'
          : '<i class="ph-bold ph-warning-circle"></i>';
    resultDecisionTitle.innerHTML = `${decisionIcon} <span>${decision}</span>`;
    resultClaimId.textContent = `ID: ${data.claimId}`;

    if (decision === "APPROVED") {
      resultDecisionDesc.textContent =
        "Assessment verified. Damage score matches weather parameters with low fraud probability.";
    } else if (decision === "REJECTED") {
      resultDecisionDesc.textContent =
        "Claim flagged and rejected due to high fraud risk or inconsistency with satellite meteorological records.";
    } else {
      resultDecisionDesc.textContent =
        "Moderate variance detected. Claim routed to adjusters for manual underwriting review.";
    }

    // Damage Score (0 - 100%)
    const va = data.visualAssessment;
    const wa = data.weatherAssessment;
    const sa = data.satelliteAssessment;
    const xai = data.explainableAi;

    const numDamage =
      va && va.damageSeverity != null
        ? va.damageSeverity
        : parseFloat(data.damageScore ?? data.claimedDamage ?? 75);
    const damage = !isNaN(numDamage) ? Math.round(numDamage) : 0;
    resultDamageScore.textContent = `${damage}%`;
    resultDamageBar.style.width = `${Math.min(100, Math.max(0, damage))}%`;
    resultDamageBar.style.backgroundColor =
      damage > 60
        ? "var(--color-danger)"
        : damage > 30
          ? "var(--color-warning)"
          : "var(--color-success)";
    resultPredictedClass.textContent =
      va && va.visualClass
        ? `Class: ${va.visualClass}`
        : data.predictedClass
          ? `Class: ${data.predictedClass}`
          : "Severity: Calculated";

    // Model Confidence (0 - 100%)
    const numConf =
      va && va.confidence != null
        ? va.confidence
        : parseFloat(data.confidence ?? 0.95);
    const confidencePct = !isNaN(numConf)
      ? numConf <= 1
        ? Math.round(numConf * 100)
        : Math.round(numConf)
      : 85;
    if (resultConfidence) {
      resultConfidence.textContent = `AI Confidence: ${confidencePct}%`;
    }
    if (resultConfidenceBar) {
      resultConfidenceBar.style.width = `${confidencePct}%`;
      resultConfidenceBar.style.backgroundColor = "var(--color-primary)";
    }

    // Fraud Score & Risk Level
    const numFraud =
      data.fraudRiskScore != null
        ? data.fraudRiskScore
        : parseFloat(data.fraudScore ?? 0.05);
    const fraudVal = !isNaN(numFraud) ? numFraud : 0;
    resultFraudScore.textContent = fraudVal.toFixed(3);
    const fraudPct = Math.round(fraudVal * 100);
    resultFraudBar.style.width = `${Math.min(100, Math.max(0, fraudPct))}%`;
    resultFraudBar.style.backgroundColor =
      fraudPct > 70
        ? "var(--color-danger)"
        : fraudPct > 40
          ? "var(--color-warning)"
          : "var(--color-success)";
    const rLevel =
      data.fraudRiskLevel ||
      data.riskLevel ||
      (fraudPct > 70 ? "HIGH" : fraudPct > 35 ? "MEDIUM" : "LOW");
    resultRiskLevel.textContent = `Risk Level: ${rLevel}`;

    // Weather / Satellite Consistency (0 - 100%)
    const numWeather =
      sa && sa.damagedAreaPercentage != null
        ? sa.damagedAreaPercentage
        : wa && wa.weatherScore != null
          ? wa.weatherScore
          : parseFloat(data.weatherConsistency ?? 85);
    const weatherCons = !isNaN(numWeather)
      ? numWeather <= 1
        ? Math.round(numWeather * 100)
        : Math.round(numWeather)
      : 80;
    resultWeatherConsistency.textContent = `${weatherCons}%`;
    resultWeatherBar.style.width = `${Math.min(100, Math.max(0, weatherCons))}%`;
    resultWeatherBar.style.backgroundColor =
      weatherCons > 60 ? "var(--color-accent)" : "var(--color-warning)";

    // Insights / SHAP cards
    renderInsights(data);

    // Raw JSON output
    jsonRawOutput.textContent = JSON.stringify(data, null, 2);

    // Scroll to results smoothly
    resultsContainer.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function getFactorMeta(factorKey, rawTitle) {
    const key = (factorKey || "").toLowerCase();
    if (key.includes("damage_mismatch") || key.includes("mismatch")) {
      return {
        icon: "ph-bold ph-scales",
        category: "Discrepancy Analysis",
        badgeClass: "badge-warning",
        title: "Damage Mismatch Assessment",
      };
    }
    if (key.includes("weather")) {
      return {
        icon: "ph-bold ph-cloud-rain",
        category: "Meteorological Feed",
        badgeClass: "badge-info",
        title: "Weather Consistency Index",
      };
    }
    if (key.includes("history") || key.includes("historical")) {
      return {
        icon: "ph-bold ph-chart-line-up",
        category: "Agronomic Yield",
        badgeClass: "badge-leaf",
        title: "Historical Plot Yield",
      };
    }
    if (key.includes("frequency") || key.includes("claim_frequency")) {
      return {
        icon: "ph-bold ph-files",
        category: "Underwriting Profile",
        badgeClass: "badge-purple",
        title: "Claim Filing Frequency",
      };
    }
    if (key.includes("claimed_damage") || key.includes("claimed")) {
      return {
        icon: "ph-bold ph-percent",
        category: "Reported Loss",
        badgeClass: "badge-primary",
        title: "Declared Loss Percentage",
      };
    }
    return {
      icon: "ph-bold ph-sliders",
      category: "Agronomic Factor",
      badgeClass: "badge-primary",
      title:
        rawTitle ||
        (factorKey
          ? factorKey.replace(/_/g, " ").toUpperCase()
          : "Factor Metric"),
    };
  }

  function renderInsights(data) {
    const va = data.visualAssessment;
    const wa = data.weatherAssessment;
    const sa = data.satelliteAssessment;
    const xai = data.explainableAi;
    const decision = data.decision || "REVIEW";

    // 1. Executive Summary Card
    if (executiveSummaryBox) {
      executiveSummaryBox.className = `executive-summary-card decision-${decision}`;
      if (execSummaryVerdict) {
        execSummaryVerdict.textContent =
          decision === "APPROVED"
            ? "Verified & Approved"
            : decision === "REJECTED"
              ? "Flagged & Rejected"
              : "Routed for Underwriter Review";
      }
      if (execSummaryText) {
        if (xai && xai.executiveSummary) {
          execSummaryText.textContent = xai.executiveSummary;
        } else if (decision === "APPROVED") {
          execSummaryText.textContent =
            "This claim was verified and approved because independent leaf photography, meteorological station feeds, and satellite acreage observations all corroborate the reported loss.";
        } else if (decision === "REJECTED") {
          execSummaryText.textContent =
            "This claim was flagged and denied due to severe contradiction with meteorological weather records, duplicate photo reuse, or abnormal claim frequency.";
        } else {
          execSummaryText.textContent =
            "Moderate variance detected between reported loss and sensor records. This claim has been routed to an adjuster for underwriting review.";
        }
      }
    }

    // 2. 3-Pillar Evidence Verification Checklist
    if (evidenceChecklistContainer) {
      evidenceChecklistContainer.innerHTML = "";

      // Pillar 1: Ground Photo Evidence
      const visualDmg =
        va && va.damageSeverity != null
          ? Math.round(va.damageSeverity)
          : Math.round(data.damageScore || 0);
      const isDuplicate =
        (data.fraudAssessment?.is_duplicate_image ||
          (data.fraudFlags &&
            data.fraudFlags.includes("DUPLICATE_IMAGE_DETECTED"))) &&
        !data.allowDuplicateImages;
      const photoStatusBadge = isDuplicate
        ? `<span class="checklist-status-badge badge-alert"><i class="ph-bold ph-warning"></i> Image Reused</span>`
        : visualDmg > 50
          ? `<span class="checklist-status-badge badge-verified"><i class="ph-bold ph-check"></i> Verified Loss</span>`
          : visualDmg > 20
            ? `<span class="checklist-status-badge badge-notice"><i class="ph-bold ph-info"></i> Moderate Loss</span>`
            : `<span class="checklist-status-badge badge-verified"><i class="ph-bold ph-check"></i> Healthy Crop</span>`;

      const p1 = document.createElement("div");
      p1.className = "checklist-card";
      p1.innerHTML = `
        <div class="checklist-card-top">
          <div class="checklist-card-title-group">
            <div class="checklist-pillar-icon"><i class="ph-bold ph-camera"></i></div>
            <div>
              <div class="checklist-pillar-name">1. Field Photo Evidence</div>
              <div class="checklist-pillar-source">MobileNetV2 Vision AI</div>
            </div>
          </div>
          ${photoStatusBadge}
        </div>
        <div class="checklist-highlight-metric">${visualDmg}% Leaf Damage</div>
        <div class="checklist-card-desc">
          Computer vision classified crop status as <strong>${va?.visualClass || data.predictedClass || "ANALYZED"}</strong> with ${Math.round((va?.confidence || data.confidence || 0.85) * 100)}% model certainty.
        </div>
        <div class="checklist-card-footer">
          <i class="ph-bold ph-shield-check"></i>
          <span>${isDuplicate ? "Alert: Photo hash matched a previous claim" : "Unique original field photo verified"}</span>
        </div>
      `;
      evidenceChecklistContainer.appendChild(p1);

      // Pillar 2: Climate & Weather Evidence
      const weatherScore =
        wa && wa.weatherScore != null ? Math.round(wa.weatherScore) : 0;
      const hazard = wa?.weatherHazard || "NORMAL";
      const rainfall =
        wa?.metrics?.rainfallMm != null
          ? `${wa.metrics.rainfallMm} mm`
          : "Monitored";
      const weatherStatusBadge =
        (wa && wa.anomalyDetected) || weatherScore >= 50
          ? `<span class="checklist-status-badge badge-verified"><i class="ph-bold ph-check"></i> Hazard Confirmed</span>`
          : `<span class="checklist-status-badge badge-notice"><i class="ph-bold ph-info"></i> Mild / Normal</span>`;

      const p2 = document.createElement("div");
      p2.className = "checklist-card";
      p2.innerHTML = `
        <div class="checklist-card-top">
          <div class="checklist-card-title-group">
            <div class="checklist-pillar-icon"><i class="ph-bold ph-cloud-rain"></i></div>
            <div>
              <div class="checklist-pillar-name">2. Climate & Weather</div>
              <div class="checklist-pillar-source">Open-Meteo ERA5 Reanalysis</div>
            </div>
          </div>
          ${weatherStatusBadge}
        </div>
        <div class="checklist-highlight-metric">${hazard} Hazard (${rainfall})</div>
        <div class="checklist-card-desc">
          ${wa?.consistencyNote || `Meteorological stations recorded ${rainfall} precipitation and weather severity of ${weatherScore}% on the disaster date.`}
        </div>
        <div class="checklist-card-footer">
          <i class="ph-bold ph-calendar-check"></i>
          <span>Correlated with loss date (${data.incidentDate || data.lossDate || "Recorded"})</span>
        </div>
      `;
      evidenceChecklistContainer.appendChild(p2);

      // Pillar 3: Satellite Farmland Evidence
      const satDmgArea =
        sa && sa.damagedAreaPercentage != null
          ? Math.round(sa.damagedAreaPercentage)
          : Math.round(data.weatherConsistency || 80);
      const satHectares = sa?.fieldAreaHectares
        ? `${sa.fieldAreaHectares} ha`
        : data.fieldAreaHectares
          ? `${data.fieldAreaHectares} ha`
          : "Marked Plot";
      const satStatusBadge =
        satDmgArea >= 50
          ? `<span class="checklist-status-badge badge-verified"><i class="ph-bold ph-check"></i> Acreage Verified</span>`
          : `<span class="checklist-status-badge badge-notice"><i class="ph-bold ph-info"></i> Low Plot Impact</span>`;

      const p3 = document.createElement("div");
      p3.className = "checklist-card";
      p3.innerHTML = `
        <div class="checklist-card-top">
          <div class="checklist-card-title-group">
            <div class="checklist-pillar-icon"><i class="ph-bold ph-planet"></i></div>
            <div>
              <div class="checklist-pillar-name">3. Satellite Farmland</div>
              <div class="checklist-pillar-source">Sentinel-2 Multi-Spectral</div>
            </div>
          </div>
          ${satStatusBadge}
        </div>
        <div class="checklist-highlight-metric">${satDmgArea}% Plot Area Loss</div>
        <div class="checklist-card-desc">
          ${sa?.summary || `Satellite spectral imagery confirmed vegetation canopy loss across ${satHectares} of farmland.`}
        </div>
        <div class="checklist-card-footer">
          <i class="ph-bold ph-map-pin"></i>
          <span>Multi-spectral NDVI drop: ${sa?.ndviDrop != null ? sa.ndviDrop.toFixed(3) : "Verified"}</span>
        </div>
      `;
      evidenceChecklistContainer.appendChild(p3);
    }

    // 3. Technical Explainable AI (SHAP) Factor Breakdown Cards in Drawer
    if (resultInsightsList) {
      resultInsightsList.innerHTML = "";
      const cards = [];

      if (xai && Array.isArray(xai.topDrivers) && xai.topDrivers.length > 0) {
        xai.topDrivers.forEach((d) => {
          const isRisk = d.direction === "INCREASES_RISK" || d.shapValue > 0;
          cards.push({
            icon: isRisk ? "ph-bold ph-trend-up" : "ph-bold ph-trend-down",
            category: isRisk ? "Risk Driver" : "Supporting Driver",
            badgeClass: isRisk ? "badge-warning" : "badge-leaf",
            title: `${d.label || d.feature} (${d.relativeImportancePct || 0}%)`,
            text:
              d.explanation ||
              `SHAP Impact Weight: ${d.shapValue > 0 ? "+" : ""}${d.shapValue?.toFixed(3)}`,
          });
        });
      }

      if (cards.length === 0) {
        cards.push({
          icon: "ph-bold ph-sliders",
          category: "Multimodal Fusion Weight",
          badgeClass: "badge-primary",
          title: "Evidence Convergence Metric",
          text: "Vision, climate, and satellite features were fused with zero discrepancy flags detected.",
        });
      }

      cards.forEach((c) => {
        const el = document.createElement("div");
        el.className = "insight-card";
        el.innerHTML = `
          <div class="insight-card-top">
            <div class="insight-icon-badge ${c.badgeClass}">
              <i class="${c.icon}"></i>
            </div>
            <div class="insight-meta">
              <span class="insight-category-pill">${c.category}</span>
              <div class="insight-card-title">${c.title}</div>
            </div>
          </div>
          <div class="insight-card-text">${c.text}</div>
        `;
        resultInsightsList.appendChild(el);
      });
    }
  }

  // Toggle Technical SHAP Drawer
  btnToggleTechnicalShap?.addEventListener("click", () => {
    technicalShapDrawer?.classList.toggle("open");
    btnToggleTechnicalShap?.classList.toggle("open");
  });

  // JSON Accordion Toggle
  jsonAccordionHeader?.addEventListener("click", () => {
    jsonAccordionContent.classList.toggle("open");
  });

  // -------------------------------------------------------------
  // Recent Claims Management
  // -------------------------------------------------------------
  const STORAGE_KEY_RECENT = "recent_claims_list";

  function getRecentClaims() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY_RECENT)) || [];
    } catch {
      return [];
    }
  }

  function saveRecentClaim(claimId, decision, cropType) {
    const list = getRecentClaims().filter((item) => item.claimId !== claimId);
    list.unshift({
      claimId,
      decision,
      cropType,
      timestamp: new Date().toISOString(),
    });
    if (list.length > 8) list.pop();
    localStorage.setItem(STORAGE_KEY_RECENT, JSON.stringify(list));
    renderRecentChips(currentLoadedClaims);
  }

  // -------------------------------------------------------------
  // Claims History Register, Dossier & Audit Timeline
  // -------------------------------------------------------------
  let currentLoadedClaims = [];
  let selectedClaimId = null;

  async function loadClaimsHistory(forceRefresh = false) {
    if (claimsCountBadge) {
      claimsCountBadge.innerHTML =
        '<i class="ph-bold ph-spinner ph-spin"></i> Fetching records...';
    }
    if (btnRefreshClaimsHistory) {
      btnRefreshClaimsHistory.disabled = true;
    }
    const refreshIcon = document.getElementById("iconRefreshClaims");
    if (refreshIcon) refreshIcon.classList.add("ph-spin");

    try {
      const res = await window.ApiClient.listClaims(50);
      const claimsList = Array.isArray(res)
        ? res
        : Array.isArray(res?.data)
          ? res.data
          : [];
      currentLoadedClaims = claimsList;

      renderRecentChips(claimsList);
      renderClaimsTable(claimsList);

      if (claimsCountBadge) {
        claimsCountBadge.innerText = `Showing ${claimsList.length} recorded claim(s)`;
      }

      // If no claim selected yet, automatically select the latest one
      if (claimsList.length > 0 && !selectedClaimId) {
        searchClaim(claimsList[0].claimId);
      }
    } catch (err) {
      console.error("Error loading claims history:", err);
      if (claimsHistoryTableBody) {
        claimsHistoryTableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:1.5rem; color:var(--color-danger)">Failed to load claims: ${err.message}</td></tr>`;
      }
      if (claimsCountBadge) {
        claimsCountBadge.innerText = "Sync failed";
      }
    } finally {
      if (btnRefreshClaimsHistory) {
        btnRefreshClaimsHistory.disabled = false;
      }
      if (refreshIcon) refreshIcon.classList.remove("ph-spin");
    }
  }

  function renderRecentChips(claimsList) {
    if (!recentClaimsContainer) return;
    recentClaimsContainer.innerHTML = "";

    const displayList =
      claimsList && claimsList.length > 0
        ? claimsList.slice(0, 8)
        : getRecentClaims();

    if (displayList.length === 0) {
      recentClaimsContainer.innerHTML =
        '<span style="font-size:0.8rem;color:var(--color-text-dim)">No claims recorded yet.</span>';
      return;
    }

    displayList.forEach((item) => {
      const cid = item.claimId;
      const dec = item.decision || item.status || "EVALUATING";
      const decClass =
        dec === "APPROVED"
          ? "approved"
          : dec === "REJECTED"
            ? "rejected"
            : "evaluating";

      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "health-status-badge";
      chip.style.cursor = "pointer";
      chip.innerHTML = `<i class="ph ph-receipt" style="color:var(--color-primary)"></i> <span>${cid}</span> <span class="status-pill ${decClass}" style="font-size:0.65rem; padding:0.1rem 0.35rem;">${dec}</span>`;
      chip.addEventListener("click", () => {
        if (inputSearchClaimId) inputSearchClaimId.value = cid;
        searchClaim(cid);
      });
      recentClaimsContainer.appendChild(chip);
    });
  }

  function renderClaimsTable(claimsList) {
    if (!claimsHistoryTableBody) return;
    claimsHistoryTableBody.innerHTML = "";

    if (!claimsList || claimsList.length === 0) {
      claimsHistoryTableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:1.5rem; color:var(--color-text-dim)">No claims submitted to the system yet.</td></tr>`;
      return;
    }

    claimsList.forEach((claim) => {
      const tr = document.createElement("tr");
      tr.className = "claim-row";
      tr.setAttribute("data-claim-id", claim.claimId);
      if (claim.claimId === selectedClaimId) {
        tr.classList.add("selected");
      }

      const rawDate = claim.createdAt || claim.incidentDate || claim.lossDate;
      const dateStr = rawDate
        ? new Date(rawDate).toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
            year: "numeric",
          })
        : "N/A";
      const dec = claim.decision || claim.status || "EVALUATING";
      const decClass =
        dec === "APPROVED"
          ? "approved"
          : dec === "REJECTED"
            ? "rejected"
            : "evaluating";
      const payoutVal =
        claim.recommendedPayout != null
          ? `${claim.recommendedPayout}%`
          : claim.payoutPercentage != null
            ? `${claim.payoutPercentage}%`
            : "0%";
      const cropName = (claim.cropType || "Crop").toUpperCase();
      const claimedPct =
        claim.claimedDamage != null ? `${claim.claimedDamage}%` : "N/A";

      tr.innerHTML = `
        <td><code style="color:var(--color-primary);font-weight:700">${claim.claimId}</code></td>
        <td>${dateStr}</td>
        <td><strong>${claim.farmerId || "Farmer"}</strong></td>
        <td>${cropName}</td>
        <td>${claimedPct}</td>
        <td><span class="status-pill ${decClass}">${dec}</span></td>
        <td><strong>${payoutVal}</strong></td>
        <td style="text-align:right">
          <button type="button" class="btn-table-action" data-cid="${claim.claimId}">
            <i class="ph ph-eye"></i> View
          </button>
        </td>
      `;

      tr.addEventListener("click", (e) => {
        searchClaim(claim.claimId);
      });

      claimsHistoryTableBody.appendChild(tr);
    });
  }

  btnRefreshClaimsHistory?.addEventListener("click", () => {
    loadClaimsHistory(true);
  });

  btnClearClaimsHistory?.addEventListener("click", async () => {
    if (
      !confirm(
        "Are you sure you want to clear all historical claims and audit records?",
      )
    )
      return;
    try {
      localStorage.removeItem(STORAGE_KEY_RECENT);
      await window.ApiClient.clearClaims();
      showToast(
        "All historical claims and audit records cleared successfully.",
        "info",
      );
      selectedClaimId = null;
      if (inputSearchClaimId) inputSearchClaimId.value = "";
      if (lookupStatusAlert) lookupStatusAlert.style.display = "none";
      if (claimDossierHeader) claimDossierHeader.style.display = "none";
      if (dossierDetailsContainer)
        dossierDetailsContainer.style.display = "none";
      if (timelineSectionWrapper) timelineSectionWrapper.style.display = "none";
      if (auditTimeline) auditTimeline.innerHTML = "";
      loadClaimsHistory(true);
    } catch (err) {
      showToast(`Failed to clear claims: ${err.message}`, "error");
    }
  });

  btnToggleAuditTrail?.addEventListener("click", () => {
    const isOpen = auditTrailDrawer?.classList.toggle("open");
    btnToggleAuditTrail.classList.toggle("open", isOpen);
    if (caretAuditTrail) {
      caretAuditTrail.style.transform = isOpen
        ? "rotate(180deg)"
        : "rotate(0deg)";
    }
  });

  btnSearchClaim?.addEventListener("click", () => {
    const query = (inputSearchClaimId?.value || "").trim();
    if (!query) {
      showToast("Please enter a Claim ID to search", "warning");
      return;
    }
    searchClaim(query);
  });

  inputSearchClaimId?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      btnSearchClaim?.click();
    }
  });

  async function searchClaim(claimId) {
    if (!claimId) return;
    selectedClaimId = claimId;
    if (inputSearchClaimId) inputSearchClaimId.value = claimId;

    // Highlight row in table
    if (claimsHistoryTableBody) {
      claimsHistoryTableBody.querySelectorAll("tr.claim-row").forEach((row) => {
        if (row.getAttribute("data-claim-id") === claimId) {
          row.classList.add("selected");
        } else {
          row.classList.remove("selected");
        }
      });
    }

    if (claimDossierHeader) claimDossierHeader.style.display = "none";
    if (lookupStatusAlert) {
      lookupStatusAlert.innerHTML = `<div class="spinner"></div> Loading verification dossier and audit trail for <strong>${claimId}</strong>...`;
      lookupStatusAlert.style.display = "flex";
    }
    if (dossierDetailsContainer) dossierDetailsContainer.style.display = "none";
    if (timelineSectionWrapper) timelineSectionWrapper.style.display = "none";
    if (auditTrailDrawer) auditTrailDrawer.classList.remove("open");
    if (btnToggleAuditTrail) btnToggleAuditTrail.classList.remove("open");
    if (caretAuditTrail) caretAuditTrail.style.transform = "rotate(0deg)";
    if (auditTimeline) auditTimeline.innerHTML = "";

    try {
      // 1. Fetch full claim details
      const claimRes = await window.ApiClient.getClaim(claimId);
      const claim = claimRes?.data || claimRes;

      // 2. Fetch audit trail
      const auditRes = await window.ApiClient.getAuditTrail(claimId);
      const auditLogs = auditRes?.data || claim.auditLogs || [];

      const payoutText =
        claim.recommendedPayout != null
          ? `${claim.recommendedPayout}%`
          : claim.payoutPercentage != null
            ? `${claim.payoutPercentage}%`
            : "0%";
      const decText = claim.decision || claim.status || "EVALUATING";
      const decClass =
        decText === "APPROVED"
          ? "approved"
          : decText === "REJECTED"
            ? "rejected"
            : "evaluating";
      const rawDate = claim.createdAt || claim.incidentDate || claim.lossDate;
      const dateStr = rawDate
        ? new Date(rawDate).toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
            year: "numeric",
          })
        : "N/A";

      if (lookupStatusAlert) {
        lookupStatusAlert.style.display = "none";
      }

      if (claimDossierHeader) {
        claimDossierHeader.innerHTML = `
          <div class="decision-hero decision-${decText} dossier-hero">
            <div class="decision-info">
              <span class="decision-tag">Verified Claim Record</span>
              <div class="decision-title">
                <span>${decText}</span>
              </div>
              <div class="decision-meta-row">
                <span>Farmer: <strong style="color:var(--color-text)">${claim.farmerId || "N/A"}</strong></span>
                <span class="meta-divider">|</span>
                <span>Crop: <strong style="color:var(--color-text)">${(claim.cropType || "N/A").toUpperCase()}</strong></span>
                <span class="meta-divider">|</span>
                <span>Loss Date: <strong style="color:var(--color-text)">${dateStr}</strong></span>
                <span class="meta-divider">|</span>
                <span>Claimed Loss: <strong style="color:var(--color-text)">${claim.claimedDamage || 0}%</strong></span>
                <span class="meta-divider">|</span>
                <span>Payout: <strong style="color:${decText === "APPROVED" ? "var(--color-primary)" : decText === "REJECTED" ? "var(--color-danger-text)" : "var(--color-warning-text)"}">${payoutText}</strong></span>
              </div>
            </div>
            <div style="display:flex; flex-direction:column; align-items:flex-end; gap:0.4rem;">
              <div class="claim-id-badge">ID: ${claim.claimId}</div>
              <span style="font-size:var(--font-size-caption); color:var(--color-text-dim); font-family:var(--font-mono);">${auditLogs.length} Verified Events</span>
            </div>
          </div>
        `;
        claimDossierHeader.style.display = "block";
      }

      renderDossierSnapshot(claim);
      renderAuditTimeline(auditLogs);
      saveRecentClaim(claim.claimId, decText, claim.cropType);
    } catch (err) {
      console.error("Error in searchClaim:", err);
      if (claimDossierHeader) claimDossierHeader.style.display = "none";
      if (lookupStatusAlert) {
        lookupStatusAlert.innerHTML = `<span style="color:var(--color-danger)">${err.message}</span>`;
        lookupStatusAlert.style.display = "flex";
      }
      showToast(`Lookup failed: ${err.message}`, "error");
    }
  }

  function renderDossierSnapshot(claim) {
    if (!dossierDetailsContainer) return;

    const visual = claim.visualAssessment || claim.assessment || {};
    const weather = claim.weatherAssessment || visual.weatherDetails || {};
    const sat = claim.satelliteAssessment || visual.satelliteDetails || {};

    const visualDmg = claim.damageScore ?? visual.damageSeverity ?? 0;
    const visualClass = claim.predictedClass || visual.visualClass || "HEALTHY";
    const visualConf = (
      (claim.confidence || visual.confidence || 0.9) * 100
    ).toFixed(0);

    const weatherHazard =
      weather.weatherHazard || visual.damageCause || "NORMAL";
    const rainMm =
      weather.metrics?.rainfallMm != null
        ? weather.metrics.rainfallMm
        : claim.rainfall != null
          ? claim.rainfall
          : 0;
    const weatherScore = (
      weather.weatherScore ??
      visual.weatherScore ??
      50
    ).toFixed(0);

    const satLossPct = (
      sat.damagedAreaPercentage ??
      visual.damagedAreaPercentage ??
      0
    ).toFixed(0);
    const satHa = sat.damagedAreaHectares ?? (claim.fieldAreaHectares || 0);
    const ndviDrop =
      sat.ndviDrop != null ? Number(sat.ndviDrop).toFixed(3) : "0.000";

    const fraudScoreVal = (
      claim.fraudRiskScore ??
      visual.fraudRiskScore ??
      0
    ).toFixed(3);
    const riskLevelVal =
      claim.fraudRiskLevel ||
      claim.riskLevel ||
      visual.fraudRiskLevel ||
      "LOW_RISK";
    const flagsCount = (claim.fraudFlags || visual.fraudFlags || []).length;

    let execSummaryHtml = "";
    const execText = claim.explainableAi?.executiveSummary;
    if (execText) {
      const dec = claim.decision || claim.status || "EVALUATING";
      const decClass = dec === "APPROVED" ? "approved" : "rejected";
      execSummaryHtml = `
        <div class="executive-summary-card" style="margin-bottom: 0.85rem;">
          <div class="exec-summary-top">
            <span class="exec-summary-badge"><i class="ph-bold ph-sparkle"></i> Multimodal Verification Verdict</span>
            <span class="exec-summary-verdict ${decClass}">${dec}</span>
          </div>
          <p class="exec-summary-text">${execText}</p>
        </div>
      `;
    }

    dossierDetailsContainer.innerHTML = `
      ${execSummaryHtml}
      <div class="dossier-grid">
        <div class="dossier-metric-card">
          <div class="dossier-metric-title"><i class="ph-bold ph-camera" style="color:var(--color-primary)"></i> Field Photo Evidence</div>
          <div class="dossier-metric-val">${visualDmg}% <span style="font-size:0.8rem;font-weight:600;color:var(--color-text-muted)">Leaf Damage</span></div>
          <div class="dossier-metric-sub">Class: <strong>${visualClass}</strong> <span style="opacity:0.3;margin:0 0.35rem">|</span> Certainty: <strong>${visualConf}%</strong></div>
        </div>

        <div class="dossier-metric-card">
          <div class="dossier-metric-title"><i class="ph-bold ph-cloud-rain" style="color:#3498db"></i> Climate & Weather</div>
          <div class="dossier-metric-val">${weatherHazard} <span style="font-size:0.8rem;font-weight:600;color:var(--color-text-muted)">Hazard</span></div>
          <div class="dossier-metric-sub">Precipitation: <strong>${rainMm} mm</strong> <span style="opacity:0.3;margin:0 0.35rem">|</span> Weather Score: <strong>${weatherScore}%</strong></div>
        </div>

        <div class="dossier-metric-card">
          <div class="dossier-metric-title"><i class="ph-bold ph-satellite" style="color:#9b59b6"></i> Satellite Farmland</div>
          <div class="dossier-metric-val">${satLossPct}% <span style="font-size:0.8rem;font-weight:600;color:var(--color-text-muted)">Plot Area Loss</span></div>
          <div class="dossier-metric-sub">Affected: <strong>${satHa} ha</strong> <span style="opacity:0.3;margin:0 0.35rem">|</span> NDVI Drop: <strong>${ndviDrop}</strong></div>
        </div>

        <div class="dossier-metric-card">
          <div class="dossier-metric-title"><i class="ph-bold ph-shield-check" style="color:#e67e22"></i> Fraud Risk & Integrity</div>
          <div class="dossier-metric-val">${fraudScoreVal} <span style="font-size:0.8rem;font-weight:600;color:var(--color-text-muted)">Score</span></div>
          <div class="dossier-metric-sub">Level: <strong>${riskLevelVal}</strong> <span style="opacity:0.3;margin:0 0.35rem">|</span> Anomaly Flags: <strong>${flagsCount}</strong></div>
        </div>
      </div>
    `;

    dossierDetailsContainer.style.display = "block";
  }

  function renderAuditTimeline(logs) {
    if (!auditTimeline) return;
    auditTimeline.innerHTML = "";

    if (!logs || logs.length === 0) {
      if (timelineSectionWrapper) timelineSectionWrapper.style.display = "none";
      auditTimeline.innerHTML =
        '<div style="color:var(--color-text-dim);font-size:0.85rem;padding:1rem 0;">No audit events recorded for this claim.</div>';
      return;
    }

    if (timelineSectionWrapper) {
      timelineSectionWrapper.style.display = "block";
      if (auditEventCountBadge) {
        auditEventCountBadge.innerText = `${logs.length} events`;
      }
    }

    const eventIcons = {
      CLAIM_SUBMITTED: "ph-file-text",
      VISION_ASSESSED: "ph-camera",
      WEATHER_VERIFIED: "ph-cloud-rain",
      SATELLITE_VERIFIED: "ph-satellite",
      FRAUD_EVALUATED: "ph-shield-warning",
      DECISION_ISSUED: "ph-seal-check",
      EXPLAINABILITY_GENERATED: "ph-sparkle",
    };

    logs.forEach((log) => {
      const item = document.createElement("div");
      item.className = "timeline-item";
      const timeVal = log.createdAt || log.timestamp;
      const timeStr = timeVal ? new Date(timeVal).toLocaleString() : "N/A";
      const icon = eventIcons[log.eventType] || "ph-tag";

      // Format key parameter badges
      let tagsHtml = "";
      const details = log.details || {};

      if (log.eventType === "CLAIM_SUBMITTED") {
        tagsHtml = `
          <span class="timeline-tag-pill">Farmer: <strong>${details.farmerId || "N/A"}</strong></span>
          <span class="timeline-tag-pill">Crop: <strong>${details.cropType || "N/A"}</strong></span>
          <span class="timeline-tag-pill">Claimed Damage: <strong>${details.claimedDamage || 0}%</strong></span>
          <span class="timeline-tag-pill">Coordinates: <strong>${details.latitude?.toFixed?.(3) || details.latitude}, ${details.longitude?.toFixed?.(3) || details.longitude}</strong></span>
        `;
      } else if (log.eventType === "VISION_ASSESSED") {
        tagsHtml = `
          <span class="timeline-tag-pill">Visual Status: <strong>${details.visualClass || "N/A"}</strong></span>
          <span class="timeline-tag-pill">Damage Severity: <strong>${details.damageSeverity || 0}%</strong></span>
          <span class="timeline-tag-pill">Confidence: <strong>${((details.confidence || 0) * 100).toFixed(1)}%</strong></span>
          <span class="timeline-tag-pill">Image Hash: <strong>${(details.imageHash || "").slice(0, 10)}...</strong></span>
        `;
      } else if (log.eventType === "WEATHER_VERIFIED") {
        tagsHtml = `
          <span class="timeline-tag-pill">Meteorological Hazard: <strong>${details.weatherHazard || details.damageCause || "NORMAL"}</strong></span>
          <span class="timeline-tag-pill">Weather Score: <strong>${details.weatherScore || 0}%</strong></span>
          <span class="timeline-tag-pill">Anomaly Detected: <strong>${details.anomalyDetected ? "YES" : "NO"}</strong></span>
          <span class="timeline-tag-pill">Source: <strong>${details.dataSource || "LIVE_ERA5_API"}</strong></span>
        `;
      } else if (log.eventType === "SATELLITE_VERIFIED") {
        tagsHtml = `
          <span class="timeline-tag-pill">Vegetation Loss: <strong>${details.damagedAreaPercentage || 0}%</strong></span>
          <span class="timeline-tag-pill">NDVI Drop: <strong>${details.ndviDrop != null ? details.ndviDrop : "N/A"}</strong></span>
          <span class="timeline-tag-pill">Field Size: <strong>${details.fieldAreaHectares || "N/A"} ha</strong></span>
          <span class="timeline-tag-pill">Classification: <strong>${details.damageClassification || "N/A"}</strong></span>
        `;
      } else if (log.eventType === "FRAUD_EVALUATED") {
        const flagList = details.fraudFlags || [];
        tagsHtml = `
          <span class="timeline-tag-pill">Risk Level: <strong>${details.fraudRiskLevel || "LOW_RISK"}</strong></span>
          <span class="timeline-tag-pill">Risk Score: <strong>${details.fraudRiskScore != null ? Number(details.fraudRiskScore).toFixed(4) : 0}</strong></span>
          <span class="timeline-tag-pill">Flags: <strong>${flagList.length > 0 ? flagList.join(", ") : "None"}</strong></span>
        `;
      } else if (log.eventType === "DECISION_ISSUED") {
        tagsHtml = `
          <span class="timeline-tag-pill">Verdict: <strong>${details.decision || "N/A"}</strong></span>
          <span class="timeline-tag-pill">Recommended Payout: <strong>${details.recommendedPayout || 0}%</strong></span>
          <span class="timeline-tag-pill">Ground Truth Damage: <strong>${details.verifiedGroundTruthDamage || 0}%</strong></span>
        `;
      } else if (log.eventType === "EXPLAINABILITY_GENERATED") {
        const drivers = details.topDrivers || [];
        tagsHtml = `
          <span class="timeline-tag-pill">Key Factors: <strong>${drivers.slice(0, 2).join(", ") || "Multimodal correlation"}</strong></span>
        `;
      }

      item.innerHTML = `
        <div class="timeline-dot"></div>
        <div class="timeline-card">
          <div class="timeline-header">
            <span class="timeline-event-name"><i class="ph-bold ${icon}"></i> ${log.eventType}</span>
            <span class="timeline-time"><i class="ph ph-clock"></i> ${timeStr}</span>
          </div>
          <span class="timeline-actor"><i class="ph ph-user"></i> Actor: ${log.actor || "system"}</span>
          ${tagsHtml ? `<div class="timeline-tags-grid">${tagsHtml}</div>` : ""}
          <details style="margin-top:0.5rem; font-size:0.75rem; color:var(--color-text-dim); cursor:pointer;">
            <summary style="user-select:none;">Inspect Raw Cryptographic Event Payload</summary>
            <pre class="timeline-payload" style="margin-top:0.4rem;">${JSON.stringify(details, null, 2)}</pre>
          </details>
        </div>
      `;
      auditTimeline.appendChild(item);
    });
  }

  // Auto-initialize claims history on startup
  loadClaimsHistory();
});
