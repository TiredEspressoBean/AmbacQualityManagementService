/**
 * Node ID minting + paste/import regeneration for DWI custom nodes.
 *
 * Background (see DIGITAL_WORK_INSTRUCTIONS_DESIGN.md decision #18):
 *
 * Every capture node in a substep's `body_blocks` carries a stable `node_id`
 * attribute. The operator response store keys off this ID, and per-execution
 * tables (`SubstepResponse`, `SubstepGateCompletion`) reference it via
 * `(step_execution, substep, node_id)` unique_together.
 *
 * Decision: client mints UUIDv7 (matches `uuid_utils.compat.uuid7` used for
 * all `SecureModel` PKs across the backend). Server validates UUID format +
 * intra-document uniqueness on `Substep.save()`.
 *
 * Regeneration is required on:
 *   - paste within the editor (would otherwise duplicate IDs)
 *   - paste across substeps (would otherwise collide across documents)
 *   - library template import (each insert is a fresh instance)
 *
 * Regeneration is NOT required on:
 *   - drag-reorder within the editor (preserves operator-response linkage)
 *   - undo a delete (ProseMirror restores the original ID, which is correct)
 *   - reload a saved document (server-issued IDs are stable)
 *
 * The set of node types that carry a `node_id` attr — the "capture nodes" —
 * is enumerated in CAPTURE_NODE_TYPES below. Content nodes (Callout, Media,
 * paragraph, heading, etc.) don't carry `node_id` and are left untouched.
 */

import { uuidv7 } from "uuidv7";

/**
 * TipTap/ProseMirror node-type names that participate in the response store
 * and therefore need a stable `node_id` attribute.
 *
 * Keep this in sync with the node library in `DIGITAL_WORK_INSTRUCTIONS_DESIGN.md`
 * (Editor & Custom Node Library → Capture nodes table).
 */
export const CAPTURE_NODE_TYPES = new Set<string>([
    "measurementSpec",
    "measurementInput",
    "attestationCheckpoint",
    "textInput",
    "choiceInput",
    "photoCapture",
    "scanInput",
    "fileCapture",
    "timer",
    "computedValue",
    "harvestedComponentCapture",
    // QMS field + 3D-annotation capture nodes. These are keyed by node_id in
    // build-captures.ts (SubstepResponse kinds: status / equipment_roles /
    // personnel_roles / signatures / defects / annotation), so each inserted
    // instance needs its own minted id — otherwise two of the same type in one
    // substep collide on (step_execution, substep, node_id).
    "qualityStatusField",
    "equipmentRolesField",
    "personnelRolesField",
    "inspectionSignatures",
    "errorTypesField",
    "partAnnotation",
]);

/**
 * Mint a fresh node_id using UUIDv7. Time-ordered so debugging tools can sort
 * by creation order without a separate timestamp; consistent with the
 * `uuid_utils.compat.uuid7` defaults on every SecureModel PK in the backend.
 */
export function newNodeId(): string {
    return uuidv7();
}

/**
 * Shape of a sample/template node passed to insertion helpers.
 * Matches the TipTap JSON node shape (`{ type, attrs, content?, marks? }`).
 */
export type TemplateNode = {
    type: string;
    attrs?: Record<string, unknown>;
    content?: TemplateNode[];
    marks?: unknown[];
};

/**
 * Return a copy of `sample` with a fresh node_id on the top-level node AND
 * recursively on any nested capture nodes within `content`. Non-capture nodes
 * are passed through unchanged (their node_id attr, if any, isn't touched).
 *
 * Use this on toolbar-insert paths so each insertion is a fresh instance.
 *
 * Idempotent for content nodes (no node_id to assign); rerunning on a
 * capture-node template just mints a new id.
 */
export function withFreshNodeId<T extends TemplateNode>(sample: T): T {
    const next: T = { ...sample };
    if (CAPTURE_NODE_TYPES.has(sample.type)) {
        next.attrs = { ...(sample.attrs ?? {}), node_id: newNodeId() };
    }
    if (Array.isArray(sample.content)) {
        next.content = sample.content.map((child) =>
            withFreshNodeId(child),
        ) as TemplateNode[];
    }
    return next;
}

/**
 * Walk a ProseMirror Slice (or any tree with `content` arrays of
 * `{ type, attrs, content? }` nodes) and regenerate node_id on every
 * capture node. Use from `transformPasted` so copy-paste — within the same
 * editor or across substeps — never produces duplicate IDs.
 *
 * The function mutates a deep clone; the input is not modified.
 *
 * Accepts any tree shape (TipTap JSON or ProseMirror Slice.toJSON output);
 * walks down `content` recursively.
 */
type RegeneratableNode = {
    type?: string;
    attrs?: Record<string, unknown> | null;
    content?: RegeneratableNode[];
};

export function regenerateNodeIds<T extends RegeneratableNode>(tree: T): T {
    const clone: T = JSON.parse(JSON.stringify(tree));
    walkAndRegenerate(clone);
    return clone;
}

function walkAndRegenerate(node: RegeneratableNode): void {
    if (node.type && CAPTURE_NODE_TYPES.has(node.type)) {
        node.attrs = { ...(node.attrs ?? {}), node_id: newNodeId() };
    }
    if (Array.isArray(node.content)) {
        for (const child of node.content) {
            walkAndRegenerate(child);
        }
    }
}