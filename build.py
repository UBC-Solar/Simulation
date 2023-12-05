import subprocess
import pathlib
import ctypes
import sys
import tqdm

"""

This script is responsible for finding and building Go shared libraries.

"""

# < ---- Commands ---- >

CMD_GET_COMPILER = "go version"
CMD_BUILD_LIB = "go build -o main.so -buildmode=c-shared "
CMD_BUILD_PERLIN = "go build -o perlin_noise.so -buildmode=c-shared "
CMD_MOVE_UNIX = "mv "
CMD_MOVE_WINDOWS = "move /y "
CMD_GET_DEPENDENCY = "go get "
CMD_MAKE_DIR_UNIX = "mkdir "
CMD_MAKE_DIR_WINDOWS = "lmkdir "

# < ---- Messages ---- >

MSG_BEGIN_BUILD = "Beginning build of Go libraries...\n"
MSG_BEGIN_IDENTIFY = "Trying to find Go compiler...\n"
MSG_FOUND_COMPILER = "Found Go compiler!\n"
MSG_ABORT = "Aborting compilation of libraries!\n"
MSG_COMPILER_NOT_FOUND = "Go compiler is not found or not installed.\n"
MSG_ERROR_WHILE_FINDING_COMPILER = "Error occurred while checking for Go compiler"
MSG_ERROR_WHILE_FINDING_ARCHITECTURE = "Error occurred while finding target architecture"
MSG_BEGIN_ARCH_FIND = "Identifying target architecture...\n"
MSG_FAILED_FIND_ARCH = "Could not identify architecture!\n"
MSG_FOUND_ARCH = "Identified architecture as: "
MSG_SEARCHING_FOR_LIBRARIES = "Searching for compatible libraries in "
MSG_FOUND_LIBRARIES = "Found compatible libraries! Compilation is not necessary.\n"
MSG_DIDNT_FIND_LIBRARIES = "Did not find compatible libraries in "
MSG_BEGIN_COMPILE = "Beginning to compile libraries!\n"
MSG_COMPILATION_FAILED = "Compilation has failed"
MSG_COMPILATION_SUCCESS = "Compilation successful!\n"
MSG_BEGIN_MOVE = "Beginning move to library directory...\n"
MSG_MOVED = "Moved "
MSG_GET_DEPENDENCIES = "Acquiring dependencies...\n"
MSG_GOT_DEPENDENCIES = "Dependencies acquired!\n"
MSG_FAILED_DEPENDENCY = "Could not acquire dependency "
MSG_FAILED_MOVE = "Failed while moving "
MSG_FAILED_DIRECTORY_CREATION = "Failed to create directory "
MSG_MOVE_SUCCESS = "Moved libraries to directory!"
MSG_SUCCESS = "Build successful!"

# < ---- Exit Codes ---- >

EXIT_GRACEFUL = 0  # Exit code for when the script has completed successfully
EXIT_PROCESS_ERROR = 1  # Exit code for when a subprocess has failed
EXIT_OS_ERROR = 2  # Exit code for when an OS error occurs
EXIT_COMPATIBILITY_ERROR = 3  # Exit code for when this script is used on an incompatible system
EXIT_COMPILATION_FAILED_ERROR = 4  # Exit code for when compilation fails
EXIT_MOVED_FAILED_ERROR = 5  # Exit code for when moving fails
EXIT_DEPENDENCY_FAILURE = 6  # Exit code for when acquiring a dependency fails

# < ---- Go Dependencies ---- >
go_parallel = "github.com/dgravesa/go-parallel/parallel"
DEPENDENCIES: list[str] = [go_parallel]


def _build_compile_lib_cmd() -> str:
    cmd = CMD_BUILD_LIB + f"{pathlib.Path(__file__).parent}/simulation/library/go_files/main.go"
    return cmd


