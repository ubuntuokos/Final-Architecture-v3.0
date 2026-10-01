"""FA3 Objective Coordination & Dependency Intelligence reference core.

Zero-authority: derives coordination state only; never executes or authorizes work.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

TERMINAL={"COMPLETED","FAILED","CANCELLED"}
REQUIRED={"REQUIRES","SEQUENCE_BEFORE","HANDOFF_AFTER","APPROVAL_BEFORE","ARTIFACT_BEFORE","EVIDENCE_BEFORE","RESOURCE_BEFORE"}

@dataclass(frozen=True)
class Dependency:
    source: str
    target: str
    relation: str="REQUIRES"

@dataclass
class Objective:
    nodes: Dict[str,str]
    dependencies: List[Dependency]=field(default_factory=list)
    explicit_blockers: Dict[str,List[str]]=field(default_factory=dict)

class CoordinationError(ValueError): pass

def _required_edges(obj: Objective):
    return [(d.source,d.target) for d in obj.dependencies if d.relation in REQUIRED]

def validate(obj: Objective):
    unknown=[(a,b) for a,b in _required_edges(obj) if a not in obj.nodes or b not in obj.nodes]
    if unknown: raise CoordinationError(f"unknown dependency nodes: {unknown}")
    graph={n:[] for n in obj.nodes}
    for a,b in _required_edges(obj): graph[b].append(a)
    visiting=set(); visited=set()
    def walk(n):
        if n in visiting: raise CoordinationError("required dependency cycle")
        if n in visited:return
        visiting.add(n)
        for x in graph[n]: walk(x)
        visiting.remove(n); visited.add(n)
    for n in graph: walk(n)

def blockers(obj: Objective)->Dict[str,List[str]]:
    validate(obj); out={n:list(obj.explicit_blockers.get(n,[])) for n in obj.nodes}
    for pre,node in _required_edges(obj):
        if obj.nodes[pre]!="COMPLETED": out[node].append(f"DEPENDENCY:{pre}")
    return {n:v for n,v in out.items() if v}

def ready(obj: Objective)->List[str]:
    blocked=blockers(obj)
    return sorted(n for n,s in obj.nodes.items() if s=="PENDING" and n not in blocked)

def downstream_impact(obj: Objective, failed: str)->List[str]:
    validate(obj); rev={n:set() for n in obj.nodes}
    for pre,node in _required_edges(obj): rev[pre].add(node)
    seen=set(); stack=list(rev.get(failed,()))
    while stack:
        n=stack.pop()
        if n in seen: continue
        seen.add(n); stack.extend(rev[n])
    return sorted(seen)

def dependency_batches(obj: Objective)->List[List[str]]:
    validate(obj); remaining=set(obj.nodes); done={n for n,s in obj.nodes.items() if s=="COMPLETED"}; batches=[]
    while remaining:
        batch=sorted(n for n in remaining if all(pre in done or pre not in remaining for pre,node in _required_edges(obj) if node==n))
        if not batch: raise CoordinationError("unresolvable dependency graph")
        batches.append(batch); done.update(batch); remaining.difference_update(batch)
    return batches

def movable_forward(obj: Objective, blocked_node: str)->List[str]:
    impact=set(downstream_impact(obj,blocked_node))|{blocked_node}
    return [n for n in ready(obj) if n not in impact]
