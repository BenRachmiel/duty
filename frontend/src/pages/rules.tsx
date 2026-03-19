import { useCallback, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  type ColumnDef,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { Icon } from "@/components/ui/icon";
import { toast } from "sonner";

import { createRule, deleteRule, fetchRules, fetchTags } from "@/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import { TagBadge } from "@/components/tag-badge";
import type { Rule, RuleType } from "@/types";

const RULE_TYPES: { value: RuleType; label: string }[] = [
  { value: "allow", label: "Allow" },
  { value: "deny", label: "Deny" },
  { value: "cooldown", label: "Cooldown" },
];

const NONE = "";

export function RulesPage() {
  const queryClient = useQueryClient();
  const { data: rules = [], isLoading } = useQuery({
    queryKey: ["rules"],
    queryFn: () => fetchRules(),
  });
  const { data: allTags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: fetchTags,
  });

  const [name, setName] = useState("");
  const [ruleType, setRuleType] = useState<RuleType>("deny");
  const [personTagId, setPersonTagId] = useState(NONE);
  const [dutyTagId, setDutyTagId] = useState(NONE);
  const [priority, setPriority] = useState("0");
  const [cooldownDays, setCooldownDays] = useState("");
  const [cooldownDutyTagId, setCooldownDutyTagId] = useState(NONE);

  const tagOptions = [
    { value: NONE, label: "Any" },
    ...allTags.map((t) => ({ value: String(t.id), label: t.name })),
  ];

  const invalidate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["rules"] });
  }, [queryClient]);

  const create = useMutation({
    mutationFn: createRule,
    onSuccess: () => {
      invalidate();
      setName("");
      setRuleType("deny");
      setPersonTagId(NONE);
      setDutyTagId(NONE);
      setPriority("0");
      setCooldownDays("");
      setCooldownDutyTagId(NONE);
      toast.success("Rule created");
    },
    onError: (e) => toast.error(e.message),
  });

  const remove = useMutation({
    mutationFn: deleteRule,
    onSuccess: () => {
      invalidate();
      toast.success("Rule deleted");
    },
    onError: (e) => toast.error(e.message),
  });

  const toNullableInt = (v: string) => (v === NONE ? null : Number(v));

  const columns = useMemo<ColumnDef<Rule>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Name",
        enableSorting: true,
        cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
      },
      {
        accessorKey: "rule_type",
        header: "Type",
        enableSorting: true,
        cell: ({ row }) => (
          <Badge
            variant={
              row.original.rule_type === "allow"
                ? "default"
                : row.original.rule_type === "deny"
                  ? "destructive"
                  : "secondary"
            }
          >
            {row.original.rule_type}
          </Badge>
        ),
      },
      {
        id: "person_tag",
        header: "Person Tag",
        enableSorting: false,
        cell: ({ row }) =>
          row.original.person_tag ? (
            <TagBadge tag={row.original.person_tag} />
          ) : (
            <span className="text-muted-foreground">Any</span>
          ),
      },
      {
        id: "duty_tag",
        header: "Duty Tag",
        enableSorting: false,
        cell: ({ row }) =>
          row.original.duty_tag ? (
            <TagBadge tag={row.original.duty_tag} />
          ) : (
            <span className="text-muted-foreground">Any</span>
          ),
      },
      {
        id: "cooldown",
        header: "Cooldown",
        enableSorting: false,
        cell: ({ row }) =>
          row.original.rule_type === "cooldown" ? (
            <span>
              {row.original.cooldown_days}d
              {row.original.cooldown_duty_tag && (
                <>
                  {" "}after <TagBadge tag={row.original.cooldown_duty_tag} />
                </>
              )}
            </span>
          ) : (
            <span className="text-muted-foreground">—</span>
          ),
      },
      {
        accessorKey: "priority",
        header: "Priority",
        enableSorting: true,
      },
      {
        id: "actions",
        enableSorting: false,
        meta: { headerClassName: "w-16" },
        cell: ({ row }) => (
          <Button variant="ghost" size="icon" onClick={() => remove.mutate(row.original.id)}>
            <Icon name="delete" className="text-destructive" />
          </Button>
        ),
      },
    ],
    [remove],
  );

  const table = useReactTable({
    data: rules,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Rules</h1>

      <form
        className="space-y-4 rounded-lg border border-border p-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (!name.trim()) return;
          create.mutate({
            name: name.trim(),
            rule_type: ruleType,
            person_tag_id: toNullableInt(personTagId),
            duty_tag_id: toNullableInt(dutyTagId),
            priority: Number(priority) || 0,
            ...(ruleType === "cooldown" && {
              cooldown_days: Number(cooldownDays) || null,
              cooldown_duty_tag_id: toNullableInt(cooldownDutyTagId),
            }),
          });
        }}
      >
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Rule name" />
          </div>
          <div className="space-y-1.5">
            <Label>Type</Label>
            <Select value={ruleType} onValueChange={(v) => setRuleType(v as RuleType)}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RULE_TYPES.map((rt) => (
                  <SelectItem key={rt.value} value={rt.value}>
                    {rt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Person Tag</Label>
            <Combobox
              options={tagOptions}
              value={personTagId}
              onValueChange={setPersonTagId}
              placeholder="Any"
              searchPlaceholder="Search tags..."
              className="w-40"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Duty Tag</Label>
            <Combobox
              options={tagOptions}
              value={dutyTagId}
              onValueChange={setDutyTagId}
              placeholder="Any"
              searchPlaceholder="Search tags..."
              className="w-40"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Priority</Label>
            <Input
              type="number"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-20"
            />
          </div>
        </div>

        {ruleType === "cooldown" && (
          <div className="flex items-end gap-3">
            <div className="space-y-1.5">
              <Label>Cooldown Days</Label>
              <Input
                type="number"
                min={1}
                value={cooldownDays}
                onChange={(e) => setCooldownDays(e.target.value)}
                className="w-28"
                placeholder="Days"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Cooldown Trigger Tag</Label>
              <Combobox
                options={tagOptions}
                value={cooldownDutyTagId}
                onValueChange={setCooldownDutyTagId}
                placeholder="Any"
                searchPlaceholder="Search tags..."
                className="w-40"
              />
            </div>
          </div>
        )}

        <Button type="submit" disabled={create.isPending}>
          Add Rule
        </Button>
      </form>

      {isLoading ? (
        <p className="text-muted-foreground">Loading...</p>
      ) : rules.length === 0 ? (
        <p className="text-muted-foreground">No rules yet.</p>
      ) : (
        <DataTable table={table} />
      )}
    </div>
  );
}
