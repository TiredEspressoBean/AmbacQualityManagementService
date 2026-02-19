/**
 * Process Flow Validation
 * Validates process structure for completeness and correctness
 */

import type { Node, Edge } from '@xyflow/react';

export type ValidationIssue = {
  type: 'error' | 'warning';
  message: string;
  nodeId?: string;
  nodeName?: string;
};

export type ValidationResult = {
  isValid: boolean;
  errors: ValidationIssue[];
  warnings: ValidationIssue[];
  all: ValidationIssue[];
};

const DECISION_NODE_TYPES = new Set(['decision', 'DecisionNode']);
const TERMINAL_NODE_TYPES = new Set(['terminal', 'TerminalNode']);
const START_NODE_TYPES = new Set(['start', 'StartNode']);
const REWORK_NODE_TYPES = new Set(['rework', 'ReworkNode']);

/**
 * Get node name for display in validation messages
 */
function getNodeName(node: Node): string {
  return (node.data?.label as string) || (node.data?.name as string) || `Step ${node.id}`;
}

/**
 * Get step type from node
 */
function getStepType(node: Node): string {
  return (node.data?.step_type as string) || node.type || 'task';
}

/**
 * Check if node is a decision node
 */
function isDecisionNode(node: Node): boolean {
  const stepType = getStepType(node);
  return DECISION_NODE_TYPES.has(stepType) || DECISION_NODE_TYPES.has(node.type || '');
}

/**
 * Check if node is a terminal node
 */
function isTerminalNode(node: Node): boolean {
  const stepType = getStepType(node);
  return TERMINAL_NODE_TYPES.has(stepType) || TERMINAL_NODE_TYPES.has(node.type || '');
}

/**
 * Check if node is a start node
 */
function isStartNode(node: Node): boolean {
  const stepType = getStepType(node);
  return START_NODE_TYPES.has(stepType) || START_NODE_TYPES.has(node.type || '');
}

/**
 * Check if node is a rework node
 */
function isReworkNode(node: Node): boolean {
  const stepType = getStepType(node);
  return REWORK_NODE_TYPES.has(stepType) || REWORK_NODE_TYPES.has(node.type || '');
}

/**
 * Build adjacency list from edges
 */
function buildAdjacencyList(nodes: Node[], edges: Edge[]): Map<string, Set<string>> {
  const adj = new Map<string, Set<string>>();

  // Initialize all nodes
  for (const node of nodes) {
    adj.set(node.id, new Set());
  }

  // Add edges
  for (const edge of edges) {
    const neighbors = adj.get(edge.source);
    if (neighbors) {
      neighbors.add(edge.target);
    }
  }

  return adj;
}

/**
 * Find all nodes reachable from a starting node using BFS
 */
function findReachableNodes(startId: string, adj: Map<string, Set<string>>): Set<string> {
  const visited = new Set<string>();
  const queue = [startId];

  while (queue.length > 0) {
    const current = queue.shift()!;
    if (visited.has(current)) continue;
    visited.add(current);

    const neighbors = adj.get(current);
    if (neighbors) {
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          queue.push(neighbor);
        }
      }
    }
  }

  return visited;
}

/**
 * Check if all paths from a node eventually reach a terminal node
 */
function allPathsTerminate(
  nodeId: string,
  adj: Map<string, Set<string>>,
  terminalIds: Set<string>,
  memo: Map<string, boolean>
): boolean {
  // Check memo first
  if (memo.has(nodeId)) {
    return memo.get(nodeId)!;
  }

  // Terminal nodes terminate
  if (terminalIds.has(nodeId)) {
    memo.set(nodeId, true);
    return true;
  }

  const neighbors = adj.get(nodeId);

  // No outgoing edges and not terminal = doesn't terminate
  if (!neighbors || neighbors.size === 0) {
    memo.set(nodeId, false);
    return false;
  }

  // All paths must terminate
  // Mark as visiting to detect cycles
  memo.set(nodeId, false);

  let allTerminate = true;
  for (const neighbor of neighbors) {
    if (!allPathsTerminate(neighbor, adj, terminalIds, memo)) {
      allTerminate = false;
      break;
    }
  }

  memo.set(nodeId, allTerminate);
  return allTerminate;
}

/**
 * Validate a process flow
 */
