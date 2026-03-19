import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type ColumnDef,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { Icon } from "@/components/ui/icon";
import { toast } from "sonner";

import { createTag, deleteTag, fetchTags } from "@/api";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TagBadge } from "@/components/tag-badge";
import type { Tag } from "@/types";

export function TagsPage() {
  const queryClient = useQueryClient();
  const { data: tags = [], isLoading } = useQuery({
    queryKey: ["tags"],
    queryFn: fetchTags,
  });

  const [name, setName] = useState("");

  const create = useMutation({
    mutationFn: createTag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      setName("");
      toast.success("Tag created");
    },
    onError: (e) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: deleteTag,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tags"] });
      toast.success("Tag deleted");
    },
    onError: (e) => toast.error(e.message),
  });

  const columns = useMemo<ColumnDef<Tag>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        enableSorting: true,
      },
      {
        id: "preview",
        header: "Preview",
        enableSorting: false,
        cell: ({ row }) => <TagBadge tag={row.original} />,
      },
      {
        id: "actions",
        enableSorting: false,
        meta: { headerClassName: "w-16" },
        cell: ({ row }) => (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => remove.mutate(row.original.id)}
            disabled={remove.isPending}
          >
            <Icon name="delete" className="text-destructive" />
          </Button>
        ),
      },
    ],
    [remove],
  );

  const table = useReactTable({
    data: tags,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Tags</h1>

      <form
        className="flex items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim()) return;
          create.mutate({ name: name.trim() });
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="tag-name">Name</Label>
          <Input
            id="tag-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. rank:sergeant"
          />
        </div>
        <Button type="submit" disabled={create.isPending}>
          Add Tag
        </Button>
      </form>

      {isLoading ? (
        <p className="text-muted-foreground">Loading...</p>
      ) : tags.length === 0 ? (
        <p className="text-muted-foreground">No tags yet.</p>
      ) : (
        <DataTable table={table} />
      )}
    </div>
  );
}
