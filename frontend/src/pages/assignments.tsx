import { useCallback, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type ColumnDef,
  type RowSelectionState,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { Icon } from "@/components/ui/icon";
import { toast } from "sonner";

import {
  acceptSolver,
  createAssignment,
  deleteAssignment,
  fetchAssignments,
  fetchDuties,
  fetchPeople,
  runSolver,
} from "@/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Combobox } from "@/components/ui/combobox";
import { DataTable } from "@/components/ui/data-table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TagBadge } from "@/components/tag-badge";
import { PaginationControls } from "@/components/pagination-controls";
import { PersonSheet } from "@/components/person-sheet";
import { DutySheet } from "@/components/duty-sheet";
import { formatDutyDates } from "@/lib/utils";
import type { Assignment, ProposedAssignment, SolverRunResponse, UnfilledDuty } from "@/types";

const PAGE_SIZE = 50;
const SOLVER_PAGE_SIZE = 50;

const ALGO_OPTIONS = [
  { value: "greedy", label: "Greedy" },
  { value: "montecarlo", label: "Monte Carlo" },
  { value: "annealing", label: "Annealing" },
] as const;

const ALGO_DEFAULTS: Record<string, number> = {
  greedy: 1,
  montecarlo: 50,
  annealing: 5000,
};

function SolverControls({
  isPending,
  onRun,
}: {
  isPending: boolean;
  onRun: (algorithm: string, iterations: number) => void;
}) {
  const [algorithm, setAlgorithm] = useState("greedy");
  const [iterations, setIterations] = useState(ALGO_DEFAULTS.greedy);

  const handleAlgoChange = useCallback((value: string) => {
    setAlgorithm(value);
    setIterations(ALGO_DEFAULTS[value]);
  }, []);

  const showIterations = algorithm !== "greedy";

  return (
    <div className="flex items-end gap-2">
      <div className="space-y-1">
        <Label className="text-xs text-muted-foreground">Algorithm</Label>
        <Select value={algorithm} onValueChange={handleAlgoChange}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ALGO_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {showIterations && (
        <div className="space-y-1">
          <Label className="text-xs text-muted-foreground">Iterations</Label>
          <Input
            type="number"
            min={1}
            max={100000}
            value={iterations}
            onChange={(e) => setIterations(Math.max(1, parseInt(e.target.value) || 1))}
            className="w-24"
          />
        </div>
      )}
      <Button
        onClick={() => onRun(algorithm, iterations)}
        disabled={isPending}
        className="relative min-w-[120px] overflow-hidden"
      >
        {isPending ? (
          <span className="text-xs">Solving...</span>
        ) : (
          <>
            <Icon name="play_arrow" className="mr-2" />
            Solve
          </>
        )}
      </Button>
    </div>
  );
}

interface AssignmentTableMeta {
  onDelete: (id: number) => void;
  onOpenPerson: (id: number) => void;
  onOpenDuty: (id: number) => void;
}

interface ProposedTableMeta {
  onOpenPerson: (id: number) => void;
  onOpenDuty: (id: number) => void;
  dutyPoints: Record<number, number>;
}

export function AssignmentsPage() {
  const queryClient = useQueryClient();
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [offset, setOffset] = useState(0);

  // Sheet state
  const [personSheetId, setPersonSheetId] = useState<number | null>(null);
  const [dutySheetId, setDutySheetId] = useState<number | null>(null);

  const filterParams = {
    ...(dateFrom && { date_from: dateFrom }),
    ...(dateTo && { date_to: dateTo }),
    limit: PAGE_SIZE,
    offset,
  };

  const { data, isLoading } = useQuery({
    queryKey: ["assignments", filterParams],
    queryFn: () => fetchAssignments(filterParams),
  });
  const assignments = data?.items ?? [];
  const total = data?.total ?? 0;

  // For combobox pickers: fetch with search
  const [personSearch, setPersonSearch] = useState("");
  const [dutySearch, setDutySearch] = useState("");

  const { data: peopleData } = useQuery({
    queryKey: ["people", { limit: 50, q: personSearch || undefined }],
    queryFn: () => fetchPeople({ limit: 50, q: personSearch || undefined }),
  });

  const { data: dutiesData } = useQuery({
    queryKey: ["duties", { limit: 50, q: dutySearch || undefined }],
    queryFn: () => fetchDuties({ limit: 50, q: dutySearch || undefined }),
  });

  const personOptions = useMemo(
    () => (peopleData?.items ?? []).map((p) => ({ value: String(p.id), label: p.name })),
    [peopleData],
  );

  const dutyOptions = useMemo(
    () => (dutiesData?.items ?? []).map((d) => ({ value: String(d.id), label: `${d.name} (${d.date})` })),
    [dutiesData],
  );

  const [personId, setPersonId] = useState("");
  const [dutyId, setDutyId] = useState("");

  // Solver state
  const [solverResult, setSolverResult] = useState<SolverRunResponse | null>(null);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [forceSelected, setForceSelected] = useState<Set<string>>(new Set());
  const [countSince, setCountSince] = useState("");
  const [expandedUnfilled, setExpandedUnfilled] = useState<Set<number>>(new Set());

  const invalidate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["assignments"] });
  }, [queryClient]);

  const create = useMutation({
    mutationFn: createAssignment,
    onSuccess: () => {
      invalidate();
      setPersonId("");
      setDutyId("");
      toast.success("Assignment created");
    },
    onError: (e) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: deleteAssignment,
    onSuccess: () => {
      invalidate();
      toast.success("Assignment deleted");
    },
    onError: (e) => toast.error(e.message),
  });

  const solver = useMutation({
    mutationFn: (opts: { countSince?: string; algorithm?: string; iterations?: number }) =>
      runSolver({
        countSince: opts.countSince || undefined,
        algorithm: opts.algorithm,
        iterations: opts.iterations,
      }),
    onSuccess: (data) => {
      setSolverResult(data);
      // Select all proposed by default
      const sel: RowSelectionState = {};
      data.proposed.forEach((_, i) => { sel[i] = true; });
      setRowSelection(sel);
      setForceSelected(new Set());
      setExpandedUnfilled(new Set());
      toast.success(`Solver proposed ${data.proposed.length} assignments`);
    },
    onError: (e) => toast.error(e.message),
  });

  const accept = useMutation({
    mutationFn: acceptSolver,
    onSuccess: (data) => {
      invalidate();
      queryClient.invalidateQueries({ queryKey: ["stats"] });
      setSolverResult(null);
      setRowSelection({});
      setForceSelected(new Set());
      toast.success(`Accepted ${data.accepted} assignments`);
    },
    onError: (e) => toast.error(e.message),
  });

  const toggleForceSelected = useCallback((key: string) => {
    setForceSelected((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const toggleExpanded = useCallback((dutyId: number) => {
    setExpandedUnfilled((prev) => {
      const next = new Set(prev);
      if (next.has(dutyId)) next.delete(dutyId);
      else next.add(dutyId);
      return next;
    });
  }, []);

  const handleAccept = () => {
    if (!solverResult) return;
    const selectedRows = proposedTable.getSelectedRowModel().rows;
    const toAccept = [
      ...selectedRows.map((r) => ({
        person_id: r.original.person.id,
        duty_id: r.original.duty.id,
      })),
      ...Array.from(forceSelected).map((key) => {
        const [pid, did] = key.split("_").map(Number);
        return { person_id: pid, duty_id: did };
      }),
    ];
    if (toAccept.length === 0) {
      toast.error("No assignments selected");
      return;
    }
    accept.mutate(toAccept);
  };

  const handleDeleteAssignment = useCallback((id: number) => {
    remove.mutate(id);
  }, [remove]);

  const handleOpenPerson = useCallback((id: number) => setPersonSheetId(id), []);
  const handleOpenDuty = useCallback((id: number) => setDutySheetId(id), []);

  // Assignments list columns (server-paginated, no sort)
  const assignmentColumns = useMemo<ColumnDef<Assignment>[]>(
    () => [
      {
        id: "person",
        header: "Person",
        enableSorting: false,
        cell: ({ row, table: t }) => {
          const meta = t.options.meta as AssignmentTableMeta;
          const a = row.original;
          return (
            <div className="flex items-center gap-2">
              <button
                className="font-medium text-primary hover:underline"
                onClick={() => meta.onOpenPerson(a.person.id)}
              >
                {a.person.name}
              </button>
              {a.person.tags.map((tag) => (
                <TagBadge key={tag.id} tag={tag} interactive />
              ))}
            </div>
          );
        },
      },
      {
        id: "duty",
        header: "Duty",
        enableSorting: false,
        cell: ({ row, table: t }) => {
          const meta = t.options.meta as AssignmentTableMeta;
          const a = row.original;
          return (
            <div className="flex items-center gap-2">
              <button
                className="text-primary hover:underline"
                onClick={() => meta.onOpenDuty(a.duty.id)}
              >
                {a.duty.name}
              </button>
              {a.duty.tags.map((tag) => (
                <TagBadge key={tag.id} tag={tag} interactive />
              ))}
            </div>
          );
        },
      },
      {
        id: "date",
        header: "Date",
        enableSorting: false,
        cell: ({ row }) => formatDutyDates(row.original.duty.date, row.original.duty.duration_days),
      },
      {
        id: "type",
        header: "Type",
        enableSorting: false,
        cell: ({ row }) => (
          <Badge variant={row.original.is_manual ? "secondary" : "default"}>
            {row.original.is_manual ? "Manual" : "Solver"}
          </Badge>
        ),
      },
      {
        id: "actions",
        enableSorting: false,
        meta: { headerClassName: "w-16" },
        cell: ({ row, table: t }) => {
          const meta = t.options.meta as AssignmentTableMeta;
          return (
            <Button variant="ghost" size="icon" onClick={() => meta.onDelete(row.original.id)}>
              <Icon name="delete" className="text-destructive" />
            </Button>
          );
        },
      },
    ],
    [],
  );

  const assignmentTableMeta: AssignmentTableMeta = useMemo(
    () => ({
      onDelete: handleDeleteAssignment,
      onOpenPerson: handleOpenPerson,
      onOpenDuty: handleOpenDuty,
    }),
    [handleDeleteAssignment, handleOpenPerson, handleOpenDuty],
  );

  const assignmentTable = useReactTable({
    data: assignments,
    columns: assignmentColumns,
    getCoreRowModel: getCoreRowModel(),
    meta: assignmentTableMeta,
  });

  // Proposed table columns (client-paginated, sortable points, row selection)
  const proposedColumns = useMemo<ColumnDef<ProposedAssignment>[]>(
    () => [
      {
        id: "select",
        enableSorting: false,
        meta: { headerClassName: "w-10" },
        header: ({ table: t }) => (
          <Checkbox
            checked={t.getIsAllPageRowsSelected()}
            onCheckedChange={(v) => t.toggleAllPageRowsSelected(!!v)}
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(v) => row.toggleSelected(!!v)}
          />
        ),
      },
      {
        id: "person",
        header: "Person",
        enableSorting: false,
        cell: ({ row, table: t }) => {
          const meta = t.options.meta as ProposedTableMeta;
          return (
            <button
              className="font-medium text-primary hover:underline"
              onClick={() => meta.onOpenPerson(row.original.person.id)}
            >
              {row.original.person.name}
            </button>
          );
        },
      },
      {
        id: "duty",
        header: "Duty",
        enableSorting: false,
        cell: ({ row, table: t }) => {
          const meta = t.options.meta as ProposedTableMeta;
          return (
            <button
              className="text-primary hover:underline"
              onClick={() => meta.onOpenDuty(row.original.duty.id)}
            >
              {row.original.duty.name}
            </button>
          );
        },
      },
      {
        id: "date",
        header: "Date",
        enableSorting: false,
        cell: ({ row }) => formatDutyDates(row.original.duty.date, row.original.duty.duration_days),
      },
      {
        id: "points",
        header: "Points",
        enableSorting: true,
        meta: { headerClassName: "text-right" },
        accessorFn: (row) => (solverResult?.duty_points[row.person.id] ?? 0),
        cell: ({ row, table: t }) => {
          const meta = t.options.meta as ProposedTableMeta;
          return (
            <div className="text-right tabular-nums">
              {meta.dutyPoints[row.original.person.id] ?? 0}
            </div>
          );
        },
      },
    ],
    [solverResult],
  );

  const proposedTableMeta: ProposedTableMeta = useMemo(
    () => ({
      onOpenPerson: handleOpenPerson,
      onOpenDuty: handleOpenDuty,
      dutyPoints: solverResult?.duty_points ?? {},
    }),
    [handleOpenPerson, handleOpenDuty, solverResult],
  );

  const proposedData = solverResult?.proposed ?? [];

  const proposedTable = useReactTable({
    data: proposedData,
    columns: proposedColumns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onRowSelectionChange: setRowSelection,
    state: { rowSelection },
    enableRowSelection: true,
    initialState: { pagination: { pageSize: SOLVER_PAGE_SIZE } },
    meta: proposedTableMeta,
  });

  const selectedCount = Object.keys(rowSelection).filter((k) => rowSelection[k]).length + forceSelected.size;
  const totalSelectable = proposedData.length + forceSelected.size;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Assignments</h1>
        <div className="flex items-center gap-3">
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Count since</Label>
            <Input
              type="date"
              value={countSince}
              onChange={(e) => setCountSince(e.target.value)}
              className="w-40"
            />
          </div>
          <SolverControls
            isPending={solver.isPending}
            onRun={(algorithm, iterations) =>
              solver.mutate({ countSince, algorithm, iterations })
            }
          />
        </div>
      </div>

      <Tabs defaultValue="list">
        <TabsList>
          <TabsTrigger value="list">Assignments</TabsTrigger>
          {solverResult && <TabsTrigger value="solver">Solver Results ({solverResult.proposed.length})</TabsTrigger>}
        </TabsList>

        <TabsContent value="list" className="space-y-4">
          <div className="flex items-end gap-3">
            <div className="space-y-1.5">
              <Label>From</Label>
              <Input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setOffset(0); }} />
            </div>
            <div className="space-y-1.5">
              <Label>To</Label>
              <Input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setOffset(0); }} />
            </div>
            {(dateFrom || dateTo) && (
              <Button variant="ghost" size="sm" onClick={() => { setDateFrom(""); setDateTo(""); setOffset(0); }}>
                Clear
              </Button>
            )}
          </div>

          <form
            className="flex items-end gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (!personId || !dutyId) return;
              create.mutate({ person_id: Number(personId), duty_id: Number(dutyId) });
            }}
          >
            <div className="space-y-1.5">
              <Label>Person</Label>
              <Combobox
                options={personOptions}
                value={personId}
                onValueChange={setPersonId}
                placeholder="Select person"
                searchPlaceholder="Search people..."
                onSearchChange={setPersonSearch}
                className="w-48"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Duty</Label>
              <Combobox
                options={dutyOptions}
                value={dutyId}
                onValueChange={setDutyId}
                placeholder="Select duty"
                searchPlaceholder="Search duties..."
                onSearchChange={setDutySearch}
                className="w-48"
              />
            </div>
            <Button type="submit" disabled={create.isPending}>
              Assign
            </Button>
          </form>

          {isLoading ? (
            <p className="text-muted-foreground">Loading...</p>
          ) : assignments.length === 0 ? (
            <p className="text-muted-foreground">No assignments found.</p>
          ) : (
            <>
              <DataTable table={assignmentTable} />
              <PaginationControls offset={offset} limit={PAGE_SIZE} total={total} onOffsetChange={setOffset} />
            </>
          )}
        </TabsContent>

        {solverResult && (
          <TabsContent value="solver" className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                {selectedCount} of {totalSelectable} selected
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSolverResult(null);
                    setRowSelection({});
                    setForceSelected(new Set());
                  }}
                >
                  Discard
                </Button>
                <Button size="sm" onClick={handleAccept} disabled={accept.isPending}>
                  Accept Selected
                </Button>
              </div>
            </div>

            {solverResult.proposed.length > 0 && (
              <>
                <DataTable table={proposedTable} />
                <PaginationControls
                  offset={proposedTable.getState().pagination.pageIndex * SOLVER_PAGE_SIZE}
                  limit={SOLVER_PAGE_SIZE}
                  total={proposedData.length}
                  onOffsetChange={(newOffset) => proposedTable.setPageIndex(Math.floor(newOffset / SOLVER_PAGE_SIZE))}
                />
              </>
            )}

            {solverResult.unfilled.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-base font-semibold">Unfilled Duties</h3>
                {solverResult.unfilled.map((uf: UnfilledDuty) => (
                  <UnfilledDutyCard
                    key={uf.duty.id}
                    unfilled={uf}
                    expanded={expandedUnfilled.has(uf.duty.id)}
                    onToggle={() => toggleExpanded(uf.duty.id)}
                    forceSelected={forceSelected}
                    onToggleForce={toggleForceSelected}
                    dutyPoints={solverResult.duty_points}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        )}
      </Tabs>

      <PersonSheet
        personId={personSheetId}
        onClose={() => setPersonSheetId(null)}
      />
      <DutySheet
        dutyId={dutySheetId}
        onClose={() => setDutySheetId(null)}
      />
    </div>
  );
}

