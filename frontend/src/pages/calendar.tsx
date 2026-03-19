import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import type { EventContentArg, DatesSetArg } from "@fullcalendar/core";
import { fetchDuties, fetchAssignments } from "@/api";
import { Icon } from "@/components/ui/icon";
import { Badge } from "@/components/ui/badge";
import { TagBadge } from "@/components/tag-badge";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { PersonSheet } from "@/components/person-sheet";
import type { Assignment, Duty, Tag } from "@/types";

function formatDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T00:00:00");
  d.setDate(d.getDate() + days);
  return formatDate(d);
}

function EventHoverContent({
  dutyId,
  assigned,
  headcount,
  tags,
  assignments,
  onOpenPerson,
}: {
  dutyId: number;
  assigned: number;
  headcount: number;
  tags: Tag[];
  assignments: Assignment[];
  onOpenPerson: (id: number) => void;
}) {
  const dutyAssignments = assignments.filter((a) => a.duty_id === dutyId);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Badge
          variant={assigned >= headcount ? "default" : "destructive"}
          className="tabular-nums"
        >
          {assigned}/{headcount} filled
        </Badge>
      </div>
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {tags.map((tag) => (
            <TagBadge key={tag.id} tag={tag} />
          ))}
        </div>
      )}
      {dutyAssignments.length > 0 ? (
        <div className="space-y-0.5">
          <span className="text-xs text-muted-foreground">Assigned:</span>
          {dutyAssignments.map((a) => (
            <button
              key={a.id}
              className="block w-full text-left text-sm text-primary hover:underline"
              onClick={() => onOpenPerson(a.person.id)}
            >
              {a.person.name}
            </button>
          ))}
        </div>
      ) : (
        <span className="text-xs text-muted-foreground">No one assigned</span>
      )}
    </div>
  );
}

function EventContent({
  arg,
  assignments,
  duties,
  onOpenPerson,
}: {
  arg: EventContentArg;
  assignments: Assignment[];
  duties: Duty[];
  onOpenPerson: (id: number) => void;
}) {
  const { fillPct, assigned, headcount } = arg.event.extendedProps;
  const dutyId = Number(arg.event.id);
  const duty = duties.find((d) => d.id === dutyId);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current?.closest(".fc-event") as HTMLElement | null;
    if (!el) return;
    const pct = Math.round(fillPct * 100);
    el.style.background = `color-mix(in oklch, var(--color-fill-full) ${pct}%, var(--color-fill-empty))`;
  }, [fillPct]);

  return (
    <HoverCard openDelay={300} closeDelay={100}>
      <HoverCardTrigger asChild>
        <div ref={ref} className="fc-event-inner w-full truncate px-1 text-xs leading-tight cursor-default">
          <span className="font-medium">{arg.event.title}</span>{" "}
          <span className="opacity-75">
            ({assigned}/{headcount})
          </span>
        </div>
      </HoverCardTrigger>
      <HoverCardContent className="w-56 p-3 text-sm" side="bottom">
        <p className="font-semibold mb-2">{arg.event.title}</p>
        <EventHoverContent
          dutyId={dutyId}
          assigned={assigned}
          headcount={headcount}
          tags={duty?.tags ?? []}
          assignments={assignments}
          onOpenPerson={onOpenPerson}
        />
      </HoverCardContent>
    </HoverCard>
  );
}

export function CalendarPage() {
  const [dateRange, setDateRange] = useState<{ from: string; to: string } | null>(null);
  const [personSheetId, setPersonSheetId] = useState<number | null>(null);

  const dutyParams = useMemo(
    () =>
      dateRange
        ? { date_from: dateRange.from, date_to: dateRange.to, limit: 500 }
        : null,
    [dateRange],
  );

  const assignmentParams = useMemo(
    () =>
      dateRange
        ? { date_from: dateRange.from, date_to: dateRange.to, limit: 2000 }
        : null,
    [dateRange],
  );

  const { data: dutiesData, isLoading: dutiesLoading } = useQuery({
    queryKey: ["duties", dutyParams],
    queryFn: () => fetchDuties(dutyParams!),
    enabled: !!dutyParams,
  });

  const { data: assignmentsData, isLoading: assignmentsLoading } = useQuery({
    queryKey: ["assignments", assignmentParams],
    queryFn: () => fetchAssignments(assignmentParams!),
    enabled: !!assignmentParams,
  });

  const duties = dutiesData?.items ?? [];
  const assignments = assignmentsData?.items ?? [];
  const isLoading = dutiesLoading || assignmentsLoading;

  const calendarEvents = useMemo(() => {
    const countByDuty = new Map<number, number>();
    for (const a of assignments) {
      countByDuty.set(a.duty_id, (countByDuty.get(a.duty_id) ?? 0) + 1);
    }

    return duties.map((duty) => {
      const assigned = countByDuty.get(duty.id) ?? 0;
      const fillPct = duty.headcount > 0 ? Math.min(assigned / duty.headcount, 1) : 0;

      return {
        id: String(duty.id),
        title: duty.name,
        start: duty.date,
        end: addDays(duty.date, duty.duration_days),
        extendedProps: { fillPct, assigned, headcount: duty.headcount },
      };
    });
  }, [duties, assignments]);

  function handleDatesSet(dateInfo: DatesSetArg) {
    const from = formatDate(dateInfo.start);
    const to = formatDate(dateInfo.end);
    setDateRange((prev) =>
      prev?.from === from && prev?.to === to ? prev : { from, to },
    );
  }

  const handleOpenPerson = useCallback((id: number) => setPersonSheetId(id), []);

  const renderEventContent = useCallback(
    (arg: EventContentArg) => (
      <EventContent
        arg={arg}
        assignments={assignments}
        duties={duties}
        onOpenPerson={handleOpenPerson}
      />
    ),
    [assignments, duties, handleOpenPerson],
  );

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Calendar</h1>
      {isLoading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Icon name="progress_activity" className="animate-spin" />
          Loading...
        </div>
      )}
      <div className="duty-calendar">
        <FullCalendar
          plugins={[dayGridPlugin]}
          initialView="dayGridMonth"
          events={calendarEvents}
          headerToolbar={{ left: "prev,next today", center: "title", right: "" }}
          eventContent={renderEventContent}
          datesSet={handleDatesSet}
          height="auto"
          firstDay={1}
        />
      </div>
      <PersonSheet
        personId={personSheetId}
        onClose={() => setPersonSheetId(null)}
      />
    </div>
  );
}
