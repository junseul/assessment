/* 전략게임 화면 전용 3D 아레나 배경.
   표시 계층만 담당하며 게임 타이밍·입력·점수에는 관여하지 않는다.
   WebGL을 쓸 수 없거나 컨텍스트를 잃으면 <html class="game-stage">를 붙이지
   않아 기존 라이트 테마 화면이 그대로 유지된다. */
(() => {
  const moduleUrl = new URL('../vendor/three/three.module.js', document.currentScript.src);
  const root = document.documentElement;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const STAR_COUNT = 220;
  const FLOOR_SIZE = 3600;
  const STAR_DEPTH = 2000;
  const STAR_SPEED = 45;
  const FRAME_INTERVAL_MS = 33;
  let renderer, scene, camera, stars, starPositions, rings = [], stopped = false, lastDrawn = 0;

  function release() {
    if (stopped) return;
    stopped = true;
    document.removeEventListener('visibilitychange', onVisibility);
    window.removeEventListener('resize', resize);
    renderer?.setAnimationLoop(null);
    scene?.traverse(object => {
      object.geometry?.dispose();
      const materials = object.material ? [].concat(object.material) : [];
      materials.forEach(material => { material.map?.dispose(); material.dispose(); });
    });
    renderer?.dispose();
    renderer?.domElement.remove();
    root.classList.remove('game-stage');
  }

  function fail(error) {
    release();
    console.warn('Three.js game stage unavailable:', error);
  }

  // 바닥 발광과 수평선 글로우에 쓸 부드러운 원형 텍스처.
  function softSpot(THREE, inner, outer) {
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = 128;
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
    gradient.addColorStop(0, inner);
    gradient.addColorStop(.55, outer);
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 128, 128);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  function build(THREE) {
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.domElement.className = 'game-stage-canvas';
    renderer.domElement.setAttribute('aria-hidden', 'true');
    renderer.domElement.addEventListener('webglcontextlost', event => {
      event.preventDefault();
      fail('WebGL context lost');
    }, { once: true });
    document.body.append(renderer.domElement);

    scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x0b1220, 900, FLOOR_SIZE * 0.7);
    camera = new THREE.PerspectiveCamera(45, 1, 1, 6000);
    camera.position.set(0, 210, 620);
    camera.lookAt(0, 20, -320);

    // 아레나 바닥 그리드
    const floor = new THREE.GridHelper(FLOOR_SIZE, 44, 0x2f6fed, 0x1d2c47);
    floor.material.transparent = true;
    floor.material.opacity = .5;
    floor.position.set(0, -60, -FLOOR_SIZE / 4);
    scene.add(floor);

    // 수평선 발광
    const glow = new THREE.Mesh(
      new THREE.PlaneGeometry(FLOOR_SIZE, FLOOR_SIZE / 2),
      new THREE.MeshBasicMaterial({
        map: softSpot(THREE, 'rgba(79,124,247,.45)', 'rgba(79,124,247,.1)'),
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
      }),
    );
    glow.position.set(0, -40, -FLOOR_SIZE / 2);
    scene.add(glow);

    // 바닥에 깔린 아레나 링
    rings = [FLOOR_SIZE * 0.16, FLOOR_SIZE * 0.26].map((radius, index) => {
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(radius, radius + 6, 96),
        new THREE.MeshBasicMaterial({
          color: 0x4f7cf7, transparent: true, depthWrite: false, side: THREE.DoubleSide,
          blending: THREE.AdditiveBlending, opacity: index ? .14 : .22,
        }),
      );
      ring.rotation.x = -Math.PI / 2;
      ring.position.set(0, -58, -FLOOR_SIZE / 8);
      scene.add(ring);
      return ring;
    });

    // 앞으로 흘러가는 입자 필드
    starPositions = new Float32Array(STAR_COUNT * 3);
    for (let i = 0; i < STAR_COUNT; i++) {
      starPositions[i * 3] = (Math.random() - .5) * 2600;
      starPositions[i * 3 + 1] = Math.random() * 900 - 220;
      starPositions[i * 3 + 2] = -STAR_DEPTH + Math.random() * STAR_DEPTH;
    }
    const starGeometry = new THREE.BufferGeometry();
    starGeometry.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    stars = new THREE.Points(starGeometry, new THREE.PointsMaterial({
      color: 0x9dc0ff, size: 3, sizeAttenuation: true,
      transparent: true, opacity: .8, depthWrite: false, blending: THREE.AdditiveBlending,
    }));
    scene.add(stars);

    resize();
    // 첫 프레임을 정상적으로 그린 뒤에만 다크 콘솔 테마를 적용한다.
    drawFrame(0, 0);
    root.classList.add('game-stage');
    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('resize', resize);
    renderer.setAnimationLoop(reducedMotion ? null : tick);
  }

  function resize() {
    const width = window.innerWidth;
    const height = Math.max(window.innerHeight, 1);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function drawFrame(delta, time) {
    if (delta) {
      const step = STAR_SPEED * delta;
      for (let i = 0; i < STAR_COUNT; i++) {
        let z = starPositions[i * 3 + 2] + step;
        if (z > 120) z -= STAR_DEPTH;
        starPositions[i * 3 + 2] = z;
      }
      stars.geometry.attributes.position.needsUpdate = true;
      // 아레나 링을 천천히 호흡시켜 정지 화면처럼 보이지 않게 한다.
      const pulse = Math.sin(time * 0.0008) * .06;
      rings.forEach((ring, index) => { ring.material.opacity = (index ? .14 : .22) + pulse; });
    }
    renderer.render(scene, camera);
  }

  function tick(time) {
    if (stopped) return;
    if (time - lastDrawn < FRAME_INTERVAL_MS) return;
    // 탭 복귀 등으로 프레임 간격이 크게 벌어져도 입자가 순간이동하지 않게 제한한다.
    const delta = Math.min(time - lastDrawn, 100) / 1000;
    lastDrawn = time;
    try { drawFrame(delta, time); } catch (error) { fail(error); }
  }

  function onVisibility() {
    if (stopped || reducedMotion) return;
    renderer.setAnimationLoop(document.visibilityState === 'hidden' ? null : tick);
  }

  import(moduleUrl.href)
    .then(THREE => { if (!stopped) build(THREE); })
    .catch(fail);
  window.addEventListener('pagehide', release, { once: true });
})();