function UnfilledDutyCard({
  unfilled,
  expanded,
  onToggle,
  forceSelected,
  onToggleForce,
  dutyPoints,
}: {
  unfilled: UnfilledDuty;
  expanded: boolean;
  onToggle: () => void;
  forceSelected: Set<string>;
  onToggleForce: (key: string) => void;
  dutyPoints: Record<number, number>;
}) {
  return (
    <Card>
      <CardHeader className="cursor-pointer py-3" onClick={onToggle}>
        <div className="flex items-center gap-2">
          {expanded ? <Icon name="expand_more" /> : <Icon name="chevron_right" />}
          <CardTitle className="text-sm font-medium">
            {unfilled.duty.name}
          </CardTitle>
          <span className="text-xs text-muted-foreground">
            {formatDutyDates(unfilled.duty.date, unfilled.duty.duration_days)}
          </span>
          <Badge variant="outline" className="ml-auto">
            {unfilled.slots_needed} slot{unfilled.slots_needed !== 1 ? "s" : ""} needed
          </Badge>
        </div>
      </CardHeader>
      {expanded && unfilled.excluded_people.length > 0 && (
        <CardContent className="pt-0">
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">Force</TableHead>
                  <TableHead>Person</TableHead>
                  <TableHead className="text-right">Points</TableHead>
                  <TableHead>Exclusion Reasons</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {unfilled.excluded_people.map((ep) => {
                  const key = `${ep.person.id}_${unfilled.duty.id}`;
                  const pts = dutyPoints[ep.person.id] ?? 0;
                  return (
                    <TableRow key={ep.person.id}>
                      <TableCell>
                        <Checkbox
                          checked={forceSelected.has(key)}
                          onCheckedChange={() => onToggleForce(key)}
                        />
                      </TableCell>
                      <TableCell className="font-medium">{ep.person.name}</TableCell>
                      <TableCell className="text-right tabular-nums">{pts}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {ep.reasons.map((r, i) => (
                            <Badge key={i} variant={r.rule_type === "deny" ? "destructive" : r.rule_type === "cooldown" ? "secondary" : "default"}>
                              {r.reason}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      )}
      {expanded && unfilled.excluded_people.length === 0 && (
        <CardContent className="pt-0">
          <p className="text-sm text-muted-foreground">No eligible people available</p>
        </CardContent>
      )}
    </Card>
  );
}
