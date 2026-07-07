import { createContext, useCallback, useContext, useState } from "react";

const ToastContext = createContext(null);

const VARIANT_CLASSES = {
  success: "bg-emerald-600",
  error: "bg-red-600",
  info: "bg-slate-800",
};

let idCounter = 0;

/**
 * Wrap the app with <ToastProvider> once, then call `useToast().showToast(...)`
 * anywhere to display a dismissible toast notification.
 */
export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const showToast = useCallback(
    (message, variant = "info", duration = 4000) => {
      const id = ++idCounter;
      setToasts((current) => [...current, { id, message, variant }]);
      if (duration) {
        setTimeout(() => removeToast(id), duration);
      }
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`min-w-[240px] rounded-lg px-4 py-3 text-sm text-white shadow-lg ${VARIANT_CLASSES[toast.variant]}`}
          >
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
