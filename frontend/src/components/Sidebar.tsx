import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/auth";
import ThemeToggle from "./ThemeToggle";

import { FaHome, FaTasks, FaUser, FaSignOutAlt } from "react-icons/fa";

import "../styles/Sidebar.css";

function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <aside className="sidebar">
      <div className="logo">
        <h2>Intern Onboarding Companion</h2>

        <p className="logo-tagline">Internship Workbench</p>
      </div>

      <nav className="menu" aria-label="Primary navigation">
        <Link
          to="/dashboard"
          className={location.pathname === "/dashboard" ? "active" : ""}
          aria-current={location.pathname === "/dashboard" ? "page" : undefined}
        >
          <FaHome aria-hidden="true" />
          <span>Dashboard</span>
        </Link>

        <Link
          to="/tasks"
          className={location.pathname === "/tasks" ? "active" : ""}
          aria-current={location.pathname === "/tasks" ? "page" : undefined}
        >
          <FaTasks aria-hidden="true" />
          <span>Onboarding Checklist</span>
        </Link>

        <Link
          to="/profile"
          className={location.pathname === "/profile" ? "active" : ""}
          aria-current={location.pathname === "/profile" ? "page" : undefined}
        >
          <FaUser aria-hidden="true" />
          <span>Profile</span>
        </Link>
      </nav>

      <div className="logout">
        <ThemeToggle />

        <button onClick={handleLogout} type="button">
          <FaSignOutAlt aria-hidden="true" />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
