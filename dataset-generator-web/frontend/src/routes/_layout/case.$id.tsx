import {createFileRoute} from "@tanstack/react-router"
import {CasesService} from "@/client";
import {useSuspenseQuery} from "@tanstack/react-query";
import {useState} from "react";
import {ChevronDown, ChevronUp, AlertCircle} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {Button} from "@/components/ui/button";

// Interfaces
interface DocumentField {
  name: string;
  value: string;
}

interface QueryDocument {
  id: string;
  title: string;
  description: string;
  section: string;
  rank: number;
  rating: number;
  ratingReason: string;
  fields: DocumentField[];
}

interface Query {
  id: string;
  text: string;
  score: number;
  documentCount: number;
  documents: QueryDocument[];
  expanded: boolean;
}


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

    // Mock data - sostituire con dati reali dall'API
    const [queries, setQueries] = useState<Query[]>([
      {
        id: "1",
        text: "Will Google link rival searches?",
        score: 1.0,
        documentCount: 34085,
        expanded: false,
        documents: []
      },
      {
        id: "2",
        text: "Musk regrets Trump posts",
        score: 1.0,
        documentCount: 4644,
        expanded: true,
        documents: [
          {
            id: "doc1",
            title: "Elon Musk says he 'regrets' some posts he made about Donald Trump - BBC News",
            description: "The billionaire says his posts went \"too far\" after attacking the US president's planned tax and spending bill.",
            section: "Technology",
            rank: 1,
            rating: 3,
            ratingReason: "weight(content:regrets in 179) [SchemaSimilarity], result of:\nweight(content:musk in 179) [SchemaSimilarity], result of:\nweight(content:posts in 179) [SchemaSimilarity], result of:",
            fields: [
              { name: "description", value: "The billionaire says his posts went \"too far\" after attacking the US president's planned tax and spending bill." },
              { name: "section", value: "Technology" }
            ]
          }
        ]
      },
      {
        id: "3",
        text: "artificial intelligence",
        score: 1.0,
        documentCount: 1433,
        expanded: false,
        documents: []
      },
      {
        id: "4",
        text: "President Trump",
        score: 1.0,
        documentCount: 8353,
        expanded: false,
        documents: []
      },
      {
        id: "5",
        text: "covid-19",
        score: 0.0,
        documentCount: 10300,
        expanded: false,
        documents: []
      }
    ]);

    const toggleQuery = (queryId: string) => {
      setQueries(queries.map(q =>
        q.id === queryId ? { ...q, expanded: !q.expanded } : q
      ));
    };

    const updateRating = (queryId: string, docId: string, newRating: number) => {
      setQueries(queries.map(q =>
        q.id === queryId
          ? {
              ...q,
              documents: q.documents.map(doc =>
                doc.id === docId ? { ...doc, rating: newRating } : doc
              )
            }
          : q
      ));
    };

    const getScoreColor = (score: number) => {
      if (score >= 1.0) return "bg-green-600";
      if (score > 0) return "bg-yellow-600";
      return "bg-red-600";
    };

    const getRatingColor = (rating: number) => {
      if (rating >= 2) return "bg-green-600";
      if (rating === 1) return "bg-yellow-600";
      return "bg-red-600";
    };

    return (
      <div className="flex flex-col gap-6">
        <header className="sticky top-0 z-10 h-16 shrink-0 items-center gap-2 border-b px-4">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">{case_obj.title}</h1>
                    <p className="text-muted-foreground">{case_obj.description}</p>
                </div>
            </div>
        </header>

        {/* Queries List */}
        <div className="space-y-2">
          {queries.map(query => (
            <div key={query.id} className="border rounded-lg overflow-hidden">
              {/* Query Header */}
              <div
                className="flex items-center p-3 cursor-pointer hover:bg-muted/50 transition-colors"
                onClick={() => toggleQuery(query.id)}
              >
                <div className={`${getScoreColor(query.score)} text-white px-3 py-2 rounded mr-3 font-bold min-w-[60px] text-center`}>
                  {query.score.toFixed(2)}
                </div>
                <div className="flex-1 font-medium">{query.text}</div>
                <div className="mr-3 text-muted-foreground font-mono text-sm">{query.documentCount}</div>
                {query.expanded ? (
                  <ChevronUp size={20} className="text-primary" />
                ) : (
                  <ChevronDown size={20} className="text-muted-foreground" />
                )}
              </div>

              {/* Expanded Documents */}
              {query.expanded && (
                <div className="border-t bg-muted/20">
                  {query.documents.length > 0 ? (
                    <>
                      {query.documents.map(doc => (
                        <div key={doc.id} className="p-4 border-b last:border-b-0 bg-background m-2 rounded-md shadow-sm">
                          <div className="flex gap-4">
                            {/* Rating Select - Left Column */}
                            <div className="w-20 flex-shrink-0">
                              <Select
                                value={String(doc.rating)}
                                onValueChange={(value) => updateRating(query.id, doc.id, Number(value))}
                              >
                                <SelectTrigger className={`${getRatingColor(doc.rating)} text-white font-bold border-none`}>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="0">0</SelectItem>
                                  <SelectItem value="1">1</SelectItem>
                                  <SelectItem value="2">2</SelectItem>
                                  <SelectItem value="3">3</SelectItem>
                                </SelectContent>
                              </Select>
                            </div>

                            {/* Document Info - Center Column */}
                            <div className="flex-1">
                              <a
                                href="#"
                                className="text-primary hover:underline font-medium text-base mb-2 block"
                                onClick={(e) => e.preventDefault()}
                              >
                                {doc.title}
                              </a>
                              <div className="space-y-1 text-sm">
                                {doc.fields.map((field, idx) => (
                                  <div key={idx} className="text-muted-foreground">
                                    <span className="font-semibold text-foreground">{field.name}:</span> {field.value}
                                  </div>
                                ))}
                                <div className="text-muted-foreground mt-2">
                                  <span className="font-semibold text-foreground">Rank:</span> #{doc.rank}
                                </div>
                              </div>
                            </div>

                            {/* Rating Reason Tooltip - Right Column */}
                            <div className="w-8 flex-shrink-0">
                              <TooltipProvider>
                                <Tooltip delayDuration={100}>
                                  <TooltipTrigger asChild>
                                    <div className="cursor-help">
                                      <AlertCircle className="text-primary" size={20} />
                                    </div>
                                  </TooltipTrigger>
                                  <TooltipContent side="left" className="max-w-md">
                                    <div className="space-y-1">
                                      <div className="font-semibold">Matches:</div>
                                      <div className="text-xs whitespace-pre-wrap">{doc.ratingReason}</div>
                                    </div>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </div>
                          </div>
                        </div>
                      ))}

                      {/* Actions at bottom of expanded query */}
                      <div className="p-3 flex gap-2">
                        <Button variant="outline" size="sm">
                          Peek at the next page of results
                        </Button>
                        <Button variant="default" size="sm">
                          Browse {query.documentCount} Results on Solr
                        </Button>
                      </div>
                    </>
                  ) : (
                    <div className="p-8 text-center text-muted-foreground">
                      No documents available for this query
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    )
}
