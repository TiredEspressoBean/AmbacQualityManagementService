"use client";

import {
  DndContext,
  MouseSensor,
  useDraggable,
  useSensor,
} from "@dnd-kit/core";
import { restrictToHorizontalAxis } from "@dnd-kit/modifiers";
import { useMouse, useThrottle, useWindowScroll } from "@uidotdev/usehooks";
import {
  addDays,
  addMinutes,
  addMonths,
  differenceInDays,
  differenceInHours,
  differenceInMinutes,
  differenceInMonths,
  endOfDay,
  endOfMonth,
  format,
  formatDate,
  formatDistance,
  getDate,
  getDaysInMonth,
  isSameDay,
  startOfDay,
  startOfMonth,
} from "date-fns";
import { atom, useAtom } from "jotai";
import throttle from "lodash.throttle";
import { PlusIcon, TrashIcon } from "lucide-react";
import type {
  CSSProperties,
  FC,
  KeyboardEventHandler,
  MouseEvent as ReactMouseEvent,
  MouseEventHandler,
  ReactNode,
  RefObject,
} from "react";
import {
  createContext,
  memo,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { Card } from "@/components/ui/card";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { cn } from "@/lib/utils";

const draggingAtom = atom(false);
const scrollXAtom = atom(0);

export const useGanttDragging = () => useAtom(draggingAtom);
export const useGanttScrollX = () => useAtom(scrollXAtom);

export type GanttStatus = {
  id: string;
  name: string;
  color: string;
};

export type GanttFeature = {
  id: string;
  name: string;
  startAt: Date;
  endAt: Date;
  status: GanttStatus;
  lane?: string; // Optional: features with the same lane will share a row
};

export type GanttMarkerProps = {
  id: string;
  date: Date;
  label: string;
};

export type Range = "hourly" | "daily" | "monthly" | "quarterly";

export type TimelineData = {
  year: number;
  quarters: {
    months: {
      days: number;
    }[];
  }[];
}[];

export type GanttContextProps = {
  // Zoom lives behind a ref, not a context value: changing the zoom NUMBER must not
  // change the context object's identity, or every consumer (all bars, header, pegs)
  // would re-render on each zoom step. In hourly mode the bars position purely off the
  // --gantt-column-width CSS variable, so a zoom needs zero React work — the provider
  // just updates that one variable. Handlers/helpers that need the live number read
  // zoomRef.current at call time.
  zoomRef: RefObject<number>;
  range: Range;
  columnWidth: number;
  sidebarWidth: number;
  headerHeight: number;
  rowHeight: number;
  onAddItem: ((date: Date) => void) | undefined;
  placeholderLength: number;
  timelineData: TimelineData;
  ref: RefObject<HTMLDivElement | null> | null;
  scrollToFeature?: (feature: GanttFeature) => void;
  // Bounded (shop) mode: when set, the timeline is exactly these day columns from
  // boundStart, instead of the fixed 3-year calendar grid — used by the hourly range.
  boundStart?: Date;
  boundDays?: number;
};

const getsDaysIn = (range: Range) => {
  // For when range is daily
  let fn = (_date: Date) => 1;

  if (range === "monthly" || range === "quarterly") {
    fn = getDaysInMonth;
  }

  return fn;
};

const getDifferenceIn = (range: Range) => {
  let fn = differenceInDays;

  if (range === "monthly" || range === "quarterly") {
    fn = differenceInMonths;
  }

  return fn;
};

const getInnerDifferenceIn = (range: Range) => {
  let fn = differenceInHours;

  if (range === "monthly" || range === "quarterly") {
    fn = differenceInDays;
  }

  return fn;
};

const getStartOf = (range: Range) => {
  let fn = startOfDay;

  if (range === "monthly" || range === "quarterly") {
    fn = startOfMonth;
  }

  return fn;
};

const getEndOf = (range: Range) => {
  let fn = endOfDay;

  if (range === "monthly" || range === "quarterly") {
    fn = endOfMonth;
  }

  return fn;
};

const getAddRange = (range: Range) => {
  let fn = addDays;

  if (range === "monthly" || range === "quarterly") {
    fn = addMonths;
  }

  return fn;
};

const getDateByMousePosition = (context: GanttContextProps, mouseX: number) => {
  // Hourly: one column = one day (columnWidth px), pixels within it map linearly
  // to minutes. Origin is the bound horizon start, matching getOffset/getWidth.
  if (context.range === "hourly") {
    const origin = context.boundStart
      ? startOfDay(context.boundStart)
      : new Date(context.timelineData[0].year, 0, 1);
    const pxPerDay = (context.columnWidth * context.zoomRef.current) / 100;
    const minutes = (mouseX / pxPerDay) * 24 * 60;
    return addMinutes(origin, minutes);
  }
  const timelineStartDate = new Date(context.timelineData[0].year, 0, 1);
  const columnWidth = (context.columnWidth * context.zoomRef.current) / 100;
  const offset = Math.floor(mouseX / columnWidth);
  const daysIn = getsDaysIn(context.range);
  const addRange = getAddRange(context.range);
  const month = addRange(timelineStartDate, offset);
  const daysInMonth = daysIn(month);
  const pixelsPerDay = Math.round(columnWidth / daysInMonth);
  const dayOffset = Math.floor((mouseX % columnWidth) / pixelsPerDay);
  const actualDate = addDays(month, dayOffset);

  return actualDate;
};

const createInitialTimelineData = (today: Date) => {
  const data: TimelineData = [];

  data.push(
    { year: today.getFullYear() - 1, quarters: new Array(4).fill(null) },
    { year: today.getFullYear(), quarters: new Array(4).fill(null) },
    { year: today.getFullYear() + 1, quarters: new Array(4).fill(null) }
  );

  for (const yearObj of data) {
    yearObj.quarters = new Array(4).fill(null).map((_, quarterIndex) => ({
      months: new Array(3).fill(null).map((_, monthIndex) => {
        const month = quarterIndex * 3 + monthIndex;
        return {
          days: getDaysInMonth(new Date(yearObj.year, month, 1)),
        };
      }),
    }));
  }

  return data;
};

const getOffset = (
  date: Date,
  timelineStartDate: Date,
  context: GanttContextProps
) => {
  const parsedColumnWidth = (context.columnWidth * context.zoomRef.current) / 100;
  const differenceIn = getDifferenceIn(context.range);
  const startOf = getStartOf(context.range);
  const fullColumns = differenceIn(startOf(date), timelineStartDate);

  if (context.range === "hourly") {
    // Position within the day column by minutes-into-day (day columns, minute detail).
    const minutesIntoDay = differenceInMinutes(date, startOf(date));
    return parsedColumnWidth * fullColumns + (minutesIntoDay / (60 * 24)) * parsedColumnWidth;
  }

  if (context.range === "daily") {
    return parsedColumnWidth * fullColumns;
  }

  const partialColumns = date.getDate();
  const daysInMonth = getDaysInMonth(date);
  const pixelsPerDay = parsedColumnWidth / daysInMonth;

  return fullColumns * parsedColumnWidth + partialColumns * pixelsPerDay;
};

const getWidth = (
  startAt: Date,
  endAt: Date | null,
  context: GanttContextProps
) => {
  const parsedColumnWidth = (context.columnWidth * context.zoomRef.current) / 100;

  if (!endAt) {
    return parsedColumnWidth * 2;
  }

  const differenceIn = getDifferenceIn(context.range);

  if (context.range === "hourly") {
    // Minute-accurate: width is the task's share of a (day-wide) column.
    return (differenceInMinutes(endAt, startAt) / (60 * 24)) * parsedColumnWidth;
  }

  if (context.range === "daily") {
    const delta = differenceIn(endAt, startAt);

    return parsedColumnWidth * (delta ? delta : 1);
  }

  const daysInStartMonth = getDaysInMonth(startAt);
  const pixelsPerDayInStartMonth = parsedColumnWidth / daysInStartMonth;

  if (isSameDay(startAt, endAt)) {
    return pixelsPerDayInStartMonth;
  }

  const innerDifferenceIn = getInnerDifferenceIn(context.range);
  const startOf = getStartOf(context.range);

  if (isSameDay(startOf(startAt), startOf(endAt))) {
    return innerDifferenceIn(endAt, startAt) * pixelsPerDayInStartMonth;
  }

  const startRangeOffset = daysInStartMonth - getDate(startAt);
  const endRangeOffset = getDate(endAt);
  const fullRangeOffset = differenceIn(startOf(endAt), startOf(startAt));
  const daysInEndMonth = getDaysInMonth(endAt);
  const pixelsPerDayInEndMonth = parsedColumnWidth / daysInEndMonth;

  return (
    (fullRangeOffset - 1) * parsedColumnWidth +
    startRangeOffset * pixelsPerDayInStartMonth +
    endRangeOffset * pixelsPerDayInEndMonth
  );
};

const calculateInnerOffset = (
  date: Date,
  range: Range,
  columnWidth: number
) => {
  const startOf = getStartOf(range);
  const endOf = getEndOf(range);
  const differenceIn = getInnerDifferenceIn(range);
  const startOfRange = startOf(date);
  const endOfRange = endOf(date);
  const totalRangeDays = differenceIn(endOfRange, startOfRange);
  const dayOfMonth = date.getDate();

  return (dayOfMonth / totalRangeDays) * columnWidth;
};

// A separate, reactive zoom channel for the few overlays that position in raw pixels
// (shift bands, peg lines) and MUST re-render to rescale on zoom. The main GanttContext
// deliberately excludes zoom so the CSS-var-positioned bars don't re-render; anything
// that can't ride the --gantt-column-width variable subscribes here instead.
const GanttZoomContext = createContext<number>(100);

const GanttContext = createContext<GanttContextProps>({
  zoomRef: { current: 100 },
  range: "monthly",
  columnWidth: 50,
  headerHeight: 60,
  sidebarWidth: 300,
  rowHeight: 36,
  onAddItem: undefined,
  placeholderLength: 2,
  timelineData: [],
  ref: null,
  scrollToFeature: undefined,
});

export type GanttContentHeaderProps = {
  renderHeaderItem: (index: number) => ReactNode;
  title: string;
  columns: number;
};

export const GanttContentHeader: FC<GanttContentHeaderProps> = ({
  title,
  columns,
  renderHeaderItem,
}) => {
  const id = useId();

  return (
    <div
      className="sticky top-0 z-20 grid w-full shrink-0 bg-backdrop/90 backdrop-blur-sm"
      style={{ height: "var(--gantt-header-height)" }}
    >
      <div>
        <div
          className="sticky inline-flex whitespace-nowrap px-3 py-2 text-muted-foreground text-xs"
          style={{
            left: "var(--gantt-sidebar-width)",
          }}
        >
          <p>{title}</p>
        </div>
      </div>
      <div
        className="grid w-full"
        style={{
          gridTemplateColumns: `repeat(${columns}, var(--gantt-column-width))`,
        }}
      >
        {Array.from({ length: columns }).map((_, index) => (
          <div
            className="shrink-0 border-border/50 border-b py-1 text-center text-xs"
            key={`${id}-${index}`}
          >
            {renderHeaderItem(index)}
          </div>
        ))}
      </div>
    </div>
  );
};

const DailyHeader: FC = () => {
  const gantt = useContext(GanttContext);

  return gantt.timelineData.map((year) =>
    year.quarters
      .flatMap((quarter) => quarter.months)
      .map((month, index) => (
        <div className="relative flex flex-col" key={`${year.year}-${index}`}>
          <GanttContentHeader
            columns={month.days}
            renderHeaderItem={(item: number) => (
              <div className="flex items-center justify-center gap-1">
                <p>
                  {format(addDays(new Date(year.year, index, 1), item), "d")}
                </p>
                <p className="text-muted-foreground">
                  {format(
                    addDays(new Date(year.year, index, 1), item),
                    "EEEEE"
                  )}
                </p>
              </div>
            )}
            title={format(new Date(year.year, index, 1), "MMMM yyyy")}
          />
          <GanttColumns
            columns={month.days}
            isColumnSecondary={(item: number) =>
              [0, 6].includes(
                addDays(new Date(year.year, index, 1), item).getDay()
              )
            }
          />
        </div>
      ))
  );
};

const MonthlyHeader: FC = () => {
  const gantt = useContext(GanttContext);

  return gantt.timelineData.map((year) => (
    <div className="relative flex flex-col" key={year.year}>
      <GanttContentHeader
        columns={year.quarters.flatMap((quarter) => quarter.months).length}
        renderHeaderItem={(item: number) => (
          <p>{format(new Date(year.year, item, 1), "MMM")}</p>
        )}
        title={`${year.year}`}
      />
      <GanttColumns
        columns={year.quarters.flatMap((quarter) => quarter.months).length}
      />
    </div>
  ));
};

const QuarterlyHeader: FC = () => {
  const gantt = useContext(GanttContext);

  return gantt.timelineData.map((year) =>
    year.quarters.map((quarter, quarterIndex) => (
      <div
        className="relative flex flex-col"
        key={`${year.year}-${quarterIndex}`}
      >
        <GanttContentHeader
          columns={quarter.months.length}
          renderHeaderItem={(item: number) => (
            <p>
              {format(new Date(year.year, quarterIndex * 3 + item, 1), "MMM")}
            </p>
          )}
          title={`Q${quarterIndex + 1} ${year.year}`}
        />
        <GanttColumns columns={quarter.months.length} />
      </div>
    ))
  );
};

// Bounded day columns from boundStart (the schedule horizon), labelled by date.
// Hourly detail comes from the minute-accurate offset/width; the timeline is exactly
// the horizon, not a 3-year grid.
const HourlyHeader: FC = () => {
  const gantt = useContext(GanttContext);
  const start = startOfDay(gantt.boundStart ?? new Date());
  const days = gantt.boundDays ?? 30;

  return (
    <div className="relative flex flex-col">
      <GanttContentHeader
        columns={days}
        title={format(start, "MMM yyyy")}
        renderHeaderItem={(item: number) => {
          const d = addDays(start, item);
          return (
            <div className="flex items-center justify-center gap-1">
              <p>{format(d, "MMM d")}</p>
              <p className="text-muted-foreground">{format(d, "EEEEE")}</p>
            </div>
          );
        }}
      />
      <GanttColumns
        columns={days}
        isColumnSecondary={(item: number) => {
          const day = addDays(start, item).getDay();
          return day === 0 || day === 6;
        }}
      />
    </div>
  );
};

const headers: Record<Range, FC> = {
  hourly: HourlyHeader,
  daily: DailyHeader,
  monthly: MonthlyHeader,
  quarterly: QuarterlyHeader,
};

export type GanttHeaderProps = {
  className?: string;
};

export const GanttHeader: FC<GanttHeaderProps> = ({ className }) => {
  const gantt = useContext(GanttContext);
  const Header = headers[gantt.range];

  return (
    <div
      className={cn(
        "-space-x-px flex h-full w-max divide-x divide-border/50",
        className
      )}
    >
      <Header />
    </div>
  );
};

export type GanttSidebarItemProps = {
  feature: GanttFeature;
  onSelectItem?: (id: string) => void;
  className?: string;
};

export const GanttSidebarItem: FC<GanttSidebarItemProps> = ({
  feature,
  onSelectItem,
  className,
}) => {
  const gantt = useContext(GanttContext);
  const tempEndAt =
    feature.endAt && isSameDay(feature.startAt, feature.endAt)
      ? addDays(feature.endAt, 1)
      : feature.endAt;
  const duration = tempEndAt
    ? formatDistance(feature.startAt, tempEndAt)
    : `${formatDistance(feature.startAt, new Date())} so far`;

  const handleClick: MouseEventHandler<HTMLDivElement> = (event) => {
    if (event.target === event.currentTarget) {
      // Scroll to the feature in the timeline
      gantt.scrollToFeature?.(feature);
      // Call the original onSelectItem callback
      onSelectItem?.(feature.id);
    }
  };

  const handleKeyDown: KeyboardEventHandler<HTMLDivElement> = (event) => {
    if (event.key === "Enter") {
      // Scroll to the feature in the timeline
      gantt.scrollToFeature?.(feature);
      // Call the original onSelectItem callback
      onSelectItem?.(feature.id);
    }
  };

  return (
    <div
      className={cn(
        "relative flex items-center gap-2.5 p-2.5 text-xs hover:bg-secondary",
        className
      )}
      key={feature.id}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      // biome-ignore lint/a11y/useSemanticElements: "This is a clickable item"
      role="button"
      style={{
        height: "var(--gantt-row-height)",
      }}
      tabIndex={0}
    >
      {/* <Checkbox onCheckedChange={handleCheck} className="shrink-0" /> */}
      <div
        className="pointer-events-none h-2 w-2 shrink-0 rounded-full"
        style={{
          backgroundColor: feature.status.color,
        }}
      />
      <p className="pointer-events-none flex-1 truncate text-left font-medium">
        {feature.name}
      </p>
      <p className="pointer-events-none text-muted-foreground">{duration}</p>
    </div>
  );
};

export const GanttSidebarHeader: FC = () => (
  <div
    className="sticky top-0 z-10 flex shrink-0 items-end justify-between gap-2.5 border-border/50 border-b bg-backdrop/90 p-2.5 font-medium text-muted-foreground text-xs backdrop-blur-sm"
    style={{ height: "var(--gantt-header-height)" }}
  >
    {/* <Checkbox className="shrink-0" /> */}
    <p className="flex-1 truncate text-left">Issues</p>
    <p className="shrink-0">Duration</p>
  </div>
);

export type GanttSidebarGroupProps = {
  children: ReactNode;
  name: string;
  accessory?: ReactNode;
  className?: string;
};

export const GanttSidebarGroup: FC<GanttSidebarGroupProps> = ({
  children,
  name,
  accessory,
  className,
}) => (
  <div className={className}>
    <div
      className="flex w-full items-center gap-2 p-2.5 text-left font-medium text-muted-foreground text-xs"
      style={{ height: "var(--gantt-row-height)" }}
    >
      <p className="flex-1 truncate">{name}</p>
      {accessory}
    </div>
    <div className="divide-y divide-border/50">{children}</div>
  </div>
);

export type GanttSidebarProps = {
  children: ReactNode;
  className?: string;
};

export const GanttSidebar: FC<GanttSidebarProps> = ({
  children,
  className,
}) => (
  <div
    className={cn(
      "sticky left-0 z-30 h-max min-h-full overflow-clip border-border/50 border-r bg-background/90 backdrop-blur-md",
      className
    )}
    data-roadmap-ui="gantt-sidebar"
  >
    <GanttSidebarHeader />
    <div className="space-y-4">{children}</div>
  </div>
);

export type GanttAddFeatureHelperProps = {
  top: number;
  className?: string;
};

export const GanttAddFeatureHelper: FC<GanttAddFeatureHelperProps> = ({
  top,
  className,
}) => {
  const [scrollX] = useGanttScrollX();
  const gantt = useContext(GanttContext);
  const [mousePosition, mouseRef] = useMouse<HTMLDivElement>();

  const handleClick = () => {
    const ganttRect = gantt.ref?.current?.getBoundingClientRect();
    const x =
      mousePosition.x - (ganttRect?.left ?? 0) + scrollX - gantt.sidebarWidth;
    const currentDate = getDateByMousePosition(gantt, x);

    gantt.onAddItem?.(currentDate);
  };

  return (
    <div
      className={cn("absolute top-0 w-full px-0.5", className)}
      ref={mouseRef}
      style={{
        marginTop: -gantt.rowHeight / 2,
        transform: `translateY(${top}px)`,
      }}
    >
      <button
        className="flex h-full w-full items-center justify-center rounded-md border border-dashed p-2"
        onClick={handleClick}
        type="button"
      >
        <PlusIcon
          className="pointer-events-none select-none text-muted-foreground"
          size={16}
        />
      </button>
    </div>
  );
};

export type GanttColumnProps = {
  index: number;
  isColumnSecondary?: (item: number) => boolean;
};

export const GanttColumn: FC<GanttColumnProps> = ({
  index,
  isColumnSecondary,
}) => {
  const gantt = useContext(GanttContext);
  const [dragging] = useGanttDragging();
  const [mousePosition, mouseRef] = useMouse<HTMLDivElement>();
  const [hovering, setHovering] = useState(false);
  const [windowScroll] = useWindowScroll();

  const handleMouseEnter = () => setHovering(true);
  const handleMouseLeave = () => setHovering(false);

  const top = useThrottle(
    mousePosition.y -
      (mouseRef.current?.getBoundingClientRect().y ?? 0) -
      (windowScroll.y ?? 0),
    10
  );

  return (
    // biome-ignore lint/a11y/noStaticElementInteractions: "This is a clickable column"
    // biome-ignore lint/nursery/noNoninteractiveElementInteractions: "This is a clickable column"
    <div
      className={cn(
        "group relative h-full overflow-hidden",
        isColumnSecondary?.(index) ? "bg-secondary" : ""
      )}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      ref={mouseRef}
    >
      {!dragging && hovering && gantt.onAddItem ? (
        <GanttAddFeatureHelper top={top} />
      ) : null}
    </div>
  );
};

export type GanttColumnsProps = {
  columns: number;
  isColumnSecondary?: (item: number) => boolean;
};

export const GanttColumns: FC<GanttColumnsProps> = ({
  columns,
  isColumnSecondary,
}) => {
  const id = useId();

  return (
    <div
      className="divide grid h-full w-full divide-x divide-border/50"
      style={{
        gridTemplateColumns: `repeat(${columns}, var(--gantt-column-width))`,
      }}
    >
      {Array.from({ length: columns }).map((_, index) => (
        <GanttColumn
          index={index}
          isColumnSecondary={isColumnSecondary}
          key={`${id}-${index}`}
        />
      ))}
    </div>
  );
};

export type GanttCreateMarkerTriggerProps = {
  onCreateMarker: (date: Date) => void;
  className?: string;
};

export const GanttCreateMarkerTrigger: FC<GanttCreateMarkerTriggerProps> = ({
  onCreateMarker,
  className,
}) => {
  const gantt = useContext(GanttContext);
  const [mousePosition, mouseRef] = useMouse<HTMLDivElement>();
  const [windowScroll] = useWindowScroll();
  const x = useThrottle(
    mousePosition.x -
      (mouseRef.current?.getBoundingClientRect().x ?? 0) -
      (windowScroll.x ?? 0),
    10
  );

  const date = getDateByMousePosition(gantt, x);

  const handleClick = () => onCreateMarker(date);

  return (
    <div
      className={cn(
        "group pointer-events-none absolute top-0 left-0 h-full w-full select-none overflow-visible",
        className
      )}
      ref={mouseRef}
    >
      <div
        className="-ml-2 pointer-events-auto sticky top-6 z-20 flex w-4 flex-col items-center justify-center gap-1 overflow-visible opacity-0 group-hover:opacity-100"
        style={{ transform: `translateX(${x}px)` }}
      >
        <button
          className="z-50 inline-flex h-4 w-4 items-center justify-center rounded-full bg-card"
          onClick={handleClick}
          type="button"
        >
          <PlusIcon className="text-muted-foreground" size={12} />
        </button>
        <div className="whitespace-nowrap rounded-full border border-border/50 bg-background/90 px-2 py-1 text-foreground text-xs backdrop-blur-lg">
          {formatDate(date, "MMM dd, yyyy")}
        </div>
      </div>
    </div>
  );
};

export type GanttFeatureDragHelperProps = {
  featureId: GanttFeature["id"];
  direction: "left" | "right";
  date: Date | null;
};

export const GanttFeatureDragHelper: FC<GanttFeatureDragHelperProps> = ({
  direction,
  featureId,
  date,
}) => {
  const [, setDragging] = useGanttDragging();
  const { attributes, listeners, setNodeRef } = useDraggable({
    id: `feature-drag-helper-${featureId}`,
  });

  const isPressed = Boolean(attributes["aria-pressed"]);

  useEffect(() => setDragging(isPressed), [isPressed, setDragging]);

  return (
    <div
      className={cn(
        "group -translate-y-1/2 !cursor-col-resize absolute top-1/2 z-[3] h-full w-6 rounded-md outline-none",
        direction === "left" ? "-left-2.5" : "-right-2.5"
      )}
      ref={setNodeRef}
      {...attributes}
      {...listeners}
    >
      <div
        className={cn(
          "-translate-y-1/2 absolute top-1/2 h-[80%] w-1 rounded-sm bg-muted-foreground opacity-0 transition-all",
          direction === "left" ? "left-2.5" : "right-2.5",
          direction === "left" ? "group-hover:left-0" : "group-hover:right-0",
          isPressed && (direction === "left" ? "left-0" : "right-0"),
          "group-hover:opacity-100",
          isPressed && "opacity-100"
        )}
      />
      {date && (
        <div
          className={cn(
            "-translate-x-1/2 absolute top-10 hidden whitespace-nowrap rounded-lg border border-border/50 bg-background/90 px-2 py-1 text-foreground text-xs backdrop-blur-lg group-hover:block",
            isPressed && "block"
          )}
        >
          {format(date, "MMM dd, yyyy")}
        </div>
      )}
    </div>
  );
};

export type GanttFeatureItemCardProps = Pick<GanttFeature, "id"> & {
  children?: ReactNode;
  className?: string;
};

export const GanttFeatureItemCard: FC<GanttFeatureItemCardProps> = ({
  id,
  children,
  className,
}) => {
  const [, setDragging] = useGanttDragging();
  const { attributes, listeners, setNodeRef } = useDraggable({ id });
  const isPressed = Boolean(attributes["aria-pressed"]);

  useEffect(() => setDragging(isPressed), [isPressed, setDragging]);

  return (
    <Card
      className={cn(
        "h-full w-full rounded-md bg-background p-2 text-xs shadow-sm",
        className
      )}
    >
      <div
        className={cn(
          "flex h-full w-full items-center justify-between gap-2 text-left",
          isPressed && "cursor-grabbing"
        )}
        {...attributes}
        {...listeners}
        ref={setNodeRef}
      >
        {children}
      </div>
    </Card>
  );
};

/** The lane a drag ended over, found by hit-testing the pointer against elements
 *  tagged `data-gantt-lane`.
 *
 *  Why hit-test rather than dnd-kit droppables: every bar owns its *own*
 *  `DndContext` (see below), and a droppable only registers with the context it is
 *  rendered inside. Making lanes droppable would mean hoisting one context to the
 *  Gantt root and re-plumbing every drag in this file. The pointer already tells us
 *  what is under it, so we ask the DOM instead.
 */
function laneUnderPointer(clientY: number): string | null {
  // Vertical band test, not `elementsFromPoint`. A lane row is `w-max` inside a
  // horizontally-scrolled timeline, so its box frequently does NOT span the cursor's
  // x — a point-hit misses the row it is visually inside. What identifies a lane is
  // its vertical band; x is the time axis and says nothing about which resource.
  for (const el of document.querySelectorAll<HTMLElement>("[data-gantt-lane]")) {
    const r = el.getBoundingClientRect();
    if (clientY >= r.top && clientY <= r.bottom) return el.dataset.ganttLane ?? null;
  }
  return null;
}

const LANE_OVERLAY_ID = "gantt-lane-drop-overlay";

/** Highlight the lane a drag is currently over, as a positioned overlay rather than a
 *  class on the lane row.
 *
 *  The row itself cannot show this: it is `w-max` and every bar inside it is absolutely
 *  positioned, so its max-content width resolves to ZERO. Styling it computes real
 *  values and paints nothing. (The same zero width is why the lane hit-test above is
 *  vertical-only — a row with no width can never contain the cursor's x.)
 *
 *  So we borrow the row's vertical band and the timeline's horizontal extent, and draw
 *  one reusable, pointer-transparent strip. Written straight to the DOM because the lane
 *  rows are rendered by the consumer, outside this component's tree.
 */
function markHoveredLane(laneId: string | null) {
  const existing = document.getElementById(LANE_OVERLAY_ID);
  if (laneId == null) {
    existing?.remove();
    return;
  }
  const lane = [...document.querySelectorAll<HTMLElement>("[data-gantt-lane]")].find(
    (l) => l.dataset.ganttLane === laneId
  );
  const board = document.querySelector(".gantt");
  if (!lane || !board) {
    existing?.remove();
    return;
  }
  const r = lane.getBoundingClientRect();
  const b = board.getBoundingClientRect();
  const el = existing ?? document.createElement("div");
  if (!existing) {
    el.id = LANE_OVERLAY_ID;
    el.style.position = "fixed";
    el.style.pointerEvents = "none";
    el.style.zIndex = "40";
    el.style.borderRadius = "4px";
    el.style.background = "rgba(14, 165, 233, 0.16)";
    el.style.boxShadow = "inset 0 0 0 2px rgba(14, 165, 233, 0.75)";
    document.body.appendChild(el);
  }
  el.style.top = `${r.top}px`;
  el.style.height = `${r.height}px`;
  el.style.left = `${b.left}px`;
  el.style.width = `${b.width}px`;
}

export type GanttFeatureItemProps = GanttFeature & {
  /** `laneId` is the lane the bar was dropped on, when that differs from the one it
   *  started in — the drag-to-reassign signal. Null/undefined means a pure time move. */
  //  Returning a promise is optional, but a handler that REJECTS tells the bar the
  //  drop was refused, and it rolls back to its previous position.
  onMove?: (
    id: string,
    startDate: Date,
    endDate: Date | null,
    laneId?: string | null,
  ) => void | Promise<unknown>;
  onSelect?: (id: string, event: ReactMouseEvent) => void;
  resizable?: boolean;
  /** Render only the positioned bar (no full-width row wrapper), so several bars
   * can share one lane row — used by the collapsed resource-lane view. */
  bare?: boolean;
  children?: ReactNode;
  className?: string;
  cardClassName?: string;
};

const GanttFeatureItemBase: FC<GanttFeatureItemProps> = ({
  onMove,
  onSelect,
  resizable,
  bare,
  children,
  className,
  cardClassName,
  ...feature
}) => {
  const [scrollX] = useGanttScrollX();
  const gantt = useContext(GanttContext);
  const timelineStartDate = useMemo(
    () => (gantt.boundStart ? startOfDay(gantt.boundStart) : new Date(gantt.timelineData.at(0)?.year ?? 0, 0, 1)),
    [gantt.timelineData]
  );
  const [startAt, setStartAt] = useState<Date>(feature.startAt);
  const [endAt, setEndAt] = useState<Date | null>(feature.endAt);

  // Keep the rendered position tied to the source data: when a move succeeds the
  // refetch hands new Date objects and the bar settles at the new time.
  //
  // This does NOT undo a refused drop, though it used to claim it did. React Query's
  // structural sharing (on by default) returns the SAME object reference when
  // refetched data is deeply equal — which is exactly the case after a rejected move —
  // so these deps never change, the effect never runs, and the bar sits at a time the
  // server refused. The rollback is explicit in `onDragEnd` instead.
  useEffect(() => {
    setStartAt(feature.startAt);
    setEndAt(feature.endAt ?? null);
  }, [feature.startAt, feature.endAt]);

  // Memoize expensive calculations
  const width = useMemo(
    () => getWidth(startAt, endAt, gantt),
    [startAt, endAt, gantt]
  );
  const offset = useMemo(
    () => getOffset(startAt, timelineStartDate, gantt),
    [startAt, timelineStartDate, gantt]
  );

  // Hourly: express position as a ZOOM-INDEPENDENT fraction of a day-column, so the bar
  // is placed with calc(var(--gantt-column-width) * fraction). A zoom then changes ONE
  // CSS variable and the browser repositions every bar via CSS — no per-bar JS/DOM work,
  // no re-layout driven from React. (Buttery zoom on ~500 bars.)
  const hourly = gantt.range === "hourly";
  const widthFraction = useMemo(
    () => (endAt ? differenceInMinutes(endAt, startAt) / (60 * 24) : 2),
    [startAt, endAt]
  );
  const leftFraction = useMemo(
    () => differenceInMinutes(startAt, timelineStartDate) / (60 * 24),
    [startAt, timelineStartDate]
  );

  const addRange = useMemo(() => getAddRange(gantt.range), [gantt.range]);
  const [mousePosition] = useMouse<HTMLDivElement>();

  const [previousMouseX, setPreviousMouseX] = useState(0);
  const [previousStartAt, setPreviousStartAt] = useState(startAt);
  const [previousEndAt, setPreviousEndAt] = useState(endAt);

  const mouseSensor = useSensor(MouseSensor, {
    activationConstraint: {
      distance: 10,
    },
  });

  // The lane the drag started in, so a drop back onto the same row reads as a pure
  // time move rather than a no-op "reassignment".
  const originLane = useRef<string | null>(null);
  const hoveredLane = useRef<string | null>(null);
  // Live pointer Y, read straight off the native event rather than from `useMouse`.
  // That hook's value is React state and lags a frame — the same staleness the hourly
  // branch below already works around — and a lane test one frame behind drops the
  // task on the row above the one under the cursor.
  const pointerY = useRef<number>(0);
  const trackPointer = useRef<((e: PointerEvent) => void) | null>(null);

  const handleItemDragStart = useCallback(() => {
    setPreviousMouseX(mousePosition.x);
    setPreviousStartAt(startAt);
    setPreviousEndAt(endAt);
    const onPointer = (e: PointerEvent) => { pointerY.current = e.clientY; };
    trackPointer.current = onPointer;
    document.addEventListener("pointermove", onPointer, { passive: true });
    pointerY.current = mousePosition.y - window.scrollY;
    originLane.current = laneUnderPointer(pointerY.current);
    hoveredLane.current = originLane.current;
  }, [mousePosition.x, mousePosition.y, startAt, endAt]);

  /** Stop tracking the pointer and clear any lane highlight. */
  const endLaneTracking = useCallback(() => {
    if (trackPointer.current) {
      document.removeEventListener("pointermove", trackPointer.current);
      trackPointer.current = null;
    }
    markHoveredLane(null);
  }, []);

  useEffect(() => endLaneTracking, [endLaneTracking]);

  const handleItemDragMove = useCallback(
    (event?: { delta?: { x: number } }) => {
      // Track the lane under the cursor so the planner can see where the drop lands.
      // The bar itself stays in its row (the drag is restricted to the horizontal
      // axis so vertical travel can't perturb the time), which is exactly why the
      // target has to be shown some other way.
      const lane = laneUnderPointer(pointerY.current);
      if (lane !== hoveredLane.current) {
        hoveredLane.current = lane;
        markHoveredLane(lane === originLane.current ? null : lane);
      }
      // Hourly: derive the shift from dnd-kit's own cumulative pixel delta rather
      // than the useMouse position — the latter is stale (0,0) on the first drag
      // before any mousemove flushes, which sent the bar flying to the horizon end.
      if (gantt.range === "hourly") {
        const dayPx = (gantt.columnWidth * gantt.zoomRef.current) / 100;
        const dx = event?.delta?.x ?? 0;
        const minutes = (dx / dayPx) * 24 * 60;
        setStartAt(addMinutes(previousStartAt, minutes));
        setEndAt(previousEndAt ? addMinutes(previousEndAt, minutes) : null);
        return;
      }
      const currentDate = getDateByMousePosition(gantt, mousePosition.x);
      const originalDate = getDateByMousePosition(gantt, previousMouseX);
      const delta =
        gantt.range === "daily"
          ? getDifferenceIn(gantt.range)(currentDate, originalDate)
          : getInnerDifferenceIn(gantt.range)(currentDate, originalDate);
      setStartAt(addDays(previousStartAt, delta));
      setEndAt(previousEndAt ? addDays(previousEndAt, delta) : null);
    },
    [gantt, mousePosition.x, previousMouseX, previousStartAt, previousEndAt]
  );

  const onDragEnd = useCallback(async () => {
    const lane = laneUnderPointer(pointerY.current) ?? hoveredLane.current;
    const movedLane = lane != null && lane !== originLane.current ? lane : null;
    endLaneTracking();
    hoveredLane.current = null;
    try {
      await onMove?.(feature.id, startAt, endAt, movedLane);
    } catch {
      // The drop was refused (precedence, release gate, horizon). Put the bar back
      // where it came from — leaving it at a time the server rejected shows the
      // planner a schedule that does not exist. The handler has already explained
      // why; this is only the visual rollback.
      setStartAt(feature.startAt);
      setEndAt(feature.endAt ?? null);
    }
  }, [onMove, feature.id, feature.startAt, feature.endAt, startAt, endAt, endLaneTracking]);

  // Resize handles report time only — a resize can't change which resource runs it.
  const onResizeEnd = useCallback(
    () => onMove?.(feature.id, startAt, endAt),
    [onMove, feature.id, startAt, endAt]
  );

  const handleLeftDragMove = useCallback(() => {
    const ganttRect = gantt.ref?.current?.getBoundingClientRect();
    const x =
      mousePosition.x - (ganttRect?.left ?? 0) + scrollX - gantt.sidebarWidth;
    const newStartAt = getDateByMousePosition(gantt, x);

    setStartAt(newStartAt);
  }, [gantt, mousePosition.x, scrollX]);

  const handleRightDragMove = useCallback(() => {
    const ganttRect = gantt.ref?.current?.getBoundingClientRect();
    const x =
      mousePosition.x - (ganttRect?.left ?? 0) + scrollX - gantt.sidebarWidth;
    const newEndAt = getDateByMousePosition(gantt, x);

    setEndAt(newEndAt);
  }, [gantt, mousePosition.x, scrollX]);

  const bar = (
      <div
        data-task-id={feature.id}
        className={cn(
          "pointer-events-auto absolute top-0.5",
          onSelect && "cursor-pointer"
        )}
        onClick={onSelect ? (e) => onSelect(feature.id, e) : undefined}
        style={{
          height: "calc(var(--gantt-row-height) - 4px)",
          width: hourly ? `calc(var(--gantt-column-width) * ${widthFraction})` : Math.round(width),
          left: hourly ? `calc(var(--gantt-column-width) * ${leftFraction})` : Math.round(offset),
        }}
      >
        {onMove && resizable && (
          <DndContext
            modifiers={[restrictToHorizontalAxis]}
            onDragEnd={onResizeEnd}
            onDragMove={handleLeftDragMove}
            sensors={[mouseSensor]}
          >
            <GanttFeatureDragHelper
              date={startAt}
              direction="left"
              featureId={feature.id}
            />
          </DndContext>
        )}
        {onMove ? (
          <DndContext
            modifiers={[restrictToHorizontalAxis]}
            onDragEnd={onDragEnd}
            onDragMove={handleItemDragMove}
            onDragStart={handleItemDragStart}
            sensors={[mouseSensor]}
          >
            <GanttFeatureItemCard id={feature.id} className={cardClassName}>
              {children ?? (
                <p className="flex-1 truncate text-xs">{feature.name}</p>
              )}
            </GanttFeatureItemCard>
          </DndContext>
        ) : (
          // No onMove (e.g. viewer lacks schedule-edit permission): render a
          // static card with no drag wiring at all, so a drag attempt can't
          // visually displace a bar that will never persist.
          <Card
            className={cn(
              "h-full w-full rounded-md bg-background p-2 text-xs shadow-sm",
              cardClassName
            )}
          >
            <div className="flex h-full w-full items-center justify-between gap-2 text-left">
              {children ?? (
                <p className="flex-1 truncate text-xs">{feature.name}</p>
              )}
            </div>
          </Card>
        )}
        {onMove && resizable && (
          <DndContext
            modifiers={[restrictToHorizontalAxis]}
            onDragEnd={onResizeEnd}
            onDragMove={handleRightDragMove}
            sensors={[mouseSensor]}
          >
            <GanttFeatureDragHelper
              date={endAt ?? addRange(startAt, 2)}
              direction="right"
              featureId={feature.id}
            />
          </DndContext>
        )}
      </div>
  );

  // Bare: just the positioned bar (the lane row is the positioned parent). Wrapped:
  // the bar inside its own full-width row (one task per row).
  if (bare) return bar;
  return (
    <div
      className={cn("relative flex w-max min-w-full py-0.5", className)}
      style={{ height: "var(--gantt-row-height)" }}
    >
      {bar}
    </div>
  );
};

// Memoized: with stable feature objects + handlers, bars entering/leaving the virtualized
// window are the only ones that (un)mount on scroll — the rest skip re-render entirely.
export const GanttFeatureItem = memo(GanttFeatureItemBase);

export type GanttFeatureListGroupProps = {
  children: ReactNode;
  className?: string;
};

export const GanttFeatureListGroup: FC<GanttFeatureListGroupProps> = ({
  children,
  className,
}) => (
  <div className={className} style={{ paddingTop: "var(--gantt-row-height)" }}>
    {children}
  </div>
);

export type GanttFeatureRowProps = {
  features: GanttFeature[];
  onMove?: (id: string, startAt: Date, endAt: Date | null) => void;
  children?: (feature: GanttFeature) => ReactNode;
  className?: string;
};

export const GanttFeatureRow: FC<GanttFeatureRowProps> = ({
  features,
  onMove,
  children,
  className,
}) => {
  // Sort features by start date to handle potential overlaps
  const sortedFeatures = [...features].sort(
    (a, b) => a.startAt.getTime() - b.startAt.getTime()
  );

  // Calculate sub-row positions for overlapping features using a proper algorithm
  const featureWithPositions = [];
  const subRowEndTimes: Date[] = []; // Track when each sub-row becomes free

  for (const feature of sortedFeatures) {
    let subRow = 0;

    // Find the first sub-row that's free (doesn't overlap)
    while (
      subRow < subRowEndTimes.length &&
      subRowEndTimes[subRow] > feature.startAt
    ) {
      subRow++;
    }

    // Update the end time for this sub-row
    if (subRow === subRowEndTimes.length) {
      subRowEndTimes.push(feature.endAt);
    } else {
      subRowEndTimes[subRow] = feature.endAt;
    }

    featureWithPositions.push({ ...feature, subRow });
  }

  const maxSubRows = Math.max(1, subRowEndTimes.length);
  const subRowHeight = 36; // Base row height

  return (
    <div
      className={cn("relative", className)}
      style={{
        height: `${maxSubRows * subRowHeight}px`,
        minHeight: "var(--gantt-row-height)",
      }}
    >
      {featureWithPositions.map((feature) => (
        <div
          className="absolute w-full"
          key={feature.id}
          style={{
            top: `${feature.subRow * subRowHeight}px`,
            height: `${subRowHeight}px`,
          }}
        >
          <GanttFeatureItem {...feature} onMove={onMove}>
            {children ? (
              children(feature)
            ) : (
              <p className="flex-1 truncate text-xs">{feature.name}</p>
            )}
          </GanttFeatureItem>
        </div>
      ))}
    </div>
  );
};

export type GanttFeatureListProps = {
  className?: string;
  children: ReactNode;
};

export const GanttFeatureList: FC<GanttFeatureListProps> = ({
  className,
  children,
}) => (
  <div
    className={cn("absolute top-0 left-0 h-full w-max space-y-4", className)}
    style={{ marginTop: "var(--gantt-header-height)" }}
  >
    {children}
  </div>
);

export const GanttMarker: FC<
  GanttMarkerProps & {
    onRemove?: (id: string) => void;
    className?: string;
  }
> = memo(({ label, date, id, onRemove, className }) => {
  const gantt = useContext(GanttContext);
  const differenceIn = useMemo(
    () => getDifferenceIn(gantt.range),
    [gantt.range]
  );
  const timelineStartDate = useMemo(
    () => (gantt.boundStart ? startOfDay(gantt.boundStart) : new Date(gantt.timelineData.at(0)?.year ?? 0, 0, 1)),
    [gantt.timelineData]
  );

  // Memoize expensive calculations
  const offset = useMemo(
    () => differenceIn(date, timelineStartDate),
    [differenceIn, date, timelineStartDate]
  );
  const innerOffset = useMemo(
    () =>
      calculateInnerOffset(
        date,
        gantt.range,
        (gantt.columnWidth * gantt.zoomRef.current) / 100
      ),
    [date, gantt.range, gantt.columnWidth]
  );

  const handleRemove = useCallback(() => onRemove?.(id), [onRemove, id]);

  return (
    <div
      className="pointer-events-none absolute top-0 left-0 z-20 flex h-full select-none flex-col items-center justify-center overflow-visible"
      style={{
        width: 0,
        transform: `translateX(calc(var(--gantt-column-width) * ${offset} + ${innerOffset}px))`,
      }}
    >
      <ContextMenu>
        <ContextMenuTrigger asChild>
          <div
            className={cn(
              "group pointer-events-auto sticky top-0 flex select-auto flex-col flex-nowrap items-center justify-center whitespace-nowrap rounded-b-md bg-card px-2 py-1 text-foreground text-xs",
              className
            )}
          >
            {label}
            <span className="max-h-[0] overflow-hidden opacity-80 transition-all group-hover:max-h-[2rem]">
              {formatDate(date, "MMM dd, yyyy")}
            </span>
          </div>
        </ContextMenuTrigger>
        <ContextMenuContent>
          {onRemove ? (
            <ContextMenuItem
              className="flex items-center gap-2 text-destructive"
              onClick={handleRemove}
            >
              <TrashIcon size={16} />
              Remove marker
            </ContextMenuItem>
          ) : null}
        </ContextMenuContent>
      </ContextMenu>
      <div className={cn("h-full w-px bg-card", className)} />
    </div>
  );
});

GanttMarker.displayName = "GanttMarker";

export type GanttProviderProps = {
  range?: Range;
  zoom?: number;
  onAddItem?: (date: Date) => void;
  children: ReactNode;
  className?: string;
  // Bound the timeline to a window (e.g. the schedule horizon) instead of the fixed
  // 3-year grid — required to make the minute-scale hourly view perform + navigate.
  boundStart?: Date;
  boundEnd?: Date;
};

export const GanttProvider: FC<GanttProviderProps> = ({
  zoom = 100,
  range = "monthly",
  onAddItem,
  children,
  className,
  boundStart,
  boundEnd,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  // Live zoom, readable by handlers/helpers without making the context value change
  // identity on zoom (which would re-render every bar). Updated on each render.
  const zoomRef = useRef(zoom);
  zoomRef.current = zoom;
  const bounded = Boolean(boundStart && boundEnd);
  const boundDays = bounded
    ? Math.max(1, differenceInDays(startOfDay(boundEnd!), startOfDay(boundStart!)) + 1)
    : undefined;
  const [timelineData, setTimelineData] = useState<TimelineData>(
    createInitialTimelineData(new Date())
  );
  const [, setScrollX] = useGanttScrollX();
  const [sidebarWidth, setSidebarWidth] = useState(0);

  const headerHeight = 60;
  const rowHeight = 36;
  let columnWidth = 50;

  if (range === "monthly") {
    columnWidth = 150;
  } else if (range === "quarterly") {
    columnWidth = 100;
  } else if (range === "hourly") {
    columnWidth = 720; // wide day columns so 15–60 min tasks are visible (~0.5 px/min)
  }

  // Memoize CSS variables to prevent unnecessary re-renders
  const cssVariables = useMemo(
    () =>
      ({
        "--gantt-zoom": `${zoom}`,
        "--gantt-column-width": `${(zoom / 100) * columnWidth}px`,
        "--gantt-header-height": `${headerHeight}px`,
        "--gantt-row-height": `${rowHeight}px`,
        "--gantt-sidebar-width": `${sidebarWidth}px`,
      }) as CSSProperties,
    [zoom, columnWidth, sidebarWidth]
  );

  useEffect(() => {
    if (scrollRef.current) {
      // Bounded (horizon) mode lands on horizon-start's time-of-day (where the work
      // begins) — columns start at midnight, so scrolling to 0 would show empty
      // pre-shift hours. The unbounded 3-year grid centres on today.
      if (bounded && boundStart) {
        const dayPx = (columnWidth * zoom) / 100;
        const minutes = boundStart.getHours() * 60 + boundStart.getMinutes();
        scrollRef.current.scrollLeft = Math.max(0, (minutes / (60 * 24)) * dayPx - 48);
      } else {
        scrollRef.current.scrollLeft =
          scrollRef.current.scrollWidth / 2 - scrollRef.current.clientWidth / 2;
      }
      setScrollX(scrollRef.current.scrollLeft);
    }
    // Runs on mount and when the horizon changes — NOT on zoom (zoom is handled by the
    // zoom-to-centre effect below), so zooming no longer snaps scroll back to the start.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setScrollX, bounded, boundStart]);

  // Keep the time under the viewport CENTRE fixed while zooming (instead of resetting).
  // Deliberately useEffect, NOT useLayoutEffect: this reads scrollLeft/clientWidth, and
  // a layout-effect read runs while the just-changed column-width has dirtied layout —
  // forcing a synchronous reflow of the whole timeline every tween frame. Running after
  // paint reads clean layout (no forced reflow); the JS tween's per-frame steps are
  // small enough that the one-frame scroll catch-up isn't visible, and the centre lands
  // exactly on settle.
  const prevDayPxRef = useRef((columnWidth * zoom) / 100);
  useEffect(() => {
    const el = scrollRef.current;
    const newDayPx = (columnWidth * zoom) / 100;
    const oldDayPx = prevDayPxRef.current;
    prevDayPxRef.current = newDayPx;
    if (!el || oldDayPx === newDayPx || oldDayPx <= 0) return;
    const centreFrac = (el.scrollLeft + el.clientWidth / 2) / oldDayPx;
    el.scrollLeft = Math.max(0, centreFrac * newDayPx - el.clientWidth / 2);
    setScrollX(el.scrollLeft);
  }, [zoom, columnWidth, setScrollX]);

  // Update sidebar width when DOM is ready
  useEffect(() => {
    const updateSidebarWidth = () => {
      const sidebarElement = scrollRef.current?.querySelector(
        '[data-roadmap-ui="gantt-sidebar"]'
      );
      const newWidth = sidebarElement ? 300 : 0;
      setSidebarWidth(newWidth);
    };

    // Update immediately
    updateSidebarWidth();

    // Also update on resize or when children change
    const observer = new MutationObserver(updateSidebarWidth);
    if (scrollRef.current) {
      observer.observe(scrollRef.current, {
        childList: true,
        subtree: true,
      });
    }

    return () => {
      observer.disconnect();
    };
  }, []);

  // Fix the useCallback to include all dependencies
  const handleScroll = useCallback(
    throttle(() => {
      const scrollElement = scrollRef.current;
      if (!scrollElement) {
        return;
      }

      const { scrollLeft, scrollWidth, clientWidth } = scrollElement;
      setScrollX(scrollLeft);

      // Bounded (horizon) mode is a fixed window — never grow the timeline.
      if (bounded) {
        return;
      }

      if (scrollLeft === 0) {
        // Extend timelineData to the past
        const firstYear = timelineData[0]?.year;

        if (!firstYear) {
          return;
        }

        const newTimelineData: TimelineData = [...timelineData];
        newTimelineData.unshift({
          year: firstYear - 1,
          quarters: new Array(4).fill(null).map((_, quarterIndex) => ({
            months: new Array(3).fill(null).map((_, monthIndex) => {
              const month = quarterIndex * 3 + monthIndex;
              return {
                days: getDaysInMonth(new Date(firstYear, month, 1)),
              };
            }),
          })),
        });

        setTimelineData(newTimelineData);

        // Scroll a bit forward so it's not at the very start
        scrollElement.scrollLeft = scrollElement.clientWidth;
        setScrollX(scrollElement.scrollLeft);
      } else if (scrollLeft + clientWidth >= scrollWidth) {
        // Extend timelineData to the future
        const lastYear = timelineData.at(-1)?.year;

        if (!lastYear) {
          return;
        }

        const newTimelineData: TimelineData = [...timelineData];
        newTimelineData.push({
          year: lastYear + 1,
          quarters: new Array(4).fill(null).map((_, quarterIndex) => ({
            months: new Array(3).fill(null).map((_, monthIndex) => {
              const month = quarterIndex * 3 + monthIndex;
              return {
                days: getDaysInMonth(new Date(lastYear, month, 1)),
              };
            }),
          })),
        });

        setTimelineData(newTimelineData);

        // Scroll a bit back so it's not at the very end
        scrollElement.scrollLeft =
          scrollElement.scrollWidth - scrollElement.clientWidth;
        setScrollX(scrollElement.scrollLeft);
      }
    }, 100),
    []
  );

  useEffect(() => {
    const scrollElement = scrollRef.current;
    if (scrollElement) {
      scrollElement.addEventListener("scroll", handleScroll);
    }

    return () => {
      // Fix memory leak by properly referencing the scroll element
      if (scrollElement) {
        scrollElement.removeEventListener("scroll", handleScroll);
      }
    };
  }, [handleScroll]);

  const scrollToFeature = useCallback(
    (feature: GanttFeature) => {
      const scrollElement = scrollRef.current;
      if (!scrollElement) {
        return;
      }

      // Use the SAME origin the feature bars are positioned from: horizon start in
      // bounded mode, else the fixed 3-year grid. (Measuring from Jan 1 of the grid
      // here scrolls to a wildly wrong offset — the far right of the timeline.)
      const timelineStartDate = boundStart
        ? startOfDay(boundStart)
        : new Date(timelineData[0].year, 0, 1);

      // Calculate the horizontal offset for the feature's start date
      const offset = getOffset(feature.startAt, timelineStartDate, {
        zoomRef,
        range,
        columnWidth,
        sidebarWidth,
        headerHeight,
        rowHeight,
        onAddItem,
        placeholderLength: 2,
        timelineData,
        ref: scrollRef,
      });

      // Land a little before the feature so it isn't flush against the sidebar.
      const targetScrollLeft = Math.max(0, offset - 80);

      scrollElement.scrollTo({
        left: targetScrollLeft,
        behavior: "smooth",
      });
    },
    [timelineData, range, columnWidth, sidebarWidth, onAddItem, boundStart]
  );

  // The context value must be identity-stable across zoom (zoom lives in zoomRef, not
  // here) so a zoom step re-renders only this provider (to update the CSS variable),
  // not the whole subtree of bars. Memoized on its real deps only.
  const contextValue = useMemo<GanttContextProps>(
    () => ({
      zoomRef,
      range,
      headerHeight,
      columnWidth,
      sidebarWidth,
      rowHeight,
      onAddItem,
      timelineData,
      placeholderLength: 2,
      ref: scrollRef,
      scrollToFeature,
      boundStart,
      boundDays,
    }),
    [
      range,
      columnWidth,
      sidebarWidth,
      onAddItem,
      timelineData,
      scrollToFeature,
      boundStart,
      boundDays,
    ]
  );

  return (
    <GanttContext.Provider value={contextValue}>
    <GanttZoomContext.Provider value={zoom}>
      <div
        className={cn(
          "gantt relative isolate grid h-full w-full flex-none select-none overflow-auto rounded-sm bg-secondary",
          range,
          className
        )}
        ref={scrollRef}
        style={{
          ...cssVariables,
          gridTemplateColumns: "var(--gantt-sidebar-width) 1fr",
          // No CSS transition on --gantt-column-width: the zoom is eased in JS (a rAF
          // tween on the applied zoom in SchedulingGanttPage), and the width + the
          // zoom-to-centre scroll adjustment must land on the SAME frame. A CSS ease
          // here would lag the width behind the scroll and make the anchor drift.
        }}
      >
        {children}
      </div>
    </GanttZoomContext.Provider>
    </GanttContext.Provider>
  );
};

export type GanttTimelineProps = {
  children: ReactNode;
  className?: string;
};

export const GanttTimeline: FC<GanttTimelineProps> = ({
  children,
  className,
}) => (
  <div
    className={cn(
      "relative flex h-full w-max flex-none overflow-clip",
      className
    )}
  >
    {children}
  </div>
);

export type GanttShiftBandsProps = {
  /** Working windows (shift calendar). The complement within [rangeStart,rangeEnd]
   * — nights, weekends, non-shift hours — is shaded. */
  windows: { start: Date; end: Date }[];
  rangeStart: Date;
  rangeEnd: Date;
  className?: string;
};

/** Background shading for non-working time, so gaps in the schedule read as
 * "the shop was closed" rather than "the solver left a hole". Hourly range only. */
export const GanttShiftBands: FC<GanttShiftBandsProps> = ({
  windows,
  rangeStart,
  rangeEnd,
  className,
}) => {
  const gantt = useContext(GanttContext);
  const zoom = useContext(GanttZoomContext);
  if (gantt.range !== "hourly" || !gantt.boundStart) {
    return null;
  }
  const origin = startOfDay(gantt.boundStart);
  const dayPx = (gantt.columnWidth * zoom) / 100;
  const toPx = (d: Date) => (differenceInMinutes(d, origin) / (60 * 24)) * dayPx;

  // Non-working gaps = complement of the working windows within the horizon.
  const sorted = [...windows]
    .map((w) => ({ s: w.start, e: w.end }))
    .sort((a, b) => a.s.getTime() - b.s.getTime());
  const gaps: { s: Date; e: Date }[] = [];
  let cursor = rangeStart;
  for (const w of sorted) {
    if (w.e <= rangeStart || w.s >= rangeEnd) continue;
    const ws = w.s < rangeStart ? rangeStart : w.s;
    const we = w.e > rangeEnd ? rangeEnd : w.e;
    if (ws > cursor) gaps.push({ s: cursor, e: ws });
    if (we > cursor) cursor = we;
  }
  if (cursor < rangeEnd) gaps.push({ s: cursor, e: rangeEnd });

  return (
    <div className={cn("pointer-events-none absolute inset-0 z-0", className)}>
      {gaps.map((g, i) => {
        const left = toPx(g.s);
        const width = toPx(g.e) - toPx(g.s);
        if (width <= 0) return null;
        return (
          <div
            key={i}
            className="absolute bg-foreground/[0.055]"
            style={{
              left: Math.round(left),
              width: Math.round(width),
              top: "var(--gantt-header-height)",
              bottom: 0,
            }}
          />
        );
      })}
    </div>
  );
};

export type GanttPegLinesProps = {
  /** Task ids of ONE job's steps, in route/time order; a curve connects each
   * step's end to the next step's start. Fewer than 2 renders nothing. */
  ids: string[];
  /** Bump to re-measure after the bars move (e.g., a drag or a re-solve). */
  revision?: number;
  className?: string;
};

/** SVG peg lines linking one job's operations across rows — the "flow of this
 * order" overlay. Positions are measured from the live bars (via data-task-id),
 * so they track zoom, scroll, and moves without re-deriving the layout math. */
export const GanttPegLines: FC<GanttPegLinesProps> = ({ ids, revision, className }) => {
  const gantt = useContext(GanttContext);
  const zoom = useContext(GanttZoomContext);
  const ref = useRef<HTMLDivElement>(null);
  const [segs, setSegs] = useState<
    { x1: number; y1: number; x2: number; y2: number }[]
  >([]);
  const idKey = ids.join(",");
  // Px per day-column at the current zoom, tracked in a ref. Zoom only scales X, so
  // instead of re-measuring bars on every zoom (getBoundingClientRect forces a full
  // layout — the reflow the profiler flagged), we measure ONCE and scale the peg X
  // by dayPx/measuredDayPx. Re-measure only when the job/data/grouping changes.
  const dayPx = (gantt.columnWidth * zoom) / 100;
  const dayPxRef = useRef(dayPx);
  dayPxRef.current = dayPx;
  const measuredDayPxRef = useRef(dayPx);

  useEffect(() => {
    const container = ref.current;
    const scope = container?.parentElement;
    if (!container || !scope || ids.length < 2) {
      setSegs([]);
      return;
    }
    // Debounced so rapid changes coalesce; still relative to this overlay (scroll-safe).
    const measure = () => {
      const c = container.getBoundingClientRect();
      const boxes = ids
        .map((id) => {
          const el = scope.querySelector(`[data-task-id="${id}"]`) as HTMLElement | null;
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return { left: r.left - c.left, right: r.right - c.left, y: r.top - c.top + r.height / 2 };
        })
        .filter((b): b is { left: number; right: number; y: number } => b !== null);
      const next = [];
      for (let i = 0; i < boxes.length - 1; i++) {
        next.push({ x1: boxes[i].right, y1: boxes[i].y, x2: boxes[i + 1].left, y2: boxes[i + 1].y });
      }
      measuredDayPxRef.current = dayPxRef.current; // remember the zoom these X's are in
      setSegs(next);
    };
    const timer = window.setTimeout(measure, 60);
    return () => window.clearTimeout(timer);
    // NB: zoom is deliberately NOT a dep — zoom is handled by scaling X below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idKey, revision, gantt.range]);

  if (ids.length < 2) return null;
  // Scale measured X to the current zoom (Y is zoom-invariant). No layout reads here.
  const sx = dayPx / (measuredDayPxRef.current || 1);
  return (
    <div ref={ref} className={cn("pointer-events-none absolute inset-0 z-20", className)}>
      <svg className="h-full w-full overflow-visible text-sky-500" fill="none">
        {segs.map((s, i) => {
          const x1 = s.x1 * sx;
          const x2 = s.x2 * sx;
          return (
            <g key={i}>
              <path
                d={`M ${x1} ${s.y1} C ${x1 + 20} ${s.y1}, ${x2 - 20} ${s.y2}, ${x2} ${s.y2}`}
                stroke="currentColor"
                strokeWidth={1.5}
                strokeOpacity={0.75}
              />
              <circle cx={x2} cy={s.y2} r={2.5} fill="currentColor" />
            </g>
          );
        })}
      </svg>
    </div>
  );
};

export type GanttTodayProps = {
  className?: string;
};

export const GanttToday: FC<GanttTodayProps> = ({ className }) => {
  const label = "Today";
  const date = useMemo(() => new Date(), []);
  const gantt = useContext(GanttContext);
  const differenceIn = useMemo(
    () => getDifferenceIn(gantt.range),
    [gantt.range]
  );
  const timelineStartDate = useMemo(
    () => (gantt.boundStart ? startOfDay(gantt.boundStart) : new Date(gantt.timelineData.at(0)?.year ?? 0, 0, 1)),
    [gantt.timelineData]
  );

  // Memoize expensive calculations
  const offset = useMemo(
    () => differenceIn(date, timelineStartDate),
    [differenceIn, date, timelineStartDate]
  );
  const innerOffset = useMemo(
    () =>
      calculateInnerOffset(
        date,
        gantt.range,
        (gantt.columnWidth * gantt.zoomRef.current) / 100
      ),
    [date, gantt.range, gantt.columnWidth]
  );

  return (
    <div
      className="pointer-events-none absolute top-0 left-0 z-20 flex h-full select-none flex-col items-center justify-center overflow-visible"
      style={{
        width: 0,
        transform: `translateX(calc(var(--gantt-column-width) * ${offset} + ${innerOffset}px))`,
      }}
    >
      <div
        className={cn(
          "group pointer-events-auto sticky top-0 flex select-auto flex-col flex-nowrap items-center justify-center whitespace-nowrap rounded-b-md bg-card px-2 py-1 text-foreground text-xs",
          className
        )}
      >
        {label}
        <span className="max-h-[0] overflow-hidden opacity-80 transition-all group-hover:max-h-[2rem]">
          {formatDate(date, "MMM dd, yyyy")}
        </span>
      </div>
      <div className={cn("h-full w-px bg-card", className)} />
    </div>
  );
};
