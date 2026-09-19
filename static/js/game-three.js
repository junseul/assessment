/* Three.js owns stimulus pixels; the existing game owns timing, input and scoring. */
(() => {
  const moduleUrl = new URL('../vendor/three/three.module.js', document.currentScript.src);
  const area = document.getElementById('playArea');
  const start = document.getElementById('startBtn');
  if (!area || !start || start.closest('[hidden]')) return;
  const originallyDisabled = start.disabled;
  start.disabled = true;
  let renderer, observer, stopped = false;
  const entries = new Map();
  const resources = new Set();

  function release() {
    stopped = true;
    observer?.disconnect();
    renderer?.setAnimationLoop(null);
    area.querySelectorAll('.three-replaced').forEach(el => el.classList.remove('three-replaced'));
    entries.clear();
    resources.forEach(resource => resource.dispose());
    resources.clear();
    renderer?.dispose();
    renderer?.domElement.remove();
  }

  function fallback(error) {
    release();
    start.disabled = originallyDisabled;
    const notice = document.createElement('p');
    notice.className = 'three-renderer-notice';
    notice.setAttribute('role', 'status');
    notice.textContent = '3D 화면을 사용할 수 없어 기본 화면으로 진행합니다.';
    area.before(notice);
    console.warn('Three.js renderer unavailable:', error);
  }

  import(moduleUrl.href).then(async THREE => {
    if (stopped) return;
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.domElement.className = 'game-three-canvas';
    renderer.domElement.setAttribute('aria-hidden', 'true');
    renderer.domElement.addEventListener('webglcontextlost', event => {
      event.preventDefault();
      fallback('WebGL context lost');
    }, { once: true });
    area.append(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(0, 1, 1, 0, 0.1, 2000);
    camera.position.z = 1000;
    scene.add(new THREE.HemisphereLight(0xffffff, 0x687890, 2));
    const light = new THREE.DirectionalLight(0xffffff, 2.5);
    light.position.set(-200, 400, 800);
    scene.add(light);
    const keep = resource => { resources.add(resource); return resource; };
    const box = keep(new THREE.BoxGeometry(1, 1, 1));
    const disc = keep(new THREE.CircleGeometry(0.5, 48));
    const ring = keep(new THREE.TorusGeometry(0.4, 0.04, 8, 40));
    const plane = keep(new THREE.PlaneGeometry(1, 1));
    const cone = keep(new THREE.ConeGeometry(0.5, 1, 5));
    const materials = new Map();
    function material(color, flat = false) {
      const key = `${color}/${flat}`;
      if (!materials.has(key)) materials.set(key, keep(flat
        ? new THREE.MeshBasicMaterial({ color })
        : new THREE.MeshStandardMaterial({ color, roughness: 0.6, metalness: 0.15 })));
      return materials.get(key);
    }
    function shape(points) {
      const outline = new THREE.Shape();
      points.forEach(([x, y], i) => i ? outline.lineTo(x, y) : outline.moveTo(x, y));
      outline.closePath();
      return keep(new THREE.ExtrudeGeometry(outline, { depth: 0.08, bevelEnabled: false }));
    }
    const aircraft = shape([[0,.43],[.08,.12],[.38,-.12],[.38,-.2],[.08,-.12],[.07,-.32],[.2,-.4],[.2,-.46],[0,-.4],[-.2,-.46],[-.2,-.4],[-.07,-.32],[-.08,-.12],[-.38,-.2],[-.38,-.12],[-.08,.12]]);
    const arrow = shape([[-.45,-.14],[.08,-.14],[.08,-.4],[.48,0],[.08,.4],[.08,.14],[-.45,.14]]);
    const glyphs = new Map();
    for (const char of '123456789★') {
      const canvas = document.createElement('canvas');
      canvas.width = canvas.height = 128;
      const ctx = canvas.getContext('2d');
      ctx.font = 'bold 96px sans-serif';
      ctx.fillStyle = '#20334b';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(char, 64, 69);
      const map = keep(new THREE.CanvasTexture(canvas));
      map.colorSpace = THREE.SRGBColorSpace;
      glyphs.set(char, keep(new THREE.MeshBasicMaterial({ map, transparent: true })));
    }
    function mesh(group, geometry, color, scale, position = [0,0,0], flat = false) {
      const object = new THREE.Mesh(geometry, material(color, flat));
      object.scale.set(...scale);
      object.position.set(...position);
      group.add(object);
      return object;
    }
    const selector = '.radar-target, .brake-box, .sort-item, .drone, .search-item, .cipher-panel > span > span, .rsvp-item, #ssStim, .three-exp-site';
    function create(el) {
      const group = new THREE.Group();
      let signal, outline, glyph;
      if (el.matches('.radar-target')) {
        signal = mesh(group, ring, '#22a06b', [1,1,1]);
        mesh(group, aircraft, '#dbe5ee', [.85,.85,.85], [0,0,.05]);
        mesh(group, box, '#2f6fed', [.07,.22,.04], [0,.06,.14]);
      } else if (el.matches('.drone')) {
        outline = mesh(group, ring, '#e5484d', [1.08,1.08,1], [0,0,-.1]);
        mesh(group, box, '#273e54', [.6,.09,.08]).rotation.z = Math.PI / 4;
        mesh(group, box, '#273e54', [.6,.09,.08]).rotation.z = -Math.PI / 4;
        for (const x of [-.27,.27]) for (const y of [-.27,.27]) {
          mesh(group, ring, '#536e85', [.38,.38,.5], [x,y,.02]);
          mesh(group, box, '#a9c9e0', [.22,.035,.02], [x,y,.04]);
        }
        mesh(group, box, '#dce7ee', [.24,.32,.16]);
        mesh(group, box, '#2f6fed', [.09,.09,.04], [0,.07,.1]);
      } else if (el.matches('.brake-box')) {
        mesh(group, box, '#273e54', [1,1,.18]);
        signal = mesh(group, box, '#22a06b', [.86,.8,.12], [0,0,.12]);
        for (const x of [-.29,0,.29]) mesh(group, box, '#ffffff', [.14,.045,.025], [x,0,.19], true);
      } else if (el.matches('.three-exp-site')) {
        const ground = mesh(group, box, '#b4d1c5', [.86,.35,.5], [0,-.22,0]);
        ground.rotation.x = .45;
        mesh(group, cone, '#658e84', [.45,.55,.5], [-.18,.12,.05]);
        mesh(group, box, '#dbe5ee', [.3,.27,.28], [.2,-.02,.2]).rotation.y = -.35;
        mesh(group, box, '#2f6fed', [.09,.09,.03], [.2,0,.37]);
      } else if (el.id === 'ssStim') {
        mesh(group, box, '#b5c8d6', [1,1,.14]);
        mesh(group, plane, '#f3f8fc', [.9,.9,1], [0,0,.08], true);
        glyph = new THREE.Mesh(plane, glyphs.get('1'));
        glyph.scale.set(.95,.95,1);
        glyph.position.z = .1;
        group.add(glyph);
      } else if (el.matches('.cipher-panel > span > span')) {
        signal = mesh(group, arrow, '#2f6fed', [1,1,1]);
      } else {
        const css = getComputedStyle(el);
        const circular = css.borderRadius === '50%';
        signal = mesh(group, circular ? disc : box, css.backgroundColor, [1,1,.12], [0,0,0], el.matches('.rsvp-item'));
        if (el.matches('.search-item')) {
          mesh(group, ring, '#d9e5f4', [.4,.4,.35], [0,0,.1]);
        } else if (el.matches('.sort-item')) {
          mesh(group, ring, '#ffffff', [.45,.45,.5], [0,0,.1]);
        }
      }
      scene.add(group);
      return { group, signal, outline, glyph };
    }

    // Compile before the first timed trial, including the fast RSVP/glyph materials.
    const warm = new THREE.Group();
    for (const geometry of [box, disc, ring, aircraft, arrow, cone, plane]) {
      mesh(warm, geometry, '#2f6fed', [1,1,1]);
      mesh(warm, geometry, '#2f6fed', [1,1,1], [0,0,0], true);
    }
    glyphs.forEach(mat => { warm.add(new THREE.Mesh(plane, mat)); renderer.initTexture(mat.map); });
    scene.add(warm);
    renderer.setSize(1, 1, false);
    await renderer.compileAsync(scene, camera);
    scene.remove(warm);
    if (stopped) return;
    let width = 0, height = 0;
    function draw() {
      if (stopped) return;
      try {
        const bounds = area.getBoundingClientRect();
        if (!bounds.width || !bounds.height) return;
        if (width !== bounds.width || height !== bounds.height) {
          width = bounds.width; height = bounds.height;
          renderer.setSize(width, height);
          camera.right = width; camera.top = height;
          camera.updateProjectionMatrix();
        }
        for (const [el, entry] of entries) if (!area.contains(el)) {
          scene.remove(entry.group);
          entries.delete(el);
        }
        const replaced = [];
        area.querySelectorAll(selector).forEach(el => {
          if (!entries.has(el)) entries.set(el, create(el));
          const { group, signal, outline, glyph } = entries.get(el);
          const rect = el.getBoundingClientRect();
          const css = getComputedStyle(el);
          group.visible = !!rect.width && !!rect.height && css.visibility !== 'hidden';
          if (glyph) {
            group.visible = group.visible && glyphs.has(el.textContent.trim());
            if (group.visible) glyph.material = glyphs.get(el.textContent.trim());
          }
          const size = el.matches('.cipher-panel > span > span, #ssStim') ? parseFloat(css.fontSize) : null;
          group.scale.set(size || el.offsetWidth, size || el.offsetHeight, Math.min(size || el.offsetWidth, size || el.offsetHeight));
          group.position.set(rect.left - bounds.left + rect.width / 2, height - (rect.top - bounds.top + rect.height / 2), 0);
          // CSS's clockwise rotation becomes counterclockwise in world coordinates.
          if (css.transform !== 'none' && !el.matches('.radar-target')) {
            const matrix = new DOMMatrixReadOnly(css.transform);
            group.rotation.z = -Math.atan2(matrix.b, matrix.a);
          }
          if (signal) {
            const color = el.matches('.radar-target') ? (el.classList.contains('danger') ? '#e5484d' : '#22a06b')
              : el.matches('.cipher-panel > span > span') ? css.color : css.backgroundColor;
            signal.material = material(color, el.matches('.rsvp-item'));
          }
          if (outline) {
            outline.visible = el.matches('.target-highlight, .selected');
            outline.material = material(el.classList.contains('selected') ? '#22a06b' : '#e5484d');
          }
          replaced.push(el);
        });
        renderer.render(scene, camera);
        // Hide originals only after a successful draw; preserve layout and hit targets.
        replaced.forEach(el => { if (!el.classList.contains('three-replaced')) el.classList.add('three-replaced'); });
      } catch (error) { fallback(error); }
    }
    observer = new MutationObserver(records => {
      // Our opacity marker must not create a self-sustaining observer loop.
      if (records.some(record => record.type !== 'attributes' || record.attributeName !== 'class'
        || record.oldValue?.replace(/\bthree-replaced\b/g, '').trim() !== record.target.className.replace(/\bthree-replaced\b/g, '').trim())) draw();
    });
    observer.observe(area, { subtree: true, childList: true, characterData: true, attributes: true, attributeOldValue: true, attributeFilter: ['style', 'class'] });
    renderer.setAnimationLoop(draw);
    start.disabled = originallyDisabled;
    draw();
  }).catch(fallback);
  window.addEventListener('pagehide', release, { once: true });
})();
