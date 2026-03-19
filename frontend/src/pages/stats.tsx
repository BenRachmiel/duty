import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import {
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import { fetchStats } from "@/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { StatsResponse } from "@/types";

function defaultDateRange(): { from: string; to: string } {
  const from = new Date();
  const to = new Date();
  from.setDate(from.getDate() - 30);
  to.setDate(to.getDate() + 30);
  return {
    from: from.toISOString().slice(0, 10),
    to: to.toISOString().slice(0, 10),
  };
}

export function StatsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const defaults = useMemo(() => defaultDateRange(), []);

  const dateFrom = searchParams.get("date_from") || defaults.from;
  const dateTo = searchParams.get("date_to") || defaults.to;

  const { data, isLoading } = useQuery<StatsResponse>({
    queryKey: ["stats", dateFrom, dateTo],
    queryFn: () => fetchStats({ date_from: dateFrom, date_to: dateTo }),
  });

  const setParam = (key: string, value: string) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set(key, value);
      return next;
    });
  };

  const histogramData = useMemo(
    () =>
      data?.points_distribution.map((b) => ({
        range: `${b.range_min.toFixed(1)}–${b.range_max.toFixed(1)}`,
        count: b.count,
      })) ?? [],
    [data?.points_distribution],
  );

  const workloadData = useMemo(
    () =>
      data?.daily_workload.map((w) => ({
        date: w.date.slice(5), // MM-DD
        demand: w.demand,
        filled: w.filled,
      })) ?? [],
    [data?.daily_workload],
  );

  const renderTooltip = ({ active, payload, label }: Record<string, unknown>) => {
    const items = payload as ReadonlyArray<{ color?: string; name?: string; value?: number }> | undefined;
    if (!active || !items?.length) return null;
    return (
      <div className="rounded-md border border-border bg-popover px-3 py-2 text-sm text-popover-foreground shadow-md">
        <p className="mb-1 font-medium">{String(label)}</p>
        {items.map((entry, i) => (
          <p key={i} className="text-popover-foreground">
            <span className="mr-1.5 inline-block size-2.5 rounded-sm" style={{ backgroundColor: entry.color }} />
            {entry.name}: {entry.value}
          </p>
        ))}
      </div>
    );
  };

  if (isLoading) {
    return <div className="p-6 text-muted-foreground">Loading...</div>;
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Stats</h1>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <Label htmlFor="date_from" className="text-sm text-muted-foreground">From</Label>
            <Input
              id="date_from"
              type="date"
              value={dateFrom}
              onChange={(e) => setParam("date_from", e.target.value)}
              className="w-36"
            />
          </div>
          <div className="flex items-center gap-1.5">
            <Label htmlFor="date_to" className="text-sm text-muted-foreground">To</Label>
            <Input
              id="date_to"
              type="date"
              value={dateTo}
              onChange={(e) => setParam("date_to", e.target.value)}
              className="w-36"
            />
          </div>
        </div>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Points</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.total_points.toLocaleString(undefined, { maximumFractionDigits: 1 })}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Fill Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(data.fill_rate * 100).toFixed(0)}%</div>
            <div className="mt-2 h-2 rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${Math.min(data.fill_rate * 100, 100)}%` }}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Personnel</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.active_personnel} <span className="text-base font-normal text-muted-foreground">/ {data.total_personnel}</span></div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Upcoming Unfilled</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data.upcoming_unfilled} <span className="text-base font-normal text-muted-foreground">{data.upcoming_unfilled === 1 ? "duty" : "duties"}</span></div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Points Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {histogramData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={histogramData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="range" tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }} stroke="var(--color-border)" />
                  <YAxis allowDecimals={false} tick={{ fill: "var(--color-muted-foreground)" }} stroke="var(--color-border)" />
                  <Tooltip content={renderTooltip} cursor={{ fill: "var(--color-accent)", opacity: 0.5 }} />
                  <Bar dataKey="count" fill="var(--color-chart-1)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-[250px] items-center justify-center text-muted-foreground">No data</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Daily Workload</CardTitle>
          </CardHeader>
          <CardContent>
            {workloadData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={workloadData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }} stroke="var(--color-border)" />
                  <YAxis allowDecimals={false} tick={{ fill: "var(--color-muted-foreground)" }} stroke="var(--color-border)" />
                  <Tooltip content={renderTooltip} />
                  <Area type="monotone" dataKey="demand" stroke="var(--color-muted-foreground)" fill="var(--color-muted)" name="Demand" />
                  <Area type="monotone" dataKey="filled" stroke="var(--color-chart-1)" fill="var(--color-chart-1)" fillOpacity={0.3} name="Filled" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-[250px] items-center justify-center text-muted-foreground">No data</div>
            )}
          </CardContent>
        </Card>
      </div>

    </div>
  );
}
