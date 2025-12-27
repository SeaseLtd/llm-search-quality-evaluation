import {createFileRoute} from "@tanstack/react-router"
import {CasesService, QueryPublic, RatingDetailed} from "@/client";
import {useSuspenseQuery} from "@tanstack/react-query";
import {useState} from "react";
import QueryCard from "@/components/Case/QueryCard";

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

    const maxRating = case_obj.max_rating_value ?? 2;
    const titleField = case_obj.document_title_field_name ?? 'title';

    const [queries, setQueries] = useState<QueryWithExpanded[]>(
      case_obj.queries ? case_obj.queries.map(q => ({ ...q, expanded: false })) : []
    );

    const toggleQuery = (queryId: string) => {
      setQueries(queries.map(q =>
        q.query_id === queryId ? { ...q, expanded: !q.expanded } : q
      ));
    };

    const updateRating = (queryId: string, docId: string, newRating: number) => {
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
    };


    return (
      <div className="flex flex-col h-full">
        <header className="shrink-0 border-b px-6 py-4 bg-background">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold tracking-tight">{case_obj.title}</h1>
              <p className="text-muted-foreground">{case_obj.description}</p>
            </div>
          </div>
        </header>

        <div className="page-content flex-1 overflow-y-auto px-6 py-4">
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
              />
            ))}
          </div>
        </div>
      </div>
    )
}
