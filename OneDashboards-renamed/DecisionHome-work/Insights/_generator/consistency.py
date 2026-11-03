"""One number, one definition: rebind copied custom visuals whose source bindings disagree with the story measures.

Each fix names the KPI conflict it closes (seen side by side in the published story, 2026-11-03):
- Budget Risk Forecast summed the raw FactCost[Cost] column over every cost type (budget + actual + EAC + benefits)
  -> P50 EUR 6.9M against an EAC of EUR 2.3M. Bound to the story EAC per cost category instead.
- Portfolio 360 ROI summed per-project ROI percentages -> 1.28x next to a 3.7x value ratio. Bound to Story | Net ROI.
- Benefits Realization showed an earned-benefit proxy (benefits x % done) as 'realised' while the cards say 'Not
  recorded'. Bound to the recorded actual benefits and the planned benefits at completion.
- KPI Grid date slicers (default: start after 8 Jan 2026) filtered the page headline -> 11 active projects there,
  15 everywhere else. The slicers now filter the grid only.
"""
from pbir import M, P

REBIND = {  # visualType prefix -> {data role: story measure}
    "bfusionBudgetRiskForecast": {"cost": "Story | Finance EAC"},
    "bfusionPortfolio360": {"roi": "Story | Net ROI"},
    "bfusionBenefitsRealization": {"realizedBenefits": "Story | Benefits Actual",
                                   "plannedBenefits": "Story | Benefits At Completion"},
}
HEADLINE_FREE_SLICERS = {("DimProject", "EstimatedStart"), ("DimProject", "EstimatedEnd")}


def _rebind(v, roles):
    qs = v["query"]["queryState"]
    for role, measure in roles.items():
        old = qs[role]["projections"][0]
        new = P(M(measure))
        for k in ("displayName", "active"):
            if k in old:
                new[k] = old[k]
        qs[role]["projections"] = [new]


def _field(vc):
    pr = vc.get("visual", {}).get("query", {}).get("queryState", {}).get("Values", {}).get("projections", [{}])[0]
    f = pr.get("field", {})
    col = f.get("Column") or f.get("Measure") or {}
    return col.get("Expression", {}).get("SourceRef", {}).get("Entity"), col.get("Property")


def _free_headline(pg):
    """Date slicers on this page stop filtering the headline card (it states the portfolio-wide figures)."""
    vis = pg.visuals
    slicers = [vc["name"] for vc in vis if vc.get("visual", {}).get("visualType") == "slicer"
               and _field(vc) in HEADLINE_FREE_SLICERS]
    heads = [vc["name"] for vc in vis if vc.get("visual", {}).get("visualType") == "card"
             and (_field(vc)[1] or "").endswith("Headline")]
    if not (slicers and heads):
        return
    links = pg.page.setdefault("visualInteractions", [])
    for s_ in slicers:
        for h in heads:
            if not any(x["source"] == s_ and x["target"] == h for x in links):
                links.append({"source": s_, "target": h, "type": "NoFilter"})


def apply(built):
    for pg in built:
        for vc in pg.visuals:
            v = vc.get("visual") or {}
            for prefix, roles in REBIND.items():
                if v.get("visualType", "").startswith(prefix):
                    _rebind(v, roles)
        _free_headline(pg)


def errors(built):
    out = []
    for pg in built:
        for vc in pg.visuals:
            v = vc.get("visual") or {}
            for prefix, roles in REBIND.items():
                if v.get("visualType", "").startswith(prefix):
                    qs = v["query"]["queryState"]
                    for role, measure in roles.items():
                        got = qs[role]["projections"][0]["field"].get("Measure", {}).get("Property")
                        if got != measure:
                            out.append(f"CONSISTENCY {pg.display}: {prefix}.{role} bound to {got!r}, not {measure!r}")
    return out
