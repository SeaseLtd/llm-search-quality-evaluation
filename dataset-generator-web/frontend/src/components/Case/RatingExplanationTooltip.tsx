import { AlertCircle } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface RatingExplanationTooltipProps {
  explanation: string | null | undefined;
}

export default function RatingExplanationTooltip({
  explanation,
}: RatingExplanationTooltipProps) {
  if (!explanation) {
    return <div className="w-8 shrink-0" />;
  }

  return (
    <div className="w-8 shrink-0">
      <TooltipProvider>
        <Tooltip delayDuration={100}>
          <TooltipTrigger asChild>
            <div className="cursor-help">
              <AlertCircle className="text-primary" size={20} />
            </div>
          </TooltipTrigger>
          <TooltipContent side="left" className="max-w-md">
            <div className="space-y-1">
              <div className="font-semibold">Rating Explanation:</div>
              <div className="text-xs whitespace-pre-wrap">{explanation}</div>
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  );
}

