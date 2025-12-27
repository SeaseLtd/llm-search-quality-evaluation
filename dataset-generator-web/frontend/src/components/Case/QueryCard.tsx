import { ChevronDown, ChevronUp } from "lucide-react";
import { RatingDetailed } from "@/client";
import DocumentCard from "./DocumentCard";

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
}

export default function QueryCard({
  query,
  titleField,
  maxRating,
  onToggle,
  onRatingChange,
}: QueryCardProps) {
  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Query Header */}
      <div
        className="flex items-center p-3 cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={onToggle}
      >
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

