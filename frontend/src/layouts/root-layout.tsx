import { NavLink, Outlet } from "react-router";
import { cn } from "@/lib/utils";
import { Toaster } from "@/components/ui/sonner";
import { Icon } from "@/components/ui/icon";

const NAV_ITEMS = [
  { to: "/assignments", label: "Assignments", icon: "assignment" },
  { to: "/calendar", label: "Calendar", icon: "calendar_month" },
  { to: "/duties", label: "Duties", icon: "task" },
  { to: "/people", label: "People", icon: "group" },
  { to: "/rules", label: "Rules", icon: "gavel" },
  { to: "/stats", label: "Stats", icon: "bar_chart" },
] as const;

export function RootLayout() {
  return (
    <div className="min-h-screen bg-background">
      <nav className="border-b border-border">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-6 px-4">
          <span className="flex items-center gap-2 text-lg font-semibold tracking-tight">
            <Icon name="shield" className="text-primary text-[1.25rem]" />
            Duty Roster
          </span>
          <div className="flex gap-1">
            {NAV_ITEMS.map(({ to, label, icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground hover:text-foreground",
                  )
                }
              >
                <Icon name={icon} className="text-[1.125rem]" />
                {label}
              </NavLink>
            ))}
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-6xl p-4">
        <Outlet />
      </main>
      <Toaster />
    </div>
  );
}
