# Compiling libraries for your OS

This document describes how to manually compile Go libraries. You should attempt to build automatically with `build.py` script first.

## Guidelines
To achieve a significant performance improvement, Simulation uses
multiple Go implementations of Pythonic functions that cannot be sped up 
with NumPy. However, Go shared libraries are platform and architecture dependent so 
you may need to build the shared libraries for your platform if they do not already exist.
Begin by building `main.so` from `main.go` in the `go_files` folder. 
Next, build the `perlin_noise.so` module from the four `.go` files in `go_files/perlin_noise`.

````bash
cd go_files
go build -o main.so -buildmode=c-shared main.go
cd perlin_noise
go build -o perlin_noise.so -buildmode=c-shared main.go vector.go perlinNoise.go simplexNoise.go
````
You may need to specify that CGO should be enabled. You may need to specify your operating system and CPU architecture. You'll need to add these flags in the command before `go build -o...`For macOS with Apple Silicon chip,
````bash
 GOARCH=arm64 GOOS=darwin CGO_ENABLED=1
````

See https://www.digitalocean.com/community/tutorials/building-go-applications-for-different-operating-systems-and-architectures
for a list of keypairs for different operating systems and architectures and how to find yours.

Once `.so` and `.h` files have been compiled, they should be placed into a new folder inside of `library/binaries` 
so that Simulation can find them. Name the folder according to your OS and architecture. As an example, libraries 
compiled for MacOS (`darwin`) on Apple Silicon (`arm64`) should live in `library/binaries/darwin_arm64`.

## Example
Compiling on Apple Silicon Mac requires the following commands to compile `go_files/main.go`:\
`GOOS=darwin GOARCH=amd64 CGO_ENABLED=1 go build -o main.so -buildmode=c-shared main.go` 