"""
The demo's two routes and how seeders find their steps.

New manufacture (Injector Build) and remanufacture (Injector Reman) are separate
processes with separate steps: no step belongs to both. A few names repeat across
them (Final Test, Rework, Nitride Coating), so a step is found *within a process*,
never by its name alone.
"""
from Tracker.models import ProcessStep, Processes

BUILD = 'Injector Build'
REMAN = 'Injector Reman'


def step_key(route, name):
    """The seed's identity for a step: routes keep their own copies of shared names."""
    return f"{route}:{name}"


def process_named(tenant, name):
    return (Processes.objects.filter(tenant=tenant, name=name)
            .order_by('-created_at').first())


def route_steps(process):
    """{step name: step} for one process."""
    if process is None:
        return {}
    return {ps.step.name: ps.step for ps in
            ProcessStep.objects.filter(process=process).select_related('step')}


def build_steps(tenant):
    return route_steps(process_named(tenant, BUILD))


def reman_steps(tenant):
    return route_steps(process_named(tenant, REMAN))
