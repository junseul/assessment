/* 영상면접 시작 화면 장식용 three.js 비주얼.
   녹화·제출 로직에는 관여하지 않는 표시 계층이다.
   WebGL을 사용할 수 없으면 아무 표시 없이 기본 화면으로 진행한다. */
(() => {
  const moduleUrl = new URL('../vendor/three/three.module.js', document.currentScript.src);
  const gate = document.getElementById('startGate');
  const host = document.getElementById('interviewThree');
  if (!gate || !host) return;

  let renderer, observer, stopped = false;
  const resources = new Set();
  const keep = resource => { resources.add(resource); return resource; };

  function release() {
    stopped = true;
    observer?.disconnect();
    renderer?.setAnimationLoop(null);
    resources.forEach(resource => resource.dispose());
    resources.clear();
    renderer?.dispose();
    renderer?.domElement.remove();
  }

  function fallback(error) {
    release();
    console.warn('Three.js start visual unavailable:', error);
  }

  import(moduleUrl.href).then(THREE => {
    if (stopped) return;
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.domElement.className = 'interview-start-canvas';
    renderer.domElement.setAttribute('aria-hidden', 'true');
    renderer.domElement.addEventListener('webglcontextlost', event => {
      event.preventDefault();
      fallback('WebGL context lost');
    }, { once: true });
    host.append(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100);
    camera.position.set(0, 0.85, 5.6);
    camera.lookAt(0, -0.15, 0);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x8a97ab, 1.5));
    const light = new THREE.DirectionalLight(0xffffff, 2);
    light.position.set(-3, 5, 6);
    scene.add(light);

    const aluminum = keep(new THREE.MeshStandardMaterial({
      color: 0x9aa7bd, roughness: 0.35, metalness: 0.7,
    }));
    const darkTrim = keep(new THREE.MeshStandardMaterial({
      color: 0x1e293b, roughness: 0.5, metalness: 0.4,
    }));
    const screenGlow = keep(new THREE.MeshBasicMaterial({ color: 0x0d1b3e }));

    // 노트북 본체
    const laptop = new THREE.Group();
    scene.add(laptop);

    const base = new THREE.Mesh(keep(new THREE.BoxGeometry(4.3, 0.16, 2.9)), aluminum);
    base.position.set(0, -1.25, 0.35);
    laptop.add(base);
    const deck = new THREE.Mesh(keep(new THREE.BoxGeometry(3.9, 0.03, 2.3)), darkTrim);
    deck.position.set(0, -1.16, 0.42);
    laptop.add(deck);
    const trackpad = new THREE.Mesh(keep(new THREE.BoxGeometry(1.15, 0.035, 0.75)), aluminum);
    trackpad.position.set(0, -1.14, 1.2);
    laptop.add(trackpad);

    // 자판: 4행 키 매트릭스
    const keyMat = keep(new THREE.MeshStandardMaterial({
      color: 0x334155, roughness: 0.55, metalness: 0.2,
    }));
    const keys = [];
    for (let row = 0; row < 4; row += 1) {
      for (let col = 0; col < 10; col += 1) {
        const key = new THREE.Mesh(keep(new THREE.BoxGeometry(0.26, 0.05, 0.26)), keyMat);
        key.position.set(-1.48 + col * 0.33, -1.11, -0.45 + row * 0.33);
        key.userData.phase = (row * 10 + col) * 0.37;
        laptop.add(key);
        keys.push(key);
      }
    }

    const lid = new THREE.Group();
    lid.position.set(0, -1.17, -1.0);
    lid.rotation.x = -0.28;
    laptop.add(lid);
    const lidBack = new THREE.Mesh(keep(new THREE.BoxGeometry(4.3, 2.9, 0.12)), aluminum);
    lidBack.position.y = 1.45;
    lid.add(lidBack);
    const screen = new THREE.Mesh(keep(new THREE.PlaneGeometry(3.9, 2.5)), screenGlow);
    screen.position.set(0, 1.45, 0.07);
    lid.add(screen);

    // 웹캠 표시등
    const camLampMat = keep(new THREE.MeshBasicMaterial({ color: 0x22c55e }));
    const camLamp = new THREE.Mesh(keep(new THREE.SphereGeometry(0.045, 16, 12)), camLampMat);
    camLamp.position.set(0, 2.78, 0.08);
    lid.add(camLamp);

    // 화면 속 화상면접 UI: 상대방 비디오와 자막 바, 녹화 배지
    const ui = new THREE.Group();
    ui.position.set(0, 1.45, 0.075);
    lid.add(ui);
    const meWindow = new THREE.Mesh(
      keep(new THREE.PlaneGeometry(1.1, 0.75)),
      keep(new THREE.MeshBasicMaterial({ color: 0x1e3a8a })),
    );
    meWindow.position.set(-1.2, -0.8, 0.01);
    ui.add(meWindow);

    // 자막 바 5개
    const barGeo = keep(new THREE.PlaneGeometry(1, 0.09));
    const bars = [];
    const barColors = [0x38bdf8, 0x38bdf8, 0x64748b, 0x38bdf8, 0x64748b];
    const barWidths = [2.35, 2.05, 1.5, 2.2, 1.7];
    barColors.forEach((color, index) => {
      const bar = new THREE.Mesh(barGeo, keep(new THREE.MeshBasicMaterial({ color })));
      bar.position.set(-1.7 + barWidths[index] / 2, -0.58 + index * 0.16, 0.01);
      bar.scale.x = barWidths[index];
      bar.userData.width = barWidths[index];
      ui.add(bar);
      bars.push(bar);
    });

    // REC 배지
    const recBadge = new THREE.Mesh(
      keep(new THREE.PlaneGeometry(0.62, 0.3)),
      keep(new THREE.MeshBasicMaterial({ color: 0xef4444 })),
    );
    recBadge.position.set(1.5, 1.02, 0.01);
    ui.add(recBadge);
    const recBadgeMat = recBadge.material;

    // 오디오 레벨 바
    const levelBars = [];
    const levelGeo = keep(new THREE.BoxGeometry(0.09, 1, 0.02));
    const levelMat = keep(new THREE.MeshBasicMaterial({ color: 0x22c55e }));
    for (let i = 0; i < 9; i += 1) {
      const level = new THREE.Mesh(levelGeo, levelMat);
      level.position.set(1.05 + i * 0.14, -0.95, 0.01);
      level.userData.phase = i * 0.65;
      ui.add(level);
      levelBars.push(level);
    }

    // 바닥 그림자
    const shadowMaterial = keep(new THREE.MeshBasicMaterial({
      color: 0x1e3a8a, transparent: true, opacity: 0.13, depthWrite: false,
    }));
    const laptopShadow = new THREE.Mesh(keep(new THREE.CircleGeometry(1.7, 48)), shadowMaterial);
    laptopShadow.rotation.x = -Math.PI / 2;
    laptopShadow.position.set(0, -1.36, 0.2);
    laptopShadow.scale.set(1.3, 0.55, 1);
    scene.add(laptopShadow);

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let width = 0, height = 0;
    function frameCamera() {
      const aspect = width / Math.max(height, 1);
      camera.aspect = aspect;
      camera.position.z = aspect < 1.1 ? 8.0 : aspect < 1.6 ? 6.6 : 5.6;
      camera.updateProjectionMatrix();
    }

    function draw(time = 0) {
      // 카메라 준비로 게이트가 숨겨지면 렌더링을 멈춘다.
      if (stopped || !gate.isConnected || gate.offsetParent === null) { release(); return; }
      try {
        const bounds = host.getBoundingClientRect();
        if (!bounds.width || !bounds.height) return;
        if (width !== bounds.width || height !== bounds.height) {
          width = bounds.width; height = bounds.height;
          renderer.setSize(width, height);
          frameCamera();
        }
        const t = time / 1000;
        laptop.rotation.y = Math.sin(t * 0.22) * 0.06;
        lid.rotation.x = -0.28 + Math.sin(t * 0.4) * 0.008;
        for (const key of keys) {
          key.position.y = -1.11 + Math.max(0, Math.sin(t * 2.2 + key.userData.phase)) * 0.035;
        }
        for (const bar of bars) {
          const target = bar.userData.width * (0.55 + 0.45 * Math.abs(Math.sin(t * 1.4 + bar.userData.width)));
          bar.scale.x += (target - bar.scale.x) * 0.08;
          bar.position.x = -1.7 + bar.scale.x / 2;
        }
        for (const level of levelBars) {
          const heightScale = 0.15 + 0.85 * Math.abs(Math.sin(t * 3.1 + level.userData.phase));
          level.scale.y = heightScale * 0.42;
          level.position.y = -0.95 + (level.scale.y / 2);
        }
        camLampMat.color.setHex(Math.sin(t * 2.4) > 0 ? 0x22c55e : 0x14532d);
        recBadgeMat.color.setHex(Math.sin(t * 4.2) > 0 ? 0xef4444 : 0x7f1d1d);
        renderer.render(scene, camera);
      } catch (error) { fallback(error); }
    }

    if (reduced) {
      draw(1800);
    } else {
      renderer.setAnimationLoop(draw);
    }
    observer = new MutationObserver(() => { if (gate.style.display === 'none') release(); });
    observer.observe(gate, { attributes: true, attributeFilter: ['style'] });
  }).catch(fallback);
  window.addEventListener('pagehide', release, { once: true });
})();
