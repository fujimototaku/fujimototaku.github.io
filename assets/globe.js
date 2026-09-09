const root = document.querySelector('#globeViz');

if (root) {
  (async () => {
    const status = document.querySelector('#globe-status');
    const spinButton = document.querySelector('#globe-spin');
    const homeButton = document.querySelector('#globe-home');
    const frame = root.closest('.globe-frame');
    const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
    const setStatus = (text) => {
      if (status) status.textContent = text;
    };

    let collapseTimer = null;

    const setExpanded = (expanded) => {
      if (!frame) return;
      frame.classList.toggle('is-expanded', expanded);
      frame.setAttribute('aria-expanded', String(expanded));
      root.setAttribute('aria-label', expanded ? '拡大中の3D地球儀' : '3D地球儀');
      if (expanded) {
        if (collapseTimer) window.clearTimeout(collapseTimer);
        window.requestAnimationFrame(() => window.dispatchEvent(new Event('resize')));
      }
    };

    const scheduleCollapse = () => {
      if (!finePointer.matches || !frame) return;
      if (collapseTimer) window.clearTimeout(collapseTimer);
      collapseTimer = window.setTimeout(() => setExpanded(false), 220);
    };

    if (frame) {
      frame.setAttribute('aria-expanded', 'false');

      frame.addEventListener('pointerenter', () => {
        if (finePointer.matches) setExpanded(true);
      });

      frame.addEventListener('pointerleave', scheduleCollapse);

      root.addEventListener('pointerdown', () => {
        if (!finePointer.matches && !frame.classList.contains('is-expanded')) {
          setExpanded(true);
        }
      }, { capture: true });

      document.addEventListener('pointerdown', (event) => {
        if (!frame.classList.contains('is-expanded')) return;
        if (frame.contains(event.target)) return;
        setExpanded(false);
      });

      document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && frame.classList.contains('is-expanded')) {
          setExpanded(false);
          root.focus();
        }
      });
    }

    try {
      const { default: Globe } = await import('https://cdn.jsdelivr.net/npm/globe.gl@2.46.2/+esm');

      const world = new Globe(root, {
        animateIn: true,
        rendererConfig: {
          antialias: true,
          alpha: true,
          powerPreference: 'high-performance'
        }
      })
        .globeImageUrl('https://cdn.jsdelivr.net/npm/three-globe@2.45.2/example/img/earth-blue-marble.jpg')
        .bumpImageUrl('https://cdn.jsdelivr.net/npm/three-globe@2.45.2/example/img/earth-topology.png')
        .backgroundColor('rgba(0,0,0,0)')
        .showAtmosphere(true)
        .atmosphereColor('#7ea7c7')
        .atmosphereAltitude(0.12)
        .showGraticules(false)
        .pointRadius(0.45)
        .pointAltitude(0.012)
        .pointColor(() => '#f0d36b')
        .pointsTransitionDuration(220);

      const renderer = world.renderer();
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

      const controls = world.controls();
      controls.autoRotate = true;
      controls.autoRotateSpeed = 0.75;
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;
      controls.enableZoom = true;
      controls.rotateSpeed = 0.72;
      controls.zoomSpeed = 0.9;

      let spinEnabled = true;
      let resumeTimer = null;

      const syncSpinButton = () => {
        if (!spinButton) return;
        spinButton.textContent = spinEnabled ? '自転 ON' : '自転 OFF';
        spinButton.setAttribute('aria-pressed', String(spinEnabled));
      };

      const pauseForInteraction = () => {
        controls.autoRotate = false;
        if (resumeTimer) window.clearTimeout(resumeTimer);
      };

      const resumeAfterInteraction = () => {
        if (resumeTimer) window.clearTimeout(resumeTimer);
        resumeTimer = window.setTimeout(() => {
          controls.autoRotate = spinEnabled;
        }, 3500);
      };

      controls.addEventListener('start', pauseForInteraction);
      controls.addEventListener('end', resumeAfterInteraction);

      const resize = () => {
        const width = Math.max(140, Math.floor(root.getBoundingClientRect().width));
        world.width(width).height(width);
      };

      const resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(root);
      resize();

      world.onGlobeReady(() => {
        const radius = world.getGlobeRadius();
        controls.minDistance = radius * 1.15;
        controls.maxDistance = radius * 4.2;
        world.pointOfView({ lat: 35.7, lng: 139.7, altitude: 2.15 }, 0);
        setStatus('触れると巨大化 / ドラッグで回転 / ホイールでズーム');
      });

      world.onGlobeClick(({ lat, lng }) => {
        world.pointsData([{ lat, lng }]);
        setStatus(`${lat >= 0 ? 'N' : 'S'} ${Math.abs(lat).toFixed(2)}° / ${lng >= 0 ? 'E' : 'W'} ${Math.abs(lng).toFixed(2)}°`);
      });

      if (spinButton) {
        spinButton.addEventListener('click', () => {
          spinEnabled = !spinEnabled;
          controls.autoRotate = spinEnabled;
          syncSpinButton();
          setStatus(spinEnabled ? '自転を再開しました' : '自転を止めました');
        });
      }

      if (homeButton) {
        homeButton.addEventListener('click', () => {
          controls.autoRotate = false;
          world.pointOfView({ lat: 43.0618, lng: 141.3545, altitude: 1.75 }, 900);
          world.pointsData([{ lat: 43.0618, lng: 141.3545 }]);
          setStatus('札幌 43.06°N / 141.35°E');
          resumeAfterInteraction();
        });
      }

      root.addEventListener('keydown', (event) => {
        if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', '+', '=', '-'].includes(event.key)) return;
        event.preventDefault();
        const pov = world.pointOfView();
        let lat = pov.lat;
        let lng = pov.lng;
        let altitude = pov.altitude;

        if (event.key === 'ArrowUp') lat = Math.min(89, lat + 8);
        if (event.key === 'ArrowDown') lat = Math.max(-89, lat - 8);
        if (event.key === 'ArrowLeft') lng -= 10;
        if (event.key === 'ArrowRight') lng += 10;
        if (event.key === '+' || event.key === '=') altitude = Math.max(0.2, altitude - 0.18);
        if (event.key === '-') altitude = Math.min(4, altitude + 0.18);

        lng = ((lng + 540) % 360) - 180;
        controls.autoRotate = false;
        world.pointOfView({ lat, lng, altitude }, 180);
        setStatus(`${lat >= 0 ? 'N' : 'S'} ${Math.abs(lat).toFixed(1)}° / ${lng >= 0 ? 'E' : 'W'} ${Math.abs(lng).toFixed(1)}°`);
        resumeAfterInteraction();
      });

      syncSpinButton();
    } catch (error) {
      console.error('Globe initialization failed:', error);
      root.classList.add('globe-error');
      setStatus('地球儀を起動できませんでした');
    }
  })();
}
