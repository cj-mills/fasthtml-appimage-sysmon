Here is the documentation for `nvitop.Device` converted to Markdown.

---

# `class nvitop.Device`

A live representation of a GPU device, which can be either a physical GPU or a virtualized MIG (Multi-Instance GPU) device.

```python
class nvitop.Device(
    index: int | tuple[int, int] | str | None = None,
    *,
    uuid: str | None = None,
    bus_id: str | None = None
)
```

The constructor returns different types of device objects based on the provided identifier. You must provide exactly one of the following arguments:

-   `index: int` -> `PhysicalDevice`
-   `index: tuple[int, int]` -> `MigDevice`
-   `uuid: str` -> `PhysicalDevice` or `MigDevice` (depending on the UUID format)
-   `bus_id: str` -> `PhysicalDevice`

**Example:**
```python
import nvitop

# Get a physical device by its index
nvidia0 = nvitop.Device(index=0)

# Get a MIG device by its physical and instance index
mig1_0 = nvitop.Device(index=(1, 0))

# Get a device by its UUID
nvidia2 = nvitop.Device(uuid='GPU-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx')
```

**Common Exceptions:**
-   `nvitop.NVMLError_LibraryNotFound`: The NVIDIA driver is not installed.
-   `nvitop.NVMLError_DriverNotLoaded`: The NVIDIA driver is not loaded.
-   `nvitop.NVMLError_NotFound`: The specified device could not be found.
-   `TypeError`: More than one identifier (e.g., both `index` and `uuid`) was provided.

---

## Class and Static Methods

#### `is_available() -> bool`
*(classmethod)*
Returns `True` if the NVML library is loaded and at least one NVIDIA device is present.

#### `driver_version() -> str | nvitop.NaType`
*(static)*
Returns the version of the installed NVIDIA display driver (e.g., `'510.47.03'`).

#### `cuda_driver_version() -> str | nvitop.NaType`
*(static)*
Returns the maximum CUDA version supported by the installed driver (e.g., `'11.6'`). (Alias: `max_cuda_version()`)

#### `cuda_runtime_version() -> str | nvitop.NaType`
*(static)*
Returns the version of the installed CUDA Runtime, which can differ from the driver's supported version. Returns `nvitop.NA` if the runtime is not found. (Alias: `cudart_version()`)

#### `count() -> int`
*(classmethod)*
Returns the total number of physical NVIDIA GPUs in the system.

#### `all() -> list[nvitop.PhysicalDevice]`
*(classmethod)*
Returns a list of all physical `Device` instances in the system.

#### `from_indices(indices) -> list[Device]`
*(classmethod)*
Returns a list of device instances from a given list of indices.

#### `from_cuda_visible_devices() -> list[nvitop.CudaDevice]`
*(static)*
Returns a list of `CudaDevice` instances based on the `CUDA_VISIBLE_DEVICES` environment variable.

---

## Properties

#### `index: int | tuple[int, int]`
The NVML index of the device. Returns an `int` for a physical device or a `tuple[int, int]` for a MIG device. (Alias: `nvml_index`)

#### `physical_index: int`
The index of the parent physical device. For a `PhysicalDevice`, this is its own index. For a `MigDevice`, this is the index of the GPU it belongs to.

#### `cuda_index: int`
The CUDA ordinal of the device, corresponding to its position in `CUDA_VISIBLE_DEVICES`. Raises a `RuntimeError` if the device is not visible to CUDA.

#### `uuid(): str | nvitop.NaType`
The globally unique, immutable identifier for the GPU.

#### `bus_id(): str | nvitop.NaType`
The PCI bus ID of the device in the format `domain:bus:device.function`.

---

## Instance Methods

### Device Information
#### `name() -> str | nvitop.NaType`
The product name of the GPU (e.g., "NVIDIA GeForce RTX 3090").

#### `is_mig_device() -> bool`
Returns `True` if this is a MIG (Multi-Instance GPU) device.

#### `mig_mode() -> str | nvitop.NaType`
Returns `'Enabled'` or `'Disabled'` to indicate if MIG mode is active.

#### `mig_devices() -> list[nvitop.MigDevice]`
Returns a list of child MIG device instances. Returns an empty list if MIG mode is not enabled.

#### `compute_mode() -> str | nvitop.NaType`
Returns the current compute mode (e.g., 'Default', 'Exclusive Process').

#### `cuda_compute_capability() -> tuple[int, int] | nvitop.NaType`
Returns the CUDA compute capability as a `(major, minor)` tuple (e.g., `(8, 6)`).

---

### Memory Usage
#### `memory_total() -> int | nvitop.NaType`
Total installed GPU memory in bytes.

#### `memory_used() -> int | nvitop.NaType`
Total GPU memory used by active contexts in bytes.

#### `memory_free() -> int | nvitop.NaType`
Total free GPU memory in bytes.

#### `memory_percent() -> float | nvitop.NaType`
The percentage of used GPU memory.

#### `memory_info() -> MemoryInfo`
Returns a named tuple `(total, free, used)` with memory values in bytes.

#### `memory_usage() -> str`
Returns a human-readable string of used/total memory (e.g., `'8192MiB / 24576MiB'`).

> **Note**: `_human` suffixed methods are also available (e.g., `memory_total_human()`) to get formatted strings like `'8.0 GiB'`.

---

### Utilization Rates
#### `gpu_utilization() -> int | nvitop.NaType`
GPU utilization rate as a percentage. (Alias: `gpu_percent()`)

#### `memory_utilization() -> int | nvitop.NaType`
Memory bandwidth utilization rate as a percentage.

#### `encoder_utilization() -> int | nvitop.NaType`
Video encoder utilization rate as a percentage.

#### `decoder_utilization() -> int | nvitop.NaType`
Video decoder utilization rate as a percentage.

#### `utilization_rates() -> UtilizationRates`
Returns a named tuple `(gpu, memory, encoder, decoder)` with all utilization rates.

---

### Temperature, Power, and Fans
#### `temperature() -> int | nvitop.NaType`
Core GPU temperature in degrees Celsius.

#### `fan_speed() -> int | nvitop.NaType`
Fan speed as a percentage of its maximum.

#### `power_usage() -> int | nvitop.NaType`
Current power draw in milliwatts. (Alias: `power_draw()`)

#### `power_limit() -> int | nvitop.NaType`
The configured power limit in milliwatts.

#### `power_status() -> str`
Returns a human-readable string of usage/limit in watts (e.g., `'150W / 350W'`).

---

### Processes
#### `processes() -> dict[int, nvitop.GpuProcess]`
Returns a dictionary of all processes running on this device, mapping PID to the `GpuProcess` object.

---

### Snapshots & Performance
#### `as_snapshot() -> nvitop.Snapshot`
Takes a one-time snapshot of the device's current state, capturing all metrics at once.

#### `oneshot() -> Generator[None]`
A context manager that caches device metrics to significantly speed up multiple queries. All metric calls within the `with` block will use the same cached data.

**Example:**
```python
device = nvitop.Device(0)

# Efficiently get multiple metrics
with device.oneshot():
    mem_used = device.memory_used_human()   # First call fetches and caches data
    gpu_util = device.gpu_utilization()     # Subsequent calls are near-instant
    temp = device.temperature()

print(f"Memory Used: {mem_used}, GPU Util: {gpu_util}%, Temp: {temp}°C")
```