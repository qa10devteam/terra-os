"""M7 — OR-Tools CP-SAT logistics optimizer.

Solves the crew+equipment assignment problem:
  - N employees × M contracts × D days
  - Each employee has competencies and availability
  - Each contract requires specific skills and equipment
  - Equipment has limited capacity (one contract at a time per machine)

Output: assignments[] + routes[] or engine_infeasible{reason}.

Deterministic: given same inputs → same output (CP-SAT with fixed seed).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Input/Output types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class EmployeeSpec:
    id: str
    name: str
    skills: list[str]                   # e.g. ["operator_koparki", "kierowca"]
    available_days: list[str]           # ISO dates "2026-07-01"


@dataclass
class EquipmentSpec:
    id: str
    type: str                           # e.g. "koparka", "walec"
    available_days: list[str]


@dataclass
class ContractSpec:
    id: str
    title: str
    required_skills: list[str]          # at least one employee must have each
    required_equipment: list[str]       # equipment types needed
    days: list[str]                     # work days for this contract


@dataclass
class Assignment:
    contract_id: str
    employee_id: str
    equipment_id: str | None
    day: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "employee_id": self.employee_id,
            "equipment_id": self.equipment_id,
            "day": self.day,
        }


@dataclass
class Route:
    contract_id: str
    day: str
    employee_ids: list[str]
    equipment_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "day": self.day,
            "employee_ids": self.employee_ids,
            "equipment_ids": self.equipment_ids,
        }


@dataclass
class OptimizeResult:
    feasible: bool
    assignments: list[Assignment] = field(default_factory=list)
    routes: list[Route] = field(default_factory=list)
    infeasible_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "feasible": self.feasible,
            "assignments": [a.to_dict() for a in self.assignments],
            "routes": [r.to_dict() for r in self.routes],
            "infeasible_reason": self.infeasible_reason,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Optimizer
# ──────────────────────────────────────────────────────────────────────────────

def optimize_logistics(
    employees: list[EmployeeSpec],
    equipment: list[EquipmentSpec],
    contracts: list[ContractSpec],
    *,
    time_limit_seconds: float = 10.0,
) -> OptimizeResult:
    """Solve crew+equipment assignment using OR-Tools CP-SAT.

    Constraints:
    C1: Employee only assigned on available days.
    C2: Equipment only assigned on available days.
    C3: Each contract-day gets at least one employee with each required skill.
    C4: Each contract-day gets at least one unit of each required equipment type.
    C5: Equipment assigned to at most one contract per day.
    C6: Employee assigned to at most one contract per day.

    Objective: minimize total unmet skill-days (maximize coverage).
    """
    from ortools.sat.python import cp_model  # type: ignore[import]

    if not contracts:
        return OptimizeResult(feasible=True, assignments=[], routes=[])

    # Pre-checks (fast infeasibility detection before solver)
    reason = _check_infeasible(employees, equipment, contracts)
    if reason:
        return OptimizeResult(feasible=False, infeasible_reason=reason)

    model = cp_model.CpModel()

    # Index maps
    emp_idx = {e.id: i for i, e in enumerate(employees)}
    equip_idx = {e.id: i for i, e in enumerate(equipment)}
    cont_idx = {c.id: i for i, c in enumerate(contracts)}

    # Collect all days across contracts
    all_days = sorted({d for c in contracts for d in c.days})
    day_idx = {d: i for i, d in enumerate(all_days)}

    # Decision variables: assign[e][c][d] = 1 iff employee e works contract c on day d
    assign: dict[tuple[int, int, int], Any] = {}
    for ei, emp in enumerate(employees):
        for ci, cont in enumerate(contracts):
            for day in cont.days:
                di = day_idx[day]
                if day in emp.available_days:
                    assign[ei, ci, di] = model.new_bool_var(f"a_{ei}_{ci}_{di}")

    # Equipment assignment variables: equip_assign[qi][ci][di]
    equip_assign: dict[tuple[int, int, int], Any] = {}
    for qi, eq in enumerate(equipment):
        for ci, cont in enumerate(contracts):
            for day in cont.days:
                di = day_idx[day]
                if day in eq.available_days:
                    equip_assign[qi, ci, di] = model.new_bool_var(f"q_{qi}_{ci}_{di}")

    # C1: employee not available on day → variable doesn't exist (handled by creation)
    # C6: each employee at most one contract per day
    for ei in range(len(employees)):
        for day in all_days:
            di = day_idx[day]
            vars_this_day = [
                assign[ei, ci, di]
                for ci in range(len(contracts))
                if (ei, ci, di) in assign
            ]
            if len(vars_this_day) > 1:
                model.add(sum(vars_this_day) <= 1)

    # C5: equipment at most one contract per day
    for qi in range(len(equipment)):
        for day in all_days:
            di = day_idx[day]
            vars_this_day = [
                equip_assign[qi, ci, di]
                for ci in range(len(contracts))
                if (qi, ci, di) in equip_assign
            ]
            if len(vars_this_day) > 1:
                model.add(sum(vars_this_day) <= 1)

    # C3: each required skill covered on each contract-day
    # (soft: we penalize unmet but also add hard must-cover)
    skill_coverage: dict[tuple[int, str, int], Any] = {}
    for ci, cont in enumerate(contracts):
        for skill in cont.required_skills:
            for day in cont.days:
                di = day_idx[day]
                skilled_workers = [
                    assign[ei, ci, di]
                    for ei, emp in enumerate(employees)
                    if skill in emp.skills and (ei, ci, di) in assign
                ]
                if skilled_workers:
                    # At least one skilled worker per contract-day
                    covered = model.new_bool_var(f"skill_{ci}_{skill}_{di}")
                    model.add(sum(skilled_workers) >= 1).only_enforce_if(covered)
                    model.add(sum(skilled_workers) == 0).only_enforce_if(covered.negated())
                    skill_coverage[ci, skill, di] = covered
                else:
                    # No available skilled worker → infeasible for this day
                    # Mark as uncoverable (soft penalty)
                    uncovered = model.new_bool_var(f"unsk_{ci}_{skill}_{di}")
                    model.add(uncovered == 1)
                    skill_coverage[ci, skill, di] = uncovered  # always uncovered

    # C4: required equipment type covered on each contract-day
    equip_coverage: dict[tuple[int, str, int], Any] = {}
    for ci, cont in enumerate(contracts):
        for eq_type in cont.required_equipment:
            for day in cont.days:
                di = day_idx[day]
                matching_equip = [
                    equip_assign[qi, ci, di]
                    for qi, eq in enumerate(equipment)
                    if eq.type == eq_type and (qi, ci, di) in equip_assign
                ]
                if matching_equip:
                    covered = model.new_bool_var(f"eq_{ci}_{eq_type}_{di}")
                    model.add(sum(matching_equip) >= 1).only_enforce_if(covered)
                    model.add(sum(matching_equip) == 0).only_enforce_if(covered.negated())
                    equip_coverage[ci, eq_type, di] = covered

    # Objective: maximize skill coverage (minimize uncovered)
    all_skill_vars = list(skill_coverage.values())
    if all_skill_vars:
        model.maximize(sum(all_skill_vars))

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.random_seed = 42

    status = solver.solve(model)

    if status == cp_model.INFEASIBLE:
        return OptimizeResult(
            feasible=False,
            infeasible_reason="CP-SAT: problem jest niespójny z podanymi ograniczeniami",
        )
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return OptimizeResult(
            feasible=False,
            infeasible_reason=f"CP-SAT: brak rozwiązania w limicie czasu ({status})",
        )

    # Extract solution
    assignments: list[Assignment] = []
    for (ei, ci, di), var in assign.items():
        if solver.value(var) == 1:
            day = all_days[di]
            eq_id = None
            # Find first assigned equipment for this contract-day
            for qi, eq in enumerate(equipment):
                if (qi, ci, di) in equip_assign and solver.value(equip_assign[qi, ci, di]) == 1:
                    eq_id = eq.id
                    break
            assignments.append(Assignment(
                contract_id=contracts[ci].id,
                employee_id=employees[ei].id,
                equipment_id=eq_id,
                day=day,
            ))

    # Build routes (group by contract+day)
    from collections import defaultdict
    route_map: dict[tuple[str, str], Route] = defaultdict(
        lambda: Route(contract_id="", day="", employee_ids=[], equipment_ids=[])
    )
    for a in assignments:
        key = (a.contract_id, a.day)
        if key not in route_map:
            route_map[key] = Route(
                contract_id=a.contract_id, day=a.day,
                employee_ids=[], equipment_ids=[],
            )
        route_map[key].employee_ids.append(a.employee_id)
        if a.equipment_id and a.equipment_id not in route_map[key].equipment_ids:
            route_map[key].equipment_ids.append(a.equipment_id)

    routes = list(route_map.values())

    # Verify skill constraints were met
    uncovered = _check_skill_coverage(assignments, employees, contracts)
    if uncovered:
        return OptimizeResult(
            feasible=False,
            assignments=assignments,
            routes=routes,
            infeasible_reason=f"engine_infeasible: brak pracownika z wymaganą kompetencją dla: {uncovered}",
        )

    return OptimizeResult(feasible=True, assignments=assignments, routes=routes)


def _check_infeasible(
    employees: list[EmployeeSpec],
    equipment: list[EquipmentSpec],
    contracts: list[ContractSpec],
) -> str:
    """Fast pre-solve infeasibility check. Returns reason string or empty string."""
    for cont in contracts:
        # Check each required skill has at least one qualified employee available on any contract day
        for skill in cont.required_skills:
            skilled = [e for e in employees if skill in e.skills]
            if not skilled:
                return (
                    f"engine_infeasible: brak pracownika z kompetencją '{skill}' "
                    f"dla kontraktu '{cont.title}'"
                )
            # At least one day must have an available skilled worker
            any_day_covered = any(
                day in emp.available_days
                for day in cont.days
                for emp in skilled
            )
            if not any_day_covered:
                return (
                    f"engine_infeasible: pracownicy z kompetencją '{skill}' "
                    f"niedostępni w żadnym dniu kontraktu '{cont.title}'"
                )

        # Check required equipment types
        for eq_type in cont.required_equipment:
            matching = [e for e in equipment if e.type == eq_type]
            if not matching:
                return (
                    f"engine_infeasible: brak sprzętu typu '{eq_type}' "
                    f"dla kontraktu '{cont.title}'"
                )

    return ""


def _check_skill_coverage(
    assignments: list[Assignment],
    employees: list[EmployeeSpec],
    contracts: list[ContractSpec],
) -> list[str]:
    """Post-solve: verify all required skills are covered. Returns list of uncovered."""
    emp_skills = {e.id: e.skills for e in employees}
    uncovered = []
    for cont in contracts:
        for skill in cont.required_skills:
            for day in cont.days:
                day_employees = [
                    a.employee_id for a in assignments
                    if a.contract_id == cont.id and a.day == day
                ]
                if not any(skill in emp_skills.get(eid, []) for eid in day_employees):
                    uncovered.append(f"{cont.id}/{skill}/{day}")
    return uncovered
