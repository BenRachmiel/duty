import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { type ColumnDef, getCoreRowModel, useReactTable } from "@tanstack/react-table";

import { fetchAssignments, fetchDuty } from "@/api";
import { Badge } from "@/components/ui/badge";
import { DataTable } from "@/components/ui/data-table";
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
    id: "person",
    header: "Person",
    enableSorting: false,
    cell: ({ row }) => <span className="font-medium">{row.original.person.name}</span>,
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

export function DutySheet({
  dutyId,
  onClose,
}: {
  dutyId: number | null;
  onClose: () => void;
}) {
  const [offset, setOffset] = useState(0);

  const { data: duty } = useQuery({
    queryKey: ["duty", dutyId],
    queryFn: () => fetchDuty(dutyId!),
    enabled: dutyId != null,
  });

  const { data: assignments } = useQuery({
    queryKey: ["assignments", { duty_id: dutyId, limit: PAGE_SIZE, offset }],
    queryFn: () =>
      fetchAssignments({ duty_id: dutyId!, limit: PAGE_SIZE, offset }),
    enabled: dutyId != null,
  });

  const tableData = assignments?.items ?? [];

  const table = useReactTable({
    data: tableData,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  return (
    <Sheet open={dutyId != null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent className="sm:max-w-lg overflow-y-auto">
        {duty && (
          <>
            <SheetHeader>
              <SheetTitle>{duty.name}</SheetTitle>
              <SheetDescription>{formatDutyDates(duty.date, duty.duration_days)}</SheetDescription>
            </SheetHeader>

            <div className="px-4 space-y-4">
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div>
                  <span className="text-muted-foreground">Headcount</span>
                  <p className="font-medium">{duty.headcount}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Duration</span>
                  <p className="font-medium">
                    {duty.duration_days} day{duty.duration_days !== 1 ? "s" : ""}
                  </p>
                </div>
                <div>
                  <span className="text-muted-foreground">Difficulty</span>
                  <p className="font-medium">{duty.difficulty}x</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="tabular-nums">
                  {duty.duration_days * duty.difficulty} pts
                </Badge>
                <Badge
                  variant={
                    duty.assignment_count >= duty.headcount
                      ? "default"
                      : "destructive"
                  }
                >
                  {duty.assignment_count}/{duty.headcount} filled
                </Badge>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {duty.tags.map((tag) => (
                  <TagBadge key={tag.id} tag={tag} />
                ))}
                {duty.tags.length === 0 && (
                  <span className="text-sm text-muted-foreground">No tags</span>
                )}
              </div>

              <div>
                <h3 className="text-sm font-semibold mb-2">Assigned People</h3>
                {assignments && assignments.items.length > 0 ? (
                  <>
                    <DataTable table={table} emptyMessage="No assignments yet" />
                    <PaginationControls
                      offset={offset}
                      limit={PAGE_SIZE}
                      total={assignments.total}
                      onOffsetChange={setOffset}
                    />
                  </>
                ) : assignments ? (
                  <p className="text-sm text-muted-foreground">
                    No assignments yet
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
