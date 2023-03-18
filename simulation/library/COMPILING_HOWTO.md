# Compiling binaries for your OS


## Guidelines
To compile Go binaries for your operating system if they don't already 
exist so that your instance of Simulation can use GoLang 
implementations, compile **all the .go files** in this folder. If you only compile some of the Go files, problems will definitely occur.
Here is how this generally may be done.\
You may need to search StackOverflow or similar for instructions for your specific OS and platform.

In your terminal and in this directory: \
`GOOS={Your operating system}`\
`go build -o *.so buildmode=c-shared *.go`\
You will need to replace *both* `*` with go file names in seperate commands for each file. 
You may also need to include: \
`GOARCH=amd64` \
and/or\
`CGO_ENABLED=1`

Once `.so` and `.h` files have been compiled, they should be placed into a new folder inside of `library/binaries` 
so that Simulation can find them.

## Example
Compiling on M1 Mac requires the following commands to compile weather_in_time_loop.so:\
`GOOS=darwin GOARCH=amd64 CGO_ENABLED=1 go build -o weather_in_time_loop.so -buildmode=c-shared weather_in_time_loop.go` 
