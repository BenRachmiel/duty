from fastapi import APIRouter

from . import assignments, duties, people, rules, solver, stats, tags

router = APIRouter(prefix="/api")
router.include_router(tags.router)
router.include_router(people.router)
router.include_router(duties.router)
router.include_router(rules.router)
router.include_router(assignments.router)
router.include_router(solver.router)
router.include_router(stats.router)
