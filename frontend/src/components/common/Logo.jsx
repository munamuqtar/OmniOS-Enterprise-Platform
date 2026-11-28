export default function Logo({ className = "", height = 40 }) {
  return <img src="/logo.png" alt="Omni Teckno" className={className} style={{ height, width: "auto" }} />;
}