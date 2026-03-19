import { useCallback, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ColumnDef, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Icon } from "@/components/ui/icon";
import { useSearchParams } from "react-router";
import { toast } from "sonner";

import {
  addDutyTag,
  createDuty,
  deleteDuty,
  fetchDuties,
  fetchTags,
  removeDutyTag,
} from "@/api";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TagBadge } from "@/components/tag-badge";
import { TagManager } from "@/components/tag-manager";
import { TagPicker } from "@/components/tag-picker";
import { PaginationControls } from "@/components/pagination-controls";
import { DutySheet } from "@/components/duty-sheet";
import { formatDutyDates } from "@/lib/utils";
import type { Duty, Tag } from "@/types";

const PAGE_SIZE = 50;

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T00:00:00");
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

interface DutyTableMeta {
  allTags: Tag[];
  onAddTag: (dutyId: number, tag: Tag) => void;
  onRemoveTag: (dutyId: number, tagId: number) => void;
  onDelete: (id: number) => void;
  onOpenDetail: (id: number) => void;
}

export function DutiesPage() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [offset, setOffset] = useState(0);

  const tagId = searchParams.get("tag_id") ? Number(searchParams.get("tag_id")) : undefined;
  const dateFrom = searchParams.get("date_from") ?? "";
  const dateTo = searchParams.get("date_to") ?? "";
  const detailId = searchParams.get("detail") ? Number(searchParams.get("detail")) : null;

  const setParam = useCallback(
    (key: string, value: string | null) => {
      setSearchParams((prev: URLSearchParams) => {
        const next = new URLSearchParams(prev);
        if (value) next.set(key, value);
        else next.delete(key);
        return next;
      });
    },
    [setSearchParams],
  );

  const filterParams = {
    ...(dateFrom && { date_from: dateFrom }),
    ...(dateTo && { date_to: dateTo }),
    ...(tagId != null && { tag_id: tagId }),
    limit: PAGE_SIZE,
    offset,
  };

  const { data, isLoading } = useQuery({
    queryKey: ["duties", filterParams],
    queryFn: () => fetchDuties(filterParams),
  });
  const duties = data?.items ?? [];
  const total = data?.total ?? 0;

  const { data: allTags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: fetchTags,
  });

  const activeTag = tagId != null ? allTags.find((t) => t.id === tagId) : undefined;

  const [name, setName] = useState("");
  const [date, setDate] = useState("");
  const [headcount, setHeadcount] = useState("1");
  const [durationDays, setDurationDays] = useState("1");
  const [difficulty, setDifficulty] = useState("1");

  const invalidatePage = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["duties", filterParams] });
  }, [queryClient, filterParams]);

  const invalidateAll = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["duties"] });
  }, [queryClient]);

  const create = useMutation({
    mutationFn: createDuty,
    onSuccess: () => {
      invalidateAll();
      setName("");
      setDate("");
      setHeadcount("1");
      setDurationDays("1");
      setDifficulty("1");
      toast.success("Duty created");
    },
    onError: (e) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: deleteDuty,
    onSuccess: () => {
      invalidateAll();
      toast.success("Duty deleted");
    },
    onError: (e) => toast.error(e.message),
  });

  const addTag = useMutation({
    mutationFn: ({ dutyId, tag }: { dutyId: number; tag: Tag }) =>
      addDutyTag(dutyId, tag),
    onSuccess: () => invalidatePage(),
    onError: (e) => toast.error(e.message),
  });

  const removeTag = useMutation({
    mutationFn: ({ dutyId, tagId }: { dutyId: number; tagId: number }) =>
      removeDutyTag(dutyId, tagId),
    onSuccess: () => invalidatePage(),
    onError: (e) => toast.error(e.message),
  });

  const handleAddTag = useCallback((dutyId: number, tag: Tag) => {
    addTag.mutate({ dutyId, tag });
  }, [addTag]);

  const handleRemoveTag = useCallback((dutyId: number, tagId: number) => {
    removeTag.mutate({ dutyId, tagId });
  }, [removeTag]);

  const handleDelete = useCallback((id: number) => {
    remove.mutate(id);
  }, [remove]);

  const handleOpenDetail = useCallback(
    (id: number) => setParam("detail", String(id)),
    [setParam],
  );

  const columns = useMemo<ColumnDef<Duty>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        enableSorting: false,
        cell: ({ row, table: t }) => {
          const meta = t.options.meta as DutyTableMeta;
          return (
            <button
              className="font-medium text-primary hover:underline text-left"
              onClick={() => meta.onOpenDetail(row.original.id)}
            >
              {row.original.name}
            </button>
          );
        },
      },
      {
        id: "date",
        header: "Date",
        enableSorting: false,
        cell: ({ row }) => formatDutyDates(row.original.date, row.original.duration_days),
      },
      {
        accessorKey: "headcount",
        header: "Headcount",
        enableSorting: false,
      },
      {
        id: "tags",
        header: "Tags",
        enableSorting: false,
        cell: ({ row, table: t }) => {
          const meta = t.options.meta as DutyTableMeta;
          const duty = row.original;
          const assignedTagIds = new Set(duty.tags.map((tag) => tag.id));
          const availableTags = meta.allTags.filter((tag) => !assignedTagIds.has(tag.id));
          return (
            <div className="flex flex-wrap items-center gap-1.5">
              {duty.tags.map((tag) => (
                <button
                  key={tag.id}
                  className="group inline-flex items-center gap-0.5"
                  onClick={() => meta.onRemoveTag(duty.id, tag.id)}
                >
                  <TagBadge tag={tag} interactive />
                  <Icon name="close" className="text-[0.75rem] opacity-0 transition-opacity group-hover:opacity-100 text-muted-foreground" />
                </button>
              ))}
              <TagPicker tags={availableTags} onSelect={(tag) => meta.onAddTag(duty.id, tag)} />
            </div>
          );
        },
      },
      {
        id: "actions",
        enableSorting: false,
        meta: { headerClassName: "w-16" },
        cell: ({ row, table: t }) => {
          const meta = t.options.meta as DutyTableMeta;
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

  const tableMeta: DutyTableMeta = useMemo(
    () => ({
      allTags,
      onAddTag: handleAddTag,
      onRemoveTag: handleRemoveTag,
      onDelete: handleDelete,
      onOpenDetail: handleOpenDetail,
    }),
    [allTags, handleAddTag, handleRemoveTag, handleDelete, handleOpenDetail],
  );

  const table = useReactTable({
    data: duties,
    columns,
    getCoreRowModel: getCoreRowModel(),
    meta: tableMeta,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Duties</h1>

      <div className="flex items-end gap-3">
        <div className="space-y-1.5">
          <Label>From</Label>
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setParam("date_from", e.target.value || null);
              setOffset(0);
            }}
          />
        </div>
        <div className="space-y-1.5">
          <Label>To</Label>
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => {
              setParam("date_to", e.target.value || null);
              setOffset(0);
            }}
          />
        </div>
        {(dateFrom || dateTo) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setParam("date_from", null);
              setParam("date_to", null);
              setOffset(0);
            }}
          >
            Clear
          </Button>
        )}
      </div>

      {activeTag && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Filtered by tag:</span>
          <TagBadge tag={activeTag} />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setParam("tag_id", null);
              setOffset(0);
            }}
          >
            Clear
          </Button>
        </div>
      )}

      <form
        className="flex items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim() || !date) return;
          create.mutate({
            name: name.trim(),
            date,
            headcount: Number(headcount) || 1,
            duration_days: Number(durationDays) || 1,
            difficulty: Number(difficulty) || 1,
          });
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="duty-name">Name</Label>
          <Input id="duty-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Night Watch" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="duty-date">Date</Label>
          <Input id="duty-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="duty-hc">Headcount</Label>
          <Input
            id="duty-hc"
            type="number"
            min={1}
            value={headcount}
            onChange={(e) => setHeadcount(e.target.value)}
            className="w-20"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="duty-dur">Days</Label>
          <Input
            id="duty-dur"
            type="number"
            min={1}
            value={durationDays}
            onChange={(e) => setDurationDays(e.target.value)}
            className="w-20"
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="duty-diff">Difficulty</Label>
          <Input
            id="duty-diff"
            type="number"
            min={0.1}
            step={0.1}
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
            className="w-20"
          />
        </div>
        {date && Number(durationDays) > 1 && (
          <span className="self-center text-xs text-muted-foreground">
            ends {addDays(date, Number(durationDays) || 1)}
          </span>
        )}
        <Button type="submit" disabled={create.isPending}>
          Add Duty
        </Button>
      </form>

      {isLoading ? (
        <p className="text-muted-foreground">Loading...</p>
      ) : duties.length === 0 ? (
        <p className="text-muted-foreground">No duties found.</p>
      ) : (
        <>
          <DataTable table={table} />
          <PaginationControls offset={offset} limit={PAGE_SIZE} total={total} onOffsetChange={setOffset} />
        </>
      )}

      <DutySheet
        dutyId={detailId}
        onClose={() => setParam("detail", null)}
      />

      <TagManager />
    </div>
  );
}
