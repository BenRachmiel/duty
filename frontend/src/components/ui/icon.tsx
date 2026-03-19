import { cn } from "@/lib/utils"

interface IconProps extends React.HTMLAttributes<HTMLSpanElement> {
  name: string
}

export function Icon({ name, className, ...props }: IconProps) {
  return (
    <span
      data-slot="icon"
      className={cn("material-symbols-outlined", className)}
      {...props}
    >
      {name}
    </span>
  )
}
