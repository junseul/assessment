/* 전략게임 선택 화면의 three.js 배경 비주얼.
   게임 로직(타이밍·입력·채점)에는 관여하지 않는 표시 계층이다.
   아이콘 자체는 DOM(SVG)이며, 떠다니는 파티클 + 떠오르는 링 + 호버 틸트만 담당한다.
   WebGL을 사용할 수 없으면 CSS 펄스만 남기고 조용히 종료한다. */
(() => {
  const moduleUrl = new URL('vendor/three/three.module.js', document.currentScript.src);
  const grid = document.querySelector('.game-select-grid');
  if (!grid) return;

  // 행성/파티클과 무관하게 아이콘에 생기를 주는 CSS 기반 동작 (WebGL 실패 시에도 유지)
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  grid.classList.add('game-icons-animated');

  if (reduceMotion.matches) return;

  const cards = [...grid.querySelectorAll('.game-select-card')];
  cards.forEach(card => {
    card.style.transform = 'perspective(700px)';
    card.addEventListener('pointermove', event => {
      const rect = card.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width - 0.5;
      const y = (event.clientY - rect.top) / rect.height - 0.5;
      card.style.transform =
        `perspective(700px) rotateX(${(-y * 7).toFixed(2)}deg) rotateY(${(x * 9).toFixed(2)}deg)`;
    });
    card.addEventListener('pointerleave', () => {
      card.style.transform = 'perspective(700px)';
    });
  });

  let renderer, raf = 0, stopped = false;
  const resources = new Set();
  const keep = resource => { resources.add(resource); return resource; };

  function release() {
    stopped = true;
    cancelAnimationFrame(raf);
    resources.forEach(resource => resource.dispose());
    resources.clear();
    renderer?.dispose();
    renderer?.domElement.remove();
  }

  function fallback(error) {
    release();
    console.warn('Three.js icon backdrop unavailable:', error);
  }

  import(moduleUrl.href).then(THREE => {
    if (stopped || !grid.isConnected) return;
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.domElement.className = 'game-icons-canvas';
    renderer.domElement.setAttribute('aria-hidden', 'true');
    renderer.domElement.addEventListener('webglcontextlost', event => {
      event.preventDefault();
      fallback('WebGL context lost');
    }, { once: true });
    grid.append(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
    camera.position.set(0, 0, 7.2);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x8a97ab, 1.5));

    // 드리프트하는 파티클
    const particleCount = 130;
    const positions = new Float32Array(particleCount * 3);
    const speeds = new Float32Array(particleCount);
    for (let i = 0; i < particleCount; i += 1) {
      positions[i * 3] = (Math.random() - 0.5) * 11;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 7;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 3;
      speeds[i] = 0.12 + Math.random() * 0.35;
    }
    const particleGeo = keep(new THREE.BufferGeometry());
    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const particles = new THREE.Points(particleGeo, keep(new THREE.PointsMaterial({
      color: 0x93c5fd, size: 0.055, transparent: true, opacity: 0.75,
    })));
    scene.add(particles);

    // 카드 위를 떠다니는 링 9개
    const rings = [];
    const ringColors = [
      0x3b82f6, 0x22c55e, 0xf59e0b, 0x8b5cf6, 0x06b6d4,
      0xec4899, 0x14b8a6, 0xf97316, 0x6366f1,
    ];
    for (let i = 0; i < 9; i += 1) {
      const ring = new THREE.Mesh(
        keep(new THREE.TorusGeometry(0.24, 0.025, 8, 40)),
        keep(new THREE.MeshBasicMaterial({ color: ringColors[i % ringColors.length], transparent: true, opacity: 0.7 })),
      );
      ring.userData = {
        baseX: -4.4 + (i % 3) * 4.4,
        baseY: 2.1 - Math.floor(i / 3) * 2.1,
        phase: i * 0.7,
        speed: 0.5 + (i % 4) * 0.13,
      };
      scene.add(ring);
      rings.push(ring);
    }

    let width = 0, height = 0;
    const clock = new THREE.Clock();
    function draw() {
      if (stopped || !grid.isConnected) { release(); return; }
      try {
        const bounds = grid.getBoundingClientRect();
        if (!bounds.width || !bounds.height) { raf = requestAnimationFrame(draw); return; }
        if (width !== bounds.width || height !== bounds.height) {
          width = bounds.width; height = bounds.height;
          renderer.setSize(width, height);
          camera.aspect = width / height;
          camera.updateProjectionMatrix();
        }
        const t = clock.getElapsedTime();
        const pos = particleGeo.attributes.position;
        for (let i = 0; i < particleCount; i += 1) {
          let y = pos.getY(i) + speeds[i] * 0.012;
          if (y > 3.6) y = -3.6;
          pos.setY(i, y);
          pos.setX(i, pos.getX(i) + Math.sin(t * 0.5 + i) * 0.0015);
        }
        pos.needsUpdate = true;
        for (const ring of rings) {
          ring.position.set(
            ring.userData.baseX + Math.sin(t * 0.4 + ring.userData.phase) * 0.22,
            ring.userData.baseY + Math.cos(t * 0.55 + ring.userData.phase) * 0.18,
            Math.sin(t * 0.3 + ring.userData.phase) * 0.4,
          );
          ring.rotation.x = t * ring.userData.speed * 0.5;
          ring.rotation.y = t * ring.userData.speed;
        }
        renderer.render(scene, camera);
      } catch (error) { fallback(error); return; }
      raf = requestAnimationFrame(draw);
    }
    draw();
    window.addEventListener('resize', () => { width = 0; });
    window.addEventListener('pagehide', release, { once: true });
  }).catch(fallback);
})();
