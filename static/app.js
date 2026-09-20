/**
 * SpecRt Web Application Logic
 * Multi-Page Navigation (Home Page vs Results Page)
 * DICOM-RT Parsing, TSP Optimization & 3D WebGL Trajectory Space
 */

document.addEventListener('DOMContentLoaded', () => {
  // Application State
  let currentResults = null;
  let isClosedTour = true;
  let currentPlotFilter = 'both'; // 'both', 'optimized', 'initial'

  // Page Elements
  const pageHome = document.getElementById('pageHome');
  const pageResults = document.getElementById('pageResults');
  const btnBackToHome = document.getElementById('btnBackToHome');
  const btnViewResults = document.getElementById('btnViewResults');

  // Home Page Elements
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('fileInput');
  const btnBrowse = document.getElementById('btnBrowse');
  const btnSample6 = document.getElementById('btnSample6');
  const btnSample8 = document.getElementById('btnSample8');
  const btnClosedMode = document.getElementById('btnClosedMode');
  const btnOpenMode = document.getElementById('btnOpenMode');
  const toleranceInput = document.getElementById('toleranceInput');
  const speedInput = document.getElementById('speedInput');
  const errorAlert = document.getElementById('errorAlert');
  const errorMessage = document.getElementById('errorMessage');
  const loadingOverlay = document.getElementById('loadingOverlay');

  // Matrix toggle buttons
  const btnMatrixTime = document.getElementById('btnMatrixTime');
  const btnMatrixDist = document.getElementById('btnMatrixDist');
  const matrixTypeLabel = document.getElementById('matrixTypeLabel');
  let activeMatrixType = 'time'; // 'time' or 'dist'

  // Background Customizer Elements
  const bgImageInput = document.getElementById('bgImageInput');
  const btnChangeBg = document.getElementById('btnChangeBg');
  const btnResetBg = document.getElementById('btnResetBg');

  // Results Page Elements
  const btnReset = document.getElementById('btnReset');
  const btnExportJSON = document.getElementById('btnExportJSON');
  const btnExportCSV = document.getElementById('btnExportCSV');
  const btnVisBoth = document.getElementById('btnVisBoth');
  const btnVisOptimized = document.getElementById('btnVisOptimized');
  const btnVisInitial = document.getElementById('btnVisInitial');
  const btnResetCamera = document.getElementById('btnResetCamera');

  // Tabs
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  // =========================================================================
  // Initialize Background Image from LocalStorage if user previously set one
  // =========================================================================
  const savedHomeBg = localStorage.getItem('specrt_home_bg');
  if (savedHomeBg) {
    document.documentElement.style.setProperty('--custom-home-bg', `url("${savedHomeBg}")`);
    if (btnResetBg) btnResetBg.style.display = 'inline-flex';
  }

  if (btnChangeBg && bgImageInput) {
    btnChangeBg.addEventListener('click', (e) => {
      e.stopPropagation();
      bgImageInput.click();
    });

    bgImageInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          const dataUrl = event.target.result;
          document.documentElement.style.setProperty('--custom-home-bg', `url("${dataUrl}")`);
          localStorage.setItem('specrt_home_bg', dataUrl);
          if (btnResetBg) btnResetBg.style.display = 'inline-flex';
        };
        reader.readAsDataURL(file);
      }
    });
  }

  if (btnResetBg) {
    btnResetBg.addEventListener('click', (e) => {
      e.stopPropagation();
      localStorage.removeItem('specrt_home_bg');
      document.documentElement.style.removeProperty('--custom-home-bg');
      btnResetBg.style.display = 'none';
      if (bgImageInput) bgImageInput.value = '';
    });
  }

  // =========================================================================
  // Multi-Page Navigation (Home Page <-> Results Page)
  // =========================================================================
  function showHomePage() {
    document.body.className = 'page-home';
    pageHome.style.display = 'block';
    pageResults.style.display = 'none';
    hideError();

    // If calculation exists, display "View Calculated Results" button
    if (currentResults) {
      btnViewResults.style.display = 'inline-flex';
    }
  }

  function showResultsPage() {
    document.body.className = 'page-results';
    pageHome.style.display = 'none';
    pageResults.style.display = 'block';

    // Refresh Plotly layout dimensions
    setTimeout(() => {
      const plotDiv = document.getElementById('plot3d');
      if (plotDiv && plotDiv.data) {
        Plotly.Plots.resize(plotDiv);
      }
    }, 50);
  }

  // Back to Home Button
  btnBackToHome.addEventListener('click', showHomePage);

  // Return to Results Button on Home Page
  btnViewResults.addEventListener('click', showResultsPage);

  // Reset / Upload New Plan Button
  btnReset.addEventListener('click', () => {
    currentResults = null;
    btnViewResults.style.display = 'none';
    fileInput.value = '';
    showHomePage();
  });

  // =========================================================================
  // Mode Toggle & Settings
  // =========================================================================
  btnClosedMode.addEventListener('click', () => {
    if (isClosedTour) return;
    isClosedTour = true;
    btnClosedMode.classList.add('active');
    btnOpenMode.classList.remove('active');
    if (currentResults && currentResults.filename.startsWith('synthetic_')) {
      fetchSample(currentResults.n_isocenters);
    }
  });

  btnOpenMode.addEventListener('click', () => {
    if (!isClosedTour) return;
    isClosedTour = false;
    btnOpenMode.classList.add('active');
    btnClosedMode.classList.remove('active');
    if (currentResults && currentResults.filename.startsWith('synthetic_')) {
      fetchSample(currentResults.n_isocenters);
    }
  });

  // Tabs Switcher
  tabButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      tabButtons.forEach((b) => b.classList.remove('active'));
      tabPanes.forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      const targetId = btn.getAttribute('data-tab');
      const targetPane = document.getElementById(targetId);
      if (targetPane) targetPane.classList.add('active');
    });
  });

  // Dropzone File Handlers
  btnBrowse.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
  });

  ['dragleave', 'dragend'].forEach((type) => {
    dropzone.addEventListener(type, () => dropzone.classList.remove('drag-over'));
  });

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  });

  // Quick Sample Buttons (No icons)
  btnSample6.addEventListener('click', (e) => {
    e.stopPropagation();
    fetchSample(6);
  });

  btnSample8.addEventListener('click', (e) => {
    e.stopPropagation();
    fetchSample(8);
  });

  // Visualization Trace Filters
  btnVisBoth.addEventListener('click', () => setVisFilter('both'));
  btnVisOptimized.addEventListener('click', () => setVisFilter('optimized'));
  btnVisInitial.addEventListener('click', () => setVisFilter('initial'));
  btnResetCamera.addEventListener('click', () => {
    const plotDiv = document.getElementById('plot3d');
    if (plotDiv && plotDiv.data) {
      Plotly.relayout(plotDiv, {
        'scene.camera': {
          eye: { x: 1.6, y: 1.6, z: 1.4 },
        },
      });
    }
  });

  // =========================================================================
  // API Requests
  // =========================================================================
  async function handleFileUpload(file) {
    hideError();
    showLoading();

    const speedVal = speedInput ? parseFloat(speedInput.value) || 20.0 : 20.0;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('closed', isClosedTour);
    formData.append('tolerance_mm', parseFloat(toleranceInput.value) || 0.1);
    formData.append('machine_speed_mms', speedVal);

    try {
      const resp = await fetch('/api/optimize', {
        method: 'POST',
        body: formData,
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || 'Failed to analyze DICOM-RT file.');
      }

      currentResults = data;
      renderResults(data);
      showResultsPage(); // Smooth transition to Second Page
    } catch (err) {
      showError(err.message);
    } finally {
      hideLoading();
    }
  }

  async function fetchSample(n) {
    hideError();
    showLoading();

    const speedVal = speedInput ? parseFloat(speedInput.value) || 20.0 : 20.0;
    const formData = new FormData();
    formData.append('n', n);
    formData.append('closed', isClosedTour);
    formData.append('machine_speed_mms', speedVal);

    try {
      const resp = await fetch('/api/sample', {
        method: 'POST',
        body: formData,
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || 'Failed to generate synthetic sample.');
      }

      currentResults = data;
      renderResults(data);
      showResultsPage(); // Smooth transition to Second Page
    } catch (err) {
      showError(err.message);
    } finally {
      hideLoading();
    }
  }

  async function fetchSample2() {
    hideError();
    showLoading();

    const speedVal = speedInput ? parseFloat(speedInput.value) || 20.0 : 20.0;
    const formData = new FormData();
    formData.append('closed', isClosedTour);
    formData.append('machine_speed_mms', speedVal);

    try {
      const resp = await fetch('/api/sample2', {
        method: 'POST',
        body: formData,
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.detail || 'Failed to load 2D planar sample plan.');
      }

      currentResults = data;
      renderResults(data);
      showResultsPage();
    } catch (err) {
      showError(err.message);
    } finally {
      hideLoading();
    }
  }

  function showLoading() {
    loadingOverlay.style.display = 'block';
  }

  function hideLoading() {
    loadingOverlay.style.display = 'none';
  }

  function showError(msg) {
    errorMessage.textContent = msg;
    errorAlert.style.display = 'flex';
  }

  function hideError() {
    errorAlert.style.display = 'none';
  }

  // =========================================================================
  // Render Optimization Results on Page 2
  // =========================================================================
  function renderResults(data) {
    // Header info
    document.getElementById('currentFileName').textContent = data.filename;
    document.getElementById('currentModeBadge').textContent = data.closed
      ? 'Closed Tour (Loop)'
      : 'Open Path (One-Way)';

    const speedBadge = document.getElementById('currentSpeedBadge');
    if (speedBadge) {
      speedBadge.textContent = `${data.metrics.machine_speed_mms || 20} mm/s Couch`;
    }

    const optRoute = data.routes.optimized || data.routes.two_opt;
    const algoTag = data.algorithm_tag || (optRoute.algorithm_tag || '(2-Opt)');

    // Dynamic Title Updates
    const kpiOptTitle = document.getElementById('kpiOptimizedTitle');
    if (kpiOptTitle) {
      kpiOptTitle.textContent = `Optimized Transit Time ${algoTag}`;
    }
    const kpiOptSub = document.getElementById('kpiOptimizedSub');
    if (kpiOptSub) {
      kpiOptSub.textContent = `${(optRoute.distance_mm || data.metrics.optimized_distance_mm).toFixed(1)} mm at ${data.metrics.machine_speed_mms || 20} mm/s`;
    }
    const recTitle = document.getElementById('recommendedOrderTitle');
    if (recTitle) {
      recTitle.textContent = `Recommended Visiting Order ${algoTag}`;
    }

    // KPI Cards - Primary metric is Machine Transit Time (seconds)
    const metrics = data.metrics;
    const savedTimeElem = document.getElementById('kpiSavedTime');
    if (savedTimeElem) savedTimeElem.textContent = metrics.time_saved_s.toFixed(2);
    document.getElementById('kpiSavedPct').textContent = `${metrics.savings_percent.toFixed(1)}% Reduction`;
    
    const savedDistSub = document.getElementById('kpiSavedDistSub');
    if (savedDistSub) {
      savedDistSub.textContent = `${metrics.distance_saved_mm.toFixed(1)} mm distance saved`;
    }

    const optTimeElem = document.getElementById('kpiOptimizedTime');
    if (optTimeElem) optTimeElem.textContent = metrics.optimized_time_s.toFixed(2);

    const initTimeElem = document.getElementById('kpiInitialTime');
    if (initTimeElem) initTimeElem.textContent = metrics.initial_time_s.toFixed(2);

    const initSubElem = document.getElementById('kpiInitialSub');
    if (initSubElem) {
      initSubElem.textContent = `Original sequence (${metrics.initial_distance_mm.toFixed(1)} mm)`;
    }

    document.getElementById('kpiPointCount').textContent = data.n_isocenters;

    const totalBeams = data.isocenters.reduce((acc, p) => acc + p.beam_names.length, 0);
    document.getElementById('kpiBeamCount').textContent = `${totalBeams} total beams mapped`;

    const kpiExactGap = document.getElementById('kpiExactGap');
    const kpiExactStatus = document.getElementById('kpiExactStatus');
    const isHeldKarpActive = data.algorithm_used && data.algorithm_used.includes('Held-Karp');

    if (metrics.held_karp_eligible && metrics.held_karp_gap_pct !== null) {
      if (isHeldKarpActive) {
        kpiExactGap.textContent = '0.00%';
        kpiExactStatus.textContent = metrics.held_karp_gap_pct > 0
          ? `Exact Global Optimum (+${metrics.held_karp_gap_pct.toFixed(1)}% vs 2-Opt)`
          : 'Exact Global Optimum Applied';
      } else {
        kpiExactGap.textContent = `${metrics.held_karp_gap_pct.toFixed(2)}%`;
        kpiExactStatus.textContent = metrics.held_karp_gap_pct === 0
          ? 'Exact Global Optimum'
          : 'Near-Optimal Gap (2-Opt)';
      }
    } else {
      kpiExactGap.textContent = 'N/A';
      kpiExactStatus.textContent = `Skipped (N=${data.n_isocenters} > 13 limit)`;
    }

    document.getElementById('kpiExecutionTime').textContent = data.execution_time_ms;

    // Recommended Path Sequence List
    const routeStrElem = document.getElementById('routePathString');
    routeStrElem.textContent = optRoute.path_str;

    const legsList = document.getElementById('legsList');
    legsList.innerHTML = '';
    const legs = optRoute.legs || [];
    document.getElementById('badgeStepCount').textContent = `${legs.length} Legs`;

    legs.forEach((leg) => {
      const card = document.createElement('div');
      card.className = 'step-card';
      const timeStr = leg.time_s !== undefined ? `${leg.time_s.toFixed(1)}s` : '';
      card.innerHTML = `
        <span class="step-num">#${leg.step}</span>
        <div class="step-transition">
          <span class="node-pill from">${leg.from_label}</span>
          <span class="step-arrow">→</span>
          <span class="node-pill to">${leg.to_label}</span>
        </div>
        <span class="step-dist">${timeStr} <small style="opacity: 0.8; font-weight: normal;">(${leg.distance_mm.toFixed(1)} mm)</small></span>
      `;
      legsList.appendChild(card);
    });

    // Populate Tables
    populateComparisonTable(data);
    populatePointsTable(data);
    populateMatrixTable(data);

    // Render 3D Plot
    renderPlot3D(data);

    // Setup Export Listeners
    setupExportHandlers(data);
  }

  // =========================================================================
  // Plotly 3D WebGL Visualizer
  // =========================================================================
  function renderPlot3D(data) {
    const isocenters = data.isocenters;
    const closed = data.closed;

    // 1. Isocenter Nodes Trace
    const xNodes = isocenters.map((p) => p.x);
    const yNodes = isocenters.map((p) => p.y);
    const zNodes = isocenters.map((p) => p.z);
    const nodeLabels = isocenters.map((p) => p.label);
    const hoverTexts = isocenters.map((p) => {
      const beams = p.beam_names.join(', ') || 'None';
      return `<b>${p.label}</b><br>X: ${p.x.toFixed(1)} mm<br>Y: ${p.y.toFixed(1)} mm<br>Z: ${p.z.toFixed(1)} mm<br>Beams: ${beams}`;
    });

    const nodesTrace = {
      name: 'Isocenters',
      type: 'scatter3d',
      mode: 'markers+text',
      x: xNodes,
      y: yNodes,
      z: zNodes,
      text: nodeLabels,
      textposition: 'top center',
      textfont: {
        family: 'Outfit, sans-serif',
        size: 13,
        color: '#FFFFFF',
      },
      hovertext: hoverTexts,
      hoverinfo: 'text',
      marker: {
        size: 8,
        color: '#FFFFFF',
        line: { color: '#961E4C', width: 2.5 },
        opacity: 0.98,
      },
    };

    // Helper to get line coordinates
    function getRouteCoords(routeIndices) {
      const x = [];
      const y = [];
      const z = [];
      routeIndices.forEach((idx) => {
        const pt = isocenters[idx];
        x.push(pt.x);
        y.push(pt.y);
        z.push(pt.z);
      });
      if (closed && routeIndices.length > 1) {
        const start = isocenters[routeIndices[0]];
        x.push(start.x);
        y.push(start.y);
        z.push(start.z);
      }
      return { x, y, z };
    }

    // 2. Initial Route Trace (Dashed, Translucent White)
    const initialCoords = getRouteCoords(data.routes.initial.indices);
    const initialTrace = {
      name: `Initial Route (${data.routes.initial.cost.toFixed(1)} mm)`,
      type: 'scatter3d',
      mode: 'lines',
      x: initialCoords.x,
      y: initialCoords.y,
      z: initialCoords.z,
      line: {
        color: 'rgba(255, 255, 255, 0.45)',
        width: 3.5,
        dash: 'dash',
      },
      hoverinfo: 'name',
    };

    // 3. Recommended Optimized Route Trace (Bright Solid White)
    const optRoute = data.routes.optimized || data.routes.two_opt;
    const algoTag = data.algorithm_tag || (optRoute.algorithm_tag || '(2-Opt)');
    const optCoords = getRouteCoords(optRoute.indices);
    const twoOptTrace = {
      name: `Optimized Route ${algoTag} (${optRoute.cost.toFixed(1)} mm)`,
      type: 'scatter3d',
      mode: 'lines',
      x: optCoords.x,
      y: optCoords.y,
      z: optCoords.z,
      line: {
        color: '#FFFFFF',
        width: 6,
      },
      hoverinfo: 'name',
    };

    const plotData = [nodesTrace, initialTrace, twoOptTrace];

    const layout = {
      paper_bgcolor: 'rgba(65, 12, 33, 0.9)',
      plot_bgcolor: 'rgba(65, 12, 33, 0.9)',
      margin: { l: 0, r: 0, b: 0, t: 0 },
      showlegend: true,
      legend: {
        x: 0.02,
        y: 0.98,
        font: { family: 'Outfit, sans-serif', color: '#FFFFFF', size: 11 },
        bgcolor: 'rgba(85, 14, 42, 0.9)',
        bordercolor: 'rgba(255, 255, 255, 0.35)',
        borderwidth: 1,
      },
      scene: {
        xaxis: {
          title: 'X (mm)',
          color: '#FFFFFF',
          gridcolor: 'rgba(255, 255, 255, 0.18)',
          zerolinecolor: 'rgba(255, 255, 255, 0.5)',
          showbackground: false,
        },
        yaxis: {
          title: 'Y (mm)',
          color: '#FFFFFF',
          gridcolor: 'rgba(255, 255, 255, 0.18)',
          zerolinecolor: 'rgba(255, 255, 255, 0.5)',
          showbackground: false,
        },
        zaxis: {
          title: 'Z (mm)',
          color: '#FFFFFF',
          gridcolor: 'rgba(255, 255, 255, 0.18)',
          zerolinecolor: 'rgba(255, 255, 255, 0.5)',
          showbackground: false,
        },
        camera: {
          eye: { x: 1.6, y: 1.6, z: 1.4 },
        },
      },
    };

    const config = {
      responsive: true,
      displayModeBar: false,
    };

    Plotly.newPlot('plot3d', plotData, layout, config);
  }

  function setVisFilter(filter) {
    currentPlotFilter = filter;
    btnVisBoth.classList.toggle('active', filter === 'both');
    btnVisOptimized.classList.toggle('active', filter === 'optimized');
    btnVisInitial.classList.toggle('active', filter === 'initial');

    const plotDiv = document.getElementById('plot3d');
    if (!plotDiv || !plotDiv.data) return;

    if (filter === 'both') {
      Plotly.restyle(plotDiv, { visible: [true, true, true] });
    } else if (filter === 'optimized') {
      Plotly.restyle(plotDiv, { visible: [true, false, true] });
    } else if (filter === 'initial') {
      Plotly.restyle(plotDiv, { visible: [true, true, false] });
    }
  }

  // =========================================================================
  // Populate Tables (Pure White Typography & Transit Time Optimization)
  // =========================================================================
  function populateComparisonTable(data) {
    const tbody = document.getElementById('comparisonTableBody');
    tbody.innerHTML = '';

    const initial = data.routes.initial;
    const twoOpt = data.routes.two_opt;
    const heldKarp = data.routes.held_karp;

    // Lowest transit time determines the OPTIMIZED algorithm
    const hasHeldKarp = heldKarp && heldKarp.time_s !== null && heldKarp.time_s !== undefined;
    const isHeldKarpOptimal = hasHeldKarp && (heldKarp.time_s <= twoOpt.time_s + 1e-6);

    // Individual savings for 2-Opt vs initial
    const twoOptSavedTime = twoOpt.savings_time_s !== undefined
      ? twoOpt.savings_time_s
      : Math.max(0, initial.time_s - twoOpt.time_s);
    const twoOptSavedPct = twoOpt.savings_percent !== undefined
      ? twoOpt.savings_percent
      : (initial.time_s > 0 ? (twoOptSavedTime / initial.time_s) * 100 : 0);

    // Badges & styling (SpecRt palette)
    const badgeOptimized = '<span class="badge" style="background: #FFFFFF; color: #961E4C; font-weight: 800; letter-spacing: 0.5px;">OPTIMIZED</span>';
    const badgeHeuristic = '<span class="badge" style="background: rgba(255,255,255,0.22); color: #FFFFFF; font-weight: 700;">2-OPT HEURISTIC</span>';
    const badgeExactGlobal = '<span class="badge" style="background: rgba(255,255,255,0.22); color: #FFFFFF; font-weight: 700;">EXACT GLOBAL</span>';
    const badgeBaseline = '<span class="badge" style="background: rgba(255,255,255,0.18); color: #FFFFFF;">BASELINE</span>';

    const twoOptStatus = isHeldKarpOptimal ? badgeHeuristic : badgeOptimized;

    const rows = [
      {
        method: 'Initial',
        time_s: initial.time_s.toFixed(2),
        savings: '0.00 s (0.0%)',
        distance: initial.distance_mm.toFixed(2),
        route: initial.path_str,
        status: badgeBaseline,
        isBest: false,
      },
      {
        method: '2-Opt',
        time_s: twoOpt.time_s.toFixed(2),
        savings: `${Number(twoOptSavedTime).toFixed(2)} s (${Number(twoOptSavedPct).toFixed(1)}%)`,
        distance: twoOpt.distance_mm.toFixed(2),
        route: twoOpt.path_str,
        status: twoOptStatus,
        isBest: !isHeldKarpOptimal,
      },
    ];

    if (hasHeldKarp) {
      const hkSavedTime = heldKarp.savings_time_s !== undefined
        ? heldKarp.savings_time_s
        : Math.max(0, initial.time_s - heldKarp.time_s);
      const hkSavedPct = heldKarp.savings_percent !== undefined
        ? heldKarp.savings_percent
        : (initial.time_s > 0 ? (hkSavedTime / initial.time_s) * 100 : 0);

      const hkStatus = isHeldKarpOptimal ? badgeOptimized : badgeExactGlobal;

      rows.push({
        method: 'Held-Karp*',
        time_s: heldKarp.time_s.toFixed(2),
        savings: `${Number(hkSavedTime).toFixed(2)} s (${Number(hkSavedPct).toFixed(1)}%)`,
        distance: heldKarp.distance_mm.toFixed(2),
        route: heldKarp.path_str,
        status: hkStatus,
        isBest: isHeldKarpOptimal,
      });
    }

    rows.forEach((r) => {
      const tr = document.createElement('tr');
      if (r.isBest) {
        tr.style.background = 'rgba(255, 255, 255, 0.13)';
      }
      tr.innerHTML = `
        <td style="font-weight: 800; color: #FFFFFF;">${r.method}</td>
        <td style="font-family: var(--font-mono); font-weight: 800; color: #FFFFFF; font-size: 14px;">${r.time_s} s</td>
        <td style="color: #FFFFFF; font-weight: 800;">${r.savings}</td>
        <td style="font-family: var(--font-mono); color: #FFFFFF;">${r.distance} mm</td>
        <td style="font-family: var(--font-mono); font-size: 12px; color: #FFFFFF;">${r.route}</td>
        <td>${r.status}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function populatePointsTable(data) {
    document.getElementById('tabPointsCount').textContent = data.isocenters.length;
    const tbody = document.getElementById('pointsTableBody');
    tbody.innerHTML = '';

    data.isocenters.forEach((iso) => {
      const tr = document.createElement('tr');
      const beams = iso.beam_names.map((b) => `<span class="code-inline">${b}</span>`).join(' ');
      tr.innerHTML = `
        <td style="font-weight: 800; color: #FFFFFF;">${iso.label}</td>
        <td style="font-family: var(--font-mono); color: #FFFFFF;">${iso.x.toFixed(2)}</td>
        <td style="font-family: var(--font-mono); color: #FFFFFF;">${iso.y.toFixed(2)}</td>
        <td style="font-family: var(--font-mono); color: #FFFFFF;">${iso.z.toFixed(2)}</td>
        <td>${beams || '<span style="color: var(--text-muted)">None</span>'}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function populateMatrixTable(data) {
    const thead = document.getElementById('matrixTableHead');
    const tbody = document.getElementById('matrixTableBody');
    const labels = data.labels;

    // Use selected matrix type (time vs distance)
    const isTime = activeMatrixType === 'time';
    const matrix = isTime ? (data.time_matrix || data.cost_matrix) : data.distance_matrix;
    const unit = isTime ? 's' : 'mm';

    if (matrixTypeLabel) {
      matrixTypeLabel.textContent = isTime
        ? 'Pairwise Machine Transit Time Matrix (seconds)'
        : 'Pairwise 3D Distance Matrix (millimeters)';
    }

    // Header
    let headHtml = `<tr><th>Point</th>`;
    labels.forEach((lbl) => {
      headHtml += `<th>${lbl}</th>`;
    });
    headHtml += '</tr>';
    thead.innerHTML = headHtml;

    // Body
    tbody.innerHTML = '';
    matrix.forEach((row, i) => {
      let rowHtml = `<tr><td style="font-weight: 800; color: #FFFFFF;">${labels[i]}</td>`;
      row.forEach((val, j) => {
        let cls = '';
        const threshold = isTime ? 4.0 : 80;
        if (i === j) cls = 'matrix-diag';
        else if (val < threshold) cls = 'matrix-low';
        else if (val < threshold * 2) cls = 'matrix-med';
        else cls = 'matrix-high';

        rowHtml += `<td class="${cls}">${val.toFixed(1)}${unit}</td>`;
      });
      rowHtml += '</tr>';
      tbody.innerHTML += rowHtml;
    });
  }

  // Matrix Switcher Listeners
  if (btnMatrixTime && btnMatrixDist) {
    btnMatrixTime.addEventListener('click', () => {
      activeMatrixType = 'time';
      btnMatrixTime.classList.add('active');
      btnMatrixDist.classList.remove('active');
      if (currentResults) populateMatrixTable(currentResults);
    });

    btnMatrixDist.addEventListener('click', () => {
      activeMatrixType = 'dist';
      btnMatrixDist.classList.add('active');
      btnMatrixTime.classList.remove('active');
      if (currentResults) populateMatrixTable(currentResults);
    });
  }

  // =========================================================================
  // Export Handlers (SpecRt Naming)
  // =========================================================================
  function setupExportHandlers(data) {
    btnExportJSON.onclick = () => {
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      });
      downloadBlob(blob, `specrt_${data.filename.replace('.dcm', '')}_results.json`);
    };

    btnExportCSV.onclick = () => {
      const initial = data.routes.initial;
      const twoOpt = data.routes.two_opt;
      const heldKarp = data.routes.held_karp;
      const hasHeldKarp = heldKarp && heldKarp.time_s !== null && heldKarp.time_s !== undefined;
      const isHeldKarpOptimal = hasHeldKarp && (heldKarp.time_s <= twoOpt.time_s + 1e-6);

      const twoOptSavedTime = twoOpt.savings_time_s !== undefined
        ? twoOpt.savings_time_s
        : Math.max(0, initial.time_s - twoOpt.time_s);
      const twoOptSavedPct = twoOpt.savings_percent !== undefined
        ? twoOpt.savings_percent
        : (initial.time_s > 0 ? (twoOptSavedTime / initial.time_s) * 100 : 0);

      let csv = `Plan: ${data.filename}, Machine Speed: ${data.metrics.machine_speed_mms || 20} mm/s\n`;
      csv += 'Method,Transit Time (s),Time Saved (s),Time Saved (%),Total Distance (mm),Route,Status\n';
      csv += `Initial,${initial.time_s.toFixed(2)},0.00,0.0%,${initial.distance_mm.toFixed(2)},"${initial.path_str}",Baseline\n`;
      csv += `2-opt,${twoOpt.time_s.toFixed(2)},${Number(twoOptSavedTime).toFixed(2)},${Number(twoOptSavedPct).toFixed(1)}%,${twoOpt.distance_mm.toFixed(2)},"${twoOpt.path_str}",${isHeldKarpOptimal ? '2-Opt Heuristic' : 'Optimized'}\n`;

      if (hasHeldKarp) {
        const hkSavedTime = heldKarp.savings_time_s !== undefined
          ? heldKarp.savings_time_s
          : Math.max(0, initial.time_s - heldKarp.time_s);
        const hkSavedPct = heldKarp.savings_percent !== undefined
          ? heldKarp.savings_percent
          : (initial.time_s > 0 ? (hkSavedTime / initial.time_s) * 100 : 0);
        csv += `Held-Karp,${heldKarp.time_s.toFixed(2)},${Number(hkSavedTime).toFixed(2)},${Number(hkSavedPct).toFixed(1)}%,${heldKarp.distance_mm.toFixed(2)},"${heldKarp.path_str}",${isHeldKarpOptimal ? 'Optimized' : 'Exact Global'}\n`;
      }

      csv += '\nExtracted Isocenters\nPoint,X (mm),Y (mm),Z (mm),Beams\n';
      data.isocenters.forEach((iso) => {
        csv += `${iso.label},${iso.x},${iso.y},${iso.z},"${iso.beam_names.join('; ')}"\n`;
      });

      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      downloadBlob(blob, `specrt_${data.filename.replace('.dcm', '')}_report.csv`);
    };
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
});
