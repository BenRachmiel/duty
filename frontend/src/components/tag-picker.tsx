import { useState } from "react";
import { Icon } from "@/components/ui/icon";

import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import type { Tag } from "@/types";

interface TagPickerProps {
  tags: Tag[];
  onSelect: (tag: Tag) => void;
}

export function TagPicker({ tags, onSelect }: TagPickerProps) {
  const [open, setOpen] = useState(false);

  if (tags.length === 0) return null;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="h-7 px-2 text-xs">
          <Icon name="add" className="mr-1 text-[0.75rem]" />
          tag
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-40 p-1" align="start">
        <div className="max-h-48 overflow-y-auto">
          {tags.map((tag) => (
            <button
              key={tag.id}
              className="w-full rounded-sm px-2 py-1.5 text-left text-sm hover:bg-accent hover:text-accent-foreground"
              onClick={() => {
                onSelect(tag);
                setOpen(false);
              }}
            >
              {tag.name}
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}
