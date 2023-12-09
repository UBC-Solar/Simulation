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

# < ---- Globals ---- >

pbar: tqdm.tqdm
os_type: str
arch_type: str
is_windows: bool
libraries_directory: str


def _build_compile_lib_cmd() -> str:
    """

    Obtain the command to build main libraries, automatically resolving file paths.

    :return: command to build main libraries as a string.

    """

    cmd = CMD_BUILD_LIB + f"{pathlib.Path(__file__).parent}/simulation/library/go_files/main.go"
    return cmd


def _build_compile_perlin_noise_cmd() -> str:
    """

    Obtain the command to build Perlin noise libraries, automatically resolving file paths.

    :return: command to build Perlin noise libraries as a string.

    """

    cmd = CMD_BUILD_PERLIN + f"{pathlib.Path(__file__).parent}/simulation/library/go_files/perlin_noise/main.go "
    cmd += f"{pathlib.Path(__file__).parent}/simulation/library/go_files/perlin_noise/perlinNoise.go "
    cmd += f"{pathlib.Path(__file__).parent}/simulation/library/go_files/perlin_noise/vector.go "
    cmd += f"{pathlib.Path(__file__).parent}/simulation/library/go_files/perlin_noise/simplexNoise.go"
    return cmd


def _str_to_cmd(cmd: str) -> list[str]:
    """

    Transform a string representing a command into a format that can be used by Subprocess.Run.

    :param cmd: the command to be converted
    :return: a list of strings

    """

    return cmd.split()


def _check_go_compiler() -> bool:
    """

    Verify that the Go compiler is installed and accessible.

    :return: a boolean indicating whether the Go compiler is available.

    """

    print("Trying to find Go compiler...\n")
    try:
        # Check if the 'go' command is available by running 'go version'
        result = subprocess.run(_str_to_cmd(CMD_GET_COMPILER), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=True, text=True)
        print(f"Go Version: {result.stdout}")
        return True

    except FileNotFoundError:
        print("Go compiler is not found or not installed.\n")
        return False

    except subprocess.CalledProcessError as e:
        print(f"Error occurred while checking for Go compiler: {e}")
        return False


def _compile() -> bool:
    """

    Compile main and Perlin noise libraries.

    :return: a boolean indicating success or failure

    """

    print("Beginning to compile libraries!\n")

    # Get build commands
    cmd_build_lib = _build_compile_lib_cmd()
    cmd_build_perlin_lib = _build_compile_perlin_noise_cmd()
    pbar.update(1)

    _get_dependencies()
    pbar.update(1)

    try:
        # Try to compile
        # check=True is intentionally missing because we don't want to throw an error right away
        result_lib = subprocess.run(cmd_build_lib, shell=True)
        pbar.update(1)

        result_perlin = subprocess.run(cmd_build_perlin_lib, shell=True)
        pbar.update(1)

        if result_lib.returncode == 0 and result_perlin.returncode == 0:
            return True

        else:
            # Try adding os_type and arch_type specifiers
            cmd_build_lib = f"GOOS={os_type} GOARCH={arch_type}" + cmd_build_lib
            cmd_build_perlin_lib = f"GOOS={os_type} GOARCH={arch_type}" + cmd_build_perlin_lib

            result_lib = subprocess.run(cmd_build_lib, shell=True)
            pbar.update(1)

            result_perlin = subprocess.run(cmd_build_perlin_lib, shell=True)
            pbar.update(1)

            if result_lib.returncode == 0 and result_perlin == 0:
                return True

            else:
                # Try adding CGO_ENABLED=1
                # check=True is enabled here because we do want to throw an error – we've got nothing else to try
                cmd_build_lib = "CGO_ENABLED=1" + cmd_build_lib
                cmd_build_perlin_lib = "CGO_ENABLED=1" + cmd_build_perlin_lib

                result_lib = subprocess.run(cmd_build_lib, shell=True, check=True)
                pbar.update(1)

                result_perlin = subprocess.run(cmd_build_perlin_lib, shell=True, check=True)
                pbar.update(1)

                return result_lib.returncode == 0 and result_perlin == 0

    except subprocess.CalledProcessError as e:
        print(f"Compilation has failed: {e}\n")
        exit(EXIT_COMPILATION_FAILED_ERROR)


def _get_dependencies() -> None:
    """

    Install Go dependencies.

    """

    print("Acquiring dependencies...\n")
    try:
        for dependency in DEPENDENCIES:
            subprocess.run(_str_to_cmd(CMD_GET_DEPENDENCY + dependency), check=True)
            pbar.update(1)

    except subprocess.CalledProcessError as e:
        print(f"Could not acquire dependency: {e}\n")
        exit(EXIT_DEPENDENCY_FAILURE)

    print("Dependencies acquired!\n")


