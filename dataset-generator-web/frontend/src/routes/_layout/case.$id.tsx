import {createFileRoute} from "@tanstack/react-router"
import {CasesService, QueryPublic, RatingDetailed, RatingsService, type ApiError} from "@/client";
import {useSuspenseQuery, useMutation} from "@tanstack/react-query";
import {useState} from "react";
import QueryCard from "@/components/Case/QueryCard";
import useCustomToast from "@/hooks/useCustomToast";
import {handleError} from "@/utils";

// Interfaces
type QueryWithExpanded = QueryPublic & { expanded: boolean };


function getCaseDetailsQueryOptions(id: string) {
    return {
        queryFn: () => CasesService.readCase({id: id}),
        queryKey: ["case_details", id],
    }
}



export const Route = createFileRoute("/_layout/case/$id")({
  component: Case,
  head: () => ({
    meta: [
      {
        title: "Cases - Dataset Generator",
      },
    ],
  }),
})


function Case() {
    const { id } = Route.useParams()
    const { data: case_obj } = useSuspenseQuery(getCaseDetailsQueryOptions(id))
    const { showErrorToast } = useCustomToast()

    const maxRating = case_obj.max_rating_value ?? 2;
    const titleField = case_obj.document_title_field_name ?? 'title';

    const [queries, setQueries] = useState<QueryWithExpanded[]>(
      case_obj.queries ? case_obj.queries.map(q => ({ ...q, expanded: false })) : []
    );

    // Track which ratings are currently being updated (for loading state)
    const [updatingRatings, setUpdatingRatings] = useState<Set<string>>(new Set());

    // Store original rating values before update (for rollback on error)
    const [originalRatings, setOriginalRatings] = useState<Map<string, RatingDetailed>>(new Map());

    // Helper to create a unique key for a rating
    const getRatingKey = (queryId: string, docId: string) => `${queryId}-${docId}`;

    // Mutation to update rating on server
    const updateRatingMutation = useMutation({
      mutationFn: ({ queryId, documentId, rating }: { queryId: string; documentId: string; rating: number }) =>
        RatingsService.updateUserRating({
          queryId: queryId,
          documentId: documentId,
          requestBody: {
            query_id: queryId,
            document_id: documentId,
            user_rating: rating
          }
        }),
      onSuccess: (data, variables) => {
        const ratingKey = getRatingKey(variables.queryId, variables.documentId);

        // Update with the server response to ensure synchronization
        setQueries(queries => queries.map(q =>
          q.query_id === variables.queryId
            ? {
                ...q,
                ratings: q.ratings!.map((r: RatingDetailed) =>
                  r.document.document_id === variables.documentId ? data : r
                )
              }
            : q
        ));

        // Remove from original ratings map
        setOriginalRatings(prev => {
          const newMap = new Map(prev);
          newMap.delete(ratingKey);
          return newMap;
        });

        // Remove from updating set
        setUpdatingRatings(prev => {
          const newSet = new Set(prev);
          newSet.delete(ratingKey);
          return newSet;
        });
      },
      onError: (error, variables) => {
        const ratingKey = getRatingKey(variables.queryId, variables.documentId);
        const originalRating = originalRatings.get(ratingKey);

        // Revert to original value on error
        if (originalRating) {
          setQueries(queries => queries.map(q =>
            q.query_id === variables.queryId
              ? {
                  ...q,
                  ratings: q.ratings!.map((r: RatingDetailed) =>
                    r.document.document_id === variables.documentId ? originalRating : r
                  )
                }
              : q
          ));

          // Remove from original ratings map
          setOriginalRatings(prev => {
            const newMap = new Map(prev);
            newMap.delete(ratingKey);
            return newMap;
          });
        }

        // Remove from updating set
        setUpdatingRatings(prev => {
          const newSet = new Set(prev);
          newSet.delete(ratingKey);
          return newSet;
        });

        // Show error message
        handleError.call(showErrorToast, error as ApiError);
      },
    });

    const toggleQuery = (queryId: string) => {
      setQueries(queries.map(q =>
        q.query_id === queryId ? { ...q, expanded: !q.expanded } : q
      ));
    };

    const updateRating = (queryId: string, docId: string, newRating: number) => {
      const ratingKey = getRatingKey(queryId, docId);

      // Save original rating before update
      const originalRating = queries
        .find(q => q.query_id === queryId)
        ?.ratings?.find(r => r.document.document_id === docId);

      if (originalRating) {
        setOriginalRatings(prev => new Map(prev).set(ratingKey, originalRating));
      }

      // Add to updating set
      setUpdatingRatings(prev => new Set(prev).add(ratingKey));

      // Update UI optimistically
      setQueries(queries.map(q =>
        q.query_id === queryId
          ? {
              ...q,
              ratings: q.ratings!.map((r: RatingDetailed) =>
                r.document.document_id === docId ? { ...r, user_rating: newRating } : r
              )
            }
          : q
      ));

      // Update server asynchronously
      updateRatingMutation.mutate({
        queryId: queryId,
        documentId: docId,
        rating: newRating
      });
    };


    return (
      <div className="flex flex-col h-full">
        <header className="shrink-0 border-b px-6 py-2 bg-background">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">{case_obj.title}</h1>
            </div>
          </div>
        </header>

        <div className="page-content flex-1 overflow-y-auto px-6 py-2">
          {/* Queries List */}
          <div className="space-y-2">
            {queries.map(query => (
              <QueryCard
                key={query.query_id}
                query={query}
                titleField={titleField}
                maxRating={maxRating}
                onToggle={() => toggleQuery(query.query_id)}
                onRatingChange={(docId, newRating) => updateRating(query.query_id, docId, newRating)}
                updatingRatings={updatingRatings}
                getRatingKey={(docId) => getRatingKey(query.query_id, docId)}
              />
            ))}
          </div>
        </div>
      </div>
    )
}
