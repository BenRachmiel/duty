import { lazy, Suspense } from "react";
import { createBrowserRouter } from "react-router";
import { RootLayout } from "./layouts/root-layout";

const PeoplePage = lazy(() => import("./pages/people").then((m) => ({ default: m.PeoplePage })));
const DutiesPage = lazy(() => import("./pages/duties").then((m) => ({ default: m.DutiesPage })));
const RulesPage = lazy(() => import("./pages/rules").then((m) => ({ default: m.RulesPage })));
const AssignmentsPage = lazy(() => import("./pages/assignments").then((m) => ({ default: m.AssignmentsPage })));
const CalendarPage = lazy(() => import("./pages/calendar").then((m) => ({ default: m.CalendarPage })));
const StatsPage = lazy(() => import("./pages/stats").then((m) => ({ default: m.StatsPage })));
const NotFoundPage = lazy(() => import("./pages/not-found").then((m) => ({ default: m.NotFoundPage })));

function SuspenseWrapper({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="p-6 text-muted-foreground">Loading...</div>}>
      {children}
    </Suspense>
  );
}

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    children: [
      { index: true, element: <SuspenseWrapper><AssignmentsPage /></SuspenseWrapper> },
      { path: "people", element: <SuspenseWrapper><PeoplePage /></SuspenseWrapper> },
      { path: "duties", element: <SuspenseWrapper><DutiesPage /></SuspenseWrapper> },
      { path: "rules", element: <SuspenseWrapper><RulesPage /></SuspenseWrapper> },
      { path: "assignments", element: <SuspenseWrapper><AssignmentsPage /></SuspenseWrapper> },
      { path: "calendar", element: <SuspenseWrapper><CalendarPage /></SuspenseWrapper> },
      { path: "stats", element: <SuspenseWrapper><StatsPage /></SuspenseWrapper> },
      { path: "*", element: <SuspenseWrapper><NotFoundPage /></SuspenseWrapper> },
    ],
  },
]);
