import { useState } from "react";
import { Outlet } from "react-router-dom";

import Navbar from "./Navbar";
import Sidebar from "./Sidebar";
import RunModal from "../pipeline/RunModal";
import { leadsApi } from "../../api/leads";

export default function Layout() {
  const [isRunModalOpen, setIsRunModalOpen] = useState(false);

  const handleGlobalExcelExport = async () => {
    try {
      const data = await leadsApi.getLeads({ limit: 1000 });
      leadsApi.exportToExcelClient(data.items, null, data.summary);
    } catch (err) {
      alert("Failed to export Excel: " + err.message);
    }
  };

  return (
    <div className="flex h-screen bg-[#0b0f19] text-slate-100 overflow-hidden">
      <Sidebar onOpenRunModal={() => setIsRunModalOpen(true)} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Navbar
          onOpenRunModal={() => setIsRunModalOpen(true)}
          onExportExcel={handleGlobalExcelExport}
        />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <Outlet context={{ openRunModal: () => setIsRunModalOpen(true) }} />
        </main>
      </div>

      <RunModal
        isOpen={isRunModalOpen}
        onClose={() => setIsRunModalOpen(false)}
      />
    </div>
  );
}
