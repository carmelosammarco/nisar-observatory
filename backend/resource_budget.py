"""Shared metadata admission estimates, not measured peak-RAM quotas."""
import os
from .processing_trace import estimated_snapshot_count


def memory_budget_bytes():
    try:
        budget=int(os.environ.get('NISAR_MEMORY_BUDGET_MB','3072'))*1024**2
        if budget<=0:raise ValueError()
    except ValueError:raise ValueError('NISAR_MEMORY_BUDGET_MB must be a positive integer in MiB.') from None
    return budget


def assess_resources(items,grid,steps=(),root=None):
    """No science reads or storage mutations; used before queue admission.

    Retains the established conservative grid-array allowance for reproducible
    readiness. Native input windows, library workspaces and exports are outside
    this estimate; a passing report is not proof of available OS RAM.
    """
    from .storage_budget import storage_status
    if root is None:
        from .access import DATA
        root=DATA
    cells=int(grid['shape'][0])*int(grid['shape'][1])
    trace_maps=estimated_snapshot_count(steps,items);trace_bytes=cells*trace_maps*4
    estimated=cells*(max(len(items),1)*12+16)*8+trace_bytes
    budget=memory_budget_bytes();errors=[];checks=[]
    if trace_maps:checks.append({'label':'Intermediate map allowance','value':f"{trace_maps} additional float32 map{'s' if trace_maps!=1 else ''} estimated · {trace_bytes/1024**2:.1f} MiB; latest per viewing group/component"})
    if estimated>budget:errors.append(f'Estimated grid working memory {estimated/1024**2:.0f} MiB exceeds the {budget/1024**2:.0f} MiB budget. Select fewer sources, a smaller area or coarser cells.')
    disk=storage_status(root)
    checks.append({'label':'Free runtime disk space','value':f"{disk['free_bytes']/1024**3:.2f} GiB free · {disk['reserve_bytes']/1024**2:.0f} MiB safety reserve"})
    if not disk['fits']:errors.append('Runtime disk space is below the safety reserve. Free space or choose another NISAR_DATA_DIR before processing. Saved data is kept.')
    checks.append({'label':'Estimated grid working memory','value':f'{estimated/1024**2:.0f} MiB · excludes native reads, export and library overhead'})
    return {'ready':not errors,'scope':'metadata resource estimate; not a RAM reservation or whole-process peak limit','errors':errors,'warnings':['Free disk space is checked again before array and export writes. Other applications can consume space after this check.'],'checks':checks,'disk_space':disk,'estimated_trace_bytes':trace_bytes,'estimated_trace_maps':trace_maps,'estimated_grid_bytes':estimated,'memory_budget_bytes':budget}


def require_resources(items,grid,steps=(),root=None):
    report=assess_resources(items,grid,steps,root)
    if not report['ready']:raise ValueError(' '.join(report['errors']))
    return report
