import { RatingDetailed } from "@/client";
import RatingSelect from "./RatingSelect";
import RatingExplanationTooltip from "./RatingExplanationTooltip";

interface DocumentCardProps {
  rating: RatingDetailed;
  titleField: string;
  maxRating: number;
  onRatingChange: (newRating: number) => void;
}

export default function DocumentCard({
  rating,
  titleField,
  maxRating,
  onRatingChange,
}: DocumentCardProps) {
  return (
    <div className="p-4 border-b last:border-b-0 bg-background m-2 rounded-md shadow-sm">
      <div className="flex gap-4">
        {/* Rating Select - Left Column */}
        <RatingSelect
          rating={rating}
          maxRating={maxRating}
          onChange={onRatingChange}
        />

        {/* Document Info - Center Column */}
        <div className="flex-1">
          <a
            href="#"
            className="text-primary hover:underline font-medium text-base mb-2 block"
            onClick={(e) => e.preventDefault()}
          >
            {rating.document.fields?.[titleField] || 'No title'}
          </a>
          <div className="space-y-1 text-sm">
            {rating.document.fields && Object.entries(rating.document.fields)
              .filter(([key]) => key !== titleField)
              .map(([key, value]) => (
                <div key={key} className="text-muted-foreground">
                  <span className="font-semibold text-foreground">{key}:</span> {String(value)}
                </div>
              ))}
          </div>
        </div>

        {/* Rating Explanation Tooltip - Right Column */}
        <RatingExplanationTooltip explanation={rating.explanation} />
      </div>
    </div>
  );
}

