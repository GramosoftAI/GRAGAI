// components/ui/FallbackLoader.tsx
export const FallbackLoader = () => (
  <div style={{
    display: "flex", flexDirection: "column",
    height: "100vh", alignItems: "center",
    justifyContent: "center", gap: 12,
  }}>
    <div style={{
      width: 40, height: 40, borderRadius: "50%",
      border: "4px solid #319795",       // teal.600 hex
      borderTopColor: "transparent",
      animation: "spin 0.7s linear infinite",
    }} />
    <span style={{ color: "#319795", fontFamily: "sans-serif" }}>Loading...</span>
    <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
  </div>
);