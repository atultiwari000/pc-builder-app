import { useEffect } from "react";
import { useGLTF } from "@react-three/drei";
import { type Group, Mesh, MeshStandardMaterial, Object3D } from "three";

type Props = {
  url: string;
  scale?: [number, number, number];
  position?: [number, number, number];
  rotation?: [number, number, number];
  tint?: string;
};

export default function GLTFModel({
  url,
  scale,
  position,
  rotation,
  tint,
}: Props) {
  const gltf = useGLTF(url) as unknown as { scene: Group };

  useEffect(() => {
    if (!tint) return;
    const applyTint = (obj: Object3D) => {
      obj.traverse((child) => {
        if ((child as Mesh).isMesh) {
          const mesh = child as Mesh;
          const material = mesh.material as
            | MeshStandardMaterial
            | MeshStandardMaterial[];
          if (Array.isArray(material)) {
            material.forEach((m) => {
              if (m && "color" in m) m.color.set(tint);
            });
          } else if (material && "color" in material) {
            material.color.set(tint);
          }
        }
      });
    };
    applyTint(gltf.scene);
  }, [gltf.scene, tint]);

  return (
    <primitive
      object={gltf.scene}
      scale={scale || [1, 1, 1]}
      position={position || [0, 0, 0]}
      rotation={rotation || [0, 0, 0]}
    />
  );
}
