import "./../styles/Login.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../services/auth";

function Login() {
  const navigate = useNavigate();

  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = async () => {
    try {
      const data = await login(phone, password);

      // Save JWT token (change this if your backend uses a different field name)
      if (data.access_token) {
        localStorage.setItem("token", data.access_token);
      }

      navigate("/dashboard");
    } catch (error) {
      console.error("Login failed:", error);
      alert("Invalid phone number or password");
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Intern Onboarding</h1>
        <h2>Login</h2>

        <div className="input-group">
          <label>Phone Number</label>
          <input
            type="tel"
            placeholder="Enter your phone number"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        </div>

        <div className="input-group">
          <label>Password</label>
          <input
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        <p className="forgot-password">
          Forgot Password?
        </p>

        <button onClick={handleLogin}>
          Login
        </button>
      </div>
    </div>
  );
}

export default Login;