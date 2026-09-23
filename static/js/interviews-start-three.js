/* interview start-screen image animation rendered with Three.js. */
(() => {
  const scriptUrl = document.currentScript.src;
  const moduleUrl = new URL('../vendor/three/three.module.js', scriptUrl);
  const imageUrl = new URL('../images/assessment/interview-video-hero.png', scriptUrl);
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
    console.warn('Three.js interview visual unavailable:', error);
  }

  import(moduleUrl.href).then(async THREE => {
    if (stopped) return;
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.domElement.className = 'interview-start-canvas';
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
        'varying vec2 vUv;',
        'void main() {',
        '  float screenRatio = uResolution.x / uResolution.y;',
        '  float imageRatio = uImageSize.x / uImageSize.y;',
        '  vec2 cover = screenRatio < imageRatio ? vec2(screenRatio / imageRatio, 1.0) : vec2(1.0, imageRatio / screenRatio);',
        '  float breath = 0.977 + sin(uTime * 0.42) * 0.006;',
        '  vec2 uv = (vUv - 0.5) * cover * breath + 0.5 - uPointer * vec2(0.013, 0.018);',
        '  uv += vec2(sin(uv.y * 12.0 + uTime * 1.1), cos(uv.x * 10.0 - uTime * 0.9)) * 0.0035;',
        '  vec3 color = texture2D(uTexture, uv).rgb;',
        '  float sweepX = fract(uTime * 0.11) * 1.5 - 0.25;',
        '  float sheen = smoothstep(0.19, 0.0, abs(vUv.x - sweepX));',
        '  float cameraGlow = 1.0 - smoothstep(0.0, 0.12, distance(vUv, vec2(0.67, 0.30) + uPointer * 0.02));',
        '  float signal = 0.5 + 0.5 * sin(uTime * 2.2);',
        '  color += vec3(0.28, 0.60, 1.0) * (cameraGlow * signal * 0.14 + sheen * 0.075);',
        '  float scanY = fract(uTime * 0.23);',
        '  float screenMask = step(0.46, vUv.x) * step(vUv.x, 0.86) * step(0.20, vUv.y) * step(vUv.y, 0.78);',
        '  float scanLine = smoothstep(0.022, 0.0, abs(vUv.y - scanY)) * screenMask;',
        '  color += vec3(0.25, 0.76, 1.0) * scanLine * 0.16;',
        '  gl_FragColor = vec4(color, 1.0);',
        '}',
      ].join('\n'),
    }));
    const scene = new THREE.Scene();
    scene.add(new THREE.Mesh(keep(new THREE.PlaneGeometry(2, 2)), material));
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 2);
    camera.position.z = 1;
    const waveGroup = new THREE.Group();
    waveGroup.position.set(-0.18, 0.30, 0.2);
    const waveGeometry = keep(new THREE.PlaneGeometry(0.014, 0.13));
    const waveMaterial = keep(new THREE.MeshBasicMaterial({
      color: 0x7ee8ff, transparent: true, opacity: 0.82, depthTest: false,
      blending: THREE.AdditiveBlending,
    }));
    const waveBars = Array.from({ length: 13 }, (_, index) => {
      const bar = new THREE.Mesh(waveGeometry, waveMaterial);
      bar.position.x = (index - 6) * 0.032;
      bar.userData.phase = index * 0.68;
      waveGroup.add(bar);
      return bar;
    });
    scene.add(waveGroup);
    const cameraPulseMaterial = keep(new THREE.MeshBasicMaterial({
      color: 0x78dfff, transparent: true, opacity: 0.72, depthTest: false,
      blending: THREE.AdditiveBlending,
    }));
    const cameraPulse = new THREE.Mesh(
      keep(new THREE.RingGeometry(0.035, 0.052, 48, 1, 0, Math.PI * 1.55)), cameraPulseMaterial,
    );
    cameraPulse.position.set(0.34, 0.42, 0.2);
    scene.add(cameraPulse);
    const particleGeometry = keep(new THREE.CircleGeometry(0.009, 16));
    const interviewParticles = Array.from({ length: 18 }, (_, index) => {
      const particleMaterial = keep(new THREE.MeshBasicMaterial({
        color: index % 3 === 0 ? 0xffd7b0 : 0x9eeaff,
        transparent: true, opacity: 0.42, depthTest: false,
        blending: THREE.AdditiveBlending,
      }));
      const particle = new THREE.Mesh(particleGeometry, particleMaterial);
      particle.position.set(-0.9 + (index % 9) * 0.225, -0.58 + Math.floor(index / 9) * 1.12, 0.18);
      particle.userData.baseX = particle.position.x;
      particle.userData.baseY = particle.position.y;
      particle.userData.phase = index * 0.73;
      scene.add(particle);
      return { particle, particleMaterial };
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
      waveBars.forEach((bar, index) => {
        bar.scale.y = 0.35 + Math.abs(Math.sin(seconds * 3.8 + bar.userData.phase)) * (0.7 + (index % 3) * 0.2);
      });
      waveGroup.position.y = 0.30 + Math.sin(seconds * 1.4) * 0.025;
      waveGroup.scale.x = 1 + Math.sin(seconds * 1.1) * 0.08;
      const pulse = 1 + (Math.sin(seconds * 3.2) + 1) * 0.48;
      cameraPulse.scale.setScalar(pulse);
      cameraPulse.rotation.z = seconds * 1.8;
      cameraPulseMaterial.opacity = 0.86 - (pulse - 1) * 0.52;
      interviewParticles.forEach(({ particle, particleMaterial }, index) => {
        particle.position.x = particle.userData.baseX + Math.sin(seconds * 0.8 + particle.userData.phase) * 0.028;
        particle.position.y = particle.userData.baseY + Math.cos(seconds * 1.25 + particle.userData.phase) * 0.055;
        const twinkle = 0.25 + Math.abs(Math.sin(seconds * 2.6 + particle.userData.phase)) * 0.65;
        particle.scale.setScalar(0.7 + twinkle * 0.8);
        particleMaterial.opacity = twinkle;
      });
      renderer.render(scene, camera);
    }

    renderer.setAnimationLoop(draw);
    observer = new MutationObserver(() => { if (gate.style.display === 'none') release(); });
    observer.observe(gate, { attributes: true, attributeFilter: ['style'] });
  }).catch(fallback);
  window.addEventListener('pagehide', release, { once: true });
})();