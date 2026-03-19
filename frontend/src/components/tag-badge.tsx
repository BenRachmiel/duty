import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";

import { fetchTagSummary } from "@/api";
import { Badge } from "@/components/ui/badge";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import type { Tag } from "@/types";

function TagBadgeInner({ tag }: { tag: Tag }) {
  return (
    <Badge variant="outline">
      {tag.name}
    </Badge>
  );
}

function InteractiveTagBadge({ tag }: { tag: Tag }) {
  const [hovered, setHovered] = useState(false);
  const { data: summary } = useQuery({
    queryKey: ["tagSummary", tag.id],
    queryFn: () => fetchTagSummary(tag.id),
    staleTime: 30_000,
    enabled: hovered,
  });

  return (
    <HoverCard openDelay={300} closeDelay={100} onOpenChange={(open) => { if (open) setHovered(true); }}>
      <HoverCardTrigger asChild>
        <span>
          <TagBadgeInner tag={tag} />
        </span>
      </HoverCardTrigger>
      <HoverCardContent className="w-64 text-sm space-y-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold">{tag.name}</span>
        </div>
        {summary && (
          <>
            <div className="flex gap-4 text-muted-foreground">
              <span>{summary.people_count} people</span>
              <span>{summary.duties_count} duties</span>
            </div>
            {summary.rules.length > 0 && (
              <div className="space-y-1">
                <span className="text-xs text-muted-foreground">Rules:</span>
                {summary.rules.map((r) => (
                  <div key={r.id} className="flex items-center gap-1">
                    <Badge variant={r.rule_type === "deny" ? "destructive" : r.rule_type === "cooldown" ? "secondary" : "default"} className="text-xs">
                      {r.rule_type}
                    </Badge>
                    <span className="truncate">{r.name}</span>
                  </div>
                ))}
              </div>
            )}
            <div className="flex gap-2 pt-1">
              <Link
                to={`/people?tag_id=${tag.id}`}
                className="text-xs text-primary hover:underline"
              >
                View people
              </Link>
              <Link
                to={`/duties?tag_id=${tag.id}`}
                className="text-xs text-primary hover:underline"
              >
                View duties
              </Link>
            </div>
          </>
        )}
      </HoverCardContent>
    </HoverCard>
  );
}

export function TagBadge({
  tag,
  interactive = false,
}: {
  tag: Tag;
  interactive?: boolean;
}) {
  if (interactive) return <InteractiveTagBadge tag={tag} />;
  return <TagBadgeInner tag={tag} />;
}
