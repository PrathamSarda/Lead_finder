import { Link, useRouteError } from "react-router-dom";

import Button from "../components/ui/Button";

export default function ErrorPage() {
  const error = useRouteError();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4 text-center">
      <p className="text-sm font-semibold text-red-600">Something went wrong</p>
      <h1 className="mt-2 text-2xl font-semibold text-slate-900">Unexpected error</h1>
      <p className="mt-2 max-w-md text-sm text-slate-500">
        {error?.statusText || error?.message || "An unexpected error occurred. Please try again."}
      </p>
      <Link to="/" className="mt-6">
        <Button>Go back home</Button>
      </Link>
    </div>
  );
}