def _build_compile_perlin_noise_cmd() -> str:
    cmd = CMD_BUILD_PERLIN + f"{pathlib.Path(__file__).parent}/simulation/library/go_files/perlin_noise/main.go "
    cmd += f"{pathlib.Path(__file__).parent}/simulation/library/go_files/perlin_noise/perlinNoise.go "
    cmd += f"{pathlib.Path(__file__).parent}/simulation/library/go_files/perlin_noise/vector.go "
    cmd += f"{pathlib.Path(__file__).parent}/simulation/library/go_files/perlin_noise/simplexNoise.go"
    return cmd


def _str_to_cmd(cmd: str) -> list[str]:
    return cmd.split()


def _check_go_compiler() -> bool:
    print(MSG_BEGIN_IDENTIFY)
    try:
        # Check if the 'go' command is available by running 'go version'
        result = subprocess.run(_str_to_cmd(CMD_GET_COMPILER), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=True, text=True)
        print(f"Go Version: {result.stdout}")
        return True

    except FileNotFoundError:
        print(MSG_COMPILER_NOT_FOUND)
        return False

    except subprocess.CalledProcessError as e:
        print(f"{MSG_ERROR_WHILE_FINDING_COMPILER}: {e}")
        return False


def _compile(keypair: tuple[str, str]) -> bool:
    print(MSG_BEGIN_COMPILE)

    cmd_build_lib = _build_compile_lib_cmd()
    cmd_build_perlin_lib = _build_compile_perlin_noise_cmd()
    pbar.update(1)

    _get_dependencies()
    pbar.update(1)

    try:
        result_lib = subprocess.run(cmd_build_lib, shell=True)
        pbar.update(1)

        result_perlin = subprocess.run(cmd_build_perlin_lib, shell=True)
        pbar.update(1)

        if result_lib.returncode == 0 and result_perlin.returncode == 0:
            return True

        else:
            cmd_build_lib = f"GOOS={keypair[0]} GOARCH={keypair[1]}" + cmd_build_lib
            cmd_build_perlin_lib = f"GOOS={keypair[0]} GOARCH={keypair[1]}" + cmd_build_perlin_lib
            result_lib = subprocess.run(cmd_build_lib, shell=True)
            pbar.update(1)

            result_perlin = subprocess.run(cmd_build_perlin_lib, shell=True)
            pbar.update(1)

            if result_lib.returncode == 0 and result_perlin == 0:
                return True

            else:
                cmd_build_lib = "CGO_ENABLED=1" + cmd_build_lib
                cmd_build_perlin_lib = "CGO_ENABLED=1" + cmd_build_perlin_lib

                result_lib = subprocess.run(cmd_build_lib, shell=True)
                pbar.update(1)

                result_perlin = subprocess.run(cmd_build_perlin_lib, shell=True)
                pbar.update(1)

                return result_lib.returncode == 0 and result_perlin == 0

    except subprocess.CalledProcessError as e:
        print(f"{MSG_COMPILATION_FAILED}: {e}\n")
        exit(EXIT_COMPILATION_FAILED_ERROR)


def _get_dependencies():
    print(MSG_GET_DEPENDENCIES)
    try:
        for dependency in DEPENDENCIES:
            subprocess.run(_str_to_cmd(CMD_GET_DEPENDENCY + dependency), check=True)
            pbar.update(1)

    except subprocess.CalledProcessError as e:
        print(f"{MSG_FAILED_DEPENDENCY}: {e}\n")
        exit(EXIT_DEPENDENCY_FAILURE)

    print(MSG_GOT_DEPENDENCIES)


def _get_keypair() -> tuple[str, str]:
    print(MSG_BEGIN_ARCH_FIND)
    try:
        result = subprocess.run(_str_to_cmd(CMD_GET_COMPILER), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=True, text=True)
        pbar.update(1)

        out: str = result.stdout
        out_split: list[str] = out.split()

        try:
            keypair = out_split[3]
            keys = keypair.split('/')
            print(MSG_FOUND_ARCH + f" {keys[0]}_{keys[1]}\n")
            pbar.update(1)

            return keys[0], keys[1]

        except IndexError:
            print(MSG_FAILED_FIND_ARCH)
            exit(EXIT_COMPATIBILITY_ERROR)

    except subprocess.CalledProcessError as e:
        print(f"{MSG_ERROR_WHILE_FINDING_ARCHITECTURE}: {e}.\n")
        exit(EXIT_PROCESS_ERROR)


