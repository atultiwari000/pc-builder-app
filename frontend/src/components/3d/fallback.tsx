import { Box, Cylinder, Sphere } from "@react-three/drei";

export function FallbackModel({ category }: { category: string }) {
  switch (category) {
    case "cpu":
      return (
        <Box args={[2, 0.2, 2]} position={[0, 0, 0]}>
          <meshStandardMaterial color={"#4ade80"} />
        </Box>
      );
    case "gpu":
      return (
        <Box args={[3, 1, 0.5]} position={[0, 0, 0]}>
          <meshStandardMaterial color={"#ef4444"} />
        </Box>
      );
    case "motherboard":
      return (
        <Box args={[4, 0.1, 3]} position={[0, 0, 0]}>
          <meshStandardMaterial color={"#3b82f6"} />
        </Box>
      );
    case "memory":
      return (
        <Box args={[0.3, 1.5, 2]} position={[0, 0, 0]}>
          <meshStandardMaterial color={"#8b5cf6"} />
        </Box>
      );
    case "storage":
      return (
        <Box args={[1.5, 0.3, 2.5]} position={[0, 0, 0]}>
          <meshStandardMaterial color={"#f59e0b"} />
        </Box>
      );
    case "cooling":
      return (
        <Cylinder args={[1, 1, 0.5, 8]} position={[0, 0, 0]}>
          <meshStandardMaterial color={"#06b6d4"} />
        </Cylinder>
      );
    default:
      return (
        <Sphere args={[1]} position={[0, 0, 0]}>
          <meshStandardMaterial color={"#6b7280"} />
        </Sphere>
      );
  }
}
