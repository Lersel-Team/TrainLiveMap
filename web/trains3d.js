// Draws train models on the map as a MapLibre custom layer. Each vehicle type is one instanced mesh per material.
// window.trainCars is filled by the page: {type, lon, lat, brg, pitch, ele, scale}.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const CAPACITY = 400;

export async function addTrainModels(map) {
  const loader = new GLTFLoader();
  const load = url => new Promise((ok, no) => loader.load(url, g => ok(g.scene), undefined, no));
  const NAMES = ['qsy', 'btc', 'cnr_ans', 'cnr_anf', 'cnr_arc', 'cnr_pwr'];
  const roots = await Promise.all(NAMES.map(n => load(`/models/${n}.glb`)));
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8678, 1.35));
  const sun = new THREE.DirectionalLight(0xfff4e6, .95); sun.position.set(.4, .5, 1); scene.add(sun);
  const types = {};
  for (const [i, name] of NAMES.entries()) {
    const root = roots[i];
    const parts = [];
    root.updateMatrixWorld(true);
    root.traverse(o => { if (o.isMesh) {
      const m = new THREE.InstancedMesh(o.geometry, o.material, CAPACITY);
      m.frustumCulled = false; m.count = 0; scene.add(m); parts.push({ mesh: m, local: o.matrixWorld.clone() });
    } });
    types[name] = parts;
  }
  const camera = new THREE.Camera();
  let renderer;
  const f = new THREE.Vector3(), u = new THREE.Vector3(), r = new THREE.Vector3(), up = new THREE.Vector3(0, 0, 1);
  const inst = new THREE.Matrix4(), out = new THREE.Matrix4(), sc = new THREE.Matrix4();
  map.addLayer({
    id: 'train-models', type: 'custom', renderingMode: '3d',
    onAdd(_, gl) { renderer = new THREE.WebGLRenderer({ canvas: map.getCanvas(), context: gl, antialias: true }); renderer.autoClear = false; },
    render(gl, args) {
      const c = map.getCenter(), org = maplibregl.MercatorCoordinate.fromLngLat(c, 0), unit = org.meterInMercatorCoordinateUnits();
      const kx = 111320 * Math.cos(c.lat * Math.PI / 180), ky = 111320;
      const n = Object.fromEntries(NAMES.map(t => [t, 0]));
      for (const v of window.trainCars || []) {
        const parts = types[v.type]; if (!parts || n[v.type] >= CAPACITY) continue;
        const b = v.brg * Math.PI / 180, p = v.pitch || 0;
        f.set(Math.sin(b) * Math.cos(p), Math.cos(b) * Math.cos(p), Math.sin(p)).normalize();
        r.crossVectors(f, up).normalize(); u.crossVectors(r, f).normalize();
        inst.makeBasis(f, u, r);                            // model X forward, Y up, Z right
        sc.makeScale(v.scale, v.scale, v.scale); inst.multiply(sc);
        inst.setPosition((v.lon - c.lng) * kx, (v.lat - c.lat) * ky, v.ele || 0);
        for (const part of parts) part.mesh.setMatrixAt(n[v.type], out.multiplyMatrices(inst, part.local));
        n[v.type]++;
      }
      for (const t in types) for (const part of types[t]) { part.mesh.count = n[t]; part.mesh.instanceMatrix.needsUpdate = true; }
      // Metres east/north/up to MapLibre's clip space; computed in doubles, so no jitter at high zoom.
      const main = new THREE.Matrix4().fromArray(args.defaultProjectionData.mainMatrix);
      const world = new THREE.Matrix4().makeTranslation(org.x, org.y, 0).scale(new THREE.Vector3(unit, -unit, unit));
      camera.projectionMatrix = main.multiply(world);
      renderer.resetState();
      renderer.render(scene, camera);
    },
  });
  return true;
}