export function validateProcessFlow(nodes: Node[], edges: Edge[]): ValidationResult {
  const issues: ValidationIssue[] = [];

  if (nodes.length === 0) {
    issues.push({
      type: 'error',
      message: 'Process has no steps',
    });
    return {
      isValid: false,
      errors: issues,
      warnings: [],
      all: issues,
    };
  }

  const _nodeMap = new Map(nodes.map(n => [n.id, n]));

  // Find start nodes
  const startNodes = nodes.filter(isStartNode);
  if (startNodes.length === 0) {
    issues.push({
      type: 'error',
      message: 'Process must have a Start step',
    });
  } else if (startNodes.length > 1) {
    issues.push({
      type: 'error',
      message: `Process has ${startNodes.length} Start steps (should have exactly 1)`,
      nodeId: startNodes[1].id,
      nodeName: getNodeName(startNodes[1]),
    });
  }

  // Find terminal nodes
  const terminalNodes = nodes.filter(isTerminalNode);
  const terminalIds = new Set(terminalNodes.map(n => n.id));

  if (terminalNodes.length === 0) {
    issues.push({
      type: 'error',
      message: 'Process must have at least one Terminal step',
    });
  }

  // Build adjacency list
  const adj = buildAdjacencyList(nodes, edges);

  // Build reverse adjacency (incoming edges)
  const reverseAdj = new Map<string, Set<string>>();
  for (const node of nodes) {
    reverseAdj.set(node.id, new Set());
  }
  for (const edge of edges) {
    reverseAdj.get(edge.target)?.add(edge.source);
  }

  // Check for orphan nodes (no connections at all, except start can have no incoming)
  for (const node of nodes) {
    const outgoing = adj.get(node.id)?.size || 0;
    const incoming = reverseAdj.get(node.id)?.size || 0;

    if (isStartNode(node)) {
      // Start nodes should have outgoing but no incoming
      if (outgoing === 0) {
        issues.push({
          type: 'error',
          message: `Start step "${getNodeName(node)}" has no outgoing connections`,
          nodeId: node.id,
          nodeName: getNodeName(node),
        });
      }
    } else if (isTerminalNode(node)) {
      // Terminal nodes should have incoming but no outgoing
      if (incoming === 0) {
        issues.push({
          type: 'error',
          message: `Terminal step "${getNodeName(node)}" has no incoming connections`,
          nodeId: node.id,
          nodeName: getNodeName(node),
        });
      }
    } else {
      // Other nodes should have both
      if (outgoing === 0 && incoming === 0) {
        issues.push({
          type: 'error',
          message: `Step "${getNodeName(node)}" is not connected to the process`,
          nodeId: node.id,
          nodeName: getNodeName(node),
        });
      } else if (incoming === 0) {
        issues.push({
          type: 'warning',
          message: `Step "${getNodeName(node)}" has no incoming connections (unreachable)`,
          nodeId: node.id,
          nodeName: getNodeName(node),
        });
      } else if (outgoing === 0) {
        issues.push({
          type: 'warning',
          message: `Step "${getNodeName(node)}" has no outgoing connections (dead end)`,
          nodeId: node.id,
          nodeName: getNodeName(node),
        });
      }
    }
  }

  // Check decision nodes have both pass and fail edges
  const decisionNodes = nodes.filter(isDecisionNode);
  for (const node of decisionNodes) {
    const outgoingEdges = edges.filter(e => e.source === node.id);
    const hasPass = outgoingEdges.some(e => e.sourceHandle === 'pass' || !e.sourceHandle);
    const hasFail = outgoingEdges.some(e => e.sourceHandle === 'fail');

    if (!hasPass && !hasFail) {
      issues.push({
        type: 'error',
        message: `Decision step "${getNodeName(node)}" has no outgoing connections`,
        nodeId: node.id,
        nodeName: getNodeName(node),
      });
    } else if (!hasPass) {
      issues.push({
        type: 'error',
        message: `Decision step "${getNodeName(node)}" is missing Pass connection`,
        nodeId: node.id,
        nodeName: getNodeName(node),
      });
    } else if (!hasFail) {
      issues.push({
        type: 'error',
        message: `Decision step "${getNodeName(node)}" is missing Fail connection`,
        nodeId: node.id,
        nodeName: getNodeName(node),
      });
    }
  }

  // Check rework nodes have max_visits configured
  const reworkNodes = nodes.filter(isReworkNode);
  for (const node of reworkNodes) {
    const maxVisits = node.data?.max_visits as number | undefined;
    if (!maxVisits || maxVisits <= 0) {
      issues.push({
        type: 'warning',
        message: `Rework step "${getNodeName(node)}" has no max visits limit configured`,
        nodeId: node.id,
        nodeName: getNodeName(node),
      });
    }
  }

  // Check all nodes are reachable from start (if start exists)
  if (startNodes.length === 1) {
    const reachable = findReachableNodes(startNodes[0].id, adj);
    for (const node of nodes) {
      if (!reachable.has(node.id) && !isStartNode(node)) {
        // Don't duplicate warning if we already flagged no incoming
        const hasIncoming = (reverseAdj.get(node.id)?.size || 0) > 0;
        if (hasIncoming) {
          issues.push({
            type: 'warning',
            message: `Step "${getNodeName(node)}" is not reachable from Start`,
            nodeId: node.id,
            nodeName: getNodeName(node),
          });
        }
      }
    }

    // Check all paths terminate
    if (terminalNodes.length > 0) {
      const memo = new Map<string, boolean>();
      if (!allPathsTerminate(startNodes[0].id, adj, terminalIds, memo)) {
        // Find specific non-terminating paths
        for (const node of nodes) {
          if (reachable.has(node.id) && !isTerminalNode(node)) {
            const nodeTerminates = memo.get(node.id);
            if (nodeTerminates === false) {
              const outgoing = adj.get(node.id)?.size || 0;
              if (outgoing === 0) {
                // Already flagged as dead end
                continue;
              }
              // Only flag if not already flagged
              const alreadyFlagged = issues.some(i => i.nodeId === node.id);
              if (!alreadyFlagged) {
                issues.push({
                  type: 'warning',
                  message: `Some paths through "${getNodeName(node)}" don't reach a Terminal step`,
                  nodeId: node.id,
                  nodeName: getNodeName(node),
                });
              }
            }
          }
        }
      }
    }
  }

  // Separate errors and warnings
  const errors = issues.filter(i => i.type === 'error');
  const warnings = issues.filter(i => i.type === 'warning');

  return {
    isValid: errors.length === 0,
    errors,
    warnings,
    all: issues,
  };
}
