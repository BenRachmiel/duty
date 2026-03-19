import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { type ColumnDef, getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { fetchAssignments, fetchPerson } from "@/api";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { TagBadge } from "@/components/tag-badge";
import { PaginationControls } from "@/components/pagination-controls";
import { formatDutyDates } from "@/lib/utils";
import type { Assignment } from "@/types";

const PAGE_SIZE = 20;

const columns: ColumnDef<Assignment>[] = [
  {
    id: "duty",
    header: "Duty",
    enableSorting: false,
    cell: ({ row }) => <span className="font-medium">{row.original.duty.name}</span>,
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
    enableSorting: false,
    meta: { headerClassName: "text-right" },
    cell: ({ row }) => (
      <div className="text-right tabular-nums">
        {row.original.duty.duration_days * row.original.duty.difficulty}
      </div>
    ),
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
];

export function PersonSheet({
  personId,
  onClose,
  countSince,
}: {
  personId: number | null;
  onClose: () => void;
  countSince?: string;
}) {
  const [sheetCountSince, setSheetCountSince] = useState(countSince ?? "");
  const [offset, setOffset] = useState(0);

  const { data: person } = useQuery({
    queryKey: ["person", personId, sheetCountSince],
    queryFn: () => fetchPerson(personId!, sheetCountSince || undefined),
    enabled: personId != null,
  });

  const { data: assignments } = useQuery({
    queryKey: ["assignments", { person_id: personId, limit: PAGE_SIZE, offset }],
    queryFn: () =>
      fetchAssignments({ person_id: personId!, limit: PAGE_SIZE, offset }),
    enabled: personId != null,
  });

  const tableData = assignments?.items ?? [];

  const table = useReactTable({
    data: tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <Sheet open={personId != null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="sm:max-w-lg overflow-y-auto">
        {person && (
          <>
            <SheetHeader>
              <SheetTitle>{person.name}</SheetTitle>
              <SheetDescription>
                {person.external_id ?? "No external ID"}
              </SheetDescription>
            </SheetHeader>

            <div className="px-4 space-y-4">
              <div className="flex flex-wrap gap-1.5">
                {person.tags.map((tag) => (
                  <TagBadge key={tag.id} tag={tag} />
                ))}
                {person.tags.length === 0 && (
                  <span className="text-sm text-muted-foreground">No tags</span>
                )}
              </div>

              <div className="flex items-center gap-3">
                <div className="space-y-1">
                  <Label className="text-xs text-muted-foreground">
                    Points since
                  </Label>
                  <Input
                    type="date"
                    value={sheetCountSince}
                    onChange={(e) => setSheetCountSince(e.target.value)}
                    className="w-40 h-8"
                  />
                </div>
                <div className="pt-5">
                  <Badge variant="secondary" className="text-base tabular-nums">
                    {person.points} pts
                  </Badge>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold mb-2">
                  Assignment History
                </h3>
                {assignments && assignments.items.length > 0 ? (
                  <>
                    <DataTable table={table} emptyMessage="No assignments" />
                    <PaginationControls
                      offset={offset}
                      limit={PAGE_SIZE}
                      total={assignments.total}
                      onOffsetChange={setOffset}
                    />
                  </>
                ) : assignments ? (
                  <p className="text-sm text-muted-foreground">
                    No assignments
                  </p>
                ) : null}
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
