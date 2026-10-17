"""Filters that turn measured pod usage into requests and limits.

Used by playbooks/measure.yml. Kept in plain Python so the arithmetic can be
read and tested on its own.
"""

import math

_CPU_SUFFIX = {"n": 1e-6, "u": 1e-3, "m": 1.0}
_MEM_BINARY = {"Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40}
_MEM_DECIMAL = {"k": 10**3, "M": 10**6, "G": 10**9, "T": 10**12}

# How measured peaks become requests and limits. Each factor is a headroom
# decision, written down once, instead of a number guessed per service.
POLICY = {
    # Requests reserve what the service was seen to use under load.
    "cpu_request_min_m": 10,
    "cpu_request_step_m": 10,
    "memory_request_factor": 1.25,  # 25% above the measured peak
    "memory_request_min_mi": 32,
    "memory_step_mi": 8,
    # Memory limits stop a leak from taking the node down; the margin covers
    # garbage-collector and start-up peaks that a short measurement can miss.
    "memory_limit_factor": 2.0,
    "memory_limit_min_extra_mi": 64,
    # CPU limits only throttle, they never kill. Keep them generous so that
    # start-up (JVM, .NET) is not slowed down too much.
    "cpu_limit_factor": 4.0,
    "cpu_limit_min_m": 200,
}


def cpu_millicores(quantity):
    """'250m' -> 250.0, '1' -> 1000.0, '123456789n' -> 123.456789."""
    q = str(quantity).strip()
    if q and q[-1] in _CPU_SUFFIX:
        return float(q[:-1]) * _CPU_SUFFIX[q[-1]]
    return float(q) * 1000.0


def memory_mib(quantity):
    """'20480Ki' -> 20.0, '64Mi' -> 64.0, '1Gi' -> 1024.0, '1048576' -> 1.0."""
    q = str(quantity).strip()
    for suffix, factor in _MEM_BINARY.items():
        if q.endswith(suffix):
            return float(q[: -len(suffix)]) * factor / 2**20
    for suffix, factor in _MEM_DECIMAL.items():
        if q.endswith(suffix):
            return float(q[: -len(suffix)]) * factor / 2**20
    return float(q) / 2**20


def peak_usage(samples, apps=None):
    """Highest CPU and memory seen per container over all samples.

    samples: a list of PodMetrics lists, one list per sampling round, as
    returned in the 'resources' field of kubernetes.core.k8s_info.
    apps: if given, only these container names are kept.
    """
    peaks = {}
    for round_ in samples:
        for pod in round_ or []:
            for container in pod.get("containers", []):
                name = container["name"]
                if apps is not None and name not in apps:
                    continue
                usage = container.get("usage", {})
                cpu = cpu_millicores(usage.get("cpu", "0"))
                mem = memory_mib(usage.get("memory", "0"))
                entry = peaks.setdefault(name, {"cpu_m": 0.0, "memory_mi": 0.0, "samples": 0})
                entry["cpu_m"] = max(entry["cpu_m"], cpu)
                entry["memory_mi"] = max(entry["memory_mi"], mem)
                entry["samples"] += 1
    for entry in peaks.values():
        entry["cpu_m"] = round(entry["cpu_m"], 1)
        entry["memory_mi"] = round(entry["memory_mi"], 1)
    return peaks


def _round_up(value, step):
    return int(math.ceil(value / step) * step)


def recommend_resources(peaks):
    """Requests and limits for each container, from its measured peak."""
    p = POLICY
    result = {}
    for name, peak in sorted(peaks.items()):
        cpu_req = max(_round_up(peak["cpu_m"], p["cpu_request_step_m"]), p["cpu_request_min_m"])
        mem_req = max(
            _round_up(peak["memory_mi"] * p["memory_request_factor"], p["memory_step_mi"]),
            p["memory_request_min_mi"],
        )
        mem_lim = _round_up(
            max(mem_req * p["memory_limit_factor"], mem_req + p["memory_limit_min_extra_mi"]),
            p["memory_step_mi"],
        )
        cpu_lim = max(_round_up(cpu_req * p["cpu_limit_factor"], p["cpu_request_step_m"]), p["cpu_limit_min_m"])
        result[name] = {
            "requests": {"cpu": "%dm" % cpu_req, "memory": "%dMi" % mem_req},
            "limits": {"cpu": "%dm" % cpu_lim, "memory": "%dMi" % mem_lim},
        }
    return result


class FilterModule(object):
    def filters(self):
        return {
            "k8s_cpu_millicores": cpu_millicores,
            "k8s_memory_mib": memory_mib,
            "k8s_peak_usage": peak_usage,
            "k8s_recommend_resources": recommend_resources,
        }