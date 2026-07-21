import { Link, useLocation, useNavigate } from "react-router-dom";

import {
  FaHome,
  FaTasks,
  FaUser,
  FaSignOutAlt,
} from "react-icons/fa";

import "../styles/Sidebar.css";

function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/");
  };

  return (
    <aside className="sidebar">
      <div className="logo">
        <h2>Intern Onboarding Companion</h2>
<p
  style={{
    fontSize: "12px",
    color: "#666",
    marginTop: "6px",
    textAlign: "center",
  }}
>
  Internship Workbench
</p>
      </div>

      <nav className="menu">
        <Link
          to="/dashboard"
          className={location.pathname === "/dashboard" ? "active" : ""}
        >
          <FaHome />
          <span>Dashboard</span>
        </Link>

        <Link
          to="/tasks"
          className={location.pathname === "/tasks" ? "active" : ""}
        >
          <FaTasks />
          <span>Onboarding Checklist</span>
        </Link>

        <Link
          to="/profile"
          className={location.pathname === "/profile" ? "active" : ""}
        >
          <FaUser />
          <span>Profile</span>
        </Link>
      </nav>

      <div className="logout">
        <button
          onClick={handleLogout}
          style={{
            background: "none",
            border: "none",
            color: "inherit",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            fontSize: "16px",
            width: "100%",
          }}
        >
          <FaSignOutAlt />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;