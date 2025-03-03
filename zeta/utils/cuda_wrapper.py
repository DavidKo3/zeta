import os
import subprocess

import torch

# from setuptools import setup
from torch.utils.cpp_extension import (
    CUDA_HOME,
)  # , BuildExtension, CUDAExtension

# ninja build does not work unless include_dirs are abs path
this_dir = os.path.dirname(os.path.abspath(__file__))


def get_cuda_bare_metal_version(cuda_dir: str):
    """
    Retrieves the bare metal version of CUDA installed in the specified directory.

    Args:
        cuda_dir (str): The directory where CUDA is installed.

    Returns:
        tuple: A tuple containing the raw output of the command, the major version of the bare metal CUDA, and the minor version of the bare metal CUDA.
    """
    raw_output = subprocess.check_output(
        [cuda_dir + "/bin/nvcc", "-V"], universal_newlines=True
    )
    output = raw_output.split()
    release_idx = output.index("release") + 1
    release = output[release_idx].split(".")
    bare_metal_major = release[0]
    bare_metal_minor = release[1][0]

    return raw_output, bare_metal_major, bare_metal_minor


def check_cuda_torch_binary_vs_bare_metal(cuda_dir: str):
    """
    Compares the version of CUDA used to compile PyTorch binaries with the version
    of CUDA used to compile CUDA extensions. Raises a RuntimeError if there is a
    version mismatch.

    Args:
        cuda_dir (str): The directory path where CUDA is installed.

    Raises:
        RuntimeError: If the version of CUDA used to compile CUDA extensions does
            not match the version used to compile PyTorch binaries.

    Returns:
        None
    """
    (
        raw_output,
        bare_metal_major,
        bare_metal_minor,
    ) = get_cuda_bare_metal_version(cuda_dir)
    torch_binary_major = torch.version.cuda.split(".")[0]
    torch_binary_minor = torch.version.cuda.split(".")[1]

    print("\nCompiling cuda extensions with")
    print(raw_output + "from " + cuda_dir + "/bin\n")

    if (bare_metal_major != torch_binary_major) or (
        bare_metal_minor != torch_binary_minor
    ):
        raise RuntimeError(
            "Cuda extensions are being compiled with a version of Cuda that"
            " does not match the version used to compile Pytorch binaries. "
            " Pytorch binaries were compiled with Cuda {}.\n".format(
                torch.version.cuda
            )
            + "In some cases, a minor-version mismatch will not cause later"
            " errors: "
            " https://github.com/NVIDIA/apex/pull/323#discussion_r287021798. "
            " You can try commenting out this check (at your own risk)."
        )


def raise_if_cuda_home_none(global_option: str) -> None:
    if CUDA_HOME is not None:
        return
    raise RuntimeError(
        f"{global_option} was requested, but nvcc was not found.  Are you sure"
        " your environment has nvcc available?  If you're installing within a"
        " container from https://hub.docker.com/r/pytorch/pytorch, only images"
        " whose names contain 'devel' will provide nvcc."
    )


def append_nvcc_threads(nvcc_extra_args):
    _, bare_metal_major, bare_metal_minor = get_cuda_bare_metal_version(
        CUDA_HOME
    )
    if int(bare_metal_major) >= 11 and int(bare_metal_minor) >= 2:
        return nvcc_extra_args + ["--threads", "4"]
    return nvcc_extra_args


def check_cuda():
    if not torch.cuda.is_available():
        # https://github.com/NVIDIA/apex/issues/486
        # Extension builds after https://github.com/pytorch/pytorch/pull/23408 attempt to query torch.cuda.get_device_capability(),
        # which will fail if you are compiling in an environment without visible GPUs (e.g. during an nvidia-docker build command).
        print(
            "\nWarning: Torch did not find available GPUs on this system.\n",
            (
                "If your intention is to cross-compile, this is not an"
                " error.\nBy default, Apex will cross-compile for Pascal"
                " (compute capabilities 6.0, 6.1, 6.2),\nVolta (compute"
                " capability 7.0), Turing (compute capability 7.5),\nand, if"
                " the CUDA version is >= 11.0, Ampere (compute capability"
                " 8.0).\nIf you wish to cross-compile for a single specific"
                ' architecture,\nexport TORCH_CUDA_ARCH_LIST="compute'
                ' capability" before running setup.py.\n'
            ),
        )
        if os.environ.get("TORCH_CUDA_ARCH_LIST", None) is None:
            _, bare_metal_major, bare_metal_minor = get_cuda_bare_metal_version(
                CUDA_HOME
            )
            if int(bare_metal_major) == 11:
                os.environ["TORCH_CUDA_ARCH_LIST"] = "6.0;6.1;6.2;7.0;7.5;8.0"
                if int(bare_metal_minor) > 0:
                    os.environ["TORCH_CUDA_ARCH_LIST"] = (
                        "6.0;6.1;6.2;7.0;7.5;8.0;8.6"
                    )
            else:
                os.environ["TORCH_CUDA_ARCH_LIST"] = "6.0;6.1;6.2;7.0;7.5"


# print("\n\ntorch.__version__  = {}\n\n".format(torch.__version__))
# TORCH_MAJOR = int(torch.__version__.split(".")[0])
# TORCH_MINOR = int(torch.__version__.split(".")[1])

# cmdclass = {}
# ext_modules = []

# raise_if_cuda_home_none("flashmm")
# # Check, if CUDA11 is installed for compute capability 8.0
# cc_flag = []
# # cc_flag.append("-gencode")
# # cc_flag.append("arch=compute_70,code=sm_70")
# cc_flag.append("-gencode")
# cc_flag.append("arch=compute_80,code=sm_80")

# ext_modules.append(
#     CUDAExtension(
#         'flashmm', [
#             'flash_mm.cpp',
#             'mm_block_fwd_cuda.cu',
#             'hyena_filter_cuda.cu',
#         ],
#         extra_compile_args={'cxx': ['-g', '-march=native', '-funroll-loops'],
#                             'nvcc': ['-O3', '--threads', '4', '-lineinfo', '--use_fast_math', '-std=c++17', '-arch=compute_70']
#         # extra_compile_args={'cxx': ['-O3'],
#         #                     'nvcc': append_nvcc_threads(['-O3', '-lineinfo', '--use_fast_math', '-std=c++17'] + cc_flag)
#                             },
#         include_dirs=[os.path.join(this_dir, 'mathdx/22.02/include')],
#     )
# )

# torch.utils.cpp_extension.COMMON_NVCC_FLAGS.remove('-D__CUDA_NO_HALF2_OPERATORS__')

# setup(
#     name="flashmm",
#     version="0.1",
#     description="Fast modules for Monarch Mixer block",
#     ext_modules=ext_modules,
#     cmdclass={"build_ext": BuildExtension} if ext_modules else {},
# )
