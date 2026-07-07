import { useNavigate } from "react-router-dom";

import { useAuth } from "../../context/AuthContext";
import Button from "../ui/Button";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-6">
      <div />
      <div className="flex items-center gap-4">
        <span className="text-sm text-slate-600">{user?.email}</span>
        <Button variant="secondary" size="sm" onClick={handleLogout}>
          Log out
        </Button>
      </div>
    </header>
  );
}
