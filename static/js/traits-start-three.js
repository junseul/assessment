/* personality start-screen image animation rendered with Three.js. */
(() => {
  const scriptUrl = document.currentScript.src;
  const moduleUrl = new URL('../vendor/three/three.module.js', scriptUrl);
  const imageUrl = new URL('../images/assessment/traits-personality-hero.png', scriptUrl);
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
    console.warn('Three.js personality visual unavailable:', error);
  }

  import(moduleUrl.href).then(async THREE => {
    if (stopped) return;
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.domElement.className = 'traits-start-canvas';
    renderer.domElement.setAttribute('aria-hidden', 'true');
    host.append(renderer.domElement);

    const texture = keep(await new THREE.TextureLoader().loadAsync(imageUrl.href));
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
    const uniforms = {
      uTexture: { value: texture },
      uResolution: { value: new THREE.Vector2(1, 1) },
      uImageSize: { value: new THREE.Vector2(texture.image.width, texture.image.height) },
      uPointer: { value: new THREE.Vector2() },
      uTime: { value: 0 },
    };
    const material = keep(new THREE.ShaderMaterial({
      uniforms,
      vertexShader: [
        'varying vec2 vUv;',
        'void main() { vUv = uv; gl_Position = vec4(position, 1.0); }',
      ].join('\n'),
      fragmentShader: [
        'uniform sampler2D uTexture;',
        'uniform vec2 uResolution, uImageSize, uPointer;',
        'uniform float uTime;',
        'float hash21(vec2 p) {',
        '  p = fract(p * vec2(123.34, 456.21));',
        '  p += dot(p, p + 45.32);',
        '  return fract(p.x * p.y);',
        '}',
        'varying vec2 vUv;',
        'void main() {',
        '  float screenRatio = uResolution.x / uResolution.y;',
        '  float imageRatio = uImageSize.x / uImageSize.y;',
        '  vec2 cover = screenRatio < imageRatio ? vec2(screenRatio / imageRatio, 1.0) : vec2(1.0, imageRatio / screenRatio);',
        '  float breath = 0.977 + sin(uTime * 0.42) * 0.006;',
        '  vec2 uv = (vUv - 0.5) * cover * breath + 0.5 - uPointer * vec2(0.013, 0.018);',
        '  uv += vec2(sin(uv.y * 14.0 + uTime * 1.5), cos(uv.x * 12.0 - uTime * 1.25)) * 0.006;',
        '  vec3 color = texture2D(uTexture, uv).rgb;',
        '  float sweepX = fract(uTime * 0.12) * 1.5 - 0.25;',
        '  float sheen = smoothstep(0.19, 0.0, abs(vUv.x - sweepX));',
        '  float focus = 1.0 - smoothstep(0.25, 0.78, distance(vUv, vec2(0.5) + uPointer * 0.06));',
        '  color += vec3(0.34, 0.48, 0.95) * (sheen * 0.07 + focus * 0.025);',
        '  vec2 sparkleGrid = vUv * vec2(72.0, 28.0);',
        '  vec2 sparkleCell = floor(sparkleGrid);',
        '  float seed = hash21(sparkleCell);',
        '  float sparkleShape = smoothstep(0.13, 0.0, length(fract(sparkleGrid) - 0.5));',
        '  float sparkle = step(0.965, seed) * sparkleShape * pow(max(0.0, sin(uTime * 3.4 + seed * 19.0)), 14.0);',
        '  color += vec3(0.72, 0.87, 1.0) * sparkle * 0.85;',
        '  gl_FragColor = vec4(color, 1.0);',
        '}',
      ].join('\n'),
    }));
    const scene = new THREE.Scene();
    scene.add(new THREE.Mesh(keep(new THREE.PlaneGeometry(2, 2)), material));
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 2);
    camera.position.z = 1;
    const traitAccents = [
      [-0.56, 0.28, 0x829dff], [0, 0.70, 0xffa690], [0.55, 0.30, 0x65dcff],
      [-0.48, -0.42, 0x86c7ff], [0.48, -0.40, 0xa98cff],
    ].map(([x, y, color], index) => {
      const group = new THREE.Group();
      const accentMaterial = keep(new THREE.MeshBasicMaterial({
        color, transparent: true, opacity: 0.55, depthTest: false,
        blending: THREE.AdditiveBlending,
      }));
      group.add(new THREE.Mesh(keep(new THREE.RingGeometry(0.105, 0.116, 64, 1, 0, Math.PI * 1.45)), accentMaterial));
      const haloMaterial = keep(accentMaterial.clone());
      haloMaterial.opacity = 0.18;
      group.add(new THREE.Mesh(keep(new THREE.RingGeometry(0.132, 0.137, 64, 1, Math.PI * 0.45, Math.PI * 1.1)), haloMaterial));
      const dot = new THREE.Mesh(
        keep(new THREE.CircleGeometry(0.018, 24)),
        keep(accentMaterial.clone()),
      );
      dot.position.x = 0.15;
      group.add(dot);
      const spark = new THREE.Mesh(
        keep(new THREE.CircleGeometry(0.012, 20)),
        keep(accentMaterial.clone()),
      );
      spark.position.x = -0.17;
      group.add(spark);
      group.position.set(x, y, 0.2);
      group.userData.baseX = x;
      group.userData.baseY = y;
      group.userData.phase = index * 1.25;
      scene.add(group);
      return { group, dot, spark, accentMaterial, haloMaterial };
    });
    const targetPointer = new THREE.Vector2();
    host.addEventListener('pointermove', event => {
      const rect = host.getBoundingClientRect();
      targetPointer.set(
        (event.clientX - rect.left) / rect.width - 0.5,
        0.5 - (event.clientY - rect.top) / rect.height,
      );
    });
    host.addEventListener('pointerleave', () => targetPointer.set(0, 0));

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const motionFactor = reduced ? 0.28 : 1;
    let width = 0, height = 0;
    function draw(time = 0) {
      if (stopped || !gate.isConnected || gate.offsetParent === null) { release(); return; }
      const nextWidth = host.clientWidth;
      const nextHeight = host.clientHeight;
      if (!nextWidth || !nextHeight) return;
      if (width !== nextWidth || height !== nextHeight) {
        width = nextWidth;
        height = nextHeight;
        const rect = host.getBoundingClientRect();
        const displayScale = Math.max(rect.width / width, rect.height / height, 1);
        renderer.setPixelRatio(Math.min((window.devicePixelRatio || 1) * displayScale, 3));
        renderer.setSize(width, height);
        uniforms.uResolution.value.set(width, height);
      }
      const seconds = time / 1000 * motionFactor;
      uniforms.uPointer.value.lerp(targetPointer, 0.035);
      uniforms.uTime.value = seconds;
      traitAccents.forEach(({ group, dot, spark, accentMaterial, haloMaterial }, index) => {
        const wave = Math.sin(seconds * 1.35 + group.userData.phase);
        group.scale.setScalar(1 + wave * 0.16);
        group.position.x = group.userData.baseX + Math.sin(seconds * 0.9 + group.userData.phase) * 0.035;
        group.position.y = group.userData.baseY + Math.cos(seconds * 1.15 + group.userData.phase) * 0.045;
        group.rotation.z = seconds * (index % 2 ? -1.25 : 1.25) + group.userData.phase;
        dot.scale.setScalar(0.8 + (wave + 1) * 0.45);
        spark.scale.setScalar(0.65 + Math.abs(Math.sin(seconds * 3.2 + group.userData.phase)) * 1.15);
        accentMaterial.opacity = 0.58 + (wave + 1) * 0.16;
        haloMaterial.opacity = 0.12 + (wave + 1) * 0.12;
      });
      renderer.render(scene, camera);
    }

    renderer.setAnimationLoop(draw);
    observer = new MutationObserver(() => { if (gate.style.display === 'none') release(); });
    observer.observe(gate, { attributes: true, attributeFilter: ['style'] });
  }).catch(fallback);
  window.addEventListener('pagehide', release, { once: true });
})();