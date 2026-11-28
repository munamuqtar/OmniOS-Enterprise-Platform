import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { screenFor } from "../../app/screens";
import Sidebar from "../sidebar/Sidebar";
import Navbar from "../navbar/Navbar";

export default function AppLayout() {
  const { pathname } = useLocation();
  const [openAt, setOpenAt] = useState(null);   // the mobile menu is open only for the page it was opened on
  const open = openAt === pathname;

  useEffect(() => {
    const screen = screenFor(pathname);
    document.title = screen ? `${screen.label} · OmniOS` : "OmniOS";
  }, [pathname]);

  return (
    <div className="app">
      <Sidebar open={open} onNavigate={() => setOpenAt(null)} />
      {open && <div className="scrim" onClick={() => setOpenAt(null)} />}
      <div className="main">
        <Navbar onMenu={() => setOpenAt(pathname)} />
        <main className="content"><Outlet /></main>
      </div>
    </div>
  );
}