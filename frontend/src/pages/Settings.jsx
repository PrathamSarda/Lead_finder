import {
  CheckCircle2,
  Database,
  Globe,
  Key,
  Layers,
  Server,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Settings() {
  const { user } = useAuth();

  return (
    <div className="space-y-6 max-w-4xl pb-16">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="rounded-full bg-indigo-500/15 px-2.5 py-0.5 text-xs font-semibold text-indigo-400">
            System Configuration
          </span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-white">Platform Settings & Integrations</h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-400">
          Inspection parameters, pipeline connectors, and client lead generation targets.
        </p>
      </div>

      {/* Target Lead Profile */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/15 text-indigo-400">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Client Lead Target</h2>
              <p className="text-xs text-slate-400">Client: Prokizen Global LLP</p>
            </div>
          </div>
          <span className="rounded-full bg-emerald-500/15 px-3 py-1 text-xs font-bold text-emerald-400 border border-emerald-500/20">
            Active Contract Target
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
            <span className="text-[11px] font-medium text-slate-400 block">Daily Lead Target</span>
            <span className="text-xl font-black text-white mt-0.5 block">80 Companies / day</span>
            <span className="text-[10px] text-slate-400">Verified official domain & email</span>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
            <span className="text-[11px] font-medium text-slate-400 block">Company Size Filter</span>
            <span className="text-xl font-black text-indigo-300 mt-0.5 block">1–20 Employees</span>
            <span className="text-[10px] text-slate-400">Small business focus</span>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3.5">
            <span className="text-[11px] font-medium text-slate-400 block">Target Region</span>
            <span className="text-xl font-black text-emerald-300 mt-0.5 block">United States</span>
            <span className="text-[10px] text-slate-400">Nationwide registry</span>
          </div>
        </div>
      </div>

      {/* Active Pipeline Connectors */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Layers className="h-5 w-5 text-indigo-400" />
          Active Pipeline Connectors & Verification Engines
        </h2>

        <div className="divide-y divide-slate-800/60 text-xs">
          <div className="flex items-center justify-between py-3">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <div>
                <p className="font-semibold text-slate-200">FMCSA Database Connector</p>
                <p className="text-slate-400">Active US registry search worker</p>
              </div>
            </div>
            <span className="rounded bg-emerald-500/10 px-2.5 py-1 text-emerald-400 font-semibold border border-emerald-500/20">
              Online
            </span>
          </div>

          <div className="flex items-center justify-between py-3">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <div>
                <p className="font-semibold text-slate-200">Company Website Resolver (DuckDuckGo / Zenserp)</p>
                <p className="text-slate-400">Domain similarity matching & website resolver</p>
              </div>
            </div>
            <span className="rounded bg-emerald-500/10 px-2.5 py-1 text-emerald-400 font-semibold border border-emerald-500/20">
              Online
            </span>
          </div>

          <div className="flex items-center justify-between py-3">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <div>
                <p className="font-semibold text-slate-200">Contact Web Crawler & Email Extractor</p>
                <p className="text-slate-400">Homepage + Contact/About page crawler with RFC email regex</p>
              </div>
            </div>
            <span className="rounded bg-emerald-500/10 px-2.5 py-1 text-emerald-400 font-semibold border border-emerald-500/20">
              Online
            </span>
          </div>

          <div className="flex items-center justify-between py-3">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <div>
                <p className="font-semibold text-slate-200">Strict Lead Verification Layer</p>
                <p className="text-slate-400">
                  Calculates confidence scores, classifies lead tiers (FULL_LEAD vs WEBSITE_ONLY)
                </p>
              </div>
            </div>
            <span className="rounded bg-emerald-500/10 px-2.5 py-1 text-emerald-400 font-semibold border border-emerald-500/20">
              Online
            </span>
          </div>
        </div>
      </div>

      {/* Account Info */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 backdrop-blur-xl">
        <h2 className="text-base font-bold text-white mb-3">Operator Account</h2>
        <div className="flex items-center justify-between rounded-xl bg-slate-950/60 p-4 border border-slate-800/80 text-xs">
          <div>
            <p className="font-semibold text-slate-200">{user?.full_name || "Prokizen Client"}</p>
            <p className="text-slate-400">{user?.email || "client@prokizen.com"}</p>
          </div>
          <span className="rounded bg-indigo-500/20 px-2.5 py-1 text-[11px] font-semibold text-indigo-300">
            {user?.role || "Lead Operations"}
          </span>
        </div>
      </div>
    </div>
  );
}
