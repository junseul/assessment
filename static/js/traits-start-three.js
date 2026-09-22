/* 성향파악 시작 화면 장식용 three.js 비주얼.
   검사 로직(타이밍·입력·채점)에는 관여하지 않는 표시 계층이다.
   WebGL을 사용할 수 없으면 아무 표시 없이 기본 화면으로 진행한다. */
(() => {
  const moduleUrl = new URL('../vendor/three/three.module.js', document.currentScript.src);
  const gate = document.getElementById('startGate');
  const host = document.getElementById('startThree');
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
    renderer.domElement.className = 'traits-start-canvas';
    renderer.domElement.setAttribute('aria-hidden', 'true');
    renderer.domElement.addEventListener('webglcontextlost', event => {
      event.preventDefault();
      fallback('WebGL context lost');
    }, { once: true });
    host.append(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    camera.position.set(0, 0.6, 8);
    camera.lookAt(0, 0, 0);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x8a97ab, 1.6));
    const light = new THREE.DirectionalLight(0xffffff, 2);
    light.position.set(-3, 5, 6);
    scene.add(light);

    // AI 머신: 딥네이비 무대 위 발광 코어 + 자이로 링 + 데이터 파티클
    const core = new THREE.Mesh(
      keep(new THREE.IcosahedronGeometry(0.85, 1)),
      keep(new THREE.MeshStandardMaterial({
        color: 0x0b1e4b, emissive: 0x2563eb, emissiveIntensity: 1.1,
        roughness: 0.3, metalness: 0.6, flatShading: true,
      })),
    );
    scene.add(core);
    const coreShell = new THREE.Mesh(
      keep(new THREE.IcosahedronGeometry(1.05, 1)),
      keep(new THREE.MeshBasicMaterial({
        color: 0x22d3ee, wireframe: true, transparent: true, opacity: 0.28,
      })),
    );
    scene.add(coreShell);

    // 자이로 링 2개
    const gyroA = new THREE.Mesh(
      keep(new THREE.TorusGeometry(1.7, 0.03, 12, 96)),
      keep(new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.3, metalness: 0.8 })),
    );
    gyroA.rotation.x = Math.PI / 2.4;
    scene.add(gyroA);
    const gyroB = new THREE.Mesh(
      keep(new THREE.TorusGeometry(2.0, 0.02, 12, 96)),
      keep(new THREE.MeshBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.55 })),
    );
    gyroB.rotation.x = Math.PI / 3;
    gyroB.rotation.y = 0.5;
    scene.add(gyroB);

    // 링 위 궤도 위성 4개
    const satellites = [];
    const satGeo = keep(new THREE.SphereGeometry(0.09, 20, 14));
    [0x22d3ee, 0x8b5cf6, 0x3b82f6, 0x67e8fb].forEach((color, index) => {
      const sat = new THREE.Mesh(satGeo, keep(new THREE.MeshBasicMaterial({ color })));
      sat.userData.phase = (index / 4) * Math.PI * 2;
      scene.add(sat);
      satellites.push(sat);
    });

    // 데이터 파티클 구
    const particleCount = 260;
    const positions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i += 1) {
      const r = 2.6 + Math.random() * 0.9;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      positions[i * 3 + 1] = r * Math.cos(phi) * 0.7;
      positions[i * 3 + 2] = r * Math.sin(phi) * Math.sin(theta);
    }
    const particleGeo = keep(new THREE.BufferGeometry());
    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const particles = new THREE.Points(particleGeo, keep(new THREE.PointsMaterial({
      color: 0x7dd3fc, size: 0.045, transparent: true, opacity: 0.8,
    })));
    scene.add(particles);

    // 바닥 그리드와 펄스 링
    const grid = new THREE.GridHelper(9, 18, 0x1e40af, 0x16295e);
    grid.position.y = -2.0;
    grid.material.transparent = true;
    grid.material.opacity = 0.5;
    scene.add(grid);
    const pulseMat = keep(new THREE.MeshBasicMaterial({
      color: 0x22d3ee, transparent: true, opacity: 0,
      side: THREE.DoubleSide, depthWrite: false,
    }));
    const pulse = new THREE.Mesh(keep(new THREE.RingGeometry(1.15, 1.22, 64)), pulseMat);
    scene.add(pulse);

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let width = 0, height = 0;
    function draw(time = 0) {
      // 검사 시작으로 게이트가 숨겨지면 렌더링을 멈춘다.
      if (stopped || !gate.isConnected || gate.offsetParent === null) { release(); return; }
      try {
        const bounds = host.getBoundingClientRect();
        if (!bounds.width || !bounds.height) return;
        if (width !== bounds.width || height !== bounds.height) {
          width = bounds.width; height = bounds.height;
          renderer.setSize(width, height);
          camera.aspect = width / height;
          camera.updateProjectionMatrix();
        }
        const t = time / 1000;
        core.rotation.y = t * 0.5;
        core.rotation.x = Math.sin(t * 0.4) * 0.12;
        coreShell.rotation.y = -t * 0.25;
        coreShell.rotation.z = t * 0.15;
        gyroA.rotation.z = t * 0.5;
        gyroB.rotation.z = -t * 0.35;
        for (const sat of satellites) {
          const angle = sat.userData.phase + t * 0.6;
          sat.position.set(Math.cos(angle) * 1.7, Math.sin(angle) * 0.7, Math.sin(angle) * 1.7 * 0.45);
        }
        particles.rotation.y = t * 0.05;
        grid.position.z = (t * 0.35) % 0.5;
        const pulseCycle = (t * 0.5) % 1;
        const pulseScale = 1 + pulseCycle * 1.9;
        pulse.scale.set(pulseScale, pulseScale, pulseScale);
        pulseMat.opacity = 0.42 * (1 - pulseCycle);
        renderer.render(scene, camera);
      } catch (error) { fallback(error); }
    }

    if (reduced) draw(0);
    else renderer.setAnimationLoop(draw);
    observer = new MutationObserver(() => { if (gate.style.display === 'none') release(); });
    observer.observe(gate, { attributes: true, attributeFilter: ['style'] });
  }).catch(fallback);
  window.addEventListener('pagehide', release, { once: true });
})();
