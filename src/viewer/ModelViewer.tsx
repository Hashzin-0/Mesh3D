import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

type Props = { url: string; label: string };
export default function ModelViewer({ url, label }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!host.current) return;
    const element = host.current;
    let disposed = false;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#111318");
    const camera = new THREE.PerspectiveCamera(42, element.clientWidth / Math.max(element.clientHeight, 1), 0.01, 1000);
    camera.position.set(2.8, 2.2, 3.5);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(element.clientWidth, element.clientHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    element.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    scene.add(new THREE.HemisphereLight(0xffffff, 0x343a46, 2.2));
    const key = new THREE.DirectionalLight(0xffffff, 2.4);
    key.position.set(4, 7, 5); scene.add(key);
    const grid = new THREE.GridHelper(6, 24, 0x414752, 0x252932); scene.add(grid);
    const loader = new GLTFLoader();
    loader.load(url, (gltf) => {
      if (disposed) return;
      scene.add(gltf.scene);
      const bounds = new THREE.Box3().setFromObject(gltf.scene);
      const center = bounds.getCenter(new THREE.Vector3());
      const size = bounds.getSize(new THREE.Vector3());
      gltf.scene.position.sub(center);
      const largest = Math.max(size.x, size.y, size.z) || 1;
      camera.position.set(largest * 1.8, largest * 1.25, largest * 2.1);
      camera.near = Math.max(largest / 1000, 0.001); camera.far = largest * 100; camera.updateProjectionMatrix();
      controls.target.set(0, 0, 0); controls.update(); setError("");
    }, undefined, (cause) => { if (!disposed) setError(cause instanceof Error ? cause.message : "Could not load this 3D artifact."); });
    let frame = 0;
    const animate = () => { if (disposed) return; frame = requestAnimationFrame(animate); controls.update(); renderer.render(scene, camera); };
    animate();
    const resize = () => { if (!element.clientWidth || !element.clientHeight) return; camera.aspect = element.clientWidth / element.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(element.clientWidth, element.clientHeight); };
    const observer = new ResizeObserver(resize); observer.observe(element);
    return () => { disposed = true; cancelAnimationFrame(frame); observer.disconnect(); controls.dispose(); renderer.dispose(); scene.traverse((object) => { const mesh = object as THREE.Mesh; if (mesh.geometry) mesh.geometry.dispose(); if (Array.isArray(mesh.material)) mesh.material.forEach((material) => material.dispose()); else if (mesh.material) mesh.material.dispose(); }); renderer.domElement.remove(); };
  }, [url]);
  return <div className="model-viewer" ref={host} role="img" aria-label={`Interactive 3D model viewer: ${label}`}>{error && <div className="viewer-error">{error}</div>}</div>;
}