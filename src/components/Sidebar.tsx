import { Link, useLocation, useNavigate } from "react-router-dom";

import {
  FaHome,
  FaTasks,
  FaCalendarAlt,
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
        <h2> Intern Onboarding-Companion</h2>
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
          <span>My Tasks</span>
        </Link>

        <Link
          to="/events"
          className={location.pathname === "/events" ? "active" : ""}
        >
          <FaCalendarAlt />
          <span>Events</span>
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
