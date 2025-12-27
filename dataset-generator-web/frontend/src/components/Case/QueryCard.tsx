import { ChevronDown, ChevronUp } from "lucide-react";
import { RatingDetailed } from "@/client";
import DocumentCard from "./DocumentCard";
import RatingSelect from "./RatingSelect";

interface QueryCardProps {
  query: {
    query_id: string;
    query: string;
    ratings: Array<RatingDetailed> | null;
    expanded: boolean;
  };
  titleField: string;
  maxRating: number;
  onToggle: () => void;
  onRatingChange: (docId: string, newRating: number) => void;
  updatingRatings: Set<string>;
  getRatingKey: (docId: string) => string;
}

// Calculate average rating for a query
const calculateAverageRating = (ratings: Array<RatingDetailed> | null): number => {
  if (!ratings || ratings.length === 0) return 0;

  const sum = ratings.reduce((acc, rating) => {
    const ratingValue = rating.user_rating ?? rating.llm_rating ?? 0;
    return acc + ratingValue;
  }, 0);

  return sum / ratings.length;
};

export default function QueryCard({
  query,
  titleField,
  maxRating,
  onToggle,
  onRatingChange,
  updatingRatings,
  getRatingKey,
}: QueryCardProps) {
  const averageRating = calculateAverageRating(query.ratings);

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Query Header */}
      <div
        className="flex items-center gap-3 p-3 cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={onToggle}
      >
        {/* Average Rating Badge */}
        <RatingSelect
          readonly
          value={averageRating}
          maxRating={maxRating}
        />
        <div className="flex-1 font-medium">{query.query}</div>
        {query.expanded ? (
          <ChevronUp size={20} className="text-primary" />
        ) : (
          <ChevronDown size={20} className="text-muted-foreground" />
        )}
      </div>

      {/* Expanded Documents */}
      {query.expanded && (
        <div className="border-t bg-muted/20">
          {query.ratings && query.ratings.length > 0 ? (
            <>
              {query.ratings.map((rating: RatingDetailed) => (
                <DocumentCard
                  key={rating.document.document_id}
                  rating={rating}
                  titleField={titleField}
                  maxRating={maxRating}
                  onRatingChange={(newRating) => onRatingChange(rating.document.document_id, newRating)}
                  isLoading={updatingRatings.has(getRatingKey(rating.document.document_id))}
                />
              ))}
            </>
          ) : (
            <div className="p-8 text-center text-muted-foreground">
              No documents available for this query
            </div>
          )}
        </div>
      )}
    </div>
  );
}