def _get_keypair() -> tuple[str, str]:
    """

    Obtain the platform and CPU architecture that we are operating from.

    :return: a tuple of two strings, the first indicating the platform, and the second the CPU architecture

    """

    print("Identifying target architecture...\n")
    try:
        result = subprocess.run(_str_to_cmd(CMD_GET_COMPILER), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=True, text=True)
        pbar.update(1)

        out: list[str] = result.stdout.split()

        try:
            # The third word should be the two strings we need
            keypair = out[3]
            keys = keypair.split('/')
            print(f"Identified architecture as: {keys[0]}_{keys[1]}\n")
            pbar.update(1)

            return keys[0], keys[1]

        except IndexError:
            print("Could not identify architecture!\n")
            exit(EXIT_COMPATIBILITY_ERROR)

    except subprocess.CalledProcessError as e:
        print(f"Error occurred while finding target architecture: {e}.\n")
        exit(EXIT_PROCESS_ERROR)


def _search_for_libraries() -> bool:
    """

    Search the appropriate directory to check whether compatible libraries already exist.

    :return: a boolean indicating if compatible binaries were found or not

    """

    print(f"Searching for compatible libraries in {os_type}_{arch_type}...\n")
    try:
        # Get the directory where compatible libraries should be located
        path_to_libraries: str = libraries_directory

        # Check if they exist and are compatible, throwing an OSError if either is not true
        ctypes.cdll.LoadLibrary(f"{path_to_libraries}/main.so")
        pbar.update(1)

        ctypes.cdll.LoadLibrary(f"{path_to_libraries}/perlin_noise.so")
        pbar.update(1)

        return True

    except OSError:
        # If an error has occurred, then they don't exist or aren't compatible.
        return False


def _get_libraries_directory() -> str:
    """

    Obtain the path to the directory where compatible libraries should be located.

    :return: a string representing a filepath from ~/ to the appropriate directory.

    """

    return f"{pathlib.Path(__file__).parent}/simulation/library/binaries/{os_type}_{arch_type}"


def _make_destination_directory() -> bool:
    """

    Create the directory for compatible binaries to be stored.

    Will benignly fail if the directory already exists.

    :return: True if the directory already exists or was created

    """

    cmd: str = CMD_MAKE_DIR_WINDOWS if is_windows else CMD_MAKE_DIR_UNIX + libraries_directory

    try:
        # Desirably, directory already existing will NOT cause an error to be thrown which
        # means we do not have to explicitly handle that case.
        subprocess.run(_str_to_cmd(cmd))
        pbar.update(1)

    except subprocess.CalledProcessError as e:
        print(f"Failed to create directory: {e}.\n")
        exit(EXIT_OS_ERROR)

    return True


def _move_to_directory() -> bool:
    """

    Move the newly compiled libraries into their destination directory.

    :return: boolean indicating success or failure, where True indicates success

    """
    print("Beginning move to library directory...\n")

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
    """

    Move a file to its destination directory.

    :param filename: file to be moved. Must include filetype extension!

    """

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
        print(f"Failed while moving: {e}")
        exit(EXIT_OS_ERROR)


def main():
    global pbar
    pbar = tqdm.tqdm(total=15, file=sys.stdout, desc="Building libraries", position=0, leave=True)

    try:
        print("Beginning build of Go libraries...\n")
        pbar.update(1)

        # Verify that we can compile Go
        if _check_go_compiler():
            print("Found Go compiler!\n")
            pbar.update(1)

        global os_type
        global arch_type
        os_type, arch_type = _get_keypair()

        global is_windows
        is_windows = os_type == "windows"

        global libraries_directory
        libraries_directory = _get_libraries_directory()
        pbar.update(1)

        if not _search_for_libraries():
            print(f"Did not find compatible libraries in {os_type}_{arch_type}.\n")

            if not _compile():
                print("Compilation has failed!")
                exit(EXIT_COMPILATION_FAILED_ERROR)

            else:
                print("Compilation successful!\n")

            if not _move_to_directory():
                print("Failed to move libraries to directory!")
                exit(EXIT_OS_ERROR)

            else:
                print("Moved libraries to directory!")

        else:
            print("Found compatible libraries! Compilation is not necessary.\n")

    except SystemExit as e:
        print("Aborting compilation of libraries!\n")
        exit(e.code)

    pbar.n = 15
    pbar.refresh()
    pbar.close()

    del libraries_directory
    del is_windows
    del arch_type
    del os_type
    del pbar

    print("Build successful!")


if __name__ == "__main__":
    main()
