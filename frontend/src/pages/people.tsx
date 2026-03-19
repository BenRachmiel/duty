import { useCallback, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type ColumnDef, getCoreRowModel, useReactTable } from "@tanstack/react-table";
import { Icon } from "@/components/ui/icon";
import { useSearchParams } from "react-router";
import { toast } from "sonner";

import {
  addPersonTag,
  createPerson,
  deletePerson,
  fetchPeople,
  fetchTags,
  importPeopleCsv,
  removePersonTag,
} from "@/api";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TagBadge } from "@/components/tag-badge";
import { TagManager } from "@/components/tag-manager";
import { TagPicker } from "@/components/tag-picker";
import { PaginationControls } from "@/components/pagination-controls";
import { PersonSheet } from "@/components/person-sheet";
import type { PersonListItem, Tag } from "@/types";

const PAGE_SIZE = 50;

interface PersonTableMeta {
  allTags: Tag[];
  onAddTag: (personId: number, tag: Tag) => void;
  onRemoveTag: (personId: number, tagId: number) => void;
  onDelete: (id: number) => void;
  onOpenDetail: (id: number) => void;
  sortBy: string;
  onSortPoints: () => void;
}

export function PeoplePage() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [offset, setOffset] = useState(0);
  const [name, setName] = useState("");
  const [externalId, setExternalId] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const tagId = searchParams.get("tag_id") ? Number(searchParams.get("tag_id")) : undefined;
  const countSince = searchParams.get("count_since") ?? "";
  const detailId = searchParams.get("detail") ? Number(searchParams.get("detail")) : null;
  const sortBy = searchParams.get("sort_by") ?? "";

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

  const pageParams = {
    limit: PAGE_SIZE,
    offset,
    ...(tagId != null && { tag_id: tagId }),
    ...(countSince && { count_since: countSince }),
    ...(sortBy && { sort_by: sortBy }),
  };

  const { data, isLoading } = useQuery({
    queryKey: ["people", pageParams],
    queryFn: () => fetchPeople(pageParams),
  });
  const people = data?.items ?? [];
  const total = data?.total ?? 0;

  const { data: allTags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: fetchTags,
  });

  const activeTag = tagId != null ? allTags.find((t) => t.id === tagId) : undefined;

  const invalidatePage = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["people", pageParams] });
  }, [queryClient, pageParams]);

  const invalidateAll = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["people"] });
  }, [queryClient]);

  const create = useMutation({
    mutationFn: createPerson,
    onSuccess: () => {
      invalidateAll();
      setName("");
      setExternalId("");
      toast.success("Person created");
    },
    onError: (e) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: deletePerson,
    onSuccess: () => {
      invalidateAll();
      toast.success("Person deleted");
    },
    onError: (e) => toast.error(e.message),
  });

  const addTag = useMutation({
    mutationFn: ({ personId, tag }: { personId: number; tag: Tag }) =>
      addPersonTag(personId, tag),
    onSuccess: () => invalidatePage(),
    onError: (e) => toast.error(e.message),
  });

  const removeTag = useMutation({
    mutationFn: ({ personId, tagId }: { personId: number; tagId: number }) =>
      removePersonTag(personId, tagId),
    onSuccess: () => invalidatePage(),
    onError: (e) => toast.error(e.message),
  });

  const csvImport = useMutation({
    mutationFn: importPeopleCsv,
    onSuccess: (data) => {
      invalidateAll();
      toast.success(`Imported ${data.length} people`);
    },
    onError: (e) => toast.error(e.message),
  });

  const handleAddTag = useCallback((personId: number, tag: Tag) => {
    addTag.mutate({ personId, tag });
  }, [addTag]);

  const handleRemoveTag = useCallback((personId: number, tagId: number) => {
    removeTag.mutate({ personId, tagId });
  }, [removeTag]);

  const handleDelete = useCallback((id: number) => {
    remove.mutate(id);
  }, [remove]);

  const handleOpenDetail = useCallback(
    (id: number) => setParam("detail", String(id)),
    [setParam],
  );

  const columns = useMemo<ColumnDef<PersonListItem>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        enableSorting: false,
        cell: ({ row, table: t }) => {
          const meta = t.options.meta as PersonTableMeta;
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
        accessorKey: "external_id",
        header: "External ID",
        enableSorting: false,
        cell: ({ row }) => (
          <span className="text-muted-foreground">{row.original.external_id ?? "—"}</span>
        ),
      },
      {
        id: "tags",
        header: "Tags",
        enableSorting: false,
        cell: ({ row, table: t }) => {
          const meta = t.options.meta as PersonTableMeta;
          const person = row.original;
          const assignedTagIds = new Set(person.tags.map((tag) => tag.id));
          const availableTags = meta.allTags.filter((tag) => !assignedTagIds.has(tag.id));
          return (
            <div className="flex flex-wrap items-center gap-1.5">
              {person.tags.map((tag) => (
                <button
                  key={tag.id}
                  className="group inline-flex items-center gap-0.5"
                  onClick={() => meta.onRemoveTag(person.id, tag.id)}
                >
                  <TagBadge tag={tag} interactive />
                  <Icon name="close" className="text-[0.75rem] opacity-0 transition-opacity group-hover:opacity-100 text-muted-foreground" />
                </button>
              ))}
              <TagPicker tags={availableTags} onSelect={(tag) => meta.onAddTag(person.id, tag)} />
            </div>
          );
        },
      },
      {
        accessorKey: "points",
        header: ({ table: t }) => {
          const meta = t.options.meta as PersonTableMeta;
          const sorted = meta.sortBy === "points_asc" ? "asc" : meta.sortBy === "points_desc" ? "desc" : null;
          return (
            <button
              className="flex items-center gap-1 text-right w-full justify-end"
              onClick={meta.onSortPoints}
            >
              Points
              {sorted === "asc" ? (
                <Icon name="arrow_upward" className="text-[0.875rem]" />
              ) : sorted === "desc" ? (
                <Icon name="arrow_downward" className="text-[0.875rem]" />
              ) : (
                <Icon name="swap_vert" className="text-[0.875rem] text-muted-foreground/50" />
              )}
            </button>
          );
        },
        enableSorting: false,
        meta: { headerClassName: "text-right" },
        cell: ({ row }) => (
          <div className="text-right tabular-nums">{row.original.points}</div>
        ),
      },
      {
        id: "actions",
        enableSorting: false,
        meta: { headerClassName: "w-16" },
        cell: ({ row, table: t }) => {
          const meta = t.options.meta as PersonTableMeta;
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

  const handleSortPoints = useCallback(() => {
    const next = sortBy === "points_desc" ? "points_asc" : sortBy === "points_asc" ? null : "points_desc";
    setParam("sort_by", next);
    setOffset(0);
  }, [sortBy, setParam]);

  const tableMeta: PersonTableMeta = useMemo(
    () => ({
      allTags,
      onAddTag: handleAddTag,
      onRemoveTag: handleRemoveTag,
      onDelete: handleDelete,
      onOpenDetail: handleOpenDetail,
      sortBy,
      onSortPoints: handleSortPoints,
    }),
    [allTags, handleAddTag, handleRemoveTag, handleDelete, handleOpenDetail, sortBy, handleSortPoints],
  );

  const table = useReactTable({
    data: people,
    columns,
    getCoreRowModel: getCoreRowModel(),
    meta: tableMeta,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">People</h1>
        <div className="flex items-center gap-3">
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Points since</Label>
            <Input
              type="date"
              value={countSince}
              onChange={(e) => {
                setParam("count_since", e.target.value || null);
                setOffset(0);
              }}
              className="w-40"
            />
          </div>
          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm" className="self-end">
                <Icon name="upload" className="mr-2" />
                Import CSV
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Import People from CSV</DialogTitle>
              </DialogHeader>
              <p className="text-sm text-muted-foreground">
                CSV should have columns: <code>name</code>, <code>external_id</code> (optional), <code>tags</code> (comma-separated, optional).
              </p>
              <input
                ref={fileRef}
                type="file"
                accept=".csv"
                className="text-sm"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) csvImport.mutate(file);
                }}
              />
            </DialogContent>
          </Dialog>
        </div>
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
          if (!name.trim()) return;
          create.mutate({ name: name.trim(), external_id: externalId.trim() || null });
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="person-name">Name</Label>
          <Input id="person-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="person-ext">External ID</Label>
          <Input id="person-ext" value={externalId} onChange={(e) => setExternalId(e.target.value)} placeholder="Optional" />
        </div>
        <Button type="submit" disabled={create.isPending}>
          Add Person
        </Button>
      </form>

      {isLoading ? (
        <p className="text-muted-foreground">Loading...</p>
      ) : people.length === 0 ? (
        <p className="text-muted-foreground">No people yet.</p>
      ) : (
        <>
          <DataTable table={table} />
          <PaginationControls offset={offset} limit={PAGE_SIZE} total={total} onOffsetChange={setOffset} />
        </>
      )}

      <PersonSheet
        personId={detailId}
        onClose={() => setParam("detail", null)}
        countSince={countSince}
      />

      <TagManager />
    </div>
  );
}
