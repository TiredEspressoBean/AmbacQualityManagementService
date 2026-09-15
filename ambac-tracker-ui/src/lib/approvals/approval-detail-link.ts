/**
 * "Where do I send someone who clicks this approval?"
 *
 * One implementation, because there were two and both were wrong in different
 * ways. ApprovalsOverviewPage mismatched `document` and `process`;
 * ApprovalsHistoryPage mismatched those AND omitted the three change-control
 * types altogether, so every PCR/PCO/PCN row fell through as well.
 *
 * The trap: the key is `content_object_info.type`, which the serializer fills
 * from `obj.content_type.model` — Django's lowercased MODEL CLASS name, not an
 * English singular. The models are `Documents` and `Processes`, so the values
 * are "documents" and "processes". Both switches were written against
 * "document" and "process", missed, and fell through to the generic
 * `/details/{model}/{id}` page — which for a document has no Approval tab, so
 * an approver arriving from their own approvals list could not approve.
 *
 * Verified against the live ContentType table rather than guessed: capa,
 * processchangerequest, processchangeorder and processchangenotice all match
 * their class names already; documents and processes were the two that did not.
 *
 * Both spellings are accepted so that renaming a model to the singular — or
 * adding a differently-named one — degrades to a working link rather than a
 * silent fall-through.
 */

/** ContentType.model (and tolerated singular aliases) -> detail route. */
const ROUTE_BY_CONTENT_TYPE: Record<string, (id: string) => string> = {
    // Model class is `Documents`, so ContentType.model is "documents".
    documents: (id) => `/documents/${id}`,
    document: (id) => `/documents/${id}`,

    capa: (id) => `/quality/capas/${id}`,

    // Model class is `Processes`.
    processes: (id) => `/process-flow?processId=${id}`,
    process: (id) => `/process-flow?processId=${id}`,

    processchangerequest: (id) => `/quality/change-control/pcrs/${id}`,
    processchangeorder: (id) => `/quality/change-control/pcos/${id}`,
    processchangenotice: (id) => `/quality/change-control/pcns/${id}`,
};

type ApprovalLike = {
    content_object_info?: { type?: string | null } | null;
    object_id?: string | number | null;
};

export function getApprovalDetailLink(approval: ApprovalLike): string {
    const contentType = approval.content_object_info?.type?.toLowerCase() ?? "";
    const objectId = String(approval.object_id ?? "");

    const route = ROUTE_BY_CONTENT_TYPE[contentType];
    if (route) return route(objectId);

    // Unmapped type: the generic model detail page. It renders the record but
    // offers none of the type's own actions, so anything routed here that a
    // user needs to ACT on belongs in the map above instead.
    return `/details/${contentType}/${objectId}`;
}
