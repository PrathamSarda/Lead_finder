import { useAuth } from "../../context/AuthContext";
import { LogOut } from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-18 items-center justify-between border-b border-slate-800/80 bg-slate-950/80 px-6 backdrop-blur-xl">
      {/* Local workflow indicator */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-400">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
          </span>
          <span>Local workspace</span>
          <span className="text-slate-400">• FMCSA + LinkedIn intent discovery</span>
        </div>
      </div>

      {/* Local user profile */}
      <div className="flex items-center gap-3">
        <div className="h-5 w-[1px] bg-slate-800" />

        {/* User Badge */}
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800 border border-slate-700 text-xs font-semibold text-slate-300">
            PG
          </div>
          <div className="hidden text-left lg:block">
            <p className="text-xs font-semibold text-slate-200">{user?.full_name || "Prokizen Client"}</p>
            <p className="text-[10px] text-slate-400">{user?.email || "client@prokizen.com"}</p>
          </div>
          <button
            onClick={logout}
            title="Log out or reset session"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
