from typing import List, Dict, Tuple, Optional
import math

# Each edge: (u, v, weight, market_symbol) where weight = -log(rate_after_fees)
Edge = Tuple[str, str, float, str]

def bellman_ford_negative_cycle(nodes: List[str], edges: List[Edge], max_hops:int) -> List[List[Tuple[str, str]]]:
    """
    Run Bellman-Ford up to max_hops relaxations and try to catch negative cycles.
    Returns a list of cycles as sequences of (node, market_symbol) pairs;
    the last tuple repeats the first node to close the cycle (symbol for the last step is for the last edge).
    """
    idx = {n:i for i,n in enumerate(nodes)}
    n = len(nodes)
    dist = [0.0]*n
    parent: List[Optional[int]] = [None]*n
    parent_edge: List[Optional[int]] = [None]*n  # index into edges

    # We relax up to max_hops times (not full n-1), focusing on short cycles.
    for _ in range(max_hops):
        updated = False
        for ei,(u,v,w,sym) in enumerate(edges):
            ui, vi = idx[u], idx[v]
            if dist[ui] + w < dist[vi] - 1e-15:
                dist[vi] = dist[ui] + w
                parent[vi] = ui
                parent_edge[vi] = ei
                updated = True
        if not updated:
            break

    cycles = []
    for ei,(u,v,w,sym) in enumerate(edges):
        ui, vi = idx[u], idx[v]
        if dist[ui] + w < dist[vi] - 1e-12:
            # Negative cycle detected, backtrack to get the cycle
            x = vi
            for _ in range(len(nodes)):
                x = parent[x] if parent[x] is not None else x
            start = x
            if start is None:
                continue
            cur = start
            seen = set()
            chain = []
            while True:
                if cur in seen or parent[cur] is None or parent_edge[cur] is None:
                    break
                seen.add(cur)
                pu = parent[cur]
                pe = parent_edge[cur]
                u_name = nodes[pu]
                v_name = nodes[cur]
                _,_,_, symb = edges[pe]
                chain.append((u_name, symb))
                cur = pu
                if cur == start:
                    break
            if len(chain) >= 2:
                seq = list(reversed(chain))
                first_node = seq[0][0]
                # close the cycle by appending first node again (symbol kept from last edge)
                seq.append((first_node, seq[-1][1]))
                cycles.append(seq)
    return cycles

def product_from_cycle(cycle: List[Tuple[str,str]], edges: List[Tuple[str,str,float,str]]) -> float:
    # cycle is [(A, sym1), (B, sym2), ..., (A, sym_last)]
    total = 1.0
    for i in range(len(cycle)-1):
        a, _ = cycle[i]
        b, _ = cycle[i+1]
        # find edge a->b
        rate = None
        for u,v,r,sym in edges:
            if u==a and v==b:
                rate = r
                break
        if rate is None:
            return 0.0
        total *= rate
    return total
