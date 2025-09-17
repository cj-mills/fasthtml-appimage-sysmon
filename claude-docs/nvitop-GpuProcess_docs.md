Here is the `nvitop.GpuProcess` documentation converted to Markdown, focusing on the Python API usage.

---

# `class nvitop.GpuProcess`

Represents a process with a given PID running on a specific GPU device.

```python
class nvitop.GpuProcess(
    pid: int | None,
    device: nvitop.Device,
    *,
    gpu_memory: int | nvitop.NaType | None = None,
    gpu_instance_id: int | nvitop.NaType | None = None,
    compute_instance_id: int | nvitop.NaType | None = None,
    type: str | nvitop.NaType | None = None
)
```

The `GpuProcess` instance is cached for the lifetime of the process. A single host process can use multiple GPUs, and the `GpuProcess` instances for the same PID on different devices are distinct objects.

Many attributes of the host process (like `username`, `cpu_percent`, `cmdline`, etc.) are accessed directly through the `GpuProcess` object.

## Properties

#### `pid: int`
The process ID.

#### `host: nvitop.HostProcess`
The underlying `HostProcess` instance running on the host system.

#### `device: nvitop.Device`
The `Device` object representing the GPU this process is running on.

#### `type: str | nvitop.NaType`
The type of the GPU context. Can be one of the following:
- `'C'`: Compute context
- `'G'`: Graphics context
- `'C+G'`: Both compute and graphics context
- `'N/A'`: Not applicable

---

## Methods

### GPU-Specific Information

#### `gpu_memory() -> int | nvitop.NaType`
Returns the used GPU memory in bytes, or `nvitop.NA` if not applicable.

#### `gpu_memory_human() -> str | nvitop.NaType`
Returns the used GPU memory in a human-readable format (e.g., "1024 MiB"), or `nvitop.NA`.

#### `gpu_memory_percent() -> float | nvitop.NaType`
Returns the percentage of GPU memory used by the process, or `nvitop.NA`.

#### `gpu_sm_utilization() -> int | nvitop.NaType`
Returns the utilization rate (%) of the Streaming Multiprocessor (SM), or `nvitop.NA`.

#### `gpu_memory_utilization() -> int | nvitop.NaType`
Returns the utilization rate (%) of the GPU memory bandwidth, or `nvitop.NA`.

#### `gpu_encoder_utilization() -> int | nvitop.NaType`
Returns the utilization rate (%) of the video encoder, or `nvitop.NA`.

#### `gpu_decoder_utilization() -> int | nvitop.NaType`
Returns the utilization rate (%) of the video decoder, or `nvitop.NA`.

#### `gpu_instance_id() -> int | nvitop.NaType`
The GPU instance ID of the MIG device, or `nvitop.NA` if not applicable.

#### `compute_instance_id() -> int | nvitop.NaType`
The compute instance ID of the MIG device, or `nvitop.NA` if not applicable.

---

### Host Process Information

These methods query the underlying host process. If the process has terminated or permissions are insufficient, they will raise an exception.

> **Note**: To prevent exceptions and receive a fallback value (`nvitop.NA`) instead, wrap your calls in the `GpuProcess.failsafe()` context manager. This is especially useful when dealing with short-lived processes.

**Common Exceptions:**
- `nvitop.host.NoSuchProcess`: The process no longer exists.
- `nvitop.host.AccessDenied`: Insufficient privileges to read the process's status.

#### `is_running() -> bool`
Returns `True` if the process is currently running.

#### `status() -> str`
Returns the current status of the process (e.g., 'running', 'sleeping').

#### `username() -> str | nvitop.NaType`
Returns the name of the user that owns the process.

#### `name() -> str | nvitop.NaType`
Returns the process name.

#### `cmdline() -> list[str]`
Returns the command line used to launch the process as a list of strings.

#### `command() -> str`
Returns the shell-escaped command line string.

#### `cpu_percent() -> float | nvitop.NaType`
Returns the process's current CPU utilization as a percentage.

#### `host_memory() -> int | nvitop.NaType`
Returns the process's Resident Set Size (RSS) memory usage in bytes.

#### `host_memory_human() -> str | nvitop.NaType`
Returns the process's RSS memory in a human-readable format.

#### `host_memory_percent() -> float | nvitop.NaType`
Returns the process's memory utilization as a percentage of total system memory.

#### `create_time() -> float | nvitop.NaType`
Returns the process creation time as seconds since the epoch.

#### `running_time() -> datetime.timedelta | nvitop.NaType`
Returns the elapsed time the process has been running as a `timedelta` object. (Alias: `elapsed_time()`)

#### `running_time_human() -> str | nvitop.NaType`
Returns the elapsed running time in a human-readable format. (Alias: `elapsed_time_human()`)

#### `running_time_in_seconds() -> float | nvitop.NaType`
Returns the elapsed running time in seconds. (Alias: `elapsed_time_in_seconds()`)

---

### Snapshots & Failsafe Context

#### `as_snapshot() -> nvitop.Snapshot`
Returns a one-time snapshot of the process's state on the GPU device. For performance, prefer the batched version `take_snapshots()`.

#### `take_snapshots(gpu_processes, *, failsafe=False) -> list[nvitop.Snapshot]`
*(classmethod)*
Takes snapshots for a list of `GpuProcess` instances efficiently. If `failsafe` is `True`, any failing method calls will return a fallback value instead of raising an exception.

#### `failsafe() -> Generator[None]`
*(classmethod)*
A context manager that enables fallback values for methods that would otherwise fail (e.g., on a terminated process). Instead of raising an exception, methods will return `nvitop.NA`.

**Example:**
```python
import nvitop
# Assume pid 10000 does not exist
p = nvitop.GpuProcess(pid=10000, device=nvitop.Device(0))

try:
    p.cpu_percent()
except nvitop.host.NoSuchProcess as e:
    print(e)
    # >>> process no longer exists (pid=10000)

# Use failsafe() to avoid the exception
with nvitop.GpuProcess.failsafe():
    cpu = p.cpu_percent()
    print(f"CPU percent: {cpu!r}")
    # >>> CPU percent: 'N/A'
    
    # nvitop.NA can be cast to float or int
    print(f"As float: {float(cpu)}")  # nan
    print(f"As int:   {int(cpu)}")    # 0
```