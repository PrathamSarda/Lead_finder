import { useAuth } from "../context/AuthContext";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";

export default function Settings() {
  const { user } = useAuth();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">Manage your account preferences.</p>
      </div>

      <Card title="Profile" description="Basic account information.">
        <div className="space-y-3 text-sm">
          <div className="flex justify-between border-b border-slate-100 pb-3">
            <span className="text-slate-500">Email</span>
            <span className="font-medium text-slate-900">{user?.email}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Full name</span>
            <span className="font-medium text-slate-900">{user?.full_name || "—"}</span>
          </div>
        </div>
      </Card>

      <Card title="Danger zone" description="Irreversible actions.">
        <Button variant="danger" disabled>
          Delete account
        </Button>
      </Card>
    </div>
  );
}