def _search_for_libraries(keypair: tuple[str, str]) -> bool:
    print(MSG_SEARCHING_FOR_LIBRARIES + keypair[0] + "_" + keypair[1] + "...\n")
    try:
        # Get the directory of potential libraries
        path_to_libraries: str = libraries_directory

        # Check if they exist and are compatible
        ctypes.cdll.LoadLibrary(f"{path_to_libraries}/main.so")
        pbar.update(1)

        ctypes.cdll.LoadLibrary(f"{path_to_libraries}/perlin_noise.so")
        pbar.update(1)

        return True

    except OSError:
        # If an error has occurred, then they don't exist or aren't compatible.
        return False


def _get_libraries_directory(keypair: tuple[str, str]) -> str:
    return f"{pathlib.Path(__file__).parent}/simulation/library/binaries/{keypair[0]}_{keypair[1]}"


def _make_destination_directory():
    cmd: str = CMD_MAKE_DIR_WINDOWS if is_windows else CMD_MAKE_DIR_UNIX + libraries_directory

    try:
        subprocess.run(_str_to_cmd(cmd))
        pbar.update(1)

    except subprocess.CalledProcessError as e:
        print(f"{MSG_FAILED_DIRECTORY_CREATION}: {e}.\n")
        exit(EXIT_OS_ERROR)

    return True


def _move_to_directory() -> bool:
    print(MSG_BEGIN_MOVE)

    if not _make_destination_directory():
        return False

    _move("main.h")
    pbar.update(1)

    _move("main.so")
    pbar.update(1)

    _move("perlin_noise.h")
    pbar.update(1)

    _move("perlin_noise.so")
    pbar.update(1)

    return True


def _move(filename: str):
    if is_windows:
        cmd = CMD_MOVE_WINDOWS
    else:
        cmd = CMD_MOVE_UNIX

    cmd += f"{filename} "
    cmd += libraries_directory

    try:
        subprocess.run(_str_to_cmd(cmd), check=True)
        print(f"Moved {filename}!\n")

    except subprocess.CalledProcessError as e:
        print(f"{MSG_FAILED_MOVE}: {e}")
        exit(EXIT_OS_ERROR)


def main():
    global pbar
    pbar = tqdm.tqdm(total=15, file=sys.stdout, desc="Building libraries", position=0, leave=True)

    try:
        print(MSG_BEGIN_BUILD)
        pbar.update(1)

        if _check_go_compiler():
            print(MSG_FOUND_COMPILER)
            pbar.update(1)

        os_type, arch_type = _get_keypair()

        global is_windows
        is_windows = os_type == "windows"

        global libraries_directory
        libraries_directory = _get_libraries_directory((os_type, arch_type))
        pbar.update(1)

        if not _search_for_libraries((os_type, arch_type)):
            print(MSG_DIDNT_FIND_LIBRARIES + os_type + "_" + arch_type + ".\n")

            if not _compile((os_type, arch_type)):
                print(MSG_COMPILATION_FAILED)
                exit(EXIT_COMPILATION_FAILED_ERROR)

            else:
                print(MSG_COMPILATION_SUCCESS)

            if not _move_to_directory():
                print(MSG_FAILED_MOVE)
                exit(EXIT_OS_ERROR)

            else:
                print(MSG_MOVE_SUCCESS)

        else:
            print(MSG_FOUND_LIBRARIES)

    except SystemExit as e:
        print(MSG_ABORT)
        exit(e.code)

    pbar.n = 15
    pbar.refresh()
    pbar.close()
    print(MSG_SUCCESS)


if __name__ == "__main__":
    main()
