import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

from .backtest import run_backtest

_WORKER_DATA = {}


def _init_worker(df, htf_dfs):
    _WORKER_DATA["df"] = df
    _WORKER_DATA["htf_dfs"] = htf_dfs


def run_case(case):
    params = {key: value for key, value in case.items() if key != "name"}
    if _WORKER_DATA:
        params.setdefault("df", _WORKER_DATA.get("df"))
        params.setdefault("htf_dfs", _WORKER_DATA.get("htf_dfs"))
    result = run_backtest(**params)
    trades = result["trades"]
    yearly = {}
    for trade in trades:
        year = trade["entry_time"][:4]
        yearly[year] = yearly.get(year, 0.0) + trade["r_multiple"]
    return {
        "name": case.get("name"),
        "params": {
            key: value
            for key, value in params.items()
            if key not in ("df", "htf_dfs")
        },
        "metrics": result["metrics"],
        "total_r": sum(t["r_multiple"] for t in trades),
        "yearly_r": yearly,
    }


def run_cases(cases, workers=4, df=None, htf_dfs=None, verbose=False):
    if workers <= 1:
        results = []
        for case in cases:
            params = dict(case)
            if df is not None:
                params.setdefault("df", df)
            if htf_dfs is not None:
                params.setdefault("htf_dfs", htf_dfs)
            results.append(run_case(params))
            if verbose:
                print(f"[{len(results)}/{len(cases)}] {params.get('name')}")
        return results

    results = []
    context = (
        mp.get_context("fork")
        if "fork" in mp.get_all_start_methods()
        else None
    )
    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_init_worker,
        initargs=(df, htf_dfs),
        mp_context=context,
    ) as executor:
        futures = {
            executor.submit(run_case, case): case.get("name") for case in cases
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result()
            except Exception as err:
                result = {"name": name, "error": repr(err)}
            results.append(result)
            if verbose:
                print(f"[{len(results)}/{len(cases)}] {name}")
    return results
